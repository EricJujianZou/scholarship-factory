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
