I have everything I need. Here's my three-lens review of the GH-4 diff.

## Lens 1 — Intent (acceptance criteria, walked one by one)

- **AC1 — new nullable fields + valid construction paths.** `models.py:31-34` adds `deadline_source`/`reward_source`/`cost_source`/`source_observed_date`, all `str | None = None`. `test_quoted_deadline_with_source_is_valid` exercises the quoted-deadline+source case; `test_null_deadline_with_none_provenance_is_valid` exercises the null/`none`/null-source case (source defaults to `None`). **Verified.**
- **AC2 — non-`none` provenance with null source rejected.** `@model_validator(mode="after")` at `models.py:42-53` raises for each of the three facts when `provenance != NONE and source is None`. `test_quoted_deadline_without_source_raises` asserts `ValidationError`. **Verified.**
- **AC3 — store round-trips all new fields; dedup/`last_seen` unchanged.** `_COLUMNS` (`store.py:22-25`) and `CREATE TABLE` (`store.py:59-62`) both gain the four columns as nullable `TEXT`; insert/update/select iterate `_COLUMNS` generically so they carry automatically. `test_source_span_fields_round_trip` covers insert→get, all four fields surviving (incl. `reward_source` staying `None`), and update preservation. Existing dedup/`last_seen` tests untouched. **Verified.**
- **AC4 — tests, no network, temp DB.** New tests use `tmp_path`, no network. **Verified.**
- **AC5 — `uv run pytest -q` green.** Test-stage evidence is structured, not just prose: `iter01_test.json` shows `exit_code: 0`, `stderr_head: ""`, 16 passed. I could not re-run the suite myself (test execution is permission-gated in this read-only session), but the structured exit code plus my line-by-line read of the tests against the implementation confirms it. **Verified via test-stage evidence + static review.**

## Lens 2 — Quality & security

- Validator fires in the correct (and only the required) direction; the symmetric rule was deliberately omitted per the plan — reasonable, avoids rejecting harmless data. Default `none`-provenance path is untouched, so GH-1 tests stay green.
- `source_observed_date` kept as `str` to mirror `deadline`/`first_seen` and the store's uniform string round-trip — sound; S6 owns parsing.
- Security: columns come from a fixed list, values are parameterized — no injection; no secrets. Minor non-blocking note: an empty-string source (`""`) passes validation since the check is `is None`; AC only mandates rejecting `null`, so this is acceptable.
- No dead code; tests assert meaningfully.

## Lens 3 — Visual

No user-facing surface — this is a model + SQLite store (data-layer) change. Playwright N/A; nothing to render.

## Tree state

The ticket's code change (models.py, store.py, both test files) is committed and clean. The remaining uncommitted items (`state.json`, `iter01_review_prompt.md`, `iter01_test*.md/json`) are harness-generated observability/state artifacts produced by running the stages themselves — the implement and test stages committed the same class of files via `chore:` commits, and the next step handles these. Not a code-completeness concern.

Everything holds.

```json
{
  "stage": "review",
  "ticket_id": "GH-4",
  "outcome": "success",
  "exit_signal": true,
  "summary": "All 5 acceptance criteria verified against code + tests across the three lenses. Model gains 4 nullable source-span fields + an after-validator requiring evidence for non-none provenance; store schema/_COLUMNS extended and round-trip covered. No user-facing surface (visual lens N/A). Could not re-run pytest (execution permission-gated in this read-only session) but confirmed via structured test-stage evidence (exit_code 0, empty stderr, 16 passed) and line-by-line static review.",
  "failure_reason": null,
  "files_changed": 4,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds provenance *evidence* to the `Opportunity` model + SQLite store, the foundation for Session 2 (Extract).\n\n**What changed**\n- `Opportunity` gains four nullable string fields: `deadline_source`, `reward_source`, `cost_source` (verbatim quoted source text per fact) and `source_observed_date` (page-stated anchor date for later S6 relative-value resolution; distinct from `first_seen`, which is fetch time).\n- A pydantic `@model_validator(mode=\"after\")` rejects any fact whose provenance is not `none` while its source span is `null` — a quoted/derived fact must carry its evidence.\n- The store's `_COLUMNS` and `CREATE TABLE` schema gain the four columns as nullable `TEXT`; insert/get/list/update round-trip them automatically via the existing column-driven mechanism.\n\n**Tradeoffs / notes**\n- `source_observed_date` is stored as a string (not a typed `date`), mirroring `deadline`/`first_seen` and keeping the store's string round-trip uniform; parsing is deferred to S6.\n- The validator enforces only the required direction (evidence required when provenance != none); the symmetric rule (rejecting a non-null source under `none` provenance) was intentionally not added.\n\n**Risk for a merger**\n- Low. New columns are nullable and additive; existing rows/behavior (URL-normalization dedup, `last_seen` refresh) are unchanged. Empty-string sources pass validation (only `null` is rejected), which is within the ticket's contract."
}
```