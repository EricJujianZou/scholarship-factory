I have what I need — `polite.py` (GH-32) already establishes the wrapper-over-`fetch_url` pattern with an injectable `fetch_fn` and clock, and `store.py`/`profile.py` establish the SQLite pattern. Here's the plan.

## Context

- `scholarship_factory/fetch.py:31` defines `FetchResult` (pydantic, with a **computed** `ok` property at `fetch.py:40`) and `fetch_url` at `fetch.py:64` — the underlying fetcher this ticket caches. Its kwargs (`timeout`/`user_agent`/`transport`) all have defaults, so it is callable as `fetch_url(url)`.
- `scholarship_factory/polite.py:29` is the closest sibling (GH-32, the third Fetch link): a wrapper that injects `fetch_fn=fetch_url` and a `clock` for testability. This ticket is the fourth link and should read like it. Note `PoliteFetcher.fetch(url)` takes **only** a url — the cache's `fetch_fn` seam must stay one-positional-arg so both it and `fetch_url` drop in.
- `store.py:34` / `profile.py:42` fix the SQLite pattern: stdlib `sqlite3`, `db_path` in the constructor, `row_factory = sqlite3.Row`, `CREATE TABLE IF NOT EXISTS` in `_init_schema`, `commit()` per write, datetimes as ISO text.
- Constraint from the ticket: failures are never cached, and the cached result must be flagged as such. `ok` is computed from `status_code`+`body`, so a round-tripped row recomputes `ok` for free — no `ok` column.

## Approach

Add `scholarship_factory/cache.py` with a `FetchCache` class (SQLite table `fetch_cache`, `get`/`put`) plus a module-level `cached_fetch(url, *, cache, fetch_fn=fetch_url, max_age=DEFAULT_MAX_AGE)` function, and add a `from_cache: bool = False` field to `FetchResult`. Provenance rides on the existing object rather than a wrapper type because every downstream consumer (extract, adapters) already takes `FetchResult`; a `CachedFetchResult` wrapper would force them all to unwrap for one boolean. The composition is a **function**, not a `CachedFetcher` class, because unlike `PoliteFetcher` it holds no per-instance mutable state — all state lives in the `FetchCache` — and a function composes with `PoliteFetcher.fetch` as `fetch_fn` without either knowing about the other. The rejected alternative was folding caching into `PoliteFetcher` as another constructor arg: it would save a module, but it welds two independent concerns (you'd lose the ability to cache without rate-limiting, and vice versa) and would make GH-32's tests re-derive cache state.

Cache key is the requested URL **as given** — not `normalize_apply_url` (`urls.py`), which encodes *opportunity dedup* identity, not *byte-fetch* identity, and would wrongly collide two URLs that return different bytes. Staleness is computed against an injectable `clock` on `FetchCache` (mirroring `polite.py:45`) so the window test needs no `sleep` or `freezegun`.

## Steps

1. Add `from_cache: bool = False` to `FetchResult` in `scholarship_factory/fetch.py` (after `error`, `fetch.py:38`) — done when existing `tests/test_fetch.py` passes unchanged and `FetchResult(...).from_cache is False`.
2. Create `scholarship_factory/cache.py` with a module docstring in the house style (see `polite.py:1-8`: names the S3 chain position — *fourth link* — and states what's out of scope, namely field-level refresh = S8), `import sqlite3`, and `DEFAULT_MAX_AGE = timedelta(days=1)` — done when the module imports cleanly.
3. Add `class FetchCache` in `cache.py` with `__init__(self, db_path: str, *, clock=lambda: datetime.now(timezone.utc))` setting `self.db_path`, `self._conn = sqlite3.connect(db_path)`, `self._conn.row_factory = sqlite3.Row`, `self._clock = clock`, then `self._init_schema()` — done when it matches `store.py:35-39`.
4. Add `FetchCache._init_schema` creating `CREATE TABLE IF NOT EXISTS fetch_cache (url TEXT PRIMARY KEY, fetched_at TEXT NOT NULL, status_code INTEGER, content_type TEXT, body TEXT, final_url TEXT NOT NULL)` + `commit()` — done when constructing two `FetchCache`s on one path raises nothing.
5. Add `FetchCache.put(self, result: FetchResult) -> None` in `cache.py` writing the six columns **explicitly** (`url=result.requested_url`, `fetched_at=result.fetched_at.isoformat()`, then `status_code`, `content_type`, `body`, `final_url`) via `INSERT INTO fetch_cache (...) VALUES (?,?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET fetched_at=excluded.fetched_at, status_code=excluded.status_code, content_type=excluded.content_type, body=excluded.body, final_url=excluded.final_url` + `commit()`. Do **not** use `model_dump()` — it includes the computed `ok` and the new `from_cache`, neither of which is a column. Done when a second `put` for the same url updates rather than raising `IntegrityError`.
6. Add `FetchCache.get(self, url: str, max_age: timedelta) -> FetchResult | None` in `cache.py`: `SELECT * FROM fetch_cache WHERE url = ?`; return `None` if no row; parse `fetched_at = datetime.fromisoformat(row["fetched_at"])`; return `None` if `self._clock() - fetched_at > max_age`; else return `FetchResult(requested_url=url, final_url=row["final_url"], status_code=row["status_code"], content_type=row["content_type"], body=row["body"], fetched_at=fetched_at, from_cache=True)` — carrying the **original** `fetched_at`, not now. Done when a fresh row returns a result with `from_cache is True` and a stale row returns `None`.
7. Add `cached_fetch(url: str, *, cache: FetchCache, fetch_fn=fetch_url, max_age: timedelta = DEFAULT_MAX_AGE) -> FetchResult` in `cache.py`: return `cached` if `cache.get(url, max_age)` is not None; else `result = fetch_fn(url)` (one positional arg, no kwargs — preserves `PoliteFetcher.fetch` compatibility); `if result.ok: cache.put(result)`; return `result` — done when the AC tests in step 9 pass.
8. Export `FetchCache`, `cached_fetch`, `DEFAULT_MAX_AGE` from `scholarship_factory/__init__.py` (import line alphabetically before `.clean`/after `.adapters`, per `__init__.py:1-12`; add all three to `__all__`) — done when `from scholarship_factory import FetchCache, cached_fetch, DEFAULT_MAX_AGE` works.
9. Create `tests/test_cache.py` using `tmp_path` (per `test_store.py:13`) and a counting fake fetcher — a closure/list recording calls and returning a canned `FetchResult` — covering: (a) first fetch calls through + second within window returns body with `from_cache is True` and call count stays 1; (b) a row older than the window refetches (count 2) and the row's `fetched_at` advances; (c) an `ok is False` result is returned but `cache.get` stays `None` and the next call refetches; (d) a `put` through one `FetchCache` is visible from a second instance on the same `tmp_path` db file. Use an injected `clock` for (b) — no real sleeping, no network. Done when `uv run pytest -q tests/test_cache.py` is green.
10. Run `uv run pytest -q` for the whole suite — done when green, confirming step 1's field addition broke no existing fetch/polite/extract test.

## Acceptance criteria mapping

- "First fetch of a URL calls the underlying fetcher and stores the result; second fetch within the window returns the cached body WITHOUT calling the underlying fetcher (asserted via injected fake), flagged as cached." -> steps 5, 6, 7; verified by test 9(a) asserting call count `== 1` and `result.from_cache is True`.
- "A result older than the window triggers a real refetch and the cache row is refreshed." -> steps 6, 7 (staleness returns `None` → miss path), step 5 (`ON CONFLICT DO UPDATE` refreshes); verified by test 9(b).
- "A failed fetch (`ok` False) is returned honestly but NOT written to the cache; the next call fetches again." -> step 7 (`if result.ok:` guard); verified by test 9(c).
- "Cache persists across `FetchCache` instances pointed at the same db file (tmp file in tests)." -> steps 3, 4 (`sqlite3.connect(db_path)` + `CREATE TABLE IF NOT EXISTS`); verified by test 9(d).
- "All tests offline, temp db only; `uv run pytest -q` green." -> steps 9, 10; verified by the fake `fetch_fn` (no `httpx`/network in `test_cache.py`) + `tmp_path`, and the full-suite run in step 10.

## Risks

1. **`model_dump()` on `FetchResult` includes the computed `ok` field** (`fetch.py:40`) and now `from_cache` — copying `store.py`'s `row = opp.model_dump()` idiom into `put` will produce keys with no matching column. Step 5 mandates explicit column mapping; if the implementer hits an `OperationalError` about column counts, this is why.
2. **Naive/aware datetime mismatch.** `FetchResult.fetched_at` is tz-aware UTC (`fetch.py:37`), so its `isoformat()` round-trips through `fromisoformat` as aware — but a test that hand-builds a `FetchResult` with a naive `fetched_at`, or a `clock` returning `datetime.now()` without `timezone.utc`, will raise `TypeError: can't subtract offset-naive and offset-aware datetimes` in step 6. Keep every clock and every test datetime tz-aware UTC.
3. **The `fetch_fn` seam narrowing.** If step 7 calls `fetch_fn(url, timeout=..., user_agent=...)` (as `polite.py:60` does), `cached_fetch` can no longer wrap `PoliteFetcher.fetch`, which is the intended composition for the full chain. Call `fetch_fn(url)` with one positional arg only; a caller needing custom timeouts passes a pre-bound `functools.partial` or a `PoliteFetcher` instance.

```json
{
  "stage": "plan",
  "ticket_id": "GH-33",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for the S3 fetch cache: new cache.py with a SQLite-backed FetchCache (get/put + freshness window, injectable clock) and a cached_fetch(url, *, cache, fetch_fn) composition, plus a from_cache flag on FetchResult and offline tmp_path tests. Mirrors polite.py's wrapper pattern and store.py's SQLite pattern.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/cache.py",
      "scholarship_factory/fetch.py:38",
      "scholarship_factory/__init__.py:3",
      "tests/test_cache.py"
    ],
    "read": [
      "scholarship_factory/polite.py:29",
      "scholarship_factory/store.py:34",
      "scholarship_factory/profile.py:42",
      "tests/test_polite.py:9",
      "tests/test_store.py:13",
      "tests/test_fetch.py:10",
      "docs/s3-fetch-design.md:58"
    ]
  }
}
```