I have completed all three review lenses. Let me record my verdict.

## Review — GH-12: deterministic date-parse layer (S6)

**Lens 1 — intent (all 5 ACs against test evidence):**
- *Multi-deadline uncollapsed* — `test_multi_deadline_not_collapsed` asserts `[date(2024,6,1), date(2024,10,1)]` (order-preserving, 2 elements). ✓
- *Relative resolves against anchor, not today* — `test_relative_..._not_today` runs the same `"closes Friday"` against two anchors and asserts distinct results (Jan-5 vs Jun-7); driven by `settings["RELATIVE_BASE"]`, never the system clock. Manually confirmed: 2024-01-01 is a Monday → Fri Jan 5; 2024-06-01 is a Saturday → Fri Jun 7. ✓
- *Unresolvable → None; computed → `derived`, else `none`, never guessed* — empty/whitespace/None guard + falsy-match guard both return `None`; `typed_deadlines` maps non-empty → `DERIVED`, else `NONE`. Covered by the `None` test and both provenance tests. ✓
- *Deterministic + offline, 4 cases* — `dateparser` only, `languages=["en"]` (no language autodetect), no network/LLM/subprocess. All four case types present. ✓
- *`uv run pytest -q` green* — test stage recorded `exit_code: 0`, 31 passed. ✓

**Lens 2 — quality & security:** Pure functions, no store mutation (so the model's `*_source` validator correctly doesn't bind). Anchor parsing is tolerant (`fromisoformat` for stored ISO anchors like `first_seen`, falling back to `dateparser.parse`) — matches how `store.py:78` writes `first_seen`. Dedup preserves first-seen order. No secrets, no unsafe I/O. Both `dateparser` imports are used (`.parse` in `_parse_anchor`, `.search.search_dates` in the main fn). No dead code or empty asserts.

**Lens 3 — visual:** No user-facing surface — this is a pure library layer (module + two exported functions). Nothing to render. Not applicable.

**Note:** I could not execute `uv run pytest`/`python` myself (approval denied in this headless session), so I verified the code logic and every test assertion by reading, and cross-checked the two relative-date claims by hand — all consistent with the test stage's recorded `exit_code: 0` / 31 passed. Working tree is clean apart from the expected run-recording artifacts (`state.json`, `observability/runs/GH-12/*`).

Everything holds.

```json
{
  "stage": "review",
  "ticket_id": "GH-12",
  "outcome": "success",
  "exit_signal": true,
  "summary": "Deterministic S6 date-parse layer: parse_deadline_dates(text, anchor) over dateparser.search_dates + typed_deadlines(opp) provenance helper. All 5 ACs verified against named tests; anchor-relative resolution, multi-deadline uncollapsed, unresolvable->None/derived provenance all correct. Pure/offline, no store mutation. Solved cleanly for the first time — candidate for a 'deterministic-parse-layer' skill.",
  "failure_reason": null,
  "files_changed": 4,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds the deterministic date-parse layer for Session 6 (date half only; money is a separate ticket). New module scholarship_factory/parse_dates.py exposes parse_deadline_dates(text, anchor) -> list[date] | None, built on dateparser.search_dates so absolute, relative, and multi-deadline strings are handled by one mechanism (naive comma-splitting would wrongly break 'September 15, 2024'). Relative expressions resolve against the passed anchor via RELATIVE_BASE (never the system clock), with PREFER_DATES_FROM='future'. A thin typed_deadlines(opp) helper derives the anchor from source_observed_date falling back to first_seen and returns the dates plus derived/none provenance; it returns values only and does not mutate the store. Multi-deadline strings return every date uncollapsed; anything unresolvable returns None (no guessing). Adds the dateparser dependency (pyproject.toml + uv.lock; tzdata pulled transitively for Windows zoneinfo). Tests cover multi-deadline, relative-vs-anchor, absolute-date, and unresolvable/None cases plus the provenance mapping; full suite 31 passed, fully offline. Risk to note for mergers: search_dates can over-match very noisy strings; current AC inputs parse cleanly, but future noisy deadline text may need result filtering — do not fall back to comma-splitting."
}
```