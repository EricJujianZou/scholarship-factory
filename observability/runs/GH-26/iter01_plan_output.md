No `progress.txt`, no `skills/`, and `httpx` is only used in `.venv` — not yet in project code. Note `httpx` is currently a **dev-only** dependency while this ticket makes it a runtime import; `tenacity` is absent from `uv.lock`. Both need to move/land in `[project].dependencies`.

Here is the plan.

## Context

- `scholarship_factory/fetch.py:6` already holds the merged `FetchResult` contract (GH-11) — `requested_url`, `final_url`, `status_code`, `content_type`, `body`, `error`, plus a computed `ok` requiring 2xx **and** a non-`None` `body` (`fetch.py:17`). `fetch_url` is the producer that module is missing; it belongs there, not a sibling.
- Repo convention (`seeds.py:1`, `urls.py:1`): one small module per concern, pydantic models, a module docstring naming what's *out* of scope, public names re-exported through `scholarship_factory/__init__.py:12`.
- Tests are flat `pytest` functions per module, no fixtures/classes (`tests/test_fetch.py:6`); `tests/test_fetch.py` currently tests only the contract's shape and has no network. New tests extend it.
- `pyproject.toml:21` lists `httpx` under `[dependency-groups].dev` only, and `tenacity` is nowhere in `uv.lock`. Since `fetch.py` will import `httpx` at import time, that dev-only placement becomes wrong the moment this ticket lands.
- No `progress.txt` and no `skills/` in this repo — nothing prior to defer to.

## Approach

Put `fetch_url` in `fetch.py` next to the contract it produces: open one `httpx.Client(follow_redirects=True, ...)` per call with the browser-like UA and timeout baked into the client, then drive attempts through a `tenacity.Retrying` object built **at call time** (so its knobs read module-level constants and tests can zero out the backoff without sleeping). Retry fires on two conditions — `retry_if_result` for 429/5xx, and `retry_if_exception_type(httpx.TransportError)`, which covers `TimeoutException` and `ConnectError` alike since both subclass it — bounded at 3 attempts. Exhaustion is handled explicitly rather than cleverly: `reraise=True` lets a persistent transport error escape as the real `httpx` exception (→ `error` set, `status_code=None`), while result-based exhaustion raises `RetryError`, whose `last_attempt.result()` is the final 429/5xx response we honestly report. 4xx never matches the retry predicate, so a 404/403 is a single attempt by construction — no explicit "don't retry" branch needed. For testability the function takes a keyword-only `transport: httpx.BaseTransport | None = None`, defaulting to real network; this is required by the "all tests offline via `MockTransport`" criterion, not speculative flexibility. **Rejected:** the `@tenacity.retry` decorator on a module-level helper — its wait/stop are frozen at decoration time, forcing tests to either sleep for real or monkeypatch tenacity internals. **Also rejected:** injecting a whole `httpx.Client`, which would hand callers control of `follow_redirects` and the UA — the two behaviours this ticket exists to guarantee.

## Steps

1. Add `httpx` to `[project].dependencies` and add `tenacity` in `pyproject.toml` via `uv add tenacity httpx`, then remove the now-redundant `httpx` entry from `[dependency-groups].dev` (`pyproject.toml:5`, `pyproject.toml:21`) — done when `uv.lock` contains a `name = "tenacity"` package and `uv run python -c "import tenacity, httpx"` exits 0.
2. Add module constants to `scholarship_factory/fetch.py`: `DEFAULT_USER_AGENT` (a current browser-like Chrome UA string), `DEFAULT_TIMEOUT = 15.0`, `RETRY_ATTEMPTS = 3`, `RETRY_WAIT_MULTIPLIER = 0.5` — done when the module imports and each constant is readable as `scholarship_factory.fetch.<NAME>`.
3. Add private `_is_retryable_status(response: httpx.Response) -> bool` in `fetch.py` returning `response.status_code == 429 or response.status_code >= 500` — done when it is True for 429/500/503 and False for 200/302/403/404.
4. Add private `_retrying() -> tenacity.Retrying` in `fetch.py` constructing (at call time, reading the step-2 constants) `stop=stop_after_attempt(RETRY_ATTEMPTS)`, `wait=wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER)`, `retry=retry_if_result(_is_retryable_status) | retry_if_exception_type(httpx.TransportError)`, `reraise=True` — done when `_retrying()` returns a fresh `Retrying` reflecting a monkeypatched `RETRY_WAIT_MULTIPLIER`.
5. Implement `fetch_url(url: str, *, timeout: float = DEFAULT_TIMEOUT, user_agent: str = DEFAULT_USER_AGENT, transport: httpx.BaseTransport | None = None) -> FetchResult` in `fetch.py`: open `httpx.Client(follow_redirects=True, timeout=timeout, headers={"User-Agent": user_agent}, transport=transport)` in a `with` block, run `response = _retrying()(client.get, url)` inside it, and build `FetchResult(requested_url=url, final_url=str(response.url), status_code=response.status_code, content_type=response.headers.get("content-type"), body=response.text)` — done when a mocked 200 returns `ok is True`.
6. Add the two exhaustion branches around the step-5 call in `fetch.py`: `except RetryError as exc: response = exc.last_attempt.result()` (falls through to the same `FetchResult` construction, reporting the final 429/5xx honestly), and `except httpx.TransportError as exc: return FetchResult(requested_url=url, final_url=url, status_code=None, body=None, error=f"{type(exc).__name__}: {exc}")` — done when a persistently-timing-out mock returns a `FetchResult` with `error` set and no exception escaping.
7. Write the module docstring for `fetch.py` in the `seeds.py:1` style, naming what is out of scope (no adapters, no robots/politeness, no caching, no JS rendering) — done when the docstring states the static-`httpx`-only boundary.
8. Export `fetch_url` from `scholarship_factory/__init__.py` — add to the `from .fetch import` line (`__init__.py:2`) and to `__all__` (`__init__.py:23`) — done when `from scholarship_factory import fetch_url` succeeds.
9. Add offline tests to `tests/test_fetch.py` using `httpx.MockTransport`, each passing `transport=` into `fetch_url` and monkeypatching `RETRY_WAIT_MULTIPLIER` to `0` in the retrying tests: (a) 200 HTML → `ok`/`body`/`content_type`/`final_url`; (b) 404 and 403 each → one handler call via a counter, `ok False`, `status_code` recorded; (c) 429-then-200 sequence → `ok True` and two calls; (d) handler raising `httpx.ConnectTimeout` every time → `error` set, `status_code is None`, exactly `RETRY_ATTEMPTS` calls; (e) UA header asserted inside the handler (`request.headers["user-agent"] == DEFAULT_USER_AGENT`); (f) 302 → 200 chain → `final_url` is the redirect target while `requested_url` is the original — done when `uv run pytest -q tests/test_fetch.py` is green.
10. Run the full suite — done when `uv run pytest -q` is green with no new warnings and the pre-existing contract tests still pass.

## Acceptance criteria mapping

- `"200 with HTML body -> FetchResult.ok True, body/content_type/final_url populated."` -> steps 5, 8; verified by test 9(a).
- `"404 and 403 -> exactly one attempt (no retry), ok False, status_code recorded, no exception."` -> steps 3, 5 (4xx never matches `_is_retryable_status`); verified by test 9(b)'s call counter.
- `"429 then 200 (mock sequence) -> retried, final result ok True."` -> steps 3, 4, 5; verified by test 9(c).
- `"Persistent timeout/transport error -> bounded retries then an honest FetchResult with error set and status_code None; no exception escapes."` -> steps 4, 6; verified by test 9(d), which asserts both the `error`/`status_code` shape and the attempt count.
- `"The request carries the browser-like User-Agent header (asserted in the mock)."` -> steps 2, 5; verified by test 9(e).
- `"A redirect records the followed final_url while preserving requested_url."` -> step 5 (`follow_redirects=True`, `final_url=str(response.url)`, `requested_url=url`); verified by test 9(f).
- `"All tests offline (httpx.MockTransport); uv run pytest -q green."` -> steps 9, 10; verified by step 10's full-suite run — no test constructs a real `httpx.Client` without a `transport`.

## Risks

1. **Result-based retry exhaustion raises `RetryError`, not the last value.** `reraise=True` governs *exceptions* only; a run that ends on a 429 still raises `RetryError`. Step 6's `except RetryError` branch is the whole mitigation — if the implementer drops it, test 9(c)'s sibling case (persistent 429) surfaces as an escaped exception rather than an honest `FetchResult`. Recover by pulling `exc.last_attempt.result()`, not by setting `retry_error_callback`.
2. **Backoff makes the suite slow or flaky if the monkeypatch is missed.** `_retrying()` must be constructed per call and read the module global (step 4) — if the implementer inlines `wait_exponential(multiplier=0.5)` as a default argument or a decorator, tests 9(c)/9(d) sleep for real (~1.5s each). If that shows up, keep the constant indirection rather than shrinking the default multiplier, which would weaken real-world backoff.
3. **`httpx.MockTransport` handler raising a timeout may not be retried if the exception type is wrong.** `httpx.TimeoutException` and `ConnectError` subclass `TransportError`, but `httpx.HTTPStatusError` does *not* — it subclasses `HTTPError`. If test 9(d) sees only one attempt, verify the handler raises a genuine `TransportError` subclass (`httpx.ConnectTimeout`) and that nothing calls `raise_for_status()`.

```json
{
  "stage": "plan",
  "ticket_id": "GH-26",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for fetch_url in scholarship_factory/fetch.py: httpx.Client with browser UA + follow_redirects, tenacity Retrying (429/5xx + TransportError, 3 attempts) built per-call so tests can zero the backoff, explicit RetryError/TransportError exhaustion branches producing honest FetchResults, and offline MockTransport tests. Also promotes httpx from dev-only to a runtime dependency and adds tenacity.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/fetch.py:6",
      "scholarship_factory/__init__.py:2",
      "tests/test_fetch.py:1",
      "pyproject.toml:5",
      "uv.lock"
    ],
    "read": [
      "scholarship_factory/seeds.py:1",
      "scholarship_factory/urls.py:1",
      "docs/s3-fetch-design.md:38",
      "CLAUDE.md"
    ]
  }
}
```