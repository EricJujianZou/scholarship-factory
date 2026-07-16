## Review — GH-26, static open-web fetcher

### Lens 1 — intent (acceptance criteria)

I walked each criterion against the actual test code rather than the test stage's prose, because `iter01_test_output.md` contains only a status block — it asserts "all 7 acceptance criteria verified" with no per-criterion evidence. That prose alone would not clear the bar. What rescues it is that I could read the tests directly, and each criterion maps to a test with real assertions against real mock-transport behavior:

| Criterion | Evidence |
|---|---|
| 200 HTML → ok/body/content_type/final_url | `tests/test_fetch.py:95` |
| 404/403 → one attempt, no retry, status recorded | `tests/test_fetch.py:107` (parametrized, counts handler calls) |
| 429 then 200 → retried, ok True | `tests/test_fetch.py:122` (asserts 2 calls) |
| Persistent transport error → bounded retries, honest result | `tests/test_fetch.py:138` (asserts call count == `RETRY_ATTEMPTS`, `status_code is None`, `error` set) |
| Browser-like User-Agent sent | `tests/test_fetch.py:154` (asserts inside handler) |
| Redirect records `final_url`, preserves `requested_url` | `tests/test_fetch.py:166` |
| All offline, suite green | Every test passes `transport=httpx.MockTransport(...)`; no test builds a client without one |

One caveat I want to state plainly rather than paper over: I could not re-run `uv run pytest -q` myself — the command needs an approval my read-only reviewer session doesn't have. I'm relying on the recorded `exit_code: 0` and "65 passed" in `observability/runs/GH-26/iter01_test.json`, which the implement stage independently corroborates. The tests themselves I verified by reading.

### Lens 2 — quality & security

The retry control flow is the part most likely to be subtly wrong, so I traced it against tenacity's actual semantics. It holds up:

- **Persistent 429** — `reraise=True` only re-raises when the last attempt *failed with an exception*. A run ending on a 429 is a successful attempt with a retryable result, so tenacity raises `RetryError`, and `fetch.py:79` catches it and recovers the real response via `exc.last_attempt.result()`. This is the exact hazard the plan flagged as Risk #1, and it's handled correctly.
- **Persistent timeout** — last attempt failed, so `reraise` surfaces the genuine `httpx.ConnectTimeout`, caught at `fetch.py:81`. `httpx.TimeoutException` and `ConnectError` both subclass `TransportError`, so the one `except` covers both.
- **4xx never retries by construction** — `_is_retryable_status` doesn't match, so no explicit "don't retry" branch is needed. Cleaner than the alternative.
- Building `Retrying` per call (`fetch.py:54`) reads module constants live, which is what lets the tests zero the backoff without sleeping or monkeypatching tenacity internals.

Reading `response.text` after the `with` block closes the client is safe — non-streaming responses are fully read on receipt. No secrets, no subprocess, no unsafe file handling. Dependency move is correct: `httpx` was dev-only and `fetch.py` now imports it at module scope, so promoting it to `[project].dependencies` alongside `tenacity` was necessary, not incidental — and `uv.lock` reflects both.

**One gap worth noting, not a blocker:** the `except RetryError` branch (persistent 429/5xx through all attempts) has no test. It's the branch the plan itself called the highest risk, and it's currently load-bearing but unexercised. It isn't in the acceptance criteria, so I'm not failing on it, but a persistent-429 test asserting `status_code == 429` and `ok is False` would be cheap and would pin the trickiest reasoning in the module. Worth a follow-up.

### Lens 3 — visual

No user-facing surface. `fetch_url` is a library function returning a pydantic model; the ticket adds no page, markup, or styling. Playwright is not applicable here — I'm not requesting it as a tool, since there's nothing to look at, not merely nothing available to look with.

### Verdict

All three lenses pass. Every criterion is verified by a test that asserts something real, the retry semantics are correct against tenacity's actual behavior, and the locked decisions in `docs/s3-fetch-design.md` (static httpx only, UA override without a fingerprint arms race, bounded backoff on 429/5xx/timeouts, honest `FetchResult`) are all honored. Branch state is clean apart from harness run artifacts.

```json
{
  "stage": "review",
  "ticket_id": "GH-26",
  "outcome": "success",
  "exit_signal": true,
  "summary": "All 7 criteria verified against the tests directly (test stage output was prose-only, no per-criterion evidence, so I re-derived from tests/test_fetch.py). Retry semantics traced against tenacity's actual reraise behavior and correct on both exhaustion paths. No user-facing surface, so no visual check applicable. Could not re-run the suite (permission-gated); relied on recorded exit_code 0. Minor gap: the RetryError branch (persistent 429) is untested. Clean first solve of the 'static fetcher with bounded retry' class — candidate for a new skill in skills/.",
  "failure_reason": null,
  "files_changed": 5,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds `fetch_url(url, *, timeout, user_agent, transport) -> FetchResult` to `scholarship_factory/fetch.py`, the producer for the `FetchResult` contract merged in GH-11.\n\n**What changed.** A single static `httpx` GET per call, with a browser-like Chrome User-Agent and `follow_redirects=True` baked into the client, driven through a `tenacity.Retrying` bounded at 3 attempts with exponential backoff. Retry fires on 429/5xx and on `httpx.TransportError` (which covers timeouts and connection errors); 4xx never matches the predicate, so a 404/403 is a single attempt by construction rather than by an explicit guard. Every outcome becomes a `FetchResult` — non-2xx records `status_code` with `ok` False, and a persistent transport error yields `error` set with `status_code` None. No exception escapes for an expected web failure. Also promotes `httpx` from a dev-only to a runtime dependency (the module now imports it at import time) and adds `tenacity`.\n\n**Tradeoffs a merger should know.** `fetch_url` takes a keyword-only `transport` parameter defaulting to the real network. This exists to satisfy the ticket's offline-tests requirement via `httpx.MockTransport`; injecting a whole `httpx.Client` was rejected because it would hand callers control of `follow_redirects` and the UA — the two behaviours this ticket exists to guarantee. The retry knobs are module constants read at call time rather than frozen in a decorator, which is what lets tests zero the backoff instead of sleeping for real.\n\n**Risks.** Retries ignore `Retry-After` on a 429 — per-host politeness and robots are a separate ticket, as are adapters, caching, and JS rendering. The exhaustion path for a persistent 429 (tenacity raises `RetryError` rather than returning the last response, so the code recovers it via `last_attempt.result()`) is implemented and correct but not directly covered by a test; a follow-up test there would be cheap insurance.\n\n**Testing.** 15 tests in `tests/test_fetch.py`, all offline via `httpx.MockTransport`; full suite green at 65 passed."
}
```