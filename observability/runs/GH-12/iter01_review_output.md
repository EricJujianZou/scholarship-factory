I have enough to complete the review. Test execution is blocked by permission mode, so I'm relying on the test-stage evidence (31 passed, criteria mapped) plus my own code read — and I verified the relative-date math by hand (Jan 1 2024 = Monday → next Friday = Jan 5; Jun 1 2024 = Saturday → next Friday = Jun 7, matching the assertions).

## Review — GH-12 (deterministic S6 date-parse layer)

**Lens 1 — intent (acceptance criteria, one by one):**
1. `"June 1st, and October 1st"` + 2024 anchor → `[2024-06-01, 2024-10-01]` uncollapsed — `test_multi_deadline_not_collapsed` asserts the exact 2-element ordered list. ✓
2. Relative expression resolves against anchor, not today — `test_relative_expression_resolves_against_anchor_not_today` runs the *same* string against two anchors and asserts two distinct dates (`2024-01-05` vs `2024-06-07`), which is the correct proof that the system clock is never used. ✓
3. Unparseable/absent → `None`; computed → `derived`, unresolvable → `none`, never guessed — `test_unparseable_or_absent_returns_none` + three `test_typed_deadlines_*` provenance tests. The deterministic boundary (empty→`None`, no-match→`None`) self-enforces no-fabrication. ✓
4. Deterministic + offline, four cases covered — `languages=["en"]` + `search_dates` only, no network/LLM; `RETURN_AS_TIMEZONE_AWARE=False` keeps output stable. ✓
5. `uv run pytest -q` green — test stage reports 31 passed. ✓

**Lens 2 — quality & security:** `parse_deadline_dates` guards empty/whitespace, dedups preserving first-seen order, returns `None` (not `[]`) when empty. `_parse_anchor` correctly tries `datetime.fromisoformat` first (handles the store's `+00:00` ISO format on Python ≥3.11) then falls back to `dateparser.parse`. `typed_deadlines` honors the locked anchor precedence (`source_observed_date` → `first_seen`) and maps non-empty→`DERIVED` else `NONE`. No store mutation, no ranking — scope respected. No injection/secret/subprocess surface; offline library. No dead code. Clean.

**Lens 3 — visual:** Not applicable — this ticket is a pure library module (`parse_dates.py`) with no user-facing surface. Nothing to render.

The uncommitted changes in the tree (`state.json`, `iter01_test.json/_output.md`) are harness-managed observability/state artifacts, not code; the code diff (`parse_dates.py`, `__init__.py`, `pyproject.toml`, `tests/`) is committed and complete.

All three lenses hold; every criterion verified against test evidence.

```json
{
  "stage": "review",
  "ticket_id": "GH-12",
  "outcome": "success",
  "exit_signal": true,
  "summary": "Deterministic S6 date-parse layer verified across all three lenses: pure parse_deadline_dates(text, anchor) over dateparser.search_dates + read-only typed_deadlines(opp) provenance helper. All 5 acceptance criteria backed by concrete tests (multi-deadline uncollapsed, relative-vs-anchor proven via two-anchor divergence, absolute date, unresolvable->None/derived provenance); 31 tests pass. No user-facing surface, so visual lens is N/A. Code clean, offline, no fabrication. Clean-first solve of the deterministic-parse-layer class — candidate for a skills/ entry.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds the deterministic date-parse layer for Session 6 (date half only; money is a separate ticket). New module scholarship_factory/parse_dates.py turns the verbatim stored `deadline` string into typed absolute date(s) with no LLM and no network.\n\nWhat changed:\n- parse_deadline_dates(text, anchor) -> list[date] | None: pure function over dateparser.search_dates. Resolves relative expressions (e.g. \"closes Friday\") against the passed anchor via RELATIVE_BASE (never the system clock), returns multiple dates for multi-deadline strings uncollapsed (e.g. \"June 1st, and October 1st\"), dedups preserving order, and returns None when nothing resolves.\n- typed_deadlines(opp) -> (dates, Provenance): read-only helper deriving the anchor from source_observed_date, falling back to first_seen; DERIVED when a value is computed, NONE otherwise. No store mutation, no ranking.\n- Adds `dateparser` dependency (uv.lock updated; tzdata comes transitively for Windows zoneinfo).\n\nTradeoffs/risks: search_dates can over-match very noisy strings; the plan documents that we keep languages=[\"en\"] and would filter month/weekday-less matches rather than comma-split (which would wrongly break \"September 15, 2024\"). PREFER_DATES_FROM=\"future\" means a yearless month resolves into the anchor's year only when the anchor precedes it — correct for the deadline-after-anchor invariant. Unresolvable input always yields None/`none` provenance by design — the layer never guesses a date."
}
```