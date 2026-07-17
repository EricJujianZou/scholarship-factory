Working tree clean, review's requested fix confirmed in place.

```
- criterion: "Two records with different apply_urls (tracking params vs clean) still dedup via URL normalization (regression guard)."
  ran: tests/test_identity.py::test_url_dedup_still_merges_one_row
  result: pass — len(store.list()) == 1

- criterion: "Two records with different hosts but identical normalized title + organization -> ONE stored row; union of facts, last_seen refreshed, no existing non-null fact overwritten."
  ran: tests/test_identity.py::test_secondary_match_merges_union_of_facts
  result: pass — merged.reward == "$1000" (existing kept), merged.deadline == "2026-07-01" (filled), merged.id == first.id, merged.first_seen == first.first_seen, merged.last_seen > first.last_seen (now a real refresh assertion, not the vacuous >= self-comparison flagged in review)

- criterion: "Same title but different organization -> two rows (no merge). Same org, different title -> two rows."
  ran: tests/test_identity.py::test_same_title_different_org_does_not_merge, test_same_org_different_title_does_not_merge
  result: pass — both assert len(store.list()) == 2

- criterion: "A thin listing item (title+url only) followed by its rich detail record (same normalized apply_url) -> one row carrying the detail facts."
  ran: tests/test_identity.py::test_thin_then_detail_same_url_carries_detail_facts
  result: pass — merged.deadline and deadline_source carry the detail facts

- criterion: "All tests offline, temp db; uv run pytest -q green."
  ran: uv run pytest -q
  result: pass — 131 passed in 1.79s
```

```json
{
  "stage": "test",
  "ticket_id": "GH-42",
  "outcome": "success",
  "exit_signal": false,
  "summary": "131 passed. Review's must-fix (vacuous last_seen assertion) confirmed corrected in tests/test_identity.py — all 5 acceptance criteria now have real evidence, including AC2's last_seen-refresh clause.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false
}
```