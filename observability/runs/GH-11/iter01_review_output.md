Running tests is denied under the current permission mode, so I couldn't re-execute the suite myself. I'll rely on the test stage's evidence (32 passed) plus a close reading of the code — for a pure data model this small, code reading is conclusive.

## Review

**Lens 1 — intent (acceptance criteria, walked one by one):**

1. `FetchResult` exists, pydantic v2, all eight fields present with correct nullability + derived `ok` → ✅ `fetch.py:6-22`. Uses `BaseModel`/`computed_field` (v2, consistent with `models.py`).
2. Success (2xx + body) → `ok=True`; failure (`None`, 4xx/5xx, or no body) → `ok=False`, may carry `error`; failure with `body=None` valid → ✅ `ok` derivation at `fetch.py:17-22` is `status_code is not None and 200<=status_code<300 and body is not None`. The `status_code is not None` guard correctly avoids a `TypeError` on the `None` comparison. Covered by `test_success_result_is_ok`, `test_404`, `test_403`, `test_connection_failure`, `test_2xx_with_no_body_is_not_ok`.
3. `final_url` may equal or differ from `requested_url` → ✅ both independent `str` fields; `test_final_url_defaults_to_requested_url` and `test_final_url_can_differ_after_redirect`.
4. `fetched_at` populated on construction → ✅ `default_factory` (tz-aware UTC); `test_fetched_at_is_populated`.
5. Tests cover success / 404-403 / connection-failure (`status_code=None` + `error`) / `ok` derivation, no network → ✅ all present; no `httpx`/network import anywhere in the diff.
6. `uv run pytest -q` green → test stage reports 32 passed; I could not re-run (permission-denied in this session).

**Lens 2 — quality & security:** Clean and minimal. Correctness is sound — notably `body is not None` (not `bool(body)`) correctly keeps an empty-but-successful page (`body=""`) as `ok=True`, honoring the locked "empty ≠ failed" decision. No security surface (no network, subprocess, secrets). No dead code; tests assert meaningfully.

**Lens 3 — visual:** No user-facing surface — `FetchResult` is an internal Fetch→Extract data contract. `final_url` correctly aligns with Extract's `source_url` parameter (`extract.py:127`). Nothing to render.

Every criterion is verified against code and test evidence; no lens found a must-fix issue. The ticket's code is fully committed (uncommitted items are harness-managed `state.json`/observability artifacts only).

```json
{
  "stage": "review",
  "ticket_id": "GH-11",
  "outcome": "success",
  "exit_signal": true,
  "summary": "FetchResult contract satisfies all 6 acceptance criteria: 8 typed fields + derived ok, correct None-guard on status_code, body-is-not-None honors empty-vs-failed, full non-network test coverage. No user-facing surface. Could not re-run pytest (permission-denied this session); relied on test stage evidence of 32 passed plus code read. Clean first solve of a pydantic-contract class — candidate for a fetch-contract skill.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds the typed `FetchResult` contract — the Fetch→Extract seam for Session 3. Foundation slice only: defines the data shape, no fetching/adapters/network.\n\n**What changed:** New `scholarship_factory/fetch.py` with a pydantic v2 `FetchResult` model (`requested_url`, `final_url`, `status_code`, `content_type`, `body`, `fetched_at`, `error`) plus a derived read-only `ok` (`True` iff 2xx status and a body is present). Exported from `scholarship_factory/__init__.py`. Non-network unit tests in `tests/test_fetch.py` cover success, 404/403, connection-failure (`status_code=None` + `error`), redirect vs. no-redirect `final_url`, and the `ok` derivation.\n\n**Notable decisions:** `ok` is a `@computed_field` property, not a stored field, so it can't drift from or be contradicted by callers. `body is not None` (not truthiness) is deliberate — an empty-but-successful page (`body=\"\"`) stays `ok=True`, keeping 'fetched, page empty' distinct from 'fetch failed', per the locked no-fabrication decision. `final_url` is Extract's `source_url` (final post-redirect URL).\n\n**Risks:** None material — pure data model, no network/IO. The fetcher that produces a `FetchResult` is a later ticket."
}
```