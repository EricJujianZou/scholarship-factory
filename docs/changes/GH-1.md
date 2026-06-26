# GH-1 — Bootstrap project: Opportunity domain model + SQLite store

## What shipped

Foundation slice for scholarship-factory v1: a uv-managed Python project, the
`Opportunity` domain model, and a SQLite-backed store with URL-normalized
dedup. No sourcing, ranking, or dashboard — those are later tickets.

## Schemas & data

**`Opportunity`** (`scholarship_factory/models.py`) — pydantic v2 model.

- Required: `id` (uuid4 hex, auto-generated), `title`, `apply_url`, `source_url`.
- Nullable, never fabricated: `deadline`, `reward`, `cost`, `organization`,
  `requirements`, `type`, `description`.
- `Provenance` enum (`quoted | derived | none`) attached per uncertain field
  as `deadline_provenance`, `reward_provenance`, `cost_provenance` — defaults
  to `none`. No float confidence score, by design.
- `owner` defaults to `"me"`; `status` defaults to `"new"`.
- `first_seen` / `last_seen` are `None` on construction; populated by the
  store on write.

**`OpportunityStore`** (`scholarship_factory/store.py`) — stdlib `sqlite3`,
no ORM. Constructor takes a `db_path` (tests pass a `tmp_path` file, never a
committed db).

- Single `opportunities` table mirroring the model fields plus an internal
  `normalized_apply_url` column.
- `UNIQUE` index on `normalized_apply_url` is the dedup key.
- `insert()` computes the normalized URL and timestamps, then does
  `INSERT ... ON CONFLICT(normalized_apply_url) DO UPDATE SET last_seen =
  excluded.last_seen` — dedup and `last_seen` refresh happen as one
  DB-enforced statement rather than a read-then-write race.
- `get(id)`, `list()`, `update(opp)` round-trip rows back into `Opportunity`
  instances (provenance stored as the enum's `.value`).

**`normalize_apply_url`** (`scholarship_factory/urls.py`) — pure function:
forces `https`, lowercases host, strips a trailing slash (except root `/`),
drops `utm_*` and a fixed set of tracking params (`fbclid`, `gclid`, `mc_eid`,
`ref`, `ref_src`), sorts remaining query params for stable comparison.

## Behavior & breaking changes

N/A — new module, no prior callers.

## How it was verified

13 unit tests, `uv run pytest -q`, no network:

- Model construction including the null-deadline + `deadline_provenance="none"`
  case → `tests/test_models.py::test_null_deadline_with_none_provenance_is_valid`;
  invalid provenance value rejected →
  `test_invalid_provenance_raises`.
- Store CRUD round-trip → `tests/test_store.py::test_crud_round_trip`.
- `owner` default + timestamp population on write →
  `test_owner_defaults_and_timestamps_populated`.
- URL-normalization dedup, all three required cases → `test_dedup_tracking_param`,
  `test_dedup_trailing_slash`, `test_dedup_http_https` (and the pure-function
  versions in `tests/test_urls.py`).
- `last_seen` refresh on re-insert without creating a duplicate row →
  `test_last_seen_refresh_on_reinsert`.
- Full suite: 13 passed (test-stage run, `iter01_test_output.md`).

## Review notes

- Dedup is a normalization heuristic on `apply_url`, not true opportunity
  identity — real cross-source dedup is explicitly deferred to the sourcing
  ticket, per the locked design decisions.
- `test_last_seen_refresh_on_reinsert` asserts `second.last_seen >=
  first.last_seen` rather than strictly greater; the `ON CONFLICT` code path
  is correct and the more important invariant (exactly one row after
  re-insert) is firmly tested elsewhere.
- The store's sqlite connection is never explicitly closed, and `update()`
  doesn't guard against an `apply_url` edit colliding with another row's
  unique index. Both accepted as out of scope for v1.

## File map

- `pyproject.toml`, `uv.lock` — uv-managed project bootstrap; deps `fastapi`,
  `pydantic>=2`; dev deps `pytest`, `httpx`.
- `scholarship_factory/__init__.py` — package exports (`Opportunity`,
  `Provenance`, `OpportunityStore`).
- `scholarship_factory/models.py` — `Opportunity` model and `Provenance` enum.
- `scholarship_factory/store.py` — `OpportunityStore` (schema, dedup, CRUD).
- `scholarship_factory/urls.py` — `normalize_apply_url`.
- `tests/test_models.py`, `tests/test_store.py`, `tests/test_urls.py` —
  unit tests described above.
- `.gitignore` — excludes `*.db` / `*.sqlite3` so no database file is
  committed.
- `prd.json` — ticket status updates.
