I couldn't get execution permission for the probe or the test suite, so I verified the regex analytically — but Python's alternation semantics here are unambiguous. Here's my review.

## Lens 1 — intent

Walking the six acceptance criteria against `tests/test_rank.py`:

| Criterion | Evidence | Status |
|---|---|---|
| Region mismatch → `ineligible` naming both values | `test_region_mismatch_is_ineligible_with_reason:21` | verified |
| Missing fields → `eligible`, sorts last | `test_missing_fields_eligible_and_sorts_last:35` | verified |
| Past deadline → `expired`, excluded but present | `test_past_deadline_is_expired_and_excluded:49` | verified |
| Deadline then reward ordering | `test_sort_deadline_then_reward:62` | verified |
| All-null profile excludes nothing | `test_null_profile_excludes_nothing:73` | verified |
| Pure, no network/LLM; suite green | imports are `re`/`datetime`/`enum`/`pydantic` + local modules only | pure: verified; green: reported (84 passed) by implement and test stages, not independently re-run — see note below |

Each written criterion has a real assertion behind it. The problem is what the criteria don't cover.

## Lens 2 — quality & security

**The `US` region pattern is broken and silently excludes eligible applicants** (`scholarship_factory/rank.py:62`):

```python
(re.compile(r"\bUS|United States (residents|citizens)\b", re.I), "US residents", frozenset({"usa"})),
```

Alternation is top-level, so this is `(\bUS)` OR `(United States (residents|citizens)\b)`. The first branch is bare `\bUS` with no `residents` requirement and `re.I` on — it matches `us` at the start of **any** word: "using", "usually", "user", and the standalone word "us". Compare the correctly-grouped neighbours on lines 61, 63, 64, which all anchor both branches — line 62 is a typo'd copy of that shape.

The failure: an opportunity described as "for students **us**ing renewable energy research" fires the "US residents" constraint. Any profile whose region canonicalizes to something other than `usa` — a `region="Canada"` profile, the exact case in the ticket — gets `INELIGIBLE` with the reason "region mismatch: requires 'US residents', profile region 'Canada'". Since `_mismatch_reasons` scans `requirements + description` together (line 95), the wide description text makes hits likely rather than exotic. "using" and "us" are ordinary words in scholarship prose.

This is not a cosmetic regex nit — it inverts the ticket's central locked decision. "Unknown is never ineligible... exclusion only on an explicit, deterministic mismatch" and "when in doubt, keep it eligible" are the whole ethos of the ticket, and this rule excludes real, eligible opportunities on a substring coincidence. The plan's own Risk 3 argued for tolerating silent misses over false exclusions; this is precisely the false exclusion it set out to prevent.

**Why the suite didn't catch it:** no test exercises the `US` rule, and no test exercises either education rule. Of the seven rules in the two tables, only "EU residents" is tested. That's the coverage gap the bug slipped through — the tests validate the acceptance-criteria list rather than the rule table, and the criteria happen to only name region-vs-region.

No security concerns: no subprocess, no file or network I/O, no secrets, no user input reaching an eval sink. Regexes are module-level constants over stored text, not user-supplied patterns. Verdict precedence (ineligible over expired, line 142) matches the plan and preserves the expiry reason. `_effective_deadline` (line 115) correctly handles the multi-deadline case per the plan's Risk 2.

## Lens 3 — visual

No user-facing surface. `rank.py` is a pure library module with no markup, styles, or rendered output — nothing for Playwright to load. Visual verification is not applicable rather than skipped for tooling.

## Fix list, ordered

1. **`scholarship_factory/rank.py:62`** — fix the alternation grouping so both branches require the constraint noun: `r"\bUS (residents|citizens)\b|\bUnited States (residents|citizens)\b"`. The bare `\bUS` branch must not survive in any form.
2. **`tests/test_rank.py`** — add a regression test proving benign prose containing "using"/"us" in `description` does **not** exclude a `region="Canada"` profile. This is the test that would have caught it.
3. **`tests/test_rank.py`** — add at least one test per remaining untested rule (`US residents`, `Canadian residents`, `UK residents`, and the three education rules): one true-positive exclusion and one benign-text non-exclusion each. The rule table is the unit worth testing here, not just the criteria list.

One process note for the next pass: the test stage's `iter01_test_output.md` records only "Committed. Working tree is clean now." plus a status block asserting all six criteria "verified... individually". That claim is prose without evidence — no per-criterion output, no failure output, no reasoning shown. It's also literally true and still missed this bug, because it checked the criteria rather than the code. I re-derived the criteria mapping from the test file myself; I could not re-run `uv run pytest -q` (the sandbox denied both the probe and the suite), so the "84 passed" figure is inherited from the prior stages, not independently confirmed. That doesn't change the verdict — the defect is in code the passing suite never touches.

```json
{
  "stage": "review",
  "ticket_id": "GH-28",
  "outcome": "failure",
  "exit_signal": false,
  "summary": "Intent lens passes: all six acceptance criteria have real assertions behind them. Quality lens found a must-fix correctness bug — the US region pattern at rank.py:62 has broken alternation grouping (`\\bUS|United States (residents|citizens)\\b`), so bare `\\bUS` with re.I matches any word starting 'us' ('using', 'usually', 'us'), firing a 'US residents' exclusion on benign description prose and marking eligible opportunities INELIGIBLE for any non-USA profile. This inverts the ticket's central locked decision that unknown is never ineligible and exclusion fires only on explicit mismatch. Untested: 6 of 7 rules in the table, which is how it survived a green suite. No visual surface (pure library module). Could not independently re-run pytest — sandbox denied execution; bug confirmed by inspection of unambiguous Python alternation semantics.",
  "failure_reason": "1. rank.py:62 — fix alternation grouping so both branches require the constraint noun: r\"\\bUS (residents|citizens)\\b|\\bUnited States (residents|citizens)\\b\". The bare \\bUS branch must not survive. 2. tests/test_rank.py — add a regression test that benign description prose containing 'using'/'us' does NOT exclude a region='Canada' profile. 3. tests/test_rank.py — add per-rule coverage (true-positive exclusion + benign-text non-exclusion) for the untested US, Canadian, UK region rules and all three education rules.",
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false
}
```