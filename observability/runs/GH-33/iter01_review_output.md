## Review — GH-33 fetch response cache

I verified all three lenses. The work holds; I'm passing it.

**Lens 1 — intent.** I walked each acceptance criterion against the actual test assertions in `tests/test_cache.py` rather than trusting the test stage's prose (its summary was vague — "5 acceptance criteria verified individually" with no per-criterion evidence, so I re-derived the mapping myself):

- Cache hit within window skips the fetcher — `tests/test_cache.py:43-46` asserts `len(calls) == 1` across two `cached_fetch` calls, plus `second.from_cache is True` and the body round-trips. Real assertion via the injected fake, as the criterion demands.
- Stale row refetches and refreshes — `tests/test_cache.py:60-65` advances the injected clock two days, asserts the new fetcher was called, and asserts `row.fetched_at == clock.now`. The refresh half of the criterion is genuinely checked, not just the refetch half.
- Failures not cached — `tests/test_cache.py:76-79` asserts both results are `ok is False`, `len(calls) == 2`, and `cache.get(...) is None`.
- Persistence across instances — `tests/test_cache.py:82-92` puts through `cache_a` and reads through `cache_b` on the same `tmp_path` db.
- Offline/temp-db — no `httpx` or network in the test module; every test takes `tmp_path`.

**Lens 2 — quality & security.** I read the code rather than skimming. Three things I specifically checked that could have been bugs but aren't:

The `put` statement drops the `error` column, which would silently lose data if an `ok` result could ever carry an error. It can't — both error paths in `fetch_url` (`fetch.py:83-89`) and `PoliteFetcher.fetch` (`polite.py:92-98`) set `body=None`/`status_code=None`, so `ok` is always `False` when `error` is set, and only `ok` results reach `put`. Safe.

The new `from_cache` field on `FetchResult` could have leaked into a fixed-column insert elsewhere. It doesn't — `model_dump()` is only ever called on `Opportunity` and `ApplicantProfile` (`store.py:80,117`, `profile.py:68`, `cli.py:39`), never on `FetchResult`. `put` maps columns explicitly, avoiding the computed-`ok` trap the plan flagged.

`cached_fetch` calls `fetch_fn(url)` with a single positional argument, which preserves composition with `PoliteFetcher.fetch(url)` (`polite.py:87`). The plan called this out as a risk and the implementation respected it.

Datetimes round-trip tz-aware, staleness uses an injectable clock so no sleeping, and the SQLite pattern (`sqlite3.connect`, `row_factory`, `CREATE TABLE IF NOT EXISTS` in `_init_schema`) matches `store.py:34-39` exactly. `__all__` is append-ordered by ticket in this repo, so the new exports are placed per convention. No secrets, no injection risk (parameterized throughout), no dead code, no tests that assert nothing.

**Lens 3 — visual.** This ticket has no user-facing surface: `cache.py` is a library module with no UI, template, or route. Visual verification is not applicable, so nothing was skipped for lack of tooling.

**One caveat, stated plainly:** the permission layer denied every attempt I made to run the test suite myself (`uv run pytest -q` and a direct `python -m pytest`), so I could not independently reproduce the green run. My confidence rests on reading all four tests' assertions line by line and on the machine-recorded `exit_code: 0` in `observability/runs/GH-33/iter01_test.json`, not on the test stage's prose summary. If the harness intends reviewers to re-run tests, that permission gap is worth a look — it's not a defect in this ticket.

```json
{
  "stage": "review",
  "ticket_id": "GH-33",
  "outcome": "success",
  "exit_signal": true,
  "summary": "All 5 acceptance criteria verified against concrete assertions in tests/test_cache.py; cache.py matches store.py's SQLite pattern and polite.py's injectable-seam pattern. Checked and cleared three latent bugs: dropped error column (safe — ok results never carry error), from_cache leaking into fixed-column model_dump inserts (never dumped), and fetch_fn arity breaking PoliteFetcher composition (single positional arg preserved). No user-facing surface, so Lens 3 is not applicable. Could not re-run pytest myself (permission-denied); relied on reading every assertion plus the recorded exit_code 0. This is the third clean SQLite-store-following-repo-pattern solve (store.py, profile.py, cache.py) — candidate for a new skill in skills/ codifying that pattern.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds a SQLite-backed response cache for the Session 3 fetch chain, so reruns mid-batch don't re-download bytes.\n\n**What changed**\n\n- New `scholarship_factory/cache.py` with `FetchCache` (a `fetch_cache` table keyed by URL, with `get`/`put` and a freshness-window lookup) and a `cached_fetch(url, *, cache, fetch_fn, max_age)` composition: cache hit within the window returns the stored result; miss or stale falls through to the real fetcher and stores the result only if it's `ok`.\n- `FetchResult` gains a `from_cache: bool = False` flag so callers can tell a cached result from a fresh one.\n- `FetchCache`, `cached_fetch`, and `DEFAULT_MAX_AGE` (1 day) are exported from the package.\n\n**Tradeoffs worth knowing**\n\n- Provenance rides on the existing `FetchResult` via a flag rather than a wrapper type, so downstream consumers (extract, adapters) don't have to unwrap for one boolean.\n- The composition is a function, not a `CachedFetcher` class, because all state lives in the `FetchCache`. It composes with `PoliteFetcher.fetch` as `fetch_fn` without either side knowing about the other — this is why `fetch_fn` is called with a single positional argument. A caller needing custom timeouts passes a pre-bound `functools.partial` or a `PoliteFetcher`.\n- The cache key is the URL as given, not `normalize_apply_url`, which encodes opportunity-dedup identity rather than byte-fetch identity and would wrongly collide URLs returning different bytes.\n- Failures are never cached, so a transient 500 can't poison a day. Only the six real columns are written; the computed `ok` is recomputed on read.\n\n**Risks**\n\n- Staleness is measured against an injectable clock; a caller passing a naive (non-tz-aware) clock will hit a TypeError on subtraction. All internal clocks and stored timestamps are tz-aware UTC.\n- No eviction beyond staleness, so the table grows unbounded over time. That's per the ticket's scope and is fine at current volumes, but is the obvious follow-up if the db gets large.\n- Field-level refresh (\"did the deadline change?\") remains Session 8's job and is explicitly out of scope here.\n\nTests are fully offline against a temp db with a fake fetcher and an injected clock — no network, no sleeping. Full suite green at 110 passed."
}
```