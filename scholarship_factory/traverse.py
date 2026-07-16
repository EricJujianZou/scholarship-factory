"""Depth-1 link traversal (Session 4 / Traverse).

Given a LIST extraction result, `traverse` fetches each thin item's detail
page, re-extracts it, and returns the enriched records plus a per-link
outcome report. It never recurses into a fetched page's own extraction
kind (v1 traversal stops at depth 1) and never touches the store --
identity/merge logic stays Session 5's job.
"""
from urllib.parse import urljoin

from pydantic import BaseModel, computed_field

from .extract import ExtractionResult, extract
from .fetch import fetch_url
from .jsonld import extract_jsonld
from .models import Opportunity
from .urls import normalize_apply_url

TRAVERSE_PAGE_CAP = 25


class LinkOutcome(BaseModel):
    url: str
    ok: bool
    status_code: int | None = None
    error: str | None = None
    opportunities_found: int = 0


class TraverseReport(BaseModel):
    outcomes: list[LinkOutcome]
    links_discovered: int
    cap_reached: bool

    @computed_field
    @property
    def links_traversed(self) -> int:
        return len(self.outcomes)


class TraverseResult(BaseModel):
    opportunities: list[Opportunity]
    report: TraverseReport


def traverse(
    result: ExtractionResult,
    listing_url: str,
    *,
    fetch_fn=fetch_url,
    extract_fn=extract,
    jsonld_fn=extract_jsonld,
    page_cap: int = TRAVERSE_PAGE_CAP,
) -> TraverseResult:
    opportunities: list[Opportunity] = []
    outcomes: list[LinkOutcome] = []
    seen: set[str] = set()
    cap_reached = False
    links_discovered = 0

    for item in result.opportunities:
        url = urljoin(listing_url, item.apply_url)
        key = normalize_apply_url(url)
        if key in seen:
            continue
        seen.add(key)
        links_discovered += 1

        if len(outcomes) >= page_cap:
            cap_reached = True
            continue

        fetch_result = fetch_fn(url)
        if not fetch_result.ok:
            outcomes.append(
                LinkOutcome(
                    url=url,
                    ok=False,
                    status_code=fetch_result.status_code,
                    error=fetch_result.error,
                )
            )
            continue

        detail_opportunities = list(
            jsonld_fn(fetch_result.body, fetch_result.final_url)
        )
        detail_opportunities.extend(
            extract_fn(fetch_result.body, fetch_result.final_url).opportunities
        )

        if not detail_opportunities:
            outcomes.append(
                LinkOutcome(
                    url=url,
                    ok=False,
                    status_code=fetch_result.status_code,
                    error="extraction yielded no opportunities",
                )
            )
            continue

        outcomes.append(
            LinkOutcome(
                url=url,
                ok=True,
                status_code=fetch_result.status_code,
                opportunities_found=len(detail_opportunities),
            )
        )
        opportunities.extend(detail_opportunities)

    return TraverseResult(
        opportunities=opportunities,
        report=TraverseReport(
            outcomes=outcomes,
            links_discovered=links_discovered,
            cap_reached=cap_reached,
        ),
    )
