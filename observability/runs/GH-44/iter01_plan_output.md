I've read the store, models, extract, fetch, cache, identity, pipeline, api, cli, the dashboard, and the neighbouring tests. Here is the plan.

## Context

- `scholarship_factory/store.py:119` — `OpportunityStore.update()` writes every column except `first_seen` and always bumps `last_seen`. That is exactly right for the `refreshed`/`changed` paths and exactly wrong for `unreachable` ("record otherwise untouched" — we did *not* see the record, so `last_seen` must not move). This is the one store change the ticket forces.
- `scholarship_factory/models.py:13` — `Opportunity` holds the three uncertain facts as `(value, *_provenance, *_source)` triples; the `_require_source_for_provenance` validator (`models.py:42`) means value/source/provenance must always be updated together. `status: str` defaults to `"new"` (`models.py:37`).
- `scholarship_factory/pipeline.py:50` — the house style for a composed run: injectable `fetch_fn`/`extract_fn` defaulting to the real `fetch_url`/`extract`, failures recorded in a pydantic report object rather than raised. `refresh.py` mirrors it.
- `scholarship_factory/cache.py:88` — the cache is opt-in at the *call site* (`cached_fetch` wraps a `fetch_fn`); its docstring already defers field-level refresh to Session 8. Bypassing the cache therefore means: `refresh.py` never imports `cache`, and defaults `fetch_fn=fetch_url`.
- `progress.txt:5` — sqlite stores are `check_same_thread=True`, so FastAPI endpoints must construct the store inside the endpoint body (`api.py:41` follows this).
- `tests/test_cli.py:88` — CLI tests monkeypatch `cli.fetch_url`/`cli.extract`; `_cmd_source` passes them explicitly at call time, so `_cmd_refresh` must too.

## Approach

`refresh_opportunity` re-fetches `opportunity.source_url` with the injected `fetch_fn` (default `fetch_url`, never `cached_fetch` — a refresh must hit the live page), re-extracts with `extract_fn`, picks the candidate whose `normalize_apply_url(apply_url)` matches the stored record, and compares only the three uncertain facts as `(value, source)` pairs. Three write paths: nothing differs → `store.update()` with `status="refreshed"` (which bumps `last_seen` for free); some fact differs → copy the new value/source/provenance onto the record and `store.update()` with `status="changed"`, recording old *and* new in the returned `RefreshOutcome`; fetch not `ok` → a new narrow `store.set_status(id, status)` that writes only the status column, leaving `last_seen` and every fact untouched. A fact present in the row but absent from the re-extract keeps its stored value and is listed in `outcome.no_longer_found`; **I am deciding that case reports `status="changed"`**, because the re-check genuinely found the page differing from what we stored, and the locked state machine (`new|refreshed|changed|unreachable`) has no fifth state to spend on it — the honesty the ticket demands lives in `no_longer_found`, not in a new status.

The rejected alternative was adding a `bump_last_seen: bool` flag to `store.update()` instead of `set_status`. It reads as configurability on a method every caller uses one way, and `unreachable` writes exactly one column — a two-line `set_status` is smaller and says what it does.

To keep the endpoint testable offline, `create_app` gains optional `fetch_fn`/`extract_fn` parameters defaulting to the real ones, matching `run_sourcing`'s injection style. Without this the only way to test `POST /refresh` is a live network call plus an API key.

## Steps

1. Add `set_status(self, id: str, status: str) -> Opportunity | None` in `scholarship_factory/store.py` (after `update`, ~`store.py:136`) issuing `UPDATE opportunities SET status = ? WHERE id = ?` and returning `self.get(id)` — done when a store test shows `set_status` changes `status` while `last_seen`, `first_seen` and every fact column are byte-identical to before.
2. Create `scholarship_factory/refresh.py` with a module docstring stating the cache bypass, `RefreshStatus(str, Enum)` (`NEW|REFRESHED|CHANGED|UNREACHABLE`), `FieldChange(BaseModel)` (`field`, `old_value`, `new_value`, `old_source`, `new_source`) and `RefreshOutcome(BaseModel)` (`opportunity_id: str`, `status: str`, `changed_fields: list[FieldChange] = []`, `no_longer_found: list[str] = []`, `fetch_status_code: int | None = None`, `error: str | None = None`) — done when `uv run python -c "from scholarship_factory.refresh import RefreshOutcome"` succeeds.
3. In `refresh.py`, add a private `_pick_candidate(extraction, opportunity)` that returns the extracted opportunity whose `normalize_apply_url(apply_url)` equals the stored record's, else the sole opportunity when the extraction has exactly one and `kind is PageKind.DETAIL`, else `None` — done when unit-covered by the tests in step 8.
4. In `refresh.py`, add `refresh_opportunity(store, opportunity_id, *, fetch_fn=fetch_url, extract_fn=extract) -> RefreshOutcome`: `store.get(opportunity_id)`, raising `KeyError(opportunity_id)` if absent; call `fetch_fn(opp.source_url)`; if not `result.ok`, call `store.set_status(opp.id, RefreshStatus.UNREACHABLE.value)` and return an outcome with `status="unreachable"`, `fetch_status_code=result.status_code`, `error=result.error` — done when the fetch-failure test (step 8) passes.
5. In `refresh.py`, complete `refresh_opportunity`'s success path: call `extract_fn(result.body, result.final_url)`, `_pick_candidate`, then loop the triples `(("deadline", "deadline_provenance", "deadline_source"), ("reward", ...), ("cost", ...))` — for each, if the candidate is `None` or its value is `None`: leave the row's value alone and append the field name to `no_longer_found` **only if the row currently holds a non-`None` value**; if the candidate's `(value, source)` differs from the row's, stage `{value, provenance, source}` into an `updates` dict and append a `FieldChange`. Then `status = CHANGED if (changed_fields or no_longer_found) else REFRESHED`, and `store.update(opp.model_copy(update={**updates, "status": status.value}))` — done when steps 8's unchanged/changed/absent tests pass.
6. Add `POST /api/opportunities/{id}/refresh` to `scholarship_factory/api.py` (after `get_opportunities`, `api.py:44`) with `response_model=RefreshOutcome`, constructing `OpportunityStore(db_path)` inside the endpoint body per `progress.txt:5`, calling `refresh_opportunity(store, id, fetch_fn=fetch_fn, extract_fn=extract_fn)`, and translating `KeyError` into `HTTPException(status_code=404, detail="opportunity not found")`; widen `create_app(db_path=None, *, fetch_fn=fetch_url, extract_fn=extract)` (`api.py:35`) so the closures capture the injected functions — done when a TestClient POST with stub functions returns 200 and an unknown id returns 404.
7. Add a per-card refresh control to `scholarship_factory/static/index.html`: in `renderCard` (`static/index.html:75`) emit `<button class="refresh" data-refresh-id="${escapeHtml(opp.id)}">Refresh</button>`, and register one delegated `click` listener on `#eligible` that POSTs to `` `/api/opportunities/${encodeURIComponent(id)}/refresh` `` and then awaits `loadOpportunities()` — done when the source-contract test in step 9 passes.
8. Add `tests/test_refresh.py` with a `FakeFetch`/`RecordingExtract` pair modelled on `tests/test_pipeline.py:26-65`, `tmp_path` db, covering: unchanged deadline → `last_seen` bumped + `status == "refreshed"` + deadline/source/provenance untouched; new deadline string → row's `deadline` and `deadline_source` are the new ones, `status == "changed"`, and `outcome.changed_fields[0].old_value` still carries the old string; deadline absent from the re-extract → row keeps the old deadline, `outcome.no_longer_found == ["deadline"]`, no fabricated `None`; fetch failure (`status_code=503, body=None, error=...`) → `status == "unreachable"` with `last_seen`/`deadline` unchanged; a `FetchCache` (`cache.py:19`) pre-populated via `put()` with a fresh body for the same `source_url` → the stub `fetch_fn` still records the call and the outcome reflects the stub's body, not the cached one — done when `uv run pytest -q tests/test_refresh.py` is green.
9. Add CLI `refresh` in `scholarship_factory/cli.py`: a `_cmd_refresh(store, opp_id)` that calls `refresh_opportunity(store, opp_id, fetch_fn=fetch_url, extract_fn=extract)` (module-level names, referenced at call time so `tests/test_cli.py:88`-style monkeypatching works), prints `status:`, each changed field's old→new, each `no_longer_found` field, and returns `1` with a `not found: <id>` stderr line on `KeyError` (mirroring `_cmd_show`, `cli.py:39`); register `sub.add_parser("refresh", parents=[common])` with a positional `id` near `cli.py:97` and dispatch it before the `_cmd_show` fallthrough at `cli.py:110`; extend the module docstring's usage block (`cli.py:7`) — done when `uv run pytest -q tests/test_cli.py` covers `refresh` on a stubbed db.
10. Export `refresh_opportunity`, `RefreshOutcome`, `RefreshStatus`, `FieldChange` from `scholarship_factory/__init__.py` (import line near `__init__.py:12`, `__all__` near `__init__.py:61`) — done when `uv run python -c "from scholarship_factory import refresh_opportunity"` succeeds.
11. Add API tests to `tests/test_api.py`: `create_app(path, fetch_fn=stub, extract_fn=stub)` → POST `/api/opportunities/{id}/refresh` returns `status == "changed"` with the new deadline; POST for an unknown id returns 404; plus a source-contract assertion that `data-refresh-id` and `/refresh` appear in `_index_html()` (`tests/test_api.py:79`) — done when `uv run pytest -q` is green overall.

## Acceptance criteria mapping

- "Stubbed re-extract with an unchanged deadline -> `last_seen` bumped, status `refreshed`, fact untouched." -> steps 5, 8; verified by the unchanged-deadline test in `tests/test_refresh.py` asserting `last_seen > before.last_seen`, `status == "refreshed"`, `deadline`/`deadline_source`/`deadline_provenance` equal to the seeded values.
- "Stubbed re-extract with a NEW deadline string -> fact + source span updated, status `changed`, old value gone from the row but the change visible in the outcome object." -> steps 5, 8; verified by the changed-deadline test asserting the row holds the new value/source, `status == "changed"`, and `outcome.changed_fields[0].old_value == "<old string>"`.
- "Stubbed re-extract where the fact is absent -> old value retained, outcome records it as no-longer-found (no silent delete, no fabricated value)." -> steps 5, 8; verified by the absent-fact test asserting `store.get(id).deadline` is unchanged and `outcome.no_longer_found == ["deadline"]`.
- "Fetch failure -> status `unreachable`, record otherwise untouched." -> steps 1, 4, 8; verified by the fetch-failure test asserting `status == "unreachable"` and that `last_seen` and all fact columns match the pre-refresh row exactly.
- "Cache is bypassed (asserted: fetch fn called even with a fresh cache entry present)." -> steps 2, 4, 8; verified by the cache test seeding `FetchCache.put()` with a fresh entry for the `source_url`, then asserting the stub `fetch_fn` recorded the call and the outcome reflects the stub's body (plus `refresh.py` importing nothing from `cache`).
- "All tests offline, temp db; `uv run pytest -q` green." -> steps 6, 8, 9, 11; verified by every test using injected stubs and `tmp_path`/`tempfile` dbs, and by a final full `uv run pytest -q`.

## Risks

- **`store.update()` re-runs `Opportunity`'s validator, and a half-staged fact triple raises.** If the implementer stages a new `deadline` without also staging `deadline_source`/`deadline_provenance`, `_require_source_for_provenance` (`models.py:49`) rejects the copy. Always stage all three from the candidate in one `updates` entry; when the candidate's value is `None`, stage nothing at all.
- **`store.update()` writes via `normalize_apply_url(opp.apply_url)` against a UNIQUE index (`store.py:73`).** A re-extract whose candidate has a different `apply_url` could collide with another row and raise `IntegrityError`. Mitigation: refresh never copies `apply_url`, `title`, or any non-uncertain field from the candidate — only the three fact triples and `status`.
- **The "fact disappeared" status choice may be contested in review.** I chose `changed` + `no_longer_found` over `refreshed`. If review rejects it, the smaller edit is flipping the `status` expression in step 5 to key off `changed_fields` only; the `no_longer_found` list and the retention behaviour stay as-is either way, so no test of criterion 3 needs rewriting.

## File manifest

```json
{
  "stage": "plan",
  "ticket_id": "GH-44",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for on-demand refresh: new refresh.py (fetch->re-extract->field-level compare on deadline/reward/cost, statuses refreshed|changed|unreachable), a narrow store.set_status that leaves last_seen alone for unreachable, POST /api/opportunities/{id}/refresh with injectable fetch/extract, a per-card dashboard button, and sf refresh <id>.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/refresh.py",
      "scholarship_factory/store.py:136",
      "scholarship_factory/api.py:35",
      "scholarship_factory/cli.py:97",
      "scholarship_factory/static/index.html:75",
      "scholarship_factory/__init__.py:12",
      "tests/test_refresh.py",
      "tests/test_api.py:79",
      "tests/test_cli.py:69"
    ],
    "read": [
      "scholarship_factory/models.py:13",
      "scholarship_factory/fetch.py:31",
      "scholarship_factory/extract.py:125",
      "scholarship_factory/cache.py:88",
      "scholarship_factory/identity.py:26",
      "scholarship_factory/pipeline.py:50",
      "scholarship_factory/urls.py",
      "tests/test_pipeline.py:26",
      "tests/test_store.py",
      "progress.txt:5"
    ]
  }
}
```