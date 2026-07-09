I have enough context to write the plan. Key findings from PRIME:

- `Opportunity` (models.py): `deadline: str | None`, anchors `source_observed_date: str | None` and `first_seen: str | None` (stored as ISO strings by `store.py`), `Provenance` enum = `QUOTED|DERIVED|NONE`. The model_validator requires `*_source` only when a *stored* provenance field ≠ none — the helper returns values, it doesn't mutate the model, so that constraint doesn't bind here.
- `dateparser`/`tzdata` are **not** in `pyproject.toml` or `uv.lock` despite the ticket's aside — the dep must be added.
- Style: pure functions, small modules, tests under `tests/test_*.py`, exports wired through `__init__.py`.

Here is the plan.

## Context

New module `scholarship_factory/parse_dates.py`; no existing file does date parsing. It reads `Opportunity` from `models.py` (`deadline: str | None`, `source_observed_date`/`first_seen: str | None`, `Provenance` enum `QUOTED|DERIVED|NONE`). `store.py` writes anchors as UTC ISO-8601 strings via `datetime.now(...).isoformat()`; `source_observed_date` may be arbitrary LLM-emitted text, so anchor parsing must be tolerant. Contrary to the ticket aside, `dateparser`/`tzdata` are absent from `pyproject.toml` and `uv.lock` — a dependency add is step 1. Locked decisions to honor: resolve relatives against the stored anchor (never "today"), unresolvable → `None`, computed → provenance `derived`, and multi-deadline strings return *both* dates uncollapsed.

## Approach

A pure function `parse_deadline_dates(text, anchor) -> list[date] | None` built on `dateparser.search.search_dates`, which handles absolute, relative, and multi-date strings in one mechanism — critical because naive comma-splitting would wrongly break a single date like `"September 15, 2024"`, whereas `search_dates` returns one match there and two for `"June 1st, and October 1st"` in appearance order. Relatives resolve via `settings["RELATIVE_BASE"] = datetime.combine(anchor, time.min)` with `PREFER_DATES_FROM="future"` (a deadline is future relative to its anchor) and `languages=["en"]` for deterministic, offline behavior. Rejected alternative: `python-dateutil` + hand-rolled splitting — it has no relative-anchor resolution and no safe multi-date tokenizer, pushing that risk onto us. A thin helper `typed_deadlines(opp) -> tuple[list[date] | None, Provenance]` derives the anchor (`source_observed_date` → `first_seen`) and maps a non-empty result to `DERIVED`, otherwise `NONE`. The helper returns values only — no store mutation, no field writes — so the model's `*_source` validator is irrelevant here.

## Steps

1. Add `dateparser` to `[project].dependencies` in `pyproject.toml` and run `uv sync` — done when `uv run python -c "import dateparser"` succeeds and `uv.lock` contains `dateparser` (+ transitive `tzdata`).
2. Create `scholarship_factory/parse_dates.py` with `parse_deadline_dates(text: str, anchor: date) -> list[date] | None`: guard empty/whitespace `text` → `None`; call `dateparser.search.search_dates(text, languages=["en"], settings={"RELATIVE_BASE": datetime.combine(anchor, time.min), "PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False})`; if result is falsy → `None`; else collect `dt.date()` for each `(_, dt)`, dedup preserving first-seen order, return the list. Done when the four AC inputs return the expected values in a REPL.
3. In the same module add `_parse_anchor(raw: str | None) -> date | None` (tolerant: try `datetime.fromisoformat`, fall back to `dateparser.parse`, return `.date()` or `None`) and `typed_deadlines(opp: Opportunity) -> tuple[list[date] | None, Provenance]`: return `(None, Provenance.NONE)` if `opp.deadline` is blank or no anchor derivable from `source_observed_date`/`first_seen`; else `dates = parse_deadline_dates(opp.deadline, anchor)` and return `(dates, Provenance.DERIVED)` if `dates` else `(None, Provenance.NONE)`. Done when a stubbed `Opportunity` with a relative deadline + anchor yields `DERIVED`.
4. Export `parse_deadline_dates` and `typed_deadlines` from `scholarship_factory/__init__.py` (add to imports and `__all__`) — done when `from scholarship_factory import parse_deadline_dates, typed_deadlines` works.
5. Create `tests/test_parse_dates.py` covering: multi-deadline `"June 1st, and October 1st"` + `date(2024,1,1)` → `[date(2024,6,1), date(2024,10,1)]`; a relative expression resolved against an anchor and asserted distinct from a today-based result; an absolute date string; an unparseable string → `None`; and the `typed_deadlines` provenance mapping (`DERIVED` vs `NONE`). Done when `uv run pytest -q` is green.

## Acceptance criteria mapping

- `"June 1st, and October 1st"` + 2024 anchor -> `[2024-06-01, 2024-10-01]` (uncollapsed) -> steps 2, 5; verified by the multi-deadline test asserting a 2-element list in order.
- Relative expression resolves against anchor, not today -> steps 2, 5; verified by the relative-vs-anchor test using `RELATIVE_BASE` and asserting the anchor-derived date (≠ today's resolution).
- Unparseable/absent -> `None`; computed -> `derived`, unresolvable -> `none`, never guessed -> steps 2, 3, 5; verified by the `None` test and the `typed_deadlines` provenance test.
- Deterministic + offline, unit tests cover all four cases -> steps 2, 5; verified by tests passing with no network/LLM (`languages=["en"]`, `search_dates` only).
- `uv run pytest -q` green -> steps 1, 5; verified by running it.

## Risks

- `search_dates` can over- or under-match noisy strings (e.g. grabbing stray numeric tokens). If a test surfaces a spurious match, constrain via `languages=["en"]` (already set) and, if still needed, add `"STRICT_PARSING": False` tuning or filter results whose matched substring lacks a month/weekday token — do not fall back to comma-splitting, which breaks `"September 15, 2024"`.
- `PREFER_DATES_FROM="future"` with a yearless month (`"June 1st"`) resolves to the anchor's year only if the anchor precedes that month; tests must anchor early in the year (e.g. `date(2024,1,1)`) to get 2024 for both June and October — make the fixture anchor explicit.
- `dateparser` needs `tzdata` on Windows for zoneinfo; if `uv sync` doesn't pull it transitively, add `tzdata` explicitly to `[project].dependencies` and re-sync.

## File manifest

Edit: `pyproject.toml`, `scholarship_factory/parse_dates.py`, `scholarship_factory/__init__.py:1`, `tests/test_parse_dates.py`. Read: `scholarship_factory/models.py:13`, `scholarship_factory/store.py:77`, `scholarship_factory/extract.py:85`, `tests/test_extract.py:36`.

```json
{
  "stage": "plan",
  "ticket_id": "GH-12",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Deterministic date-parse layer: pure parse_deadline_dates(text, anchor) on dateparser.search_dates + a typed_deadlines(opp) provenance helper; anchor-relative, multi-deadline uncollapsed, unresolvable->None. Requires adding the dateparser dependency.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {"edit": ["pyproject.toml", "scholarship_factory/parse_dates.py", "scholarship_factory/__init__.py:1", "tests/test_parse_dates.py"], "read": ["scholarship_factory/models.py:13", "scholarship_factory/store.py:77", "scholarship_factory/extract.py:85", "tests/test_extract.py:36"]}
}
```