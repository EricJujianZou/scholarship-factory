"""Static open-web fetcher (Session 3 / Fetch, first link).

`fetch_url` performs a single static `httpx` GET with a browser-like
User-Agent and bounded retry on 429/5xx/transport errors, producing a
`FetchResult` that represents every outcome honestly. Out of scope: source
adapters, robots/politeness, caching, and headless/JS rendering (deferred
until a real fixture proves a static fetch returns an empty SPA shell).
"""
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel, Field, computed_field
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 15.0
RETRY_ATTEMPTS = 3
RETRY_WAIT_MULTIPLIER = 0.5


class FetchResult(BaseModel):
    requested_url: str
    final_url: str
    status_code: int | None = None
    content_type: str | None = None
    body: str | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    @computed_field
    @property
    def ok(self) -> bool:
        return (
            self.status_code is not None
            and 200 <= self.status_code < 300
            and self.body is not None
        )


def _is_retryable_status(response: httpx.Response) -> bool:
    return response.status_code == 429 or response.status_code >= 500


def _retrying() -> Retrying:
    return Retrying(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER),
        retry=retry_if_result(_is_retryable_status)
        | retry_if_exception_type(httpx.TransportError),
        reraise=True,
    )


def fetch_url(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    transport: httpx.BaseTransport | None = None,
) -> FetchResult:
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": user_agent},
        transport=transport,
    ) as client:
        try:
            response = _retrying()(client.get, url)
        except RetryError as exc:
            response = exc.last_attempt.result()
        except httpx.TransportError as exc:
            return FetchResult(
                requested_url=url,
                final_url=url,
                status_code=None,
                body=None,
                error=f"{type(exc).__name__}: {exc}",
            )

    return FetchResult(
        requested_url=url,
        final_url=str(response.url),
        status_code=response.status_code,
        content_type=response.headers.get("content-type"),
        body=response.text,
    )
