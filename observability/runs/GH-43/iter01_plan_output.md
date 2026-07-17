I have what I need. Verified against the repo: FastAPI 0.138.1 and httpx 0.28.1 are already installed (so `TestClient` works), but **uvicorn is absent from `uv.lock`** and must be added. The one real design hazard I found is SQLite thread affinity, which the plan pins down explicitly.

## Context

- `rank.rank(opportunities, profile, today=None) -> RankedResults` (`scholarship_factory/rank.py:126`) already returns exactly the shape the ticket's API needs: `eligible`/`excluded` lists of `RankedOpportunity` (`rank.py:30`), each carrying the full `Opportunity` (verbatim `deadline`/`reward` strings — `models.py:19-20`), a `verdict`, `reasons`, and the *parsed* `deadline: date | None` + `reward: MoneyValue | None`. Parsed-alongside-verbatim is structural, so no new serialization model is needed.
- `ProfileStore` (`profile.py:42`) has `insert`/`get(id)`/`list()`/`update`, but **no "get the single profile" accessor** — the API must resolve `owner="me"`'s profile via `list()`, creating a default row on first read.
- `OpportunityStore.__init__` / `ProfileStore.__init__` open a `sqlite3.connect` at construction (`store.py:38`, `profile.py:45`) with the default `check_same_thread=True`. FastAPI runs sync `def` endpoints in a threadpool, so a store built once at app-construction time would raise `ProgrammingError` on request. This constraint shapes the whole design.
- `cli.py:24` sets the db-path convention: `--db`, else `$SF_DB_PATH`, else `./scholarship_factory.db`. `serve` reuses `_default_db_path()` verbatim.
- `fastapi`/`httpx` are in `uv.lock`; `uvicorn` is not.

## Approach

Build `api.py` around a `create_app(db_path)` factory that closes over the path only, and open both stores **per request** inside a FastAPI dependency. SQLite connections are cheap, this is a single-user local service, and per-request construction keeps each connection on the thread that uses it — sidestepping the `check_same_thread` failure that a shared app-level store would hit under both TestClient and uvicorn. Endpoints return `RankedResults` directly as the response model: it already pairs parsed values with verbatim strings, and pydantic serializes `deadline=None` to JSON `null`, satisfying the no-fabrication rule for free.

The rejected alternative was a single module-level store plus `async def` endpoints. It avoids the threadpool but not the bug: the store is still constructed on the main thread and used on the event-loop thread, so the cross-thread error remains — and it would force async endpoints purely to work around a connection lifetime issue, which is the wrong reason to pick a concurrency model.

## Steps

1. Add `uvicorn` to `dependencies` in `pyproject.toml` via `uv add uvicorn` — done when `uv.lock` contains `name = "uvicorn"` and `uv run python -c "import uvicorn"` succeeds.
2. Create `scholarship_factory/api.py` with `_default_db_path()` imported from `.cli` and a `create_app(db_path: str) -> FastAPI` factory — done when `create_app(":memory:")` returns a `FastAPI` instance.
3. In `api.py`, add a `_load_or_create_profile(store: ProfileStore) -> ApplicantProfile` helper: return `store.list()[0]` if non-empty, else `store.insert(ApplicantProfile())` (owner stays `"me"`) — done when calling it twice on a fresh db yields the same `id`.
4. In `api.py`, add `GET /api/opportunities` returning `rank(OpportunityStore(db_path).list(), _load_or_create_profile(ProfileStore(db_path)))` typed as `response_model=RankedResults`, with both stores opened inside the request handler — done when a seeded db returns `{"eligible": [...], "excluded": [...]}`.
5. In `api.py`, add `GET /api/profile` (returns `ApplicantProfile`) and `PUT /api/profile` taking a `ProfileUpdate` pydantic body of `region`, `education_level`, `field_of_study`, `tags: list[str]`, `bio` — apply via `existing.model_copy(update=body.model_dump())` so `id`/`owner`/`created_at` are preserved, then `store.update(...)` — done when `PUT` then `GET` round-trips all five fields with an unchanged `id`.
6. Create `scholarship_factory/static/index.html`: self-contained vanilla-JS page that fetches `/api/opportunities` and `/api/profile`, renders eligible cards (title, org, verbatim deadline, verbatim reward, `apply_url` anchor), a `<details>` excluded section listing `verdict` + `reasons`, and a profile `<form>` issuing `PUT /api/profile` then re-fetching. Render any absent fact as the literal text `no deadline found` / `no reward found` — never a placeholder value — done when the file references both endpoint paths and has no build step or CDN import.
7. In `api.py`, mount `GET /` returning `FileResponse(Path(__file__).parent / "static" / "index.html", media_type="text/html")` — done when `GET /` returns 200 with `text/html` content-type.
8. Add a `serve` subparser in `cli.py` (`--host` default `127.0.0.1`, `--port` default `8000`, inheriting the existing `common` `--db` parent) that calls `uvicorn.run(create_app(args.db or _default_db_path()), host=..., port=...)`, importing `uvicorn` inside `_cmd_serve` to keep `sf list`/`show` import-light — done when `sf serve --help` exits 0.
9. Create `tests/test_api.py` following `tests/test_cli.py:12`'s `tempfile.mkstemp` pattern: a fixture seeding an eligible future-deadline opp, a `deadline=None` opp, an expired opp (`deadline="January 1, 2020"`), and an EU-only opp against a `region="Canada"` profile; build `TestClient(create_app(path))` — done when all five acceptance tests below pass.
10. Run `uv run pytest -q` — done when the full suite is green.

## Acceptance criteria mapping

- `"GET /api/opportunities` on a seeded temp db returns eligible items in rank order plus excluded items with verdicts/reasons; parsed deadline/reward appear alongside the verbatim stored strings."` -> steps 4, 9; verified by `test_opportunities_ranked_with_parsed_and_verbatim` asserting `eligible` titles in deadline order, `excluded[0]["verdict"] == "ineligible"` with a non-empty `reasons`, and for a `reward="$5,000"` opp both `item["opportunity"]["reward"] == "$5,000"` and `item["reward"]["amount"] == 5000.0`.
- `"An opportunity with deadline=None serializes with a null deadline (nothing invented) and the page renders it as absent."` -> steps 4, 6, 9; verified by `test_missing_deadline_serializes_null` asserting `item["deadline"] is None` and `item["opportunity"]["deadline"] is None`, plus an assertion that `index.html` contains the string `no deadline found`.
- `"PUT /api/profile updates region/education_level/field_of_study/tags/bio and a subsequent GET /api/opportunities reflects re-ranking against the new profile."` -> steps 3, 5, 9; verified by `test_profile_update_reranks`: the EU-only opp is excluded under `region="Canada"`, then `PUT /api/profile` with `region="Germany"` (an `_REGION_ALIASES` entry mapping to `eu`, `rank.py:51`) moves it into `eligible`.
- `"GET / serves the dashboard HTML (asserted 200 + content-type html; page references the two API endpoints)."` -> steps 6, 7, 9; verified by `test_root_serves_dashboard` asserting `status_code == 200`, `"text/html" in r.headers["content-type"]`, and both `/api/opportunities` and `/api/profile` in `r.text`.
- `"No auth added; TestClient only, no network; uv run pytest -q green."` -> steps 9, 10; verified by the whole `tests/test_api.py` using only `TestClient` with no `fetch`/network import and no auth dependency anywhere in `api.py`.

## Risks

1. **SQLite cross-thread error.** If the implementer hoists the stores to app scope (the obvious "efficient" move), sync endpoints in FastAPI's threadpool will raise `ProgrammingError: SQLite objects created in a thread can only be used in that thread`. Keep store construction inside the request handler as specified in step 4. If a shared store is genuinely wanted later, it needs `check_same_thread=False` plus a lock — out of scope here.
2. **Per-request connections are never closed.** Neither store exposes a `close()`, so connections are reclaimed only on GC. Acceptable for a single-user local service; do **not** "fix" it by editing `store.py`/`profile.py` — that would exceed this ticket's surface.
3. **Ranking uses `date.today()`.** `rank()` has no injectable `today` at the API layer, so tests must not use near-term relative deadlines. Use an explicit far-past year (`"January 1, 2020"`) for the expired case and a far-future one (`"September 15, 2099"`) for the eligible case, so verdicts hold no matter when the suite runs. Note `typed_deadlines` (`parse_dates.py:44`) needs an anchor from `source_observed_date` or `first_seen`; `store.insert` always sets `first_seen`, so seeded opps parse correctly.

```json
{
  "stage": "plan",
  "ticket_id": "GH-43",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for the read API + dashboard: create_app(db_path) factory in api.py with per-request SQLite stores (avoids FastAPI threadpool cross-thread error), RankedResults returned directly as the response model so parsed values ship alongside verbatim strings, a static index.html at /, an sf serve subcommand, and TestClient tests. uvicorn is missing from uv.lock and must be added via uv add.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/api.py",
      "scholarship_factory/static/index.html",
      "scholarship_factory/cli.py:74",
      "tests/test_api.py",
      "pyproject.toml:5",
      "uv.lock"
    ],
    "read": [
      "scholarship_factory/rank.py:126",
      "scholarship_factory/rank.py:30",
      "scholarship_factory/profile.py:42",
      "scholarship_factory/store.py:35",
      "scholarship_factory/models.py:13",
      "scholarship_factory/parse_money.py:23",
      "scholarship_factory/parse_dates.py:44",
      "tests/test_cli.py:12",
      "tests/test_rank.py:12",
      "tests/test_profile.py:21"
    ]
  }
}
```