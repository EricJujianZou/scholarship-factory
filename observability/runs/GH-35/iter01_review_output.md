I have what I need. I couldn't execute the suite (this review session is read-only — `uv run pytest` was denied), so I verified by reading the code and tests against each criterion.

## Lens 1 — intent

The five criteria all have tests that map cleanly and read as correct:

- **AC 1** is covered at both levels: `tests/test_traverse.py:47` asserts each thin item's URL is fetched and that the detail record carries `deadline`, `Provenance.QUOTED`, and `source_url` == detail page; `tests/test_pipeline.py:170` proves the *stored* record keeps the deadline. That second test is the important one, and the design behind it is right — since `store.insert` (`scholarship_factory/store.py:93`) upserts `last_seen` only, thin items are never stored at all, which is what lets the detail's facts land without touching identity logic.
- **AC 2** (`tests/test_traverse.py:93`), **AC 3** (`:119`), and **AC 4** (`:163`, dedup via `normalize_apply_url`) are asserted as specified.
- Depth-1 is correctly enforced structurally: `traverse` ignores the returned `kind` (`scholarship_factory/traverse.py:89`) rather than branching on it, so recursion is impossible by construction rather than bounded by the cap.

**AC 5 is unverified.** The test stage's output file (`observability/runs/GH-35/iter01_test_output.md`) claims "all 5 acceptance criteria verified with quoted evidence" but contains only a status block — there is no evidence in it, quoted or otherwise. I could not re-run the suite myself to compensate.

## Lens 2 — quality & security

One correctness bug, and it's the exact failure mode the plan pre-identified as its top risk.

`_to_opportunity` resolves a thin item's link as `apply_url=item.apply_url or source_url` (`scholarship_factory/extract.py:106`). `LLMItem.apply_url` is `str | None = None`, and the system prompt only says listing items are "typically title + url" — it does not require a url. So a listing item the model returns without a link gets `apply_url` set to **the listing page's own URL**.

That self-link walks straight through `traverse`:

1. `urljoin(listing_url, listing_url)` → the listing URL, not in `seen`, so it gets fetched — a redundant refetch of the page just fetched.
2. `extract_fn` re-extracts the listing, returning `PageKind.LIST` with all its thin items.
3. `traverse` ignores `kind` (correct for depth-1) so those thin items are treated as detail records, reported `ok=True`, and returned.
4. `run_sourcing` stores them.

If the link-less item appears before its siblings in the listing, the thin duplicates are inserted *ahead* of the real detail records; the `last_seen`-only upsert then silently discards the detail's deadline. That is the plan's Risk 1 — "the store shows one record with a `NULL` deadline and no error anywhere" — reachable through ordinary model output, and it contradicts the ticket's locked decision that the detail page's richer facts must be what lands. Nothing in the tests catches it, because every stub supplies an explicit `apply_url`.

The fix is small and belongs in `traverse`, not the store: seed the `seen` set with `normalize_apply_url(listing_url)` (or skip items whose resolved URL normalizes to the listing's), so a self-link is never followed. Note the plan's own warning that the wrong fix here is adding fact-merging to `store.insert`.

No security concerns: no secrets, no subprocess or file handling, fetches are injected, and failures are recorded per-link rather than raised.

## Lens 3 — visual

This ticket has no user-facing surface. The only presentation change is CLI stdout (`scholarship_factory/cli.py:55-63`), which reads correctly against AC 2 — it prints the traversed/discovered totals and a per-target cap line only when `cap_reached`, and prints nothing when no target was traversed. Playwright is not applicable to a CLI, so nothing was skipped for lack of tooling.

## Verdict

Failing on the self-link bug. It's roughly a two-line fix, but it silently corrupts the exact fact AC 1 is about, so it shouldn't merge as-is. The structure of the change is otherwise sound and I'd expect it to pass on the next iteration.

```json
{
  "stage": "review",
  "ticket_id": "GH-35",
  "outcome": "failure",
  "exit_signal": false,
  "summary": "Design is sound (thin items never stored, so detail facts land; depth-1 enforced structurally by ignoring kind). Two blockers: (1) a thin item with no apply_url inherits the listing URL via extract.py:106's `item.apply_url or source_url` fallback, so traverse refetches the listing, treats its thin items as detail records, and stores them - the plan's own Risk 1, silently nulling the deadline AC 1 requires; (2) the test stage recorded zero evidence despite claiming quoted evidence, and this read-only session cannot run pytest, so AC 5 is unverified.",
  "failure_reason": "1. scholarship_factory/traverse.py:62 - self-link traversal. extract.py:106 sets a link-less thin item's apply_url to the listing's own source_url (LLMItem.apply_url is `str | None` and the system prompt does not mandate a url). traverse then urljoins that to the listing URL, fetches the listing again, and since it ignores the returned PageKind (correctly, for depth-1) it treats the listing's thin items as detail records, reports ok=True, and returns them for storage. When the link-less item precedes its siblings, the thin duplicates are inserted before the real detail records and store.py:93's last_seen-only upsert discards the detail's deadline - AC 1 fails silently with no error anywhere. Fix in traverse (NOT by adding fact-merging to store.insert): seed the `seen` set with normalize_apply_url(listing_url), or skip any item whose resolved URL normalizes to the listing URL. 2. tests/test_traverse.py - add a regression case: a LIST result containing one item whose apply_url equals the listing URL must produce zero fetches for that item and no thin records in the output. 3. observability/runs/GH-35/iter01_test_output.md contains only a status block asserting 'all 5 acceptance criteria verified with quoted evidence' while containing none; the test stage must paste actual pytest output so AC 5 is verifiable by a reviewer who cannot execute tests.",
  "files_changed": 6,
  "suggested_tools": [],
  "system_repair_suggested": false
}
```