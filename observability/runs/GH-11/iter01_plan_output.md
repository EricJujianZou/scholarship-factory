The implementation, export, and tests already exist on-branch and match the ticket's locked decisions. This is a re-entry into the plan stage; I produce the plan following `stage_specs/plan_feat.md` exactly, reflecting the current shape in `scholarship_factory/fetch.py`.

## Context

The seam belongs with the other pydantic v2 models. `scholarship_factory/models.py:1-14` sets house style: `from pydantic import BaseModel, Field`, `str | None = None` for nullables, `Field(default_factory=...)` for auto-populated fields (`id`, `models.py:14`). Extract consumes a `source_url` (`scholarship_factory/extract.py:125`) — that value is exactly this ticket's `final_url` (post-redirect URL). Timestamps elsewhere use tz-aware UTC (`store.py`); for an in-model field, `datetime.now(timezone.utc)` via `default_factory` is idiomatic. `scholarship_factory/__init__.py:1-18` is the public surface — every model is re-exported and named in `__all__`. Tests mirror `tests/test_models.py`: construct, assert fields. No network anywhere in this ticket.

## Approach

Put `FetchResult` in a dedicated `scholarship_factory/fetch.py` (parallel to `models.py`/`extract.py`), reserving the future fetcher's home without polluting the Opportunity-centric `models.py`. The eight declared fields are plain typed fields; `fetched_at` uses `Field(default_factory=lambda: datetime.now(timezone.utc))` so it self-populates tz-aware. `ok` is a read-only derived value implemented as a pydantic v2 `@computed_field` property returning `status_code is not None and 200 <= status_code < 300 and body is not None` — keeping `ok` un-settable and always consistent with its inputs. Rejected alternative: a stored `ok` field set via `model_validator(mode="after")` (the `models.py:42` style) — it works but lets a caller pass a contradictory `ok=` and needs guarding, so the computed property is strictly simpler for a purely derived flag.

## Steps

1. Create `scholarship_factory/fetch.py` — `FetchResult(BaseModel)` with `requested_url: str`, `final_url: str`, `status_code: int | None = None`, `content_type: str | None = None`, `body: str | None = None`, `fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))`, `error: str | None = None`, and a `@computed_field @property def ok(self) -> bool` computing `status_code is not None and 200 <= status_code < 300 and body is not None`. Done when `FetchResult(requested_url="x", final_url="x")` constructs and `.ok is False`.
2. Edit `scholarship_factory/__init__.py` — add `from .fetch import FetchResult` and `"FetchResult"` to `__all__`. Done when `from scholarship_factory import FetchResult` succeeds.
3. Create `tests/test_fetch.py` mirroring `tests/test_models.py`: (a) success 2xx+body → `ok is True`; (b) 404 and 403 → `ok is False`; (c) connection failure (`status_code=None, body=None, error=...`) constructs and `ok is False`; (d) `final_url` defaults equal to and can differ from `requested_url`; (e) `fetched_at` is a `datetime`; (f) 2xx with `body=None` → `ok is False`. Done when all pass.
4. Run `uv run pytest -q`. Done when green.

## Acceptance criteria mapping

- "`FetchResult` exists (pydantic v2) with all eight fields + derived `ok`" -> steps 1, 2; verified by construction/field asserts and the import.
- "Success (2xx + body) → `ok=True`; failure (status `None`, 4xx/5xx, or no body) → `ok=False`, may carry `error`; `body=None` failure valid" -> step 1 (`ok` computed field), step 3; verified by tests a, b, c, f.
- "`final_url` equals `requested_url` when no redirect; may differ" -> step 1 (two independent `str` fields); verified by test d.
- "`fetched_at` populated on construction" -> step 1 (`default_factory`); verified by test e.
- "Unit tests cover success / 404-403 / connection-failure (`status_code=None` + `error`) / `ok` derivation; no network" -> step 3; verified by step 4, no `httpx`/network imported.
- "`uv run pytest -q` green" -> step 4; verified by exit 0.

## Risks

1. **`computed_field` decorator order** — `@computed_field` must sit above `@property` and the property must be annotated `-> bool`, or `ok` won't register. If it errors, check decorator order.
2. **`fetched_at` assertion flake** — assert `isinstance(result.fetched_at, datetime)`, never equality against a captured time.
3. **`body=""` vs `body=None`** — `ok` uses `body is not None`, so an empty-but-successful page (`body=""`) stays `ok=True`; do not switch to `bool(body)`, which would misreport an empty page as a failed fetch and violate the locked no-fabrication decision.

## File manifest

Carried in the status block below.

```json
{
  "stage": "plan",
  "ticket_id": "GH-11",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan to add a derived-`ok` FetchResult pydantic v2 model in a new fetch.py, export it, and unit-test success/404/403/connection-failure/ok-derivation with no network. Implementation already present on-branch and matches this plan exactly.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {"edit": ["scholarship_factory/fetch.py", "scholarship_factory/__init__.py:2", "tests/test_fetch.py"], "read": ["scholarship_factory/models.py:1", "scholarship_factory/extract.py:125", "scholarship_factory/store.py", "tests/test_models.py"]}
}
```