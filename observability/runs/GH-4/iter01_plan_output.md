I have everything needed. Here is the plan.

## Context

This ticket extends the GH-1 `Opportunity` model + SQLite store with provenance *evidence*. Touched files: `scholarship_factory/models.py:13-35` (the `Opportunity` pydantic v2 model, with `Provenance` enum and existing `deadline_provenance`/`reward_provenance`/`cost_provenance` fields) and `scholarship_factory/store.py` (the `OpportunityStore` whose `_COLUMNS` list at `store.py:7-27`, `CREATE TABLE` at `:37-67`, `insert`/`update`/`_row_to_opp` all build rows from `model_dump()` and select all columns). Tests live in `tests/test_models.py` and `tests/test_store.py`. Two constraints shape the approach: (1) the store derives columns generically from `model_dump()` + a fixed `_COLUMNS` list, so new fields round-trip automatically once added to both; (2) GH-1 tests construct opportunities with default (`none`) provenance, so any new validation must leave the `none`-provenance path untouched.

## Approach

Add four nullable `str | None` fields to the model — `deadline_source`, `reward_source`, `cost_source`, `source_observed_date` — mirroring the existing provenance fields, and enforce AC #2 with a single pydantic v2 `@model_validator(mode="after")` that rejects any of the three facts whose provenance is not `none` while its source span is `null`. I keep `source_observed_date` as `str` (verbatim page-stated date), matching `deadline`/`first_seen` which are already stored as ISO/text strings rather than typed dates — S6 owns parsing, and a `date` type here would force conversion churn in the store's string-based round-trip. In the store, append the four columns to `_COLUMNS` and the `CREATE TABLE` schema as nullable `TEXT`; insert/update/select need no further change because they already iterate `_COLUMNS`. I rejected enforcing the symmetric rule (reject non-null source when provenance is `none`) — the AC only mandates the "evidence required for quoted/derived" direction, and the extra constraint isn't requested and risks rejecting harmless data.

## Steps

1. Add `deadline_source: str | None = None`, `reward_source: str | None = None`, `cost_source: str | None = None`, and `source_observed_date: str | None = None` to the `Opportunity` model in `scholarship_factory/models.py` (after the provenance fields, ~line 29) — done when the model accepts and exposes all four new fields with `None` defaults.
2. Add `from pydantic import BaseModel, Field, model_validator` and a `@model_validator(mode="after")` to `Opportunity` in `scholarship_factory/models.py` that, for each `(provenance, source)` pair of the three facts, raises `ValueError` when provenance `!= Provenance.NONE` and source is `None` — done when constructing a `quoted` deadline with `deadline_source=None` raises `ValidationError` and the same with a non-null source succeeds.
3. Append `"deadline_source", "reward_source", "cost_source", "source_observed_date"` to `_COLUMNS` in `scholarship_factory/store.py:7-27` (e.g. after `cost_provenance`) — done when the list length matches the new column count and ordering is internally consistent with the named-column INSERT.
4. Add the four columns as nullable `TEXT` (no `NOT NULL`) to the `CREATE TABLE` statement in `scholarship_factory/store.py:_init_schema` — done when a fresh store creates the table with the new columns and `uv run pytest -q` constructs the schema without error.
5. Add model tests to `tests/test_models.py`: a valid `quoted` deadline + `deadline_source` case; the existing null-deadline/`none`-provenance/`deadline_source=None` valid case; and a `provenance != "none"` + null-source case asserting `ValidationError` — done when all three pass.
6. Add a store round-trip test to `tests/test_store.py`: insert an opportunity carrying `deadline_source`, `cost_source`, and `source_observed_date` (with matching `quoted` provenance), then `get`/`list` and assert all four new fields survive; confirm an `update` preserves them — done when the new fields match after round-trip and existing dedup/`last_seen` tests still pass.
7. Run `uv run pytest -q` — done when the full suite is green.

## Acceptance criteria mapping

- "`Opportunity` has nullable `deadline_source`/`reward_source`/`cost_source` and `source_observed_date`; quoted deadline + `deadline_source` valid, and null-deadline/`none`/null-source valid" -> steps 1, 2; verified by the new and existing cases in `tests/test_models.py`.
- "A fact with `provenance != "none"` and a `null` source span is rejected" -> step 2; verified by the `ValidationError` test in step 5.
- "Store insert/get/list/update round-trips all new fields; dedup and `last_seen` from GH-1 unchanged" -> steps 3, 4, 6; verified by the new round-trip test plus the untouched dedup/`last_seen` tests in `tests/test_store.py`.
- "Unit tests cover the new fields incl. null-deadline case and round-trip; no network, temp DB only" -> steps 5, 6; verified by `tmp_path`-based store tests and model tests (no network).
- "`uv run pytest -q` green" -> step 7; verified by the suite passing.

## Risks

1. **`_COLUMNS`/`CREATE TABLE` mismatch.** The INSERT uses named columns and pulls values via `[row[c] for c in _COLUMNS]`, so a column in `_COLUMNS` but absent from the table (or vice-versa) raises an `OperationalError` or `KeyError`. If it materializes, diff the column names in `_COLUMNS` against the `CREATE TABLE` body and ensure both lists contain the four new names.
2. **Validator breaks GH-1 defaults.** If the `model_validator` is written too strictly (e.g. also requiring source when provenance is `none`), GH-1's `test_defaults`/store tests that use default `none` provenance will fail. The validator must only fire on `provenance != none and source is None`; verify the existing model/store suites stay green.
3. **`source_observed_date` type choice.** If a reviewer expects a typed `date`, the `str` choice could be questioned. Mitigation: it mirrors `deadline`/`first_seen` (already strings) and S6 owns parsing — keep as `str` and the store's string round-trip stays uniform.

## File manifest

```json
{
  "stage": "plan",
  "ticket_id": "GH-4",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan to add nullable per-fact source-span fields (deadline_source/reward_source/cost_source) + source_observed_date to Opportunity with a model_validator enforcing evidence for non-none provenance, extend the store's _COLUMNS and schema, and cover with model + store round-trip tests.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {"edit": ["scholarship_factory/models.py:13", "scholarship_factory/store.py:7", "tests/test_models.py", "tests/test_store.py"], "read": ["scholarship_factory/__init__.py", "docs/s2-extract-tickets.md:22", "prd.json:23"]}
}
```