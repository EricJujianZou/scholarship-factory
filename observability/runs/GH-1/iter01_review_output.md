Review complete. I've read the full diff (all source + tests + config), the plan/implement/test stage outputs, and confirmed the test stage's "13 passed" against the actual test code (I couldn't re-run `uv run pytest` myself — the harness denied the command — so I relied on the test-stage evidence plus a line-by-line read of the code).

## Lens 1 — Intent (acceptance criteria, one by one)

1. **uv project + package + green suite** — ✅ `pyproject.toml` is uv-managed (`[dependency-groups] dev`), `uv.lock` committed, `scholarship_factory/` package exists; test stage ran 13 passed.
2. **Opportunity model, nullable deadline/reward/cost + provenance enum** — ✅ `models.py:7-35`; `Provenance(str, Enum)` = quoted/derived/none; `test_null_deadline_with_none_provenance_is_valid` confirms the required case; invalid value raises `ValidationError`.
3. **SQLite store insert/get/list/update, configurable path, temp db** — ✅ `store.py`; `db_path` is a ctor arg; tests use `tmp_path`; `.gitignore` excludes `*.db`/`*.sqlite3` and no db file is in the diff.
4. **Dedup via UNIQUE index on normalized apply_url (3 cases) + last_seen refresh** — ✅ UNIQUE index + `ON CONFLICT(normalized_apply_url) DO UPDATE SET last_seen = excluded.last_seen`; `urls.py` handles tracking params, trailing slash, http/https; all three dedup cases + refresh tested.
5. **owner defaults "me"; first_seen/last_seen on write** — ✅ verified in model defaults and `test_owner_defaults_and_timestamps_populated`.
6. **Required unit-test coverage, no network** — ✅ all four required areas covered, purely in-process.
7. **Full suite green** — ✅ 13 passed.

## Lens 2 — Quality & security
- SQL uses f-strings but **only** for static `_COLUMNS` names; all values are parameterized — no injection. No secrets. `ON CONFLICT` logic correctly preserves `first_seen` and refreshes `last_seen` (read the code, confirmed). Provenance enum-to-`.value` normalization on write is clean and round-trips correctly.
- **Non-blocking notes** (not must-fix, for future tickets): `test_last_seen_refresh_on_reinsert` asserts `second.last_seen >= first.last_seen`, which wouldn't catch a no-op refresh on its own — but the code path is verifiably correct and the more important "exactly one row" invariant is firmly tested. The store never closes its connection, and `update()` could raise `IntegrityError` if `apply_url` is mutated into a collision — both out of scope for v1.

## Lens 3 — Visual
No user-facing surface in this ticket (domain model + store only; FastAPI is a declared dependency but no routes/UI). Visual verification N/A.

The work holds across all three lenses and the working tree is clean. This is a clean first solve of the "bootstrap pydantic-model + sqlite-store" class — candidate for a `skills/` entry (for a human/system-repair ticket to create).

```json
{
  "stage": "review",
  "ticket_id": "GH-1",
  "outcome": "success",
  "exit_signal": true,
  "summary": "All 7 acceptance criteria verified against code and tests (13 passed in test stage). Opportunity model, pure URL normalizer, and stdlib-sqlite3 store with ON CONFLICT dedup are correct; no injection/secrets; no user-facing surface (visual N/A). Minor non-blocking notes: last_seen-refresh test uses >= and the conn is never closed. Clean first solve of the model+store class — candidate for a skills/ entry.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Bootstrap scholarship-factory v1: the Opportunity domain model + its SQLite store.\n\nWhat changed:\n- uv-managed Python project at repo root (pyproject.toml + uv.lock; deps fastapi/pydantic, dev pytest/httpx) and the scholarship_factory package.\n- Opportunity pydantic v2 model: required id/title/apply_url/source_url; nullable deadline/reward/cost/organization/requirements/type/description; quoted|derived|none Provenance enum per uncertain fact (no float confidence by design); owner defaults 'me', status defaults 'new'; store-populated first_seen/last_seen.\n- normalize_apply_url(): pure function forcing https, lowercasing host, stripping utm_*/tracking params, sorting remaining query, and normalizing trailing slash.\n- OpportunityStore (stdlib sqlite3, no ORM): configurable db path, schema with a UNIQUE index on normalized_apply_url, insert/get/list/update, and INSERT ... ON CONFLICT DO UPDATE SET last_seen so dedup + last_seen refresh are one atomic statement enforced by the DB.\n- 13 unit tests (model null-deadline+provenance, CRUD round-trip, the three URL-dedup cases, last_seen refresh); all use tmp_path, no network.\n\nKey design honored: never fabricate (nullable facts + provenance, no floats), single-user 'owner' seam, source_url kept distinct from apply_url, dedup deliberately heuristic.\n\nRisks/notes for the merger: dedup is a normalization heuristic, not true opportunity identity (real cross-source dedup is deferred). The last_seen-refresh test asserts >= rather than strictly-greater (code path is correct; worth tightening later). The sqlite connection is never explicitly closed and update() doesn't guard against an apply_url change colliding with another row's unique index — both acceptable for v1 scope."
}
```