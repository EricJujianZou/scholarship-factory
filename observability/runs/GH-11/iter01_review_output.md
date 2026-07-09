Execution of `uv run` is blocked in this read-only review session, so I'll rely on the test stage's evidence plus direct code reading (the sanctioned fallback). I've read the actual `fetch.py` code, not just the prose. Here's my three-lens review.

## Review — GH-11: FetchResult contract

**Diff reviewed:** `scholarship_factory/fetch.py` (new), `scholarship_factory/__init__.py:2,17`, `tests/test_fetch.py` (new). Product code is committed; the only uncommitted files are harness bookkeeping (`observability/runs/GH-11/iter01_test*`, `state.json`) — expected mid-run, not product dirt.

### Lens 1 — intent (each criterion vs. evidence)

1. **`FetchResult` exists w/ all fields + derived `ok`** ✓ — `fetch.py:6-22`: `requested_url: str`, `final_url: str`, `status_code: int | None`, `content_type: str | None`, `body: str | None`, `fetched_at: datetime` (default_factory), `error: str | None`, and `ok` as a `@computed_field` property. Pydantic v2, matches `models.py` house style.
2. **`ok` derivation + honest failures** ✓ — `ok = status_code is not None and 200 <= status_code < 300 and body is not None`. Correct: 2xx+body→True; `None`/4xx/5xx/no-body→False. `body=None` failure constructs fine (no validator forbids it). Tests `test_success`, `test_404`, `test_403`, `test_connection_failure`, `test_2xx_with_no_body` cover it.
3. **`final_url` == / ≠ `requested_url`** ✓ — two independent `str` fields; `test_final_url_defaults_to_requested_url` and `test_final_url_can_differ_after_redirect` cover both. Matches the locked source_url-is-final-URL decision, and `extract()` consumes exactly this `final_url` as its `source_url` (`extract.py:125`).
4. **`fetched_at` populated on construction** ✓ — `Field(default_factory=lambda: datetime.now(timezone.utc))`, tz-aware; `test_fetched_at_is_populated`.
5. **Tests cover the required cases, no network** ✓ — 8 tests, no `httpx`/network imports in either file.
6. **`uv run pytest -q` green** ✓ (via test-stage evidence) — test stage reports 32 passed; I could not re-run here (execution denied), but the enumerated per-criterion evidence is specific, not vague, and the code reads correct.

### Lens 2 — quality & security
Correct `ok` logic, no off-by-one (range `200–299`). Deliberately uses `body is not None` (not `bool(body)`) so an empty-but-successful page `body=""` stays `ok=True` — honors the no-fabrication decision. No secrets, subprocess, file, or network handling — pure data model. No dead code; tests assert real behavior.

### Lens 3 — visual
No user-facing surface (a typed model). Nothing to render; Playwright N/A.

**Verdict: success.** Every criterion verified with evidence, no must-fix issues, product branch clean.

```json
{
  "stage": "review",
  "ticket_id": "GH-11",
  "outcome": "success",
  "exit_signal": true,
  "summary": "FetchResult contract holds against all 6 criteria. Read fetch.py directly: pydantic v2 model with the 8 required fields and a computed `ok` (2xx AND body-present), honest failure representation (body=None valid), final_url distinct from requested_url. 8 no-network tests map to each criterion; test stage reports 32 passed (could not re-run pytest here — execution denied in review session — verified by code reading + test-stage evidence). No user-facing surface. Non-product working-tree changes are harness artifacts only.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds the `FetchResult` pydantic v2 contract — the typed hand-off object between Fetch (S3) and Extract (S2). This is a foundation slice: the shared data shape only, with no fetching, adapters, or network.\n\n`FetchResult` carries `requested_url`, `final_url` (post-redirect; this is Extract's `source_url`), nullable `status_code`/`content_type`/`body`, an auto-populated tz-aware `fetched_at`, nullable `error`, and a derived `ok` (`True` iff status is 2xx and body is present). Failed fetches are represented honestly — a `body=None`/`status_code=None` result is valid and reports `ok=False` rather than masquerading as empty-but-successful content.\n\nTradeoff: `ok` is a read-only `@computed_field` rather than a stored/validated field, so it can never be set to a value contradicting its inputs. `ok` uses `body is not None` (not truthiness), so an empty-but-successful page (`body=\"\"`) stays `ok=True`, per the locked no-fabrication decision.\n\nRisks: none of note. Pure data model, no network, no I/O. 8 unit tests cover success / 404 / 403 / connection-failure / redirect / empty-body cases with no network; full suite green (32 passed)."
}
```