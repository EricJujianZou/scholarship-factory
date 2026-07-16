import httpx
import pytest

import scholarship_factory.fetch as fetch_module
from scholarship_factory import PoliteFetcher
from scholarship_factory.polite import DEFAULT_MIN_INTERVAL


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, duration: float) -> None:
        self.slept.append(duration)
        self.now += duration


def _allow_all_robots(path="/robots.txt"):
    def handler(request):
        if request.url.path == path:
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="ok")

    return handler


def test_same_host_second_fetch_is_spaced():
    clock = FakeClock()
    requested_paths = []

    def handler(request):
        requested_paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="ok")

    fetcher = PoliteFetcher(
        clock=clock.time,
        sleep=clock.sleep,
        transport=httpx.MockTransport(handler),
    )

    fetcher.fetch("https://example.com/a")
    clock.slept.clear()
    fetcher.fetch("https://example.com/b")

    assert DEFAULT_MIN_INTERVAL in clock.slept


def test_different_hosts_are_not_delayed():
    clock = FakeClock()

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="ok")

    fetcher = PoliteFetcher(
        clock=clock.time,
        sleep=clock.sleep,
        transport=httpx.MockTransport(handler),
    )

    # Warm both hosts' robots cache and rate-limit state first.
    fetcher.fetch("https://example.com/a")
    fetcher.fetch("https://other.com/b")
    clock.slept.clear()

    fetcher.fetch("https://example.com/c")
    fetcher.fetch("https://other.com/d")

    assert clock.slept == []


def test_disallowed_url_is_not_fetched():
    clock = FakeClock()
    requested_paths = []

    def handler(request):
        requested_paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        return httpx.Response(200, text="ok")

    fetcher = PoliteFetcher(
        clock=clock.time,
        sleep=clock.sleep,
        transport=httpx.MockTransport(handler),
    )

    result = fetcher.fetch("https://example.com/private")

    assert "/private" not in requested_paths
    assert result.ok is False
    assert "robots" in result.error


def test_robots_404_fails_open():
    clock = FakeClock()

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, text="not found")
        return httpx.Response(200, text="ok")

    fetcher = PoliteFetcher(
        clock=clock.time,
        sleep=clock.sleep,
        transport=httpx.MockTransport(handler),
    )

    result = fetcher.fetch("https://example.com/page")

    assert result.ok is True


def test_robots_timeout_fails_open(monkeypatch):
    monkeypatch.setattr(fetch_module, "RETRY_WAIT_MULTIPLIER", 0)
    clock = FakeClock()

    def handler(request):
        if request.url.path == "/robots.txt":
            raise httpx.ConnectTimeout("timed out", request=request)
        return httpx.Response(200, text="ok")

    fetcher = PoliteFetcher(
        clock=clock.time,
        sleep=clock.sleep,
        transport=httpx.MockTransport(handler),
    )

    result = fetcher.fetch("https://example.com/page")

    assert result.ok is True


def test_robots_requested_once_per_host():
    clock = FakeClock()
    requested_paths = []

    def handler(request):
        requested_paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, text="ok")

    fetcher = PoliteFetcher(
        clock=clock.time,
        sleep=clock.sleep,
        transport=httpx.MockTransport(handler),
    )

    fetcher.fetch("https://example.com/a")
    fetcher.fetch("https://example.com/b")
    fetcher.fetch("https://example.com/c")

    assert requested_paths.count("/robots.txt") == 1


def test_robots_404_fail_open_miss_is_cached_too():
    clock = FakeClock()
    requested_paths = []

    def handler(request):
        requested_paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(404, text="not found")
        return httpx.Response(200, text="ok")

    fetcher = PoliteFetcher(
        clock=clock.time,
        sleep=clock.sleep,
        transport=httpx.MockTransport(handler),
    )

    fetcher.fetch("https://example.com/a")
    fetcher.fetch("https://example.com/b")

    assert requested_paths.count("/robots.txt") == 1
