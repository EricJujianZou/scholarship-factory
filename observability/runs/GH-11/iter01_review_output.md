I have everything I need. Here is my review.

## Review — GH-11: FetchResult contract

**Manifest sufficiency:** The plan's manifest (`fetch.py`, `__init__.py`, `test_fetch.py`) is accurate — those are the only product-code changes; the rest of the diff is harness bookkeeping (`prd/`, `observability/`, `docs/`, `state.json`, `CLAUDE.md`/`notes_for_claude.md` prose).

### Lens 1 — intent (acceptance criteria, walked one by one)

1. **Type exists, pydantic v2, all 8 fields + derived `ok`** ✓ — `fetch.py:6-22`: `requested_url`, `final_url`, `status_code: int|None`, `content_type: str|None`, `body: str|None`, `fetched_at`, `error: str|None`, plus `ok` as a `@computed_field` property. Exported in `__init__.py:2,17`.
2. **`ok` derivation + honest failure** ✓ — `ok = status_code is not None and 200 <= status_code < 300 and body is not None`. Verified by `test_success_result_is_ok`, `test_404`/`test_403`, `test_2xx_with_no_body_is_not_ok`, and `test_connection_failure...` (constructs with `body=None`, valid). Note the deliberate `body is not None` (not `bool(body)`), so an empty-but-successful page (`body=""`) stays `ok=True` — correctly honors the locked no-fabrication decision.
3. **`final_url` may equal or differ from `requested_url`** ✓ — two independent `str` fields; `test_final_url_defaults_to_requested_url` and `test_final_url_can_differ_after_redirect`.
4. **`fetched_at` populated on construction** ✓ — `Field(default_factory=lambda: datetime.now(timezone.utc))`; `test_fetched_at_is_populated`.
5. **Tests cover success / 404-403 / connection-failure (`status_code=None`+`error`) / `ok` derivation, no network** ✓ — 8 tests, no `httpx`/network import anywhere.
6. **`uv run pytest -q` green** ✓ — test stage evidence: 32 passed (8 in `test_fetch.py`). (I could not re-run locally — the sandbox denied every pytest invocation — but the code is trivially verifiable by reading and the test-stage evidence is concrete, not vague.)

### Lens 2 — quality & security
- **Correctness:** `ok` logic is sound across all branches (None status, 4xx/5xx, empty body, empty-string body). `computed_field`/`property` decorator order is correct. No off-by-one or unhandled-None paths.
- **Security:** No network, subprocess, file, or secret handling — pure data model. Clean.
- **Hygiene:** No dead code; every test asserts meaningfully. Matches `models.py` house style.

One design note (not a defect): `final_url` has no auto-default copying `requested_url`; the producing fetcher (a later ticket) sets it. This is consistent with the plan and keeps the contract honest — flagging only for awareness, not as a fix.

### Lens 3 — visual
No user-facing surface — `FetchResult` is a pure typed data contract. Playwright not applicable; nothing to render.

**Verdict:** All three lenses pass, every criterion verified against evidence, working tree clean. `exit_signal: true`.

```json
{
  "stage": "review",
  "ticket_id": "GH-11",
  "outcome": "success",
  "exit_signal": true,
  "summary": "FetchResult contract meets all 6 acceptance criteria: pydantic v2 model with 8 fields + derived `ok`, honest failure representation (body=None valid, empty-string body stays ok), final_url distinct from requested_url, fetched_at auto-populated. 8 unit tests, no network. All three review lenses pass; no user-facing surface. Clean first solve of the 'shared typed seam' class — candidate for a skills/ entry.",
  "failure_reason": null,
  "files_changed": 3,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds the `FetchResult` contract — the typed hand-off between Fetch (S3) and Extract (S2). Foundation slice only: defines the data shape, no fetching, adapters, or network.\n\n**What changed**\n- New `scholarship_factory/fetch.py`: `FetchResult` (pydantic v2) with `requested_url`, `final_url` (post-redirect; this is Extract's `source_url`), nullable `status_code`/`content_type`/`body`/`error`, auto-populated `fetched_at` (tz-aware UTC), and a derived `ok` computed field (`True` iff 2xx and body present).\n- Exported from `scholarship_factory/__init__.py`.\n- `tests/test_fetch.py`: 8 tests covering success, 404/403, connection failure (status=None + error), redirect divergence, fetched_at population, and the ok derivation. No network.\n\n**Notes for the merger**\n- `ok` uses `body is not None`, so an empty-but-successful page (`body=\"\"`) is `ok=True` — deliberate, honoring the locked no-fabrication decision (a failed fetch must be distinguishable from an empty one).\n- `final_url` is a required field with no auto-default; the fetcher that populates it (a later ticket) is responsible for setting it equal to `requested_url` when no redirect occurred.\n- Merges first so the next S3 wave (static fetcher, politeness, adapters, cache) can branch from it."
}
```