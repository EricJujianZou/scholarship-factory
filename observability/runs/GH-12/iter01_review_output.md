I have everything I need. The `uv run` commands are blocked by the reviewer's read-only permission profile, so I can't independently execute the suite — but I've read the code, the tests, and the reference files, and the test stage supplies concrete evidence (31 passed). Let me assess against the three mandatory lenses.

## Review — GH-12 (deterministic date-parse layer)

**Lens 1 — intent (acceptance criteria, one by one):**

1. **Multi-deadline uncollapsed** — `parse_deadline_dates` uses `dateparser.search.search_dates` (not comma-splitting), collects `dt.date()` per match preserving order with a dedup guard. `test_multi_deadline_not_collapsed` asserts `[date(2024,6,1), date(2024,10,1)]` exactly. ✓
2. **Relative resolves against anchor, not today** — `RELATIVE_BASE = datetime.combine(anchor, time.min)`. `test_relative_expression_resolves_against_anchor_not_today` proves it *structurally*: the same `"closes Friday"` string against two different anchors yields two distinct dates (`[2024-01-05]` vs `[2024-06-07]`), which is impossible if the system clock were used. Strong test design. ✓
3. **Unresolvable → None; computed → derived, never guessed** — empty/whitespace guard and falsy-match guard both return `None`; `typed_deadlines` maps a non-empty result to `DERIVED`, else `NONE`. No fabrication path exists. Three `test_typed_deadlines_*` tests cover derived, unresolvable→none, and absent-deadline→none. ✓
4. **Deterministic + offline; tests cover 4 cases** — `languages=["en"]`, `search_dates` only, no network/LLM. All four required cases present (multi, relative-vs-anchor, absolute, None). ✓
5. **`uv run pytest -q` green** — test stage evidence: 31 passed. I confirmed the tests assert correct expected values and the code produces them; could not re-run myself (harness denied `uv run` under the reviewer profile), but the evidence is concrete, not prose. ✓

**Lens 2 — quality & security:**
- Correctness clean: empty-text guard, order-preserving dedup, `return dates or None`. `_parse_anchor` tries `datetime.fromisoformat` then falls back to `dateparser.parse` — tolerant of both the `+00:00` ISO strings `store.py` writes and looser anchors. `typed_deadlines` correctly derives anchor as `source_observed_date` → `first_seen`.
- The model's `_require_source_for_provenance` validator binds only on stored `*_provenance` fields; this helper returns values and never persists, so it's correctly untouched (no store mutation, per scope). ✓
- Security: pure parsing, no subprocess/file/network, no secrets. Both `dateparser` imports are used (`.parse` in `_parse_anchor`, `.search.search_dates` in the main fn) — no dead imports. ✓

**Lens 3 — visual:** No user-facing surface — this is a pure library module. Nothing to render; Playwright not applicable.

**Note (non-blocking):** the working tree shows modifications to `observability/runs/GH-12/iter01_test*` and `state.json` — harness run-bookkeeping, not ticket code. The code diff (`parse_dates.py`, tests, `__init__.py` exports, `pyproject.toml`/`uv.lock` deps) is committed and clean.

Every criterion is verified with evidence, no lens found a must-fix issue, and the code is sound. This is a clean first solve of a "deterministic parse-layer over a stored string" class — a reasonable candidate for a `skills/` entry.

```json
{
  "stage": "review",
  "ticket_id": "GH-12",
  "outcome": "success",
  "exit_signal": true,
  "summary": "All 5 acceptance criteria verified against code + tests. parse_deadline_dates resolves relatives against the passed anchor (proven by same-string/two-anchor test), keeps multi-deadline strings uncollapsed, and returns None when unresolvable; typed_deadlines maps results to derived/none with no store mutation. Pure/offline, no security concerns, no user-facing surface. Test stage: 31 passed (I could not re-run pytest — reviewer profile denies `uv run` — but read tests+code confirm the behavior). Clean first solve of the deterministic-parse-layer class; candidate for a skills/ entry.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds the deterministic Session-6 date-parse layer: turns the verbatim stored `deadline` string into typed `date` values without any LLM or network call.\n\n**What changed**\n- `scholarship_factory/parse_dates.py`: `parse_deadline_dates(text, anchor) -> list[date] | None` built on `dateparser.search.search_dates`, plus a read-only `typed_deadlines(opp) -> (dates, Provenance)` helper.\n- Exports both from `scholarship_factory/__init__.py`; adds `dateparser` to `pyproject.toml`/`uv.lock`.\n- `tests/test_parse_dates.py`: 7 tests (multi-deadline, relative-vs-anchor, absolute, unparseable, and the three provenance cases).\n\n**Design decisions honored**\n- Relative expressions (\"closes Friday\") resolve against the stored anchor (`source_observed_date` → `first_seen`), never the system clock — enforced via `RELATIVE_BASE` and proven by a test that gets different results from the same string under different anchors.\n- Multi-deadline strings (\"June 1st, and October 1st\") return both dates uncollapsed; `search_dates` is used instead of comma-splitting so single dates like \"September 15, 2024\" are not wrongly split.\n- Unresolvable input → `None` with provenance `none`; a computed value gets provenance `derived`. No date is ever guessed. No store mutation, no ranking (out of scope).\n\n**Risks for the merger**\n- `PREFER_DATES_FROM=\"future\"` on a yearless month resolves into the anchor's year only when the anchor precedes that month; strings whose month is before the anchor could land in the next year. Acceptable for the deadline-after-anchor assumption, but worth knowing when downstream ranking consumes these dates.\n- `dateparser` needs `tzdata` on Windows (already pulled transitively); a fresh env that lacks it would need it added explicitly."
}
```