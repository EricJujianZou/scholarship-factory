The implementation already exists on-branch and matches a prior successful plan. This plan-stage re-trigger just needs the work-order produced. Here is the grounded plan.

## Context

New module `scholarship_factory/parse_dates.py` (currently the only date-parsing code). It reads `Opportunity` from `models.py`: `deadline: str | None`, anchors `source_observed_date: str | None` and `first_seen: str | None` (stored by `store.py` as ISO-8601 strings), and the `Provenance` enum `QUOTED|DERIVED|NONE`. The model's `_require_source_for_provenance` validator binds only when a *stored* `*_provenance` field is set with a `None` source — this ticket's helper returns values and never mutates the model, so that constraint does not apply. Contrary to the ticket aside, `dateparser`/`tzdata` are absent from `pyproject.toml`/`uv.lock`, so a dependency add is required. Locked decisions to honor: resolve relatives against the stored anchor (never "today"), unresolvable → `None`, computed → provenance `derived`, multi-deadline strings returned uncollapsed.

## Approach

A pure function `parse_deadline_dates(text, anchor) -> list[date] | None` built on `dateparser.search.search_dates`, which handles absolute, relative, and multi-date strings in one mechanism — critical because naive comma-splitting would wrongly break a single date like `"September 15, 2024"`, while `search_dates` returns one match there and two for `"June 1st, and October 1st"` in appearance order. Relatives resolve via `settings["RELATIVE_BASE"] = datetime.combine(anchor, time.min)` with `PREFER_DATES_FROM="future"` (a deadline is future relative to its anchor) and `languages=["en"]` for deterministic offline behavior. A thin `typed_deadlines(opp) -> tuple[list[date] | None, Provenance]` derives the anchor (`source_observed_date` → `first_seen`, via a tolerant `_parse_anchor` that tries `datetime.fromisoformat` then `dateparser.parse`) and maps a non-empty result to `DERIVED`, else `NONE`. Rejected alternative: `python-dateutil` + hand-rolled comma splitting — it has no relative-anchor resolution and no safe multi-date tokenizer, pushing that risk onto us.

## Steps

1. Add `dateparser` to `[project].dependencies` in `pyproject.toml` and `uv sync` — done when `uv run python -c "import dateparser"` succeeds and `uv.lock` carries `dateparser` (+ transitive `tzdata`).
2. Create `scholarship_factory/parse_dates.py` with `parse_deadline_dates(text: str | None, anchor: date) -> list[date] | None`: guard empty/whitespace `text` → `None`; call `search_dates(text, languages=["en"], settings={"RELATIVE_BASE": datetime.combine(anchor, time.min), "PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False})`; falsy result → `None`; else collect `dt.date()` per match, dedup preserving first-seen order, return list or `None` if empty — done when the four AC inputs return expected values.
3. In the same module add `_parse_anchor(raw) -> date | None` (try `fromisoformat`, fall back to `dateparser.parse`) and `typed_deadlines(opp) -> tuple[list[date] | None, Provenance]`: `(None, Provenance.NONE)` when `opp.deadline` blank or no anchor derivable; else `(dates, DERIVED)` if `parse_deadline_dates` non-empty, else `(None, NONE)` — done when a stubbed `Opportunity` with a relative deadline + anchor yields `DERIVED`.
4. Export `parse_deadline_dates` and `typed_deadlines` from `scholarship_factory/__init__.py` (imports + `__all__`) — done when `from scholarship_factory import parse_deadline_dates, typed_deadlines` works.
5. Create `tests/test_parse_dates.py` covering the multi-deadline case, a relative-vs-anchor case (same string against two anchors → distinct results, proving it never uses the system clock), an absolute-date case, an unparseable → `None` case, and the `typed_deadlines` provenance mapping — done when `uv run pytest -q` is green.

## Acceptance criteria mapping

- `"June 1st, and October 1st"` + 2024 anchor -> `[2024-06-01, 2024-10-01]` (uncollapsed) -> steps 2, 5; verified by the multi-deadline test asserting a 2-element ordered list.
- Relative expression resolves against anchor, not today -> steps 2, 5; verified by the relative-vs-anchor test using `RELATIVE_BASE` and asserting the anchor-derived date.
- Unparseable/absent -> `None`; computed -> `derived`, unresolvable -> `none`, never guessed -> steps 2, 3, 5; verified by the `None` test and the `typed_deadlines` provenance test.
- Deterministic + offline, tests cover all four cases -> steps 2, 5; verified by tests passing with no network/LLM (`languages=["en"]`, `search_dates` only).
- `uv run pytest -q` green -> steps 1, 5; verified by running it.

## Risks

- `search_dates` can over-/under-match noisy strings (stray numeric tokens). If a test surfaces a spurious match, keep `languages=["en"]` and, if still needed, filter results whose matched substring lacks a month/weekday token — do **not** fall back to comma-splitting, which breaks `"September 15, 2024"`.
- `PREFER_DATES_FROM="future"` with a yearless month (`"June 1st"`) resolves to the anchor's year only if the anchor precedes that month; anchor test fixtures early in the year (e.g. `date(2024,1,1)`) so June and October both land in 2024.
- On Windows `dateparser` needs `tzdata` for zoneinfo; if `uv sync` doesn't pull it transitively, add `tzdata` explicitly and re-sync.

## File manifest

Edit: `pyproject.toml`, `scholarship_factory/parse_dates.py`, `scholarship_factory/__init__.py:1`, `tests/test_parse_dates.py`. Read: `scholarship_factory/models.py:13`, `scholarship_factory/store.py:77`.

```json
{
  "stage": "plan",
  "ticket_id": "GH-12",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Deterministic S6 date-parse layer: pure parse_deadline_dates(text, anchor) over dateparser.search_dates + typed_deadlines(opp) provenance helper; anchor-relative resolution, multi-deadline uncollapsed, unresolvable->None/derived. Requires adding the dateparser dependency. Note: implementation already present on-branch from a prior completed run; this is a plan-stage re-trigger.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {"edit": ["pyproject.toml", "scholarship_factory/parse_dates.py", "scholarship_factory/__init__.py:1", "tests/test_parse_dates.py"], "read": ["scholarship_factory/models.py:13", "scholarship_factory/store.py:77"]}
}
```