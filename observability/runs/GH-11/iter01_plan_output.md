I have everything I need. Writing the plan.

## Context

The seam lives alongside the other pydantic v2 models. `scholarship_factory/models.py:1-13` sets the style: `from pydantic import BaseModel, Field`, `Field(default_factory=...)` for auto-populated fields (see `id`), and `str | None = None` for nullables. `scholarship_factory/extract.py:125-127` shows Extract's entry point takes `source_url` — that value is exactly this ticket's `final_url`. Timestamps elsewhere use `datetime.now(timezone.utc)` (`store.py:78`), but as ISO strings; for a pydantic field a timezone-aware `datetime` with `default_factory` is the idiomatic in-model choice. `scholarship_factory/__init__.py:1-16` is the public API surface — every model is re-exported and listed in `__all__`. Tests mirror `tests/test_models.py`: construct instances, assert fields, use `pytest.raises(ValidationError)` for invalid cases. No network anywhere in this ticket.

## Approach

Add a new `FetchResult` pydantic v2 `BaseModel` in a dedicated module `scholarship_factory/fetch.py` (parallel to `models.py`/`extract.py`, keeping the future fetcher's home ready without co-locating it in `models.py`, which is Opportunity-centric). The eight declared fields are plain typed fields; `fetched_at` is a `datetime = Field(default_factory=lambda: datetime.now(timezone.utc))` so it self-populates on construction. `ok` is a read-only derived value, implemented as a pydantic v2 `@computed_field` property returning `200 <= status_code < 300 and bool(body)` — this keeps `ok` un-settable and always consistent with `status_code`/`body`, which a stored bool field could drift from. Rejected alternative: a stored `ok` field set via `model_validator(mode="after")` (the style in `models.py:42`) — it works but lets callers pass a contradictory `ok=` and needs guarding, so the computed property is strictly simpler and safer for a purely derived flag.

## Steps

1. Create `scholarship_factory/fetch.py` — imports `datetime`, `timezone` from `datetime`; `BaseModel`, `Field`, `computed_field` from `pydantic`. Define `FetchResult(BaseModel)` with fields: `requested_url: str`, `final_url: str`, `status_code: int | None = None`, `content_type: str | None = None`, `body: str | None = None`, `fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))`, `error: str | None = None`. Add a `@computed_field @property def ok(self) -> bool` returning `self.status_code is not None and 200 <= self.status_code < 300 and self.body is not None`. Done when the module imports and `FetchResult(requested_url="x", final_url="x")` constructs.
2. Edit `scholarship_factory/__init__.py` — add `from .fetch import FetchResult` and append `"FetchResult"` to `__all__`. Done when `from scholarship_factory import FetchResult` succeeds.
3. Create `tests/test_fetch.py` — mirror `tests/test_models.py` structure with tests for: (a) success result (2xx + body) → `ok is True`; (b) 404 and 403 results → `ok is False`; (c) connection failure `status_code=None, body=None, error="..."` constructs and `ok is False`; (d) `final_url == requested_url` default case and a redirected case where they differ; (e) `fetched_at` is populated and is a `datetime`; (f) 2xx with `body=None` → `ok is False` (guards the "empty-but-successful must be honest" decision). Done when all tests pass.
4. Run `uv run pytest -q`. Done when the suite is green.

## Acceptance criteria mapping

- "`FetchResult` exists (pydantic v2) with `requested_url`, `final_url`, `status_code` (nullable), `content_type` (nullable), `body` (nullable), `fetched_at`, `error` (nullable), and a derived `ok`." -> step 1; verified by test 3a construction + field asserts and the import in step 2.
- "A success result (2xx + body) has `ok=True`; a failure (status `None`, or 4xx/5xx, or no body) has `ok=False` and may carry an `error`; constructing a failure with `body=None` is valid." -> step 1 (`ok` computed field), step 3; verified by tests 3a, 3b, 3c, 3f.
- "`final_url` equals `requested_url` when no redirect occurred; the two are allowed to differ." -> step 1 (both are independent `str` fields); verified by test 3d.
- "`fetched_at` is populated on construction." -> step 1 (`default_factory`); verified by test 3e.
- "Unit tests cover: success, 404/403, connection-failure (`status_code=None` + `error`), and `ok` derivation. No network." -> step 3; verified by running the tests (step 4). No `httpx`/network imported.
- "`uv run pytest -q` green." -> step 4; verified by the command exiting 0.

## Risks

1. **pydantic v2 `computed_field` on a `@property`** — must be `@computed_field` above `@property` (decorator order) and the property annotated `-> bool`, or `ok` won't serialize/validate. If it errors, confirm decorator order and that pydantic is v2 (it is — `models.py` uses `model_validator(mode="after")`).
2. **`fetched_at` timezone/type mismatch in tests** — asserting an exact value will flake; the test must only assert `isinstance(result.fetched_at, datetime)` (and optionally `.tzinfo is not None`), not equality.
3. **`ok` truthiness on empty-string body** — `self.body is not None` treats `body=""` as present (`ok` can be True with an empty string). The decisions say distinguish "fetched, page empty" from "fetch failed", and failure sets `body=None`, so `is not None` is the correct test; do not switch to `bool(body)` which would call an empty successful page a failure.

## File manifest

Covered in the status block below.

```json
{
  "stage": "plan",
  "ticket_id": "GH-11",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan to add a derived-`ok` FetchResult pydantic v2 model in a new fetch.py, export it, and unit-test success/404/403/connection-failure/ok-derivation with no network.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {"edit": ["scholarship_factory/fetch.py", "scholarship_factory/__init__.py:1", "tests/test_fetch.py"], "read": ["scholarship_factory/models.py:1", "scholarship_factory/extract.py:125", "scholarship_factory/store.py:78", "tests/test_models.py"]}
}
```