"""Sourcing run: seeds -> adapters -> fetch -> extract -> store (GH-34).

`run_sourcing` composes the already-merged pieces into one end-to-end run.
It adds no new judgment logic: fetch failures are recorded, not raised, and
both extract paths (JSON-LD structured + LLM) run on every successfully
fetched target so their opportunities can both land in the store.
"""
from collections.abc import Callable, Iterable
from urllib.parse import urljoin

from pydantic import BaseModel, computed_field

from .adapters import SkippedSeed, targets_for_seeds
from .extract import ExtractionResult, PageKind, extract
from .fetch import FetchResult, fetch_url
from .identity import merge_into
from .jsonld import extract_jsonld
from .models import Opportunity
from .seeds import Seed
from .store import OpportunityStore
from .traverse import TRAVERSE_PAGE_CAP, TraverseReport, TraverseResult, traverse
from .urls import normalize_apply_url

FetchFn = Callable[[str], FetchResult]
JsonldFn = Callable[[str, str], list[Opportunity]]
ExtractFn = Callable[[str, str], ExtractionResult]


class TargetOutcome(BaseModel):
    url: str
    ok: bool
    status_code: int | None = None
    error: str | None = None
    opportunities_stored: int = 0
    traversal: TraverseReport | None = None
    unlinked_items_dropped: int = 0


class SourcingReport(BaseModel):
    outcomes: list[TargetOutcome]
    skipped: list[SkippedSeed]

    @computed_field
    @property
    def targets_attempted(self) -> int:
        return len(self.outcomes)

    @computed_field
    @property
    def opportunities_stored(self) -> int:
        return sum(o.opportunities_stored for o in self.outcomes)


def _linked_items(
    items: list[Opportunity], listing_url: str
) -> tuple[list[Opportunity], int]:
    """Split a listing's thin items into those carrying their own link, and a count
    of those that don't.

    A link-less item falls back to the listing's own URL (`extract.py`), which is
    the dedup key -- storing two of them would merge two distinct opportunities
    into a single row. Drop them rather than merge; the caller reports the count.
    """
    listing_key = normalize_apply_url(listing_url)
    linked = [
        item
        for item in items
        if normalize_apply_url(urljoin(listing_url, item.apply_url)) != listing_key
    ]
    return linked, len(items) - len(linked)


def _fold_listing_items(
    items: list[Opportunity], traversal: TraverseResult, listing_url: str
) -> list[Opportunity]:
    """One record per opportunity: a listing's thin item and the detail record it
    linked to are the same opportunity, even when their `apply_url`s differ.

    The traversal edge is the identity here -- URL equality can't see it, because a
    detail page usually states a different apply link (an external form) than the
    listing linked to. The detail record wins; the listing's facts fill its gaps,
    which is what keeps a login-walled detail page from erasing them. An item whose
    link yielded nothing (capped, unreachable, extracted empty) is kept as-is.
    """
    folded = {key: list(records) for key, records in traversal.by_link.items()}
    unmatched: list[Opportunity] = []

    for item in items:
        key = normalize_apply_url(urljoin(listing_url, item.apply_url))
        records = folded.get(key)
        if records:
            records[0] = merge_into(records[0], item)
        else:
            unmatched.append(item)

    return [opp for records in folded.values() for opp in records] + unmatched


def run_sourcing(
    seeds: Iterable[Seed],
    store: OpportunityStore,
    *,
    fetch_fn: FetchFn = fetch_url,
    extract_fn: ExtractFn = extract,
    jsonld_fn: JsonldFn = extract_jsonld,
    page_cap: int = TRAVERSE_PAGE_CAP,
) -> SourcingReport:
    plan = targets_for_seeds(seeds)
    outcomes: list[TargetOutcome] = []

    for target in plan.targets:
        result = fetch_fn(target.url)
        if not result.ok:
            outcomes.append(
                TargetOutcome(
                    url=target.url,
                    ok=False,
                    status_code=result.status_code,
                    error=result.error,
                )
            )
            continue

        opportunities = list(jsonld_fn(result.body, result.final_url))
        try:
            extraction = extract_fn(result.body, result.final_url)
        except Exception as exc:  # LLM outage/quota: record it, keep the run going
            outcomes.append(
                TargetOutcome(
                    url=target.url,
                    ok=False,
                    status_code=result.status_code,
                    error=f"extract failed: {type(exc).__name__}: {exc}",
                )
            )
            continue

        traversal_report: TraverseReport | None = None
        unlinked_dropped = 0
        if extraction.kind == PageKind.LIST:
            traversal = traverse(
                extraction,
                result.final_url,
                fetch_fn=fetch_fn,
                extract_fn=extract_fn,
                jsonld_fn=jsonld_fn,
                page_cap=page_cap,
            )
            linked, unlinked_dropped = _linked_items(
                extraction.opportunities, result.final_url
            )
            opportunities.extend(
                _fold_listing_items(linked, traversal, result.final_url)
            )
            traversal_report = traversal.report
        else:
            opportunities.extend(extraction.opportunities)

        for opportunity in opportunities:
            store.insert(opportunity)

        outcomes.append(
            TargetOutcome(
                url=target.url,
                ok=True,
                status_code=result.status_code,
                opportunities_stored=len(opportunities),
                traversal=traversal_report,
                unlinked_items_dropped=unlinked_dropped,
            )
        )

    return SourcingReport(outcomes=outcomes, skipped=plan.skipped)
