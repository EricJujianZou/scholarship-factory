Confirmed the bug and audited the rest of the table myself. The review found one broken rule; I found a second, milder gap while checking the others. The repo already uses `pytest.mark.parametrize` (`tests/test_adapters.py:23`), which is how the per-rule coverage should be written rather than 14 near-duplicate functions.

## Context

- Retry of a plan whose implementation shipped and went green (84 passed) but failed review on one rule. Only `scholarship_factory/rank.py:60-65` (the region rule table) and `tests/test_rank.py` need to change; the module's structure, models, sort, and verdict precedence were all reviewed clean and stay as-is.
- The defect (`rank.py:62`): `r"\bUS|United States (residents|citizens)\b"` — `|` binds at top level, so branch one is a bare `\bUS` under `re.I` and matches "**us**ing", "**us**ually", "**us**er". Any non-`usa` profile gets a false `INELIGIBLE`, inverting the ticket's central locked decision.
- My own audit of the remaining six rules found one more, milder issue: `rank.py:61` is `\bEU residents\b`, so "EU **citizens**" and the plural-only phrasing never fire. That is a silent miss (Risk 3's tolerated direction), not a false exclusion — fixing it while the table is open, but it is not the review's blocker.
- Lines 63, 64 and all three education rules (`rank.py:82-84`) are correctly grouped; the fix must not disturb them beyond the shared shape change.
- Tests are plain pytest functions with an `_opp(**kwargs)` factory (`tests/test_rank.py:10`) and a frozen `TODAY = date(2026, 7, 15)`; `pytest.mark.parametrize` is established in the repo (`tests/test_adapters.py:23`, `tests/test_fetch.py:107`).

## Approach

Rather than patch line 62 with the review's suggested `r"\bUS (residents|citizens)\b|\bUnited States (residents|citizens)\b"`, rewrite all four region patterns into one shape that makes the bug unrepresentable: put the alternation inside a non-capturing group and the required noun *outside* it — `r"\b(?:US|United States) (?:residents?|citizens?)\b"`. The review's version is correct but repeats the noun on each branch, which is exactly the shape that invited the typo; hoisting the noun out means no future branch can be added without it. This is the same edit size, so it costs nothing over the literal fix. I rejected extracting a `_demands(subjects)` helper that builds these patterns: it is fewer characters but adds an abstraction over a seven-line table for a single call site, and the "Canada only" and "must be a…" phrasings don't fit one noun template — the `(?:…)` shape fixes the bug class without the indirection. Tests move from criteria-shaped to rule-shaped: every rule in both tables gets a parametrized true-positive and a benign-text negative, which is the coverage gap that let a green suite ship the bug.

## Steps

1. Fix the region rule table in `scholarship_factory/rank.py:60-65` — rewrite all four patterns with the alternation grouped and the noun hoisted out: EU → `r"\b(?:EU|European Union) (?:residents?|citizens?)\b"`, label `"EU residents"`, `{"eu"}`; US → `r"\b(?:US|United States) (?:residents?|citizens?)\b"`, label `"US residents"`, `{"usa"}`; Canada → `r"\b(?:Canadian (?:residents?|citizens?)|Canada only)\b"`, label `"Canadian residents"`, `{"canada"}`; UK → `r"\b(?:UK|United Kingdom) (?:residents?|citizens?)\b"`, label `"UK residents"`, `{"uk"}`. All keep `re.I`. Done when no pattern in the list contains a top-level `|` outside a `(?:...)` group.
2. Regroup the three education patterns in `scholarship_factory/rank.py:81-85` to the same shape — `r"\b(?:high school students? only|must be a high school student)\b"`, `r"\b(?:undergraduates? only|must be an undergraduate)\b"`, `r"\b(?:graduate students? only|PhD (?:students?|candidates?) only)\b"`. Labels and `satisfied_by` sets are unchanged. Done when each pattern's alternation sits inside `(?:...)` and the existing education behavior is unchanged.
3. Add `test_benign_us_prose_does_not_exclude` to `tests/test_rank.py` — a `region="Canada"` profile against `_opp(description="For students using renewable energy research, usually joining us in the lab")`, asserting `results.excluded == []` and `results.eligible[0].verdict == Verdict.ELIGIBLE`. This is the regression test for the shipped bug; it must fail against the current `rank.py:62`. Done when it passes after step 1 and the description text contains "using", "usually", and standalone "us".
4. Add a parametrized `test_region_rule_fires_on_explicit_constraint` to `tests/test_rank.py` over `(requirements, profile_region, expected_label)` covering all four region rules: `("Open to EU residents only", "Canada", "EU residents")`, `("US citizens only", "Canada", "US residents")`, `("Canada only", "Germany", "Canadian residents")`, `("Open to UK residents", "Canada", "UK residents")`. Assert `Verdict.INELIGIBLE` and that the single reason names both `expected_label` and the profile region. Done when all four cases pass.
5. Add a parametrized `test_region_rule_does_not_fire_on_benign_text` to `tests/test_rank.py` over benign prose per rule, with `region="Canada"` (and `region="Germany"` for the Canada case so the rule *could* fire): `"a European Union grant program"`, `"we ship to United States addresses"`, `"the Canadian Space Agency sponsors this"`, `"UK based mentors will advise"`. Assert every item is `Verdict.ELIGIBLE` and `results.excluded == []` — each string names a region without stating a residency constraint. Done when all four cases pass.
6. Add a parametrized `test_education_rule_fires_on_explicit_constraint` to `tests/test_rank.py` over `(requirements, profile_education, expected_label)`: `("High school students only", "undergraduate", "high school students only")`, `("Undergraduates only", "phd", "undergraduate students only")`, `("Graduate students only", "high school", "graduate students only")`. Assert `Verdict.INELIGIBLE` and both values named in the reason. Done when all three pass.
7. Add a parametrized `test_education_rule_does_not_fire_on_benign_text` to `tests/test_rank.py` over `"open to high school students and undergraduates"`, `"undergraduate research experience preferred"`, `"graduate students are encouraged to apply"`, each with `education_level="undergraduate"`, asserting `Verdict.ELIGIBLE` and no exclusions — "preferred"/"encouraged"/"and" are not the `only` constraint the rules require. Done when all three pass.
8. Run `uv run pytest -q tests/test_rank.py` — done when the file is green and the new-test count reflects the parametrized cases (roughly 14 added).
9. Run `uv run pytest -q` from the repo root — done when the full suite is green with no regression against the previously reported 84 passed.

## Acceptance criteria mapping

Criteria 1–5 already have passing assertions carried over unchanged from iteration 1 (`tests/test_rank.py:21-89`); this iteration re-verifies them via step 9 and deepens the rule-table coverage beneath criterion 1.

- "An opportunity whose requirements explicitly demand a region different from the profile's region -> `ineligible` with a reason naming both values." -> steps 1, 4; verified by the existing `test_region_mismatch_is_ineligible_with_reason:21` plus the new parametrized `test_region_rule_fires_on_explicit_constraint` covering all four region rules rather than just EU.
- "Missing `deadline` / `reward` / `requirements` -> stays `eligible`; sorts after opportunities with parsed deadlines." -> unchanged; verified by existing `test_missing_fields_eligible_and_sorts_last:35`, re-run in step 9.
- "A parsed deadline before `today` -> `expired`, excluded from the eligible ordering but present in results with a reason." -> unchanged; verified by existing `test_past_deadline_is_expired_and_excluded:49`, re-run in step 9.
- "Two eligible dated opportunities -> soonest deadline first; equal deadlines -> larger parsed reward first." -> unchanged; verified by existing `test_sort_deadline_then_reward:62`, re-run in step 9.
- "Profile with all-null fields -> nothing excluded (everything eligible or expired)." -> unchanged; verified by existing `test_null_profile_excludes_nothing:73` and `test_unrecognized_region_never_excludes:82`, re-run in step 9.
- "Pure functions, no network, no LLM; `uv run pytest -q` green." -> steps 1–9; verified by step 9's full-suite run; imports in `rank.py:12-21` are unchanged by this iteration and remain `re`/`datetime`/`enum`/`pydantic` plus local modules.

Underpinning the ticket's "unknown is never ineligible" locked decision (the thing the shipped bug violated): steps 3, 5, 7 — the benign-text negatives are what hold that line, and they are the tests the criteria list never asked for.

## Risks

1. **Under `re.I`, `\b(?:US|United States) (?:residents?|citizens?)\b` still matches the pronoun in "join us residents of the program".** The noun requirement makes this far narrower than the shipped bug, but it is not zero. Do *not* fix it by making the US rule case-sensitive while its six neighbours stay `re.I` — a per-rule casing flag is a new concept in the table for a contrived string. Accept the miss for v1; if a real fixture ever trips it, that is the signal to revisit.
2. **Step 3's regression test must be confirmed to fail against the current code, not just pass after the fix.** If it is written after step 1 lands it may pass for the wrong reason (e.g. a typo makes the description miss the rule entirely). Write it so "using"/"usually"/"us" appear in `description` specifically — `_mismatch_reasons` (`rank.py:95`) joins `requirements` and `description`, and `description` is the wide field that made the bug likely.
3. **Widening the EU rule to `(?:residents?|citizens?)` changes behavior the existing tests assert.** `test_region_mismatch_is_ineligible_with_reason:23` uses "Open to EU residents only" and still matches, but if any other existing test relies on "EU citizens" *not* firing, it will now fail. Step 9 catches it; if that happens the correct response is to keep the widened rule and update the stale test — the widening is a deliberate coverage fix, not a regression.

```json
{
  "stage": "plan",
  "ticket_id": "GH-28",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Retry plan for GH-28: fix the broken US region regex at rank.py:62 by hoisting the required noun outside a non-capturing alternation group (applied to all seven rules so the bug class is unrepresentable), and replace criteria-shaped tests with rule-shaped parametrized coverage — a true-positive and a benign-text negative per rule, including the 'using'/'us' regression test that would have caught the shipped bug.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/rank.py:60",
      "scholarship_factory/rank.py:81",
      "tests/test_rank.py"
    ],
    "read": [
      "scholarship_factory/rank.py:94",
      "scholarship_factory/models.py:13",
      "scholarship_factory/profile.py:17",
      "tests/test_adapters.py:23",
      "tests/test_fetch.py:107",
      "observability/runs/GH-28/iter01_review_output.md"
    ]
  }
}
```