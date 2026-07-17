Working tree is now clean.

```json
{
  "stage": "implement",
  "ticket_id": "GH-42",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Added scholarship_factory/identity.py (normalize_text, find_duplicate, merge_into), wired store.insert() to consult it before writing; URL hits and secondary title+organization hits both merge via update() with null-fill-only field merging. 131 tests pass including 8 new in tests/test_identity.py. Committed state.json/observability logs to satisfy clean-tree gate.",
  "failure_reason": null,
  "files_changed": 3,
  "suggested_tools": [],
  "system_repair_suggested": false
}
```