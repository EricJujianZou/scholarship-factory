I have everything needed. This is a greenfield Python repo (no source yet), single ticket GH-1, with an autocommit hook on edits. Writing the plan.

---

## Context

Greenfield repo — only `prd.json`, `.github/`, `.claude/settings.json` exist; no Python source, no `progress.txt`, no `skills/`. This ticket creates the entire `scholarship_factory` package from scratch, so there is no neighbouring code to match — conventions come from the ticket itself (uv-managed, pydantic v2, stdlib `sqlite3`, no ORM). Two constraints shape everything: (1) **never fabricate** — `deadline`/`reward`/`cost` are nullable and each pairs with a `quoted|derived|none` provenance enum (no floats); (2) dedup is a `UNIQUE` index on a **normalized** `apply_url`, kept distinct from `source_url`. Note `.claude/settings.json` autocommits every Edit/Write, so a `.gitignore` must land early to keep `__pycache__`/`.venv`/`*.db` out of commits and honor "never a committed db file."

## Approach

Three small modules under `scholarship_factory/`: `models.py` (a `Provenance` str-enum + `Opportunity` pydantic v2 model), `urls.py` (a pure `normalize_apply_url()` function), and `store.py` (an `OpportunityStore` class wrapping stdlib `sqlite3`). Splitting URL normalization into its own pure function lets it be unit-tested in isolation and keeps the store focused on persistence. The store uses SQLite's `INSERT ... ON CONFLICT(normalized_apply_url) DO UPDATE SET last_seen=excluded.last_seen` so dedup and the `last_seen`-refresh-on-re-insert are one atomic statement against the `UNIQUE` index — the DB enforces the invariant rather than read-then-write Python logic (which would race and duplicate). Timestamps and `normalized_apply_url` are store-managed (computed on write), not model fields the caller supplies. Rejected alternative: a `confidence: float` per fact — explicitly forbidden by the ticket ("provenance, not a confidence score — no floats"). Rejected: an ORM (SQLAlchemy) — ticket says stdlib `sqlite3` is fine for v1; an ORM is over-build.

## Steps

1. Create `pyproject.toml` (uv-managed) in `scholarship_factory` — `[project]` name `scholarship-factory`, `requires-python = ">=3.11"`, `dependencies = ["fastapi", "pydantic>=2"]`; `[dependency-groups] dev = ["pytest", "httpx"]` (uv syncs the `dev` group by default so `uv run pytest` resolves); `[build-system]` = hatchling with `[tool.hatch.build.targets.wheel] packages = ["scholarship_factory"]`. Done when `uv run pytest -q` executes (even "no tests" is fine at this point) from repo root.
2. Create `.gitignore` at repo root — entries `__pycache__/`, `*.pyc`, `.venv/`, `*.db`, `*.sqlite3`, `uv.lock` optional-keep. Done when no `.venv`/`*.db`/`__pycache__` paths can be staged by the autocommit hook.
3. Create `scholarship_factory/__init__.py` — re-export `Opportunity`, `Provenance`, `OpportunityStore`, `normalize_apply_url`. Done when `from scholarship_factory import Opportunity, OpportunityStore` imports cleanly.
4. Create `scholarship_factory/models.py` — `class Provenance(str, Enum)` with `QUOTED="quoted"`, `DERIVED="derived"`, `NONE="none"`; `class Opportunity(BaseModel)` (pydantic v2). Fields: `id: str` (default `uuid4().hex`), `title: str`, `apply_url: str`, `source_url: str`, all required; nullable `deadline/reward/cost/organization/requirements/type/description: str | None = None`; `deadline_provenance/reward_provenance/cost_provenance: Provenance = Provenance.NONE`; `owner: str = "me"`; `status: str = "new"`; `first_seen: str | None = None`, `last_seen: str | None = None` (store-populated). Done when `Opportunity(title=..., apply_url=..., source_url=..., deadline=None, deadline_provenance="none")` validates and an invalid provenance string raises `ValidationError`.
5. Create `scholarship_factory/urls.py` — `normalize_apply_url(url: str) -> str`: `urlsplit`, force scheme→`https` (http/https equal), lowercase host, drop tracking query params (prefix `utm_` plus set `{"fbclid","gclid","mc_eid","ref","ref_src"}`), keep remaining params sorted, strip trailing `/` from path (root `/`→``), reassemble via `urlunsplit`. Done when the three normalization cases (tracking param, trailing slash, http-vs-https) collapse to one identical string in unit tests.
6. Create `scholarship_factory/store.py` — `class OpportunityStore`: `__init__(self, db_path)` (configurable path; opens `sqlite3.connect`, sets `row_factory = sqlite3.Row`, calls `_init_schema`). Schema: `opportunities` table with all model columns + a `normalized_apply_url TEXT NOT NULL` column and `CREATE UNIQUE INDEX ... ON opportunities(normalized_apply_url)`. Methods: `insert(opp)` (compute `normalized_apply_url`, set `first_seen`/`last_seen=now` UTC ISO via `datetime.now(timezone.utc).isoformat()`, `INSERT ... ON CONFLICT(normalized_apply_url) DO UPDATE SET last_seen=excluded.last_seen`, then return the stored row as `Opportunity`); `get(id) -> Opportunity | None`; `list() -> list[Opportunity]`; `update(opp) -> Opportunity` (update row by `id`, refresh `last_seen`). Add `_row_to_opp` helper. Done when CRUD round-trips and re-insert of a dedup-equal URL leaves one row with a newer `last_seen`.
7. Create `tests/test_models.py` — assert null-deadline + `deadline_provenance="none"` construction is valid; `owner` defaults `"me"` and `status` defaults `"new"`; invalid provenance raises `ValidationError`. Done when these pass.
8. Create `tests/test_urls.py` — assert the three normalization cases produce equal normalized strings and a genuinely different URL does not collide. Done when these pass.
9. Create `tests/test_store.py` — use `tmp_path` fixture for the db file (never committed); cover CRUD round-trip (insert→get→list→update), the three dedup cases each leaving exactly one row, and `last_seen` refresh (re-insert yields newer `last_seen`, same `id`, `first_seen` unchanged); `first_seen`/`last_seen` non-null after write. Done when these pass.
10. Verify full suite — `uv run pytest -q` green from repo root. Done when exit code 0 with all tests passing and no network used.

## Acceptance criteria mapping

- "`pyproject.toml` (uv-managed) and a `scholarship_factory` package exist, and `uv run pytest -q` runs and passes" -> steps 1, 3, 10; verified by `uv run pytest -q` exit 0.
- "`Opportunity` model … `deadline`/`reward`/`cost` nullable, each carries provenance enum `quoted|derived|none`; null `deadline` + `deadline_provenance="none"` is valid" -> step 4; verified by `tests/test_models.py`.
- "SQLite store supports insert, get-by-id, list, update; db path configurable; tests use a temporary database" -> steps 6, 9; verified by `tests/test_store.py` using `tmp_path`.
- "dedup via `UNIQUE` index on normalized `apply_url` (tracking params, trailing slash, http-vs-https); re-insert updates `last_seen` instead of duplicating" -> steps 5, 6, 8, 9; verified by `tests/test_urls.py` + `tests/test_store.py` dedup/refresh cases.
- "`owner` defaults `\"me\"`; `first_seen`/`last_seen` populated on write" -> steps 4, 6; verified by `tests/test_models.py` (default) + `tests/test_store.py` (timestamps non-null).
- "Unit tests cover model construction (null-deadline+provenance), store CRUD round-trip, URL-normalization dedup (three cases), `last_seen` refresh; no network/external services" -> steps 7, 8, 9; verified by the three test files (all in-process, `tmp_path`).
- "Full suite `uv run pytest -q` stays green" -> step 10; verified by final `uv run pytest -q`.

## Risks

1. **`uv run pytest` can't import the package** — if the build backend/packages config is wrong, the package won't install into uv's env and tests fail on import. If it materializes, confirm `[tool.hatch.build.targets.wheel] packages = ["scholarship_factory"]` matches the dir name and that `scholarship_factory/__init__.py` exists; as a fallback set `[tool.pytest.ini_options] pythonpath = ["."]`.
2. **`ON CONFLICT` target mismatch** — the conflict clause must name the column carrying the `UNIQUE` index (`normalized_apply_url`); if SQLite raises "no unique constraint matching", ensure the `UNIQUE INDEX` (or inline `UNIQUE`) is created on exactly that column before any insert.
3. **Over-engineering URL normalization** — the ticket warns this is a heuristic, not identity. Keep the tracking-param list small and the function pure; do not add `www.`-stripping, port handling, or unicode host punycode beyond what the three test cases need.

```json
{
  "stage": "plan",
  "ticket_id": "GH-1",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan to bootstrap uv/pydantic-v2 scholarship_factory package: Provenance enum + Opportunity model, pure URL normalizer, stdlib sqlite3 store with ON CONFLICT dedup on normalized_apply_url, and three test files.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {"edit": ["pyproject.toml", ".gitignore", "scholarship_factory/__init__.py", "scholarship_factory/models.py", "scholarship_factory/urls.py", "scholarship_factory/store.py", "tests/test_models.py", "tests/test_urls.py", "tests/test_store.py"], "read": ["prd.json", ".claude/settings.json"]}
}
```