Fixed the broken `US` region regex (bare `\bUS` was matching "using"/"usually"/standalone "us" and falsely excluding eligible opportunities), applied the same noun-hoisting fix to all seven rules to make the bug class unrepresentable, and added parametrized per-rule coverage (true-positive + benign-text negative) for all region and education rules plus the specific "using"/"us" regression test. Full suite: 99 passed, tree clean.

```json
{
  "stage": "implement",
  "ticket_id": "GH-28",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Fixed the broken US region regex in rank.py (bare \\bUS matched any 'us'-prefixed word) by hoisting the required noun outside the alternation for all seven rules; added parametrized per-rule true-positive/benign-text coverage in test_rank.py, including the regression test for the shipped bug. Full suite green (99 passed).",
  "failure_reason": null,
  "files_changed": 2,
  "suggested_tools": [],
  "system_repair_suggested": false
}
```