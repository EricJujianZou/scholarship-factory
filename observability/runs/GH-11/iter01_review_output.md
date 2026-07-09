All three lenses check out. Let me record my findings.

## Review — GH-11: FetchResult contract

**Manifest sufficiency.** Accurate. The only product-code changes are `fetch.py` (new), `__init__.py` (export), and `tests/test_fetch.py` (new). Remaining working-tree modifications (`observability/…`, `state.json`) are harness bookkeeping, not part of this ticket's diff.

### Lens 1 — intent (acceptance criteria, walked)

1. **Type exists, pydantic v2, all 8 fields + derived `ok`** ✓ — `fetch.py:6-22`: `requested_url`, `final_url`, `status_code: int|None`, `content_type: str|None`, `body: str|None`, `fetched_at`, `error: str|None`, and `ok` as a `@computed_field @property`. Exported at `__init__.py:2` and in `__all__`. `pydantic>=2` in the manifest, so `computed_field` is available.
2. **`ok` derivation + honest failure** ✓ — `status_code is not None and 200 <= status_code < 300 and body is not None`. The deliberate `body is not None` (not `bool(body)`) keeps an empty-but-successful page (`body=""`) as `ok=True`, honoring the locked no-fabrication decision. Covered by the success, 404, 403, and `2xx_with_no_body` tests; the connection-failure test constructs with `body=None` and asserts it is valid.
3. **`final_url` may equal or differ from `requested_url`** ✓ — two independent `str` fields; both tests present.
4. **`fetched_at` populated on construction** ✓ — `Field(default_factory=lambda: datetime.now(timezone.utc))`, tz-aware, matching `store.py` convention; `test_fetched_at_is_populated`.
5. **Tests cover success / 404-403 / connection-failure / `ok` derivation, no network** ✓ — 8 tests; no `httpx`/network import in either `fetch.py` or `test_fetch.py`.
6. **`uv run pytest -q` green** ✓ (via evidence) — I could not re-run: the sandbox denied every `pytest`/`uv` invocation, same as the test and prior review stages. Test-stage evidence is concrete (32 passed, 8 in `test_fetch.py`), and the code is trivially verifiable by reading.

**Seam confirmed:** `extract.extract(raw_html, source_url, …)` (`extract.py:125`) consumes exactly `source_url`, which `FetchResult.final_url` is defined to feed. The typed hand-off lines up.

### Lens 2 — quality & security
Correctness is sound across every `ok` branch (None status, 4xx/5xx, empty body, empty-string body); decorator order correct. No network, subprocess, file, or secret handling — a pure data model. No dead code; every test asserts meaningfully; matches `models.py` house style.

### Lens 3 — visual
No user-facing surface — a pure typed data contract. Playwright not applicable; nothing to render.

**Verdict:** all three lenses pass, every criterion verified against evidence, product diff clean and committed. This is a clean first solve of the "shared typed seam" class (cf. GH-1/GH-4) — a candidate for a `skills/` entry.

```json
{
  "stage": "review",
  "ticket_id": "GH-11",
  "outcome": "success",
  "exit_signal": true,
  "summary": "FetchResult contract meets all 6 acceptance criteria: pydantic v2 model, 8 fields + derived `ok` (True iff 2xx and body present), honest failure (body=None valid, empty-string body stays ok), final_url distinct from requested_url and confirmed to feed extract()'s source_url, tz-aware fetched_at auto-populated. 8 unit tests, no network. All three lenses pass; no user-facing surface. Clean first solve of the 'shared typed seam' class — candidate for a skills/ entry.",
  "failure_reason": null,
  "files_changed": 3,
  "suggested_tools": ["playwright"],
  "system_repair_suggested": false,
  "pr_description": "Adds the `FetchResult` contract — the typed hand-off between Fetch (S3) and Extract (S2). Foundation slice only: defines the data shape; no fetching, adapters, or network.\n\n**What changed**\n- New `scholarship_factory/fetch.py`: `FetchResult` (pydantic v2) with `requested_url`, `final_url` (post-redirect; this is Extract's `source_url`), nullable `status_code`/`content_type`/`body`/`error`, auto-populated tz-aware `fetched_at`, and a derived `ok` computed field (`True` iff status is 2xx and body is present).\n- Exported from `scholarship_factory/__init__.py`.\n- `tests/test_fetch.py`: 8 tests covering success, 404/403, connection failure (status=None + error), redirect divergence, fetched_at population, and the ok derivation. No network.\n\n**Notes for the merger**\n- `ok` uses `body is not None`, so an empty-but-successful page (`body=\"\"`) is `ok=True` — deliberate, honoring the locked no-fabrication decision (a failed fetch must stay distinguishable from an empty one).\n- `final_url` is required with no auto-default; the fetcher that populates it (a later ticket) sets it equal to `requested_url` when no redirect occurred.\n- Merges first so the next S3 wave (static fetcher, politeness, adapters, cache) branches from it."
}
```