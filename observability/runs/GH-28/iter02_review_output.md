Execution stayed denied, so I verified the regexes analytically again and cross-checked the test stage's evidence.

## Lens 1 — intent

The `US` pattern (`scholarship_factory/rank.py:62`) is now `\b(?:US|United States) (?:residents?|citizens?)\b`. The noun is hoisted outside the alternation, so both branches require `residents`/`citizens` — the bare `\bUS` branch is gone. Tracing the old failure string: "using" matches `US` at the boundary, then needs a space, finds "i", fails; same for "usually" and standalone "us in the lab". No match. The bug is fixed, and the implementer applied the shape to all seven rules, so a future branch can't be added without the noun.

I checked the widened patterns for new false positives, since `(?:EU|European Union)` now has a two-character branch that could match inside words. On "a European Union grant program", the `EU` branch matches "Eu" of "European", then requires a space and finds "r" — backtracks to the `European Union` branch, matches, then requires " residents" and finds " grant". No match. Same structure holds for the `UK` and `US` branches. The `Canada only` alternation at line 63 keeps both `\b` guards.

The test stage's evidence is much better this iteration, and its numbers check out independently: it reports 21 tests in `test_rank.py`, and the file contains exactly 6 original + 1 regression + 4 + 4 + 3 + 3 parametrized cases = 21. That consistency is what I could verify without execution.

| Criterion | Evidence | Status |
|---|---|---|
| Region mismatch → `ineligible` naming both values | `test_region_rule_fires_on_explicit_constraint:115`, all four rules | verified |
| Missing fields → `eligible`, sorts last | `test_missing_fields_eligible_and_sorts_last:37` | verified |
| Past deadline → `expired`, excluded but present | `test_past_deadline_is_expired_and_excluded:51` | verified |
| Deadline then reward ordering | `test_sort_deadline_then_reward:64` | verified |
| All-null profile excludes nothing | `test_null_profile_excludes_nothing:75`, `test_unrecognized_region_never_excludes:84` | verified |
| Pure, no network/LLM; suite green | imports unchanged; 99 passed reported by implement and test stages | pure: verified; green: reported, not independently re-run |

My three fix-list items from iteration 1 all landed: the regex is fixed, `test_benign_us_prose_does_not_exclude:94` is the regression test (with "using", "usually", and standalone "us" in `description`, the wide field), and every rule in both tables now has a true-positive and a benign-text negative.

## Lens 2 — quality & security

The sort, verdict precedence, and models are untouched from iteration 1, where I reviewed them clean. No new dead code, no commented-out blocks. Still no I/O, subprocess, secrets, or user-supplied patterns.

Two non-blocking observations I'm recording rather than failing on:

The benign education case `"undergraduate research experience preferred"` (`tests/test_rank.py:174`) passes for a weaker reason than intended. All three cases use `education_level="undergraduate"`, and that string only touches the undergraduate rule — whose `satisfied_by` is `{"undergraduate"}`. So even if the pattern *did* wrongly fire, the profile satisfies it and nothing is excluded. The case can't fail. The other two cases (high-school rule and graduate rule against an undergraduate profile) do genuinely exercise the pattern, so the rules stay covered; this one case is just redundant.

The plan's Risk 1 stands: `US residents` under `re.I` still matches the pronoun in a contrived string like "join us residents of the program". I agree with the plan's call to accept it for v1 — a per-rule casing flag would introduce a new concept in the table for a string that doesn't occur in real scholarship prose, and the exposure is now vastly narrower than the shipped bug.

## Lens 3 — visual

No user-facing surface. `rank.py` is a pure library module with no markup, styles, or rendered output — nothing for Playwright to load. Not applicable rather than skipped for tooling.

## Verdict

Passing. The blocker is genuinely fixed, fixed at the bug-class level rather than the single line, and the coverage gap that let it ship is closed. The one caveat on my sign-off: I could not execute `uv run pytest -q` — the sandbox denied it across both iterations — so the "99 passed" figure is inherited from the implement and test stages, corroborated by the test-count cross-check but not independently re-run.

```json
{
  "stage": "review",
  "ticket_id": "GH-28",
  "outcome": "success",
  "exit_signal": true,
  "summary": "Iteration-1 blocker is fixed: the US region pattern at rank.py:62 now hoists the required noun outside the alternation (\\b(?:US|United States) (?:residents?|citizens?)\\b), so 'using'/'usually'/'us' no longer false-match; the same shape was applied to all seven rules, making the bug class unrepresentable. Rule-shaped parametrized coverage (true-positive + benign-text negative per rule) plus the specific 'using'/'us' regression test closes the gap that let a green suite ship the bug. All six acceptance criteria verified with evidence; no user-facing surface, so visual lens is N/A. Caveat: sandbox denied pytest execution, so 99-passed is inherited from prior stages, corroborated by an independent test-count cross-check (21 in test_rank.py = 6+1+4+4+3+3, matches the file exactly). Non-blocking: the benign education case at test_rank.py:174 is vacuous (profile satisfies the only rule its text touches), and the plan's accepted Risk 1 ('join us residents' pronoun match) remains.",
  "failure_reason": null,
  "files_changed": 2,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds `scholarship_factory/rank.py`: a deterministic `rank(opportunities, profile, *, today=...)` that scores stored opportunities against the single applicant profile with no LLM call and no fit-score float.\n\n**What it does.** Each opportunity gets a verdict (`eligible | ineligible | expired`) plus human-readable `reasons` naming the rule that fired. Eligible items sort most-actionable-first: soonest deadline, then larger reward, then title, with undated opportunities after dated ones. Expired items are excluded from the eligible ordering but still returned so the dashboard can show them separately. Deadlines come from the existing `parse_dates` layer, rewards from `parse_money`; `today` is injectable for tests.\n\n**The central invariant** is that unknown is never ineligible — exclusion fires only on an explicit, deterministic mismatch. This is structural, not a habit: the rule table is two-sided, so an opportunity constraint excludes only when the profile field also canonicalizes to a known token via an alias table. A profile region of 'Germany' canonicalizes to `eu` and therefore satisfies an 'EU residents' constraint; an unrecognized or null region can never fire a rule at all.\n\n**Tradeoff worth knowing.** The alias tables are the sole gate on false exclusion, and they are deliberately small (v1). Adding a constraint pattern without the matching profile-side aliases causes a real mismatch to go *uncaught* rather than a wrong exclusion — that direction is intentional. Do not add a raw-string fallback when the alias lookup misses; that would reintroduce the false-exclusion risk.\n\n**Risk for a merger.** The first cut of the US region rule had a regex precedence bug (`\\bUS|United States (residents|citizens)` — bare `\\bUS` under `re.I` matched 'using', 'usually', 'us') that falsely excluded eligible opportunities for any non-US profile, and a green 84-test suite missed it because the tests were shaped around the acceptance criteria rather than the rule table. Both are fixed: all seven patterns now hoist the required noun outside a non-capturing alternation, and every rule has a true-positive and a benign-text negative test. If you extend the table, keep that shape and add both test directions. One accepted limitation: under `re.I`, 'US residents' still matches the pronoun in contrived text like 'join us residents' — judged not worth a per-rule casing flag for v1."
}
```