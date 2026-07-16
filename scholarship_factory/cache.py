"""Response cache (Session 3 / Fetch, fourth link).

`FetchCache` stores successful (`ok`) `FetchResult`s in SQLite keyed by
URL, and `cached_fetch` composes a cache lookup with any `fetch_fn` that
takes a single positional `url` (`fetch_url` or `PoliteFetcher.fetch`).
Within a freshness window a repeat request returns the cached result
instead of refetching; failures are never cached. Out of scope:
field-level refresh ("did the deadline change?"), which is Session 8's
job - this is only about not re-downloading bytes mid-run/day.
"""
import sqlite3
from datetime import datetime, timedelta, timezone

from .fetch import FetchResult, fetch_url

DEFAULT_MAX_AGE = timedelta(days=1)


class FetchCache:
    def __init__(self, db_path: str, *, clock=lambda: datetime.now(timezone.utc)):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._clock = clock
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fetch_cache (
                url TEXT PRIMARY KEY,
                fetched_at TEXT NOT NULL,
                status_code INTEGER,
                content_type TEXT,
                body TEXT,
                final_url TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def put(self, result: FetchResult) -> None:
        self._conn.execute(
            """
            INSERT INTO fetch_cache (url, fetched_at, status_code, content_type, body, final_url)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                fetched_at = excluded.fetched_at,
                status_code = excluded.status_code,
                content_type = excluded.content_type,
                body = excluded.body,
                final_url = excluded.final_url
            """,
            (
                result.requested_url,
                result.fetched_at.isoformat(),
                result.status_code,
                result.content_type,
                result.body,
                result.final_url,
            ),
        )
        self._conn.commit()

    def get(self, url: str, max_age: timedelta) -> FetchResult | None:
        cur = self._conn.execute(
            "SELECT * FROM fetch_cache WHERE url = ?", (url,)
        )
        row = cur.fetchone()
        if row is None:
            return None

        fetched_at = datetime.fromisoformat(row["fetched_at"])
        if self._clock() - fetched_at > max_age:
            return None

        return FetchResult(
            requested_url=url,
            final_url=row["final_url"],
            status_code=row["status_code"],
            content_type=row["content_type"],
            body=row["body"],
            fetched_at=fetched_at,
            from_cache=True,
        )


def cached_fetch(
    url: str,
    *,
    cache: FetchCache,
    fetch_fn=fetch_url,
    max_age: timedelta = DEFAULT_MAX_AGE,
) -> FetchResult:
    cached = cache.get(url, max_age)
    if cached is not None:
        return cached

    result = fetch_fn(url)
    if result.ok:
        cache.put(result)
    return result
