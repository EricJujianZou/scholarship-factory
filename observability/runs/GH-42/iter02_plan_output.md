Verified: the merge path at `store.py:81` delegates to `update()`, which writes a fresh `last_seen`, excludes `first_seen` from its SET clause (`store.py:124`), and keys on `id` — which `model_copy` preserves. So all three of the review's proposed assertions will pass against the current source, and this is genuinely a test-only fix.

## Context

- Retry of iteration 1. The suite is green (131 passed) and the review cleared `scholarship_factory/identity.py` and `scholarship_factory/store.py` as correct; it failed the iteration on **evidence, not behavior**.
- The single defect is `tests/test_identity.py:51`: `assert merged.last_seen >= merged.first_seen`. `insert()` sets `first_seen` and `last_seen` to the same `now` (`store.py:86-87`), so this holds for any row whether or not a merge ever refreshed it. AC2 names "`last_seen` refreshed" explicitly, so that clause currently has no evidence behind it.
- I confirmed the fix is test-only rather than trusting the review: the merge path at `store.py:81` calls `self.update(merge_into(existing, opp))`, and `update()` writes a fresh `last_seen` (`store.py:115`), omits `first_seen` from its SET clause (`store.py:124`), and keys on `id`, which `model_copy` carries over from `existing` (`identity.py:59`). The refresh, the id-stability, and the `first_seen` preservation are all real — only the assertion was weak.
- Nothing else in the iteration-1 plan changes; the design-vs-AC4 contradiction resolution was reviewed and upheld.

## Approach

Rewrite the three closing assertions of `test_secondary_match_merges_union_of_facts` to compare the merged row against the *first insert's returned row* instead of against itself. Binding `first = store.insert(...)` gives a real pre-merge baseline, which turns one vacuous check into three falsifiable ones: `merged.last_seen > first.last_seen` (the refresh actually happened), `merged.id == first.id` (the incoming record merged into the existing row rather than replacing it), and `merged.first_seen == first.first_seen` (the original sighting survived). This is exactly the review's prescription, and I'm following it because it's correct, not merely because it was prescribed. The alternative I rejected was freezing the clock with a `monkeypatch` on `datetime.now` to make the ordering deterministic: it would prove the refresh just as well but would mock out the very code path under test, add a fixture to a suite that has none, and buy nothing — two inserts with a sqlite commit between them are milliseconds apart against a microsecond-resolution `isoformat()`, so `>` is not a flake risk.

## Steps

1. Bind the first insert's return value in `test_secondary_match_merges_union_of_facts` in `tests/test_identity.py:21` — change `store.insert(` to `first = store.insert(` on the first call only, leaving its `make_opp(...)` arguments untouched — done when `first` holds the pre-merge row and the second `store.insert(` at line 31 remains unbound.
2. Replace the vacuous assertion at `tests/test_identity.py:51` with the three real ones — `assert merged.id == first.id`, `assert merged.first_seen == first.first_seen`, `assert merged.last_seen > first.last_seen` — done when the test asserts against `first` rather than against `merged`'s own fields, and no `>=` self-comparison remains.
3. Run `uv run pytest -q` — done when the suite is green at 131 passed, with `tests/test_identity.py` and `tests/test_store.py` unchanged in count.
4. Sanity-check that step 2's assertions can actually fail — done when you have confirmed by reading that `store.py:81` routes merges through `update()`; if `merged.last_seen > first.last_seen` fails, do **not** weaken it back to `>=`, treat it as a real regression in the merge path (see Risks).

## Acceptance criteria mapping

- "Two records with different `apply_url`s (tracking params vs clean) still dedup via URL normalization (regression guard)." -> unchanged from iteration 1; verified by `tests/test_identity.py:12` `test_url_dedup_still_merges_one_row` and the pre-existing `tests/test_store.py:39` `test_dedup_tracking_param`, both re-run in step 3.
- "Two records with different hosts but identical normalized title + organization -> ONE stored row; the merged row has the union of facts (null filled from incoming), `last_seen` refreshed, and no existing non-null fact overwritten." -> steps 1, 2; the row-count, union-of-facts and no-overwrite clauses are verified by the untouched assertions at `tests/test_identity.py:46-50`, and the previously unverified "`last_seen` refreshed" clause is now verified by `assert merged.last_seen > first.last_seen`.
- "Same title but different organization -> two rows (no merge). Same org, different title -> two rows." -> unchanged; verified by `tests/test_identity.py:54` and `tests/test_identity.py:65`, re-run in step 3.
- "A thin listing item (title+url only) followed by its rich detail record (same normalized apply_url) -> one row carrying the detail facts." -> unchanged; verified by `tests/test_identity.py:76` `test_thin_then_detail_same_url_carries_detail_facts`, re-run in step 3.
- "All tests offline, temp db; `uv run pytest -q` green." -> step 3; verified by the full suite. The edited test still uses `tmp_path` and constructs `Opportunity` objects directly, so it stays offline.

## Risks

1. **Over-correcting into the source.** The review cleared `identity.py` and `store.py`, and I independently confirmed the merge path refreshes `last_seen`. If step 3 goes red, the cause is in the test edit, not the store — re-read the edit before touching any source file. Changing `identity.py` or `store.py` in this iteration means something has gone wrong with the diagnosis, not with the code.
2. **Weakening the assertion to make it pass.** `>` is the entire point of the fix; `>=` is what failed review. If `merged.last_seen > first.last_seen` ever fails, the merge path stopped calling `update()` — a genuine regression to investigate at `store.py:81`, not an assertion to relax.
3. **Touching the second insert.** Only the *first* `store.insert(` at line 21 gets bound to `first`. Binding the second as well, or reordering the two inserts, would invert the baseline and make `merged.reward == "$1000"` at line 48 fail, since the existing-wins policy depends on which record lands first.

```json
{
  "stage": "plan",
  "ticket_id": "GH-42",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Retry plan for the single review defect: tests/test_identity.py:51's vacuous `merged.last_seen >= merged.first_seen` is replaced by three real assertions against the first insert's returned row (id stable, first_seen preserved, last_seen strictly refreshed), closing AC2's unverified 'last_seen refreshed' clause. Test-only change, independently confirmed by tracing store.py:81 -> update(), which refreshes last_seen and excludes first_seen; identity.py and store.py stay untouched.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "tests/test_identity.py:21",
      "tests/test_identity.py:51"
    ],
    "read": [
      "scholarship_factory/store.py:78",
      "scholarship_factory/store.py:115",
      "scholarship_factory/store.py:124",
      "scholarship_factory/identity.py:46",
      "scholarship_factory/identity.py:59",
      "tests/test_store.py:4",
      "observability/runs/GH-42/iter01_review_output.md"
    ]
  }
}
```