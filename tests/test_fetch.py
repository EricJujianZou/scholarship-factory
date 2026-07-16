from datetime import datetime

import httpx
import pytest

import scholarship_factory.fetch as fetch_module
from scholarship_factory import FetchResult, fetch_url


def test_success_result_is_ok():
    result = FetchResult(
        requested_url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        content_type="text/html",
        body="<html></html>",
    )
    assert result.ok is True


def test_404_result_is_not_ok():
    result = FetchResult(
        requested_url="https://example.com/missing",
        final_url="https://example.com/missing",
        status_code=404,
        body="Not Found",
    )
    assert result.ok is False


def test_403_result_is_not_ok():
    result = FetchResult(
        requested_url="https://example.com/forbidden",
        final_url="https://example.com/forbidden",
        status_code=403,
        body="Forbidden",
    )
    assert result.ok is False


def test_connection_failure_result_is_valid_and_not_ok():
    result = FetchResult(
        requested_url="https://example.com",
        final_url="https://example.com",
        status_code=None,
        body=None,
        error="Connection timed out",
    )
    assert result.status_code is None
    assert result.body is None
    assert result.error == "Connection timed out"
    assert result.ok is False


def test_final_url_defaults_to_requested_url():
    result = FetchResult(
        requested_url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        body="ok",
    )
    assert result.final_url == result.requested_url


def test_final_url_can_differ_after_redirect():
    result = FetchResult(
        requested_url="https://short.link/abc",
        final_url="https://example.com/real-page",
        status_code=200,
        body="ok",
    )
    assert result.final_url != result.requested_url


def test_fetched_at_is_populated():
    result = FetchResult(
        requested_url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        body="ok",
    )
    assert isinstance(result.fetched_at, datetime)


def test_2xx_with_no_body_is_not_ok():
    result = FetchResult(
        requested_url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        body=None,
    )
    assert result.ok is False


def test_fetch_url_200_html():
    def handler(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html></html>")

    result = fetch_url("https://example.com", transport=httpx.MockTransport(handler))

    assert result.ok is True
    assert result.body == "<html></html>"
    assert result.content_type == "text/html"
    assert result.final_url == "https://example.com"


@pytest.mark.parametrize("status_code", [404, 403])
def test_fetch_url_4xx_is_single_attempt(status_code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status_code, text="nope")

    result = fetch_url("https://example.com", transport=httpx.MockTransport(handler))

    assert len(calls) == 1
    assert result.ok is False
    assert result.status_code == status_code


def test_fetch_url_retries_429_then_succeeds(monkeypatch):
    monkeypatch.setattr(fetch_module, "RETRY_WAIT_MULTIPLIER", 0)
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, text="ok")

    result = fetch_url("https://example.com", transport=httpx.MockTransport(handler))

    assert len(calls) == 2
    assert result.ok is True


def test_fetch_url_persistent_transport_error(monkeypatch):
    monkeypatch.setattr(fetch_module, "RETRY_WAIT_MULTIPLIER", 0)
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectTimeout("timed out", request=request)

    result = fetch_url("https://example.com", transport=httpx.MockTransport(handler))

    assert len(calls) == fetch_module.RETRY_ATTEMPTS
    assert result.status_code is None
    assert result.error is not None
    assert result.ok is False


def test_fetch_url_sends_browser_user_agent():
    seen = {}

    def handler(request):
        seen["user_agent"] = request.headers["user-agent"]
        return httpx.Response(200, text="ok")

    fetch_url("https://example.com", transport=httpx.MockTransport(handler))

    assert seen["user_agent"] == fetch_module.DEFAULT_USER_AGENT


def test_fetch_url_follows_redirect_and_records_final_url():
    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://example.com/end"})
        return httpx.Response(200, text="ok")

    result = fetch_url(
        "https://example.com/start", transport=httpx.MockTransport(handler)
    )

    assert result.requested_url == "https://example.com/start"
    assert result.final_url == "https://example.com/end"
