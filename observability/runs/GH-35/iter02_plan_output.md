The diagnosis is confirmed and narrow. Here's the retry plan.

## Context

Iteration 1 shipped a structurally sound change (6 files, suite green at 122 passed) that the review failed on one real correctness bug, not a design error. The design — thin items are never stored, so the detail extraction's facts land despite `store.py:93`'s `last_seen`-only upsert — is correct and stays.

The bug is at `scholarship_factory/traverse.py:61-67`. `extract.py:106` resolves a thin item as `apply_url=item.apply_url or source_url`, and `LLMItem.apply_url` is `str | None = None` (extract.py:40) with a system prompt that never mandates a url. So a link-less listing item inherits **the listing's own URL**. `traverse` then `urljoin`s that to itself, finds it absent from `seen`, refetches the listing, and — because it correctly ignores the returned `PageKind` for depth-1 (traverse.py:89) — treats the listing's own thin items as detail records and returns them `ok=True` for storage. If that item precedes its siblings, the thin duplicates insert first and the upsert silently discards the detail's deadline: AC 1 fails with no error anywhere.

Iteration 1's plan named this as Risk 1 but guarded only the store side of it, not the self-link entry point. Two of the three blockers are code; the third is test-stage evidence discipline.

## Approach

Seed the `seen` set with `normalize_apply_url(listing_url)` before the loop. This is a one-line fix that makes the existing dedup path do the work: a self-link hits the `key in seen` check at traverse.py:64 and is skipped before any fetch, before `links_discovered` increments, and before it can produce records. It reuses the mechanism already proven by AC 4 rather than adding a parallel guard, and it lands entirely in `traverse` — the review and iteration 1's own plan both flag that the *wrong* fix is teaching `store.insert` to merge facts, since field-level merge is Session 5/8 work.

The rejected alternative was an explicit `if key == normalize_apply_url(listing_url): continue` inside the loop with a `LinkOutcome` recorded for it. That reports the skip, but it adds a second skip concept and, worse, misclassifies: a self-link is not a *link* and not a *failure*, so emitting a per-link outcome for it would inflate the report with a link the listing never actually offered. Silent skip is consistent with how duplicate links are already treated. `links_discovered` counting only real, non-self, deduped links is the honest number.

No signature, model, or pipeline change — iteration 1's `run_sourcing` wiring, report shape, and CLI output all stay as merged.

## Steps

1. **Seed the dedup set** in `scholarship_factory/traverse.py:57` — change `seen: set[str] = set()` to `seen: set[str] = {normalize_apply_url(listing_url)}`. `normalize_apply_url` is already imported (traverse.py:17). Done when a LIST result whose sole item's `apply_url` is the listing URL yields `fetch_fn.calls == []`.
2. **Note the invariant** in `scholarship_factory/traverse.py:1-8` — extend the module docstring with one sentence: a thin item that resolves to the listing itself (extract.py:106's `apply_url or source_url` fallback for a link-less item) is not a link and is skipped. Done when the docstring states why the self-link case exists; this is the one comment worth writing, since the guard's necessity is invisible from `traverse.py` alone.
3. **Add the self-link regression test** to `tests/test_traverse.py` as `test_thin_item_linking_to_listing_itself_is_not_traversed`, reusing the module's existing `make_opp` / `FakeFetch` / `ok_result` / `RecordingExtract` / `no_jsonld` helpers (tests/test_traverse.py:11-44). Build a LIST result whose **first** item is `make_opp("https://example.com/listing", title="Linkless")` (mirroring the fallback, and ordered first because that is the ordering that corrupts the store) and whose second is a real detail link. Pass `FakeFetch` a mapping containing **only** the detail URL — a self-link fetch then raises `KeyError` rather than silently passing. Assert `fetch_fn.calls == ["https://example.com/detail"]`, that no returned opportunity has `title == "Linkless"`, and `report.links_discovered == 1`. Done when this test fails on `git stash` of step 1 and passes with it.
4. **Add the end-to-end guard** to `tests/test_pipeline.py` as `test_listing_item_without_link_does_not_store_thin_record`: seed URL extracts LIST with a link-less first item plus one real thin item; the detail URL extracts DETAIL with a quoted deadline. Assert `store.list()` has exactly one record and it carries the deadline. Done when it passes — this is the assertion that would have caught the bug at the level AC 1 actually cares about (the store), which the traverse-level tests could not.
5. **Run `uv run pytest -q`** — done when the full suite is green (expect 124 passed: iteration 1's 122 plus steps 3 and 4).

## Acceptance criteria mapping

Iteration 1's tests for all five criteria remain and were accepted by the review (test_traverse.py:47, :93, :119, :163; test_pipeline.py:170). This iteration only re-verifies AC 1, whose coverage was defective, and AC 5, which was never evidenced.

- "A stubbed listing extraction with N thin items -> traverse fetches each item URL ... ends up stored WITH that deadline (quoted provenance + source span)" -> steps 1, 3, 4; verified by the existing test_pipeline.py:170 **plus** the new step-4 test, which closes the hole: every iteration-1 stub supplied an explicit `apply_url`, so none exercised the fallback that breaks this criterion.
- "Page cap: with cap=2 and 5 thin items, only 2 detail fetches happen and the report flags the early stop." -> unchanged; verified by existing test_traverse.py:93. Step 1 seeds `seen` with a URL that is not among the 5 items, so the cap counts are unaffected.
- "A detail fetch failure or empty extraction is reported for that link; remaining links still process." -> unchanged; verified by existing test_traverse.py:119.
- "No fetch of the same detail URL twice within one traverse call." -> steps 1, 3; verified by existing test_traverse.py:163 and strengthened by the new self-link case, which is the same dedup mechanism applied to the listing URL.
- "All tests offline with stubbed fetch/extract; `uv run pytest -q` green." -> step 5; verified by pasting the **actual pytest output** into the test stage's output file. The review could not execute tests and iteration 1's `iter01_test_output.md` contained only a status block claiming "verified with quoted evidence" while quoting none — a raw pass/fail line is the only thing that makes this criterion checkable by a non-executing reviewer.

## Risks

1. **Seeding `seen` suppresses a legitimate link that normalizes to the listing URL.** A listing that genuinely lists itself as an opportunity would be skipped. This is the correct trade for v1: `normalize_apply_url` strips only tracking params and trailing slashes (urls.py:6-23), so a collision means the detail page *is* the listing page, and following it would re-enter the depth-1 violation the review documented. If a real fixture later shows this dropping a real opportunity, the fix is at the extract contract (make a listing item's url required, or mark items with no link) — not by loosening this guard.
2. **The implementer "improves" the fix by reporting the skip as a `LinkOutcome`.** That inflates `links_discovered` / `links_traversed` with a link that does not exist, which is the opposite of the ticket's honest-reporting decision and would break the step-3 assertion `links_discovered == 1`. Keep the skip silent, exactly as duplicate links are.
3. **The step-3 test is written with a `FakeFetch` that has a self-link entry mapped.** Then the guard's absence would not raise, the test would pass either way, and the regression is uncaught. Omitting the self-link from the mapping deliberately turns a regression into a `KeyError`. If this test passes with step 1 reverted, it is testing nothing — verify it fails first.

```json
{
  "stage": "plan",
  "ticket_id": "GH-35",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Retry plan for the review's self-link bug: seed traverse's `seen` set with normalize_apply_url(listing_url) so a link-less thin item (which extract.py:106 gives the listing's own URL) is skipped before any fetch, instead of refetching the listing and returning its thin items as detail records. One-line fix plus two regression tests (traverse-level and store-level); iteration 1's design, signatures, and pipeline wiring are unchanged and stay.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/traverse.py:57",
      "scholarship_factory/traverse.py:1",
      "tests/test_traverse.py:44",
      "tests/test_pipeline.py:170"
    ],
    "read": [
      "scholarship_factory/extract.py:40",
      "scholarship_factory/extract.py:106",
      "scholarship_factory/traverse.py:61",
      "scholarship_factory/traverse.py:89",
      "scholarship_factory/store.py:93",
      "scholarship_factory/urls.py:6",
      "scholarship_factory/pipeline.py:72",
      "scholarship_factory/cli.py:55",
      "tests/test_traverse.py:11",
      "observability/runs/GH-35/iter01_review_output.md",
      "observability/runs/GH-35/iter01_test_output.md"
    ]
  }
}
```