from datetime import datetime, timedelta, timezone

from scholarship_factory import FetchCache, FetchResult, cached_fetch


class FakeClock:
    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_result(url="https://example.com/a", ok=True, fetched_at=None) -> FetchResult:
    return FetchResult(
        requested_url=url,
        final_url=url,
        status_code=200 if ok else 500,
        content_type="text/html",
        body="<html></html>" if ok else None,
        fetched_at=fetched_at or datetime.now(timezone.utc),
    )


def make_fetcher(result: FetchResult):
    calls = []

    def fetch_fn(url):
        calls.append(url)
        return result

    return fetch_fn, calls


def test_second_fetch_within_window_is_cached(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    cache = FetchCache(str(tmp_path / "cache.db"), clock=clock)
    fetch_fn, calls = make_fetcher(make_result(fetched_at=clock.now))

    first = cached_fetch("https://example.com/a", cache=cache, fetch_fn=fetch_fn)
    second = cached_fetch("https://example.com/a", cache=cache, fetch_fn=fetch_fn)

    assert len(calls) == 1
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.body == "<html></html>"


def test_stale_result_triggers_refetch(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    cache = FetchCache(str(tmp_path / "cache.db"), clock=clock)
    fetch_fn, calls = make_fetcher(make_result(fetched_at=clock.now))

    cached_fetch("https://example.com/a", cache=cache, fetch_fn=fetch_fn)

    clock.now = clock.now + timedelta(days=2)
    fetch_fn2, calls2 = make_fetcher(make_result(fetched_at=clock.now))
    result = cached_fetch("https://example.com/a", cache=cache, fetch_fn=fetch_fn2)

    assert len(calls2) == 1
    assert result.from_cache is False

    row = cache.get("https://example.com/a", timedelta(days=1))
    assert row is not None
    assert row.fetched_at == clock.now


def test_failed_fetch_is_not_cached(tmp_path):
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    cache = FetchCache(str(tmp_path / "cache.db"), clock=clock)
    fetch_fn, calls = make_fetcher(make_result(ok=False, fetched_at=clock.now))

    first = cached_fetch("https://example.com/a", cache=cache, fetch_fn=fetch_fn)
    second = cached_fetch("https://example.com/a", cache=cache, fetch_fn=fetch_fn)

    assert first.ok is False
    assert second.ok is False
    assert len(calls) == 2
    assert cache.get("https://example.com/a", timedelta(days=1)) is None


def test_cache_persists_across_instances(tmp_path):
    db_path = str(tmp_path / "cache.db")
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    cache_a = FetchCache(db_path, clock=clock)
    cache_a.put(make_result(fetched_at=clock.now))

    cache_b = FetchCache(db_path, clock=clock)
    result = cache_b.get("https://example.com/a", timedelta(days=1))

    assert result is not None
    assert result.from_cache is True
