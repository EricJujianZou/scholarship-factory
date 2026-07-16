"""Per-host politeness layer (Session 3 / Fetch, third link).

`PoliteFetcher` wraps `fetch_url` with two protections: per-host minimum
spacing between requests, and a robots.txt check per host (cached in
memory, fetched at most once per host per instance). robots.txt itself
being unreachable or malformed fails open — politeness is insurance, not
a gate that can wedge the whole run.
"""
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from .fetch import DEFAULT_TIMEOUT, DEFAULT_USER_AGENT, FetchResult, fetch_url

DEFAULT_MIN_INTERVAL = 2.0


def _host(url: str) -> str:
    return urlsplit(url).netloc.lower()


def _robots_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


class PoliteFetcher:
    def __init__(
        self,
        *,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
        transport: httpx.BaseTransport | None = None,
        clock=time.monotonic,
        sleep=time.sleep,
        fetch_fn=fetch_url,
    ):
        self._min_interval = min_interval
        self._timeout = timeout
        self._user_agent = user_agent
        self._transport = transport
        self._clock = clock
        self._sleep = sleep
        self._fetch_fn = fetch_fn
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}

    def _wait_for_host(self, host: str) -> None:
        if host in self._last_request:
            elapsed = self._clock() - self._last_request[host]
            remaining = self._min_interval - elapsed
            if remaining > 0:
                self._sleep(remaining)
        self._last_request[host] = self._clock()

    def _fetch(self, url: str) -> FetchResult:
        return self._fetch_fn(
            url,
            timeout=self._timeout,
            user_agent=self._user_agent,
            transport=self._transport,
        )

    def _robots_parser(self, url: str, host: str) -> RobotFileParser | None:
        if host in self._robots:
            return self._robots[host]

        robots_url = _robots_url(url)
        self._wait_for_host(host)
        result = self._fetch(robots_url)

        parser: RobotFileParser | None = None
        if result.ok:
            try:
                parser = RobotFileParser()
                parser.set_url(robots_url)
                parser.parse(result.body.splitlines())
            except Exception:
                parser = None

        self._robots[host] = parser
        return parser

    def fetch(self, url: str) -> FetchResult:
        host = _host(url)
        parser = self._robots_parser(url, host)

        if parser is not None and not parser.can_fetch(self._user_agent, url):
            return FetchResult(
                requested_url=url,
                final_url=url,
                status_code=None,
                body=None,
                error=f"robots.txt disallows {url}",
            )

        self._wait_for_host(host)
        return self._fetch(url)
