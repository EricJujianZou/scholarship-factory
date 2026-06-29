# GH-4 — Opportunity: store per-fact source span (provenance evidence)

## What shipped

Foundation for Session 2 (Extract): the `Opportunity` model and its SQLite
store now carry the **evidence** behind each uncertain fact — the verbatim
source text a `quoted`/`derived` value was read from — alongside the existing
provenance enum (GH-1). This is the checkable receipt that separates a
legitimate value from a fabrication, and it lets the later deterministic S6
parse layer resolve relative values without a second LLM call. Model + store
only; no extraction logic.

## Schemas & data

**`Opportunity`** (`scholarship_factory/models.py`) — four new nullable
`str | None` fields:

- `deadline_source`, `reward_source`, `cost_source` — the verbatim quoted
  source text for each fact, or `null` when the fact is absent / its
  provenance is `none`.
- `source_observed_date` — the page-stated anchor date S6 needs to resolve
  relative deadlines later (the page is gone by then); `null` if none. Kept
  distinct from `first_seen`, which is *when we fetched*, not *when the source
  was authored*.

A `@model_validator(mode="after")` rejects any fact whose provenance is not
`none` while its source span is `null` — a quoted/derived fact must carry its
evidence. Only the required direction is enforced; the symmetric rule
(rejecting a non-null source under `none` provenance) was intentionally not
added.

**`OpportunityStore`** (`scholarship_factory/store.py`) — the four columns are
added to `_COLUMNS` and the `CREATE TABLE` schema as nullable `TEXT`;
insert/get/list/update carry them automatically via the existing
column-driven mechanism. URL-normalization dedup and `last_seen` refresh from
GH-1 are unchanged.

## Behavior & breaking changes

Additive only. New columns are nullable; existing rows and behavior (dedup,
`last_seen`) are untouched. `source_observed_date` is stored as a string
(mirroring `deadline`/`first_seen`); parsing is deferred to S6. An empty-string
source passes validation (only `null` is rejected) — within the ticket's
contract.

## How it was verified

16 unit tests, `uv run pytest -q`, no network, temporary DB only:

- New nullable fields + valid construction paths →
  `tests/test_models.py::test_quoted_deadline_with_source_is_valid`,
  `test_null_deadline_with_none_provenance_is_valid`.
- Non-`none` provenance with a null source rejected →
  `test_quoted_deadline_without_source_raises` (asserts `ValidationError`).
- Store round-trips all four new fields, incl. a field staying `None` and
  update preservation → `tests/test_store.py::test_source_span_fields_round_trip`.
- GH-1 dedup / `last_seen` tests left untouched and still green.
- Full suite: 16 passed (re-run green at finalize time).

## Review notes

- The model + store change passed the review gate (intent / quality / visual
  lenses; visual N/A — data-layer only). Columns come from a fixed list and
  values are parameterized — no injection.
- This ticket is branched on `chore/s2-extract-prep` (the S2 grounding docs +
  fixtures), which is unmerged; the PR stacks on it.

## File map

- `scholarship_factory/models.py` — four source-span fields + the
  evidence-required `@model_validator`.
- `scholarship_factory/store.py` — `_COLUMNS` + `CREATE TABLE` gain the four
  nullable `TEXT` columns.
- `tests/test_models.py`, `tests/test_store.py` — the tests described above.
- `prd.json` — ticket status updates.

## Finalize note

The document stage's first attempt failed with an API stall mid-stream, which
interrupted the run after the review gate had already passed. This changelog
and the done-marking were completed by hand from the committed, review-passed
work; no code was changed.
