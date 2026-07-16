I have everything I need. The fetcher's signature, the pydantic/`MockTransport` conventions, and one real trap (tenacity sleeps for real unless `RETRY_WAIT_MULTIPLIER` is patched) all shape the plan below.

## Context

- `scholarship_factory/fetch.py:64` — `fetch_url(url, *, timeout, user_agent, transport)` → `FetchResult`; the polite layer wraps this and must not change it. `FetchResult.ok` (`fetch.py:42`) is a computed field: `status_code is None` + `body is None` already yields `ok is False`, so a robots-denied result just needs `error` set.
- `fetch.py:78` retries via tenacity with `wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER)` — a robots.txt *timeout* routed through `fetch_url` sleeps for real. `tests/test_fetch.py:139` handles this by monkeypatching `RETRY_WAIT_MULTIPLIER` to 0; the robots-timeout test must do the same to honor "no real sleep".
- Conventions: modules are flat and single-purpose with a docstring naming their place in the Session-3 chain (`adapters.py:1`), pydantic `BaseModel` for data, plain functions/classes otherwise, and every public name re-exported in `scholarship_factory/__init__.py:13`.
- Tests are offline via `httpx.MockTransport` with a handler closure appending to a `calls` list (`tests/test_fetch.py:110`) — that pattern is exactly how "transport never called" gets asserted.
- No `progress.txt` and no `skills/` in this repo; `skill_match` is null.

## Approach

Add `scholarship_factory/polite.py` with a `PoliteFetcher` class holding two in-memory dicts keyed by host (`netloc.lower()`): last-request time and cached robots parser. `fetch(url)` consults robots first (returning early on disallow, before any spacing wait, since no request is made), then applies per-host spacing, then delegates to an injected `fetch_fn` defaulting to `fetch_url`. Clock and sleep are constructor-injected (`time.monotonic` / `time.sleep` defaults) so tests drive time with a fake that advances on `sleep`. Robots.txt is fetched through the same `fetch_fn` — reusing the retry/User-Agent/transport path rather than a second HTTP code path — and its parse result is cached under a `host in dict` check so a fail-open miss caches as `None` and is never re-requested. Rejected alternative: a module-level function with global state, which is what "per fetcher instance" caching in the ACs rules out and which would leak host state across runs and tests.

**Two sub-decisions made now, so the implementer doesn't re-interpret:**
1. The robots.txt request itself participates in rate limiting and updates the host's last-request time. It is a real request to that host; exempting it would mean back-to-back hits on first contact — precisely what this ticket insures against.
2. Robots is consulted using `urllib.robotparser.RobotFileParser.parse(body.splitlines())` + `can_fetch(user_agent, url)`. Its prefix-token matching gives us the "our UA, falling back to `*`" semantics the ticket locks, for free.

## Steps

1. Create `scholarship_factory/polite.py` with module docstring (Session 3 / Fetch, politeness link), `DEFAULT_MIN_INTERVAL = 2.0`, and `PoliteFetcher.__init__(self, *, min_interval=DEFAULT_MIN_INTERVAL, timeout=DEFAULT_TIMEOUT, user_agent=DEFAULT_USER_AGENT, transport=None, clock=time.monotonic, sleep=time.sleep, fetch_fn=fetch_url)` storing `_last_request: dict[str, float]` and `_robots: dict[str, RobotFileParser | None]` — done when the module imports cleanly and instances construct with no args.
2. Add `_host(url)` (via `urlsplit(url).netloc.lower()`) and `_robots_url(url)` (`f"{scheme}://{netloc}/robots.txt"`) helpers in `polite.py` — done when `_host("https://Example.com/a")  == "example.com"`.
3. Add `_wait_for_host(self, host)` in `polite.py`: if host seen, compute `elapsed = self._clock() - self._last_request[host]` and `self._sleep(self._min_interval - elapsed)` when `elapsed < min_interval`; then set `self._last_request[host] = self._clock()` — done when a fake clock records a sleep of the remaining interval and none for an unseen host.
4. Add `_robots_parser(self, url, host)` in `polite.py`: return cached value if `host in self._robots`; else `_wait_for_host(host)`, `fetch_fn(robots_url, ...)`, and on `result.ok` parse into a `RobotFileParser` (with `set_url`), else cache `None`; wrap the parse in `try/except Exception` → `None` for malformed robots — done when a second call for the same host issues no new request.
5. Add `PoliteFetcher.fetch(self, url) -> FetchResult` in `polite.py`: resolve parser; if parser is not None and `not parser.can_fetch(self._user_agent, url)`, return `FetchResult(requested_url=url, final_url=url, status_code=None, body=None, error=f"robots.txt disallows {url}")` without calling `fetch_fn`; else `_wait_for_host(host)` and return `fetch_fn(url, timeout=..., user_agent=..., transport=...)` — done when a disallowed URL returns `ok is False` with a robots `error`.
6. Export `PoliteFetcher` (and `DEFAULT_MIN_INTERVAL`) from `scholarship_factory/__init__.py` — add the import line near `from .fetch import ...` (`__init__.py:3`) and the `__all__` entries — done when `from scholarship_factory import PoliteFetcher` works.
7. Create `tests/test_polite.py` with a `FakeClock` helper (`now` float; `sleep(d)` appends `d` to `slept` and advances `now`) and a `MockTransport` handler recording requested paths, covering the six cases in the mapping below — done when `uv run pytest -q` is green.

## Acceptance criteria mapping

- "Two consecutive fetches to the same host are spaced by the configured interval (asserted via injected clock/sleep — no real sleep in tests); fetches to different hosts are not delayed." -> steps 3, 5, 7; verified by `test_same_host_second_fetch_is_spaced` (robots allow-all handler; assert `min_interval` appears in `clock.slept` for the second fetch) and `test_different_hosts_are_not_delayed` (two hosts; assert no sleep attributable to cross-host spacing).
- "A URL disallowed by the host's robots.txt is not fetched (underlying transport never called) and returns a `FetchResult` with `ok` False and a robots-specific `error`." -> steps 4, 5, 7; verified by `test_disallowed_url_is_not_fetched` — handler serves `/robots.txt` with `Disallow: /private`, then assert `"/private" not in requested_paths`, `result.ok is False`, and `"robots" in result.error`.
- "robots.txt returning 404/timeout -> the fetch proceeds (fail open)." -> steps 4, 7; verified by `test_robots_404_fails_open` (robots → 404, target → 200, assert `result.ok is True`) and `test_robots_timeout_fails_open` (handler raises `httpx.ConnectTimeout` for `/robots.txt`; **monkeypatch `fetch_module.RETRY_WAIT_MULTIPLIER` to 0** per `tests/test_fetch.py:139` so tenacity does not really sleep).
- "robots.txt is requested at most once per host per fetcher instance." -> steps 4, 7; verified by `test_robots_requested_once_per_host` — three fetches to one host, assert `requested_paths.count("/robots.txt") == 1`; plus a 404-robots variant proving the fail-open miss is cached too.
- "All tests offline (`httpx.MockTransport` / injected fakes); `uv run pytest -q` green." -> steps 1, 7; verified by every test passing `transport=httpx.MockTransport(handler)` and `clock`/`sleep` fakes into the constructor, and a full `uv run pytest -q` run.

## Risks

1. **Real sleeping sneaks into the suite via tenacity, not via our `sleep`.** The robots-timeout test routes through `fetch_url`'s retry loop, which uses `wait_exponential` and would add ~1.5s of genuine sleep. If the suite slows down noticeably, the missing `monkeypatch.setattr(fetch_module, "RETRY_WAIT_MULTIPLIER", 0)` is the cause — not the injected clock.
2. **`RobotFileParser.can_fetch` with the browser User-Agent may match unexpectedly.** It lowercases and splits on `/`, so `DEFAULT_USER_AGENT` reduces to the token `mozilla`; a robots file with an explicit `User-agent: mozilla` group would take precedence over `*`. This is correct stdlib semantics and what the ticket locks, but write the disallow test's fixture against `User-agent: *` so it tests the intended path.
3. **`can_fetch` on a `RobotFileParser` that was never fed content returns `True` by default**, which silently looks like fail-open even when caching is broken. Guard against a false-green on the "at most once per host" criterion by asserting on the recorded request paths (the transport is the source of truth), never on the parser's return value alone.

```json
{
  "stage": "plan",
  "ticket_id": "GH-32",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for a PoliteFetcher in a new scholarship_factory/polite.py wrapping fetch_url with per-host min-interval spacing (injected clock/sleep) and cached, fail-open robots.txt checks via urllib.robotparser; tests in tests/test_polite.py use httpx.MockTransport and a fake clock.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/polite.py",
      "tests/test_polite.py",
      "scholarship_factory/__init__.py:3"
    ],
    "read": [
      "scholarship_factory/fetch.py:64",
      "scholarship_factory/fetch.py:42",
      "scholarship_factory/urls.py:6",
      "scholarship_factory/adapters.py:1",
      "tests/test_fetch.py:110",
      "tests/test_fetch.py:139",
      "pyproject.toml"
    ]
  }
}
```