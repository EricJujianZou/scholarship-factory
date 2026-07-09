On-branch state confirmed: `parse_dates.py`, `dateparser` dep, exports, and `test_parse_dates.py` all present and matching the prior successful plan. Here is the grounded work order.

## Context

The feature lives in `scholarship_factory/parse_dates.py` (`parse_dates.py:9`) — the only date-parsing code. It reads from `models.py`: `Opportunity.deadline: str | None` (verbatim stored string, GH-1), the anchors `source_observed_date: str | None` (GH-4) and `first_seen: str | None`, and the `Provenance` enum (`QUOTED|DERIVED|NONE`). `store.py` writes `first_seen` as an ISO-8601 string with `+00:00` offset, so the anchor parser must tolerate that. The model's `_require_source_for_provenance` validator binds only on *stored* `*_provenance` fields — this ticket's helper returns values and never persists, so it does not apply. Locked decisions honored: relatives resolve against the stored anchor (never "today"), unresolvable → `None`, computed → `derived`, multi-deadline strings uncollapsed. `dateparser` is present in `pyproject.toml:8` (with transitive `tzdata` for Windows).

## Approach

A pure function `parse_deadline_dates(text, anchor) -> list[date] | None` built on `dateparser.search.search_dates`, which handles absolute, relative, and multi-date strings in one mechanism — critical because naive comma-splitting would wrongly break a single date like `"September 15, 2024"`, while `search_dates` returns one match there and two for `"June 1st, and October 1st"` in appearance order. Relatives resolve via `settings["RELATIVE_BASE"] = datetime.combine(anchor, time.min)` with `PREFER_DATES_FROM="future"` (a deadline is future relative to its anchor), `RETURN_AS_TIMEZONE_AWARE=False`, and `languages=["en"]` for deterministic offline behavior. A thin read-only `typed_deadlines(opp) -> tuple[list[date] | None, Provenance]` derives the anchor (`source_observed_date` → `first_seen`, via a tolerant `_parse_anchor` that tries `datetime.fromisoformat` then `dateparser.parse`) and maps a non-empty result to `DERIVED`, else `NONE`. Rejected alternative: `python-dateutil` + hand-rolled comma splitting — no relative-anchor resolution and no safe multi-date tokenizer, pushing that risk onto us.

## Steps

1. Confirm `dateparser` is in `[project].dependencies` in `pyproject.toml` and `uv.lock` — done when `uv run python -c "import dateparser"` succeeds. *(Present, `pyproject.toml:8`.)*
2. `scholarship_factory/parse_dates.py` — `parse_deadline_dates(text, anchor)`: guard empty/whitespace `text` → `None`; call `search_dates(text, languages=["en"], settings={RELATIVE_BASE, PREFER_DATES_FROM:"future", RETURN_AS_TIMEZONE_AWARE:False})`; falsy → `None`; else collect `dt.date()` per match, dedup preserving first-seen order, return list or `None` if empty — done when the four AC inputs return expected values. *(Present, `parse_dates.py:9`.)*
3. Same module — `_parse_anchor(raw)` (ISO-first, `dateparser.parse` fallback) and `typed_deadlines(opp)`: `(None, NONE)` when `deadline` blank or no anchor derivable; else `(dates, DERIVED)` if non-empty, else `(None, NONE)` — done when a stubbed `Opportunity` with a relative deadline + anchor yields `DERIVED`. *(Present, `parse_dates.py:33`, `:44`.)*
4. Export `parse_deadline_dates` and `typed_deadlines` from `scholarship_factory/__init__.py` — done when `from scholarship_factory import parse_deadline_dates, typed_deadlines` works. *(Present, `__init__.py:4,17-18`.)*
5. `tests/test_parse_dates.py` covering multi-deadline, relative-vs-anchor (same string vs two anchors → distinct dates, proving no system-clock use), absolute-date, unparseable→`None`, and the three `typed_deadlines` provenance cases — done when `uv run pytest -q` is green. *(Present.)*

## Acceptance criteria mapping

- `"June 1st, and October 1st"` + 2024 anchor -> `[2024-06-01, 2024-10-01]` (uncollapsed) -> steps 2, 5; verified by `test_multi_deadline_not_collapsed` asserting the 2-element ordered list.
- Relative expression resolves against anchor, not today -> steps 2, 5; verified by `test_relative_expression_resolves_against_anchor_not_today` (two anchors → distinct dates from the same string).
- Unparseable/absent -> `None`; computed -> `derived`, unresolvable -> `none`, never guessed -> steps 2, 3, 5; verified by `test_unparseable_or_absent_returns_none` + the three `test_typed_deadlines_*` provenance tests.
- Deterministic + offline, tests cover all four cases -> steps 2, 5; verified by tests passing with no network/LLM (`languages=["en"]`, `search_dates` only).
- `uv run pytest -q` green -> steps 1, 5; verified by running it.

## Risks

- `search_dates` can over-/under-match noisy strings (stray numeric tokens). If a test surfaces a spurious match, keep `languages=["en"]` and, if needed, filter results whose matched substring lacks a month/weekday token — do **not** fall back to comma-splitting, which breaks `"September 15, 2024"`.
- `PREFER_DATES_FROM="future"` with a yearless month (`"June 1st"`) resolves to the anchor's year only if the anchor precedes that month; fixtures anchor early in the year (`date(2024,1,1)`) so June and October both land in 2024.
- On Windows `dateparser` needs `tzdata` for zoneinfo; if a fresh `uv sync` doesn't pull it transitively, add `tzdata` explicitly and re-sync.

## File manifest

Edit: `pyproject.toml`, `scholarship_factory/parse_dates.py`, `scholarship_factory/__init__.py:1`, `tests/test_parse_dates.py`. Read: `scholarship_factory/models.py:13`, `scholarship_factory/store.py:77`.

```json
{
  "stage": "plan",
  "ticket_id": "GH-12",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Deterministic S6 date-parse layer: pure parse_deadline_dates(text, anchor) over dateparser.search_dates + read-only typed_deadlines(opp) provenance helper; anchor-relative resolution, multi-deadline uncollapsed, unresolvable->None/derived. Implementation already present and verified on-branch (test_parse_dates.py, exports, dateparser dep) from a prior completed run; this is a plan-stage re-trigger, so the plan is grounded in the actual on-branch state for implement/test to verify.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {"edit": ["pyproject.toml", "scholarship_factory/parse_dates.py", "scholarship_factory/__init__.py:1", "tests/test_parse_dates.py"], "read": ["scholarship_factory/models.py:13", "scholarship_factory/store.py:77"]}
}
```