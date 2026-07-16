I have what I need. One important finding to flag up front: **the ticket's design text and acceptance criterion 4 contradict each other**, and I've resolved it rather than reporting blocked — details in the plan's Approach and Risks.

## Context

- `scholarship_factory/store.py:77` `insert()` is the only write path (`pipeline.py:93` is its sole non-test caller). Today a URL-dedup hit does `ON CONFLICT(normalized_apply_url) DO UPDATE SET last_seen` — it refreshes `last_seen` and **discards every fact on the incoming record**.
- `scholarship_factory/models.py:13` `Opportunity` carries three fact *triples* (`deadline`/`deadline_provenance`/`deadline_source`, same for `reward`/`cost`) with a validator at `models.py:42` requiring `<fact>_source` whenever provenance ≠ `none`. A merge must move each triple atomically or the model raises.
- `scholarship_factory/urls.py:6` `normalize_apply_url` is the existing primary key and stays untouched (AC1 is a pure regression guard).
- `REPO_CONTENT.md:110` locks: "On a dedup hit, the store refreshes only `last_seen`. Field-level refresh on re-sight is the refresh session's job." This constrains the merge policy but does not forbid null-filling — see Approach.
- No `progress.txt` and no `skills/` in this repo; `skill_match` is null.

## Approach

Put the identity probe and merge policy in a new `identity.py` and consult them at the **top of `store.insert()`**, so every caller (pipeline and tests) gets dedup for free with no pipeline change. On an identity hit, `insert` delegates to the existing `store.update()`, which already writes `last_seen = now`, preserves `first_seen` (excluded from its SET clause at `store.py:124`), and keys off `id` — so the merged record needs no new SQL. `find_duplicate` scans `store.list()` in Python rather than adding normalized title/org columns: new columns would require an `ALTER TABLE` migration for databases created under the old schema (`CREATE TABLE IF NOT EXISTS` will not add them, and every read would then fail on a missing column), which is a real cost against an O(n) scan over a v1 corpus of hundreds of rows. That's the alternative I rejected.

**The contradiction, and how I resolved it.** The ticket's design says a URL hit keeps "existing behavior", but AC4 requires a thin listing item followed by its rich detail record *at the same normalized URL* to yield one row **carrying the detail facts** — which existing behavior actively throws away. AC4 is unsatisfiable under a literal reading of the design bullet, so the two cannot both hold. I resolved it in favor of AC4: **both** the URL hit and the secondary-title+org hit run the same `merge_into`. This does not violate `REPO_CONTENT.md:110`, because that line governs *refresh* (a fact whose value changed), and the merge policy explicitly keeps the existing value on any non-null conflict. Only null→non-null filling happens here. If the reviewer disagrees, the disagreement is with AC4, not with this plan.

## Steps

1. Create `scholarship_factory/identity.py` with `normalize_text(value: str | None) -> str | None` — lowercase, replace non-alphanumeric with a space (`re.sub(r"[^\w\s]", " ", ...)`), collapse whitespace, strip; return `None` for `None` or a string that folds to empty — done when `normalize_text("The  Smith-Jones Fund!") == "the smith jones fund"` and `normalize_text("  --  ") is None`.
2. Add `merge_into(existing, incoming) -> Opportunity` in `identity.py` — for each triple in `(("deadline", "deadline_provenance", "deadline_source"), ("reward", ...), ("cost", ...))`, copy all three fields from `incoming` **only when `existing`'s value field is `None`**; for each of `("organization", "requirements", "type", "description", "source_observed_date")` fill only when existing is `None`; keep `existing`'s `id`, `first_seen`, `title`, `apply_url`, `source_url`, `owner`, `status` unconditionally. Return `existing.model_copy(update=...)` — done when merging a fact-bearing incoming into a null-fact existing yields the incoming triple intact, and merging two conflicting non-null deadlines returns the existing one.
3. Add `find_duplicate(store, opportunity) -> Opportunity | None` in `identity.py` — first return any row whose `normalize_apply_url(row.apply_url)` equals the incoming's; else, only if `normalize_text(title)` **and** `normalize_text(organization)` are both non-`None` on the incoming, return the first row matching both; else `None`. Import `OpportunityStore` under `TYPE_CHECKING` only, to avoid the `store` ↔ `identity` import cycle — done when the module imports cleanly and a same-title/different-org pair returns `None`.
4. Wire `scholarship_factory/store.py:77` `insert()` — at the top, `existing = find_duplicate(self, opp)`; if not `None`, `return self.update(merge_into(existing, opp))`; otherwise fall through to the current INSERT unchanged. Leave the `ON CONFLICT` clause at `store.py:93` in place as-is (unreachable now, harmless, and not mine to remove) — done when `uv run pytest -q tests/test_store.py tests/test_pipeline.py` is green.
5. Export `find_duplicate` and `merge_into` from `scholarship_factory/__init__.py` following the existing alphabetized-import + `__all__` convention at `__init__.py:1-59` — done when `from scholarship_factory import find_duplicate, merge_into` works.
6. Create `tests/test_identity.py` covering the five criteria below, using a `tmp_path` sqlite db and a local `make_opp` helper mirroring `tests/test_store.py:4` — done when `uv run pytest -q` is green.

## Acceptance criteria mapping

- "Two records with different `apply_url`s (tracking params vs clean) still dedup via URL normalization (regression guard)." -> steps 3, 4; verified by the existing `tests/test_store.py:39` `test_dedup_tracking_param` staying green, plus a new `test_url_dedup_still_merges_one_row`.
- "Two records with different hosts but identical normalized title + organization -> ONE stored row; the merged row has the union of facts (null filled from incoming), `last_seen` refreshed, and no existing non-null fact overwritten." -> steps 1, 2, 3, 4; verified by `test_secondary_match_merges_union_of_facts` asserting `len(store.list()) == 1`, incoming's deadline triple present, existing's conflicting non-null reward unchanged, and `last_seen >= first_seen`.
- "Same title but different organization -> two rows (no merge). Same org, different title -> two rows." -> step 3; verified by `test_same_title_different_org_does_not_merge` and `test_same_org_different_title_does_not_merge`, each asserting `len(store.list()) == 2`.
- "A thin listing item (title+url only) followed by its rich detail record (same normalized apply_url) -> one row carrying the detail facts." -> steps 2, 4; verified by `test_thin_then_detail_same_url_carries_detail_facts` asserting one row whose `deadline`/`deadline_source` come from the detail record (and whose `title` stays the thin item's, per the non-null-conflict policy).
- "All tests offline, temp db; `uv run pytest -q` green." -> step 6; verified by `uv run pytest -q` — every test constructs `Opportunity` objects directly and touches no network.

## Risks

1. **The AC4 contradiction is a judgment call.** If a reviewer reads the design bullet's "existing behavior" literally, step 4's merge-on-URL-hit looks like scope creep. It isn't optional: AC4 fails without it. If challenged, the narrower fallback is to merge only when the existing row's fact is `None` **and** the row was never fact-bearing — but that is strictly more complexity for the same observable outcome, so don't take it unless AC4 itself is rewritten.
2. **The fact triple must move together.** Copying `deadline` without `deadline_source` trips the validator at `models.py:42` and raises `ValueError` at merge time, not at test time. If you see that error, you have split a triple — key the copy on the *value* field being `None` and move all three.
3. **`pipeline.py:100` counts `opportunities_stored=len(opportunities)`, i.e. records extracted, not rows written.** Merging makes that count diverge from the store's row count more often. `test_pipeline.py:167` asserts `report.opportunities_stored == 2` and will still pass, since nothing in the pipeline tests sets a non-null `organization` (so no secondary match can fire). Leave the counter alone — changing its meaning is not in this ticket; mention it if a reviewer asks.

```json
{
  "stage": "plan",
  "ticket_id": "GH-42",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan: new identity.py (normalize_text, merge_into, find_duplicate) consulted at the top of store.insert(), reusing the existing update() for the merged write. Resolved a real contradiction between the ticket's 'URL hit -> existing behavior' design text and AC4, which requires URL hits to merge facts; resolved in favor of AC4 (null-fill only, never overwrite a non-null fact), which stays consistent with REPO_CONTENT.md:110.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/identity.py",
      "scholarship_factory/store.py:77",
      "scholarship_factory/__init__.py:1",
      "tests/test_identity.py"
    ],
    "read": [
      "scholarship_factory/models.py:13",
      "scholarship_factory/models.py:42",
      "scholarship_factory/urls.py:6",
      "scholarship_factory/pipeline.py:93",
      "scholarship_factory/traverse.py:90",
      "tests/test_store.py:39",
      "tests/test_pipeline.py:170",
      "tests/test_pipeline.py:245",
      "REPO_CONTENT.md:110"
    ]
  }
}
```