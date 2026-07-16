"""Sourcing run: seeds -> adapters -> fetch -> extract -> store (GH-34).

`run_sourcing` composes the already-merged pieces into one end-to-end run.
It adds no new judgment logic: fetch failures are recorded, not raised, and
both extract paths (JSON-LD structured + LLM) run on every successfully
fetched target so their opportunities can both land in the store.
"""
from collections.abc import Callable, Iterable

from pydantic import BaseModel, computed_field

from .adapters import SkippedSeed, targets_for_seeds
from .extract import ExtractionResult, PageKind, extract
from .fetch import FetchResult, fetch_url
from .jsonld import extract_jsonld
from .models import Opportunity
from .seeds import Seed
from .store import OpportunityStore
from .traverse import TRAVERSE_PAGE_CAP, TraverseReport, traverse

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
        extraction = extract_fn(result.body, result.final_url)
        traversal_report: TraverseReport | None = None
        if extraction.kind == PageKind.LIST:
            traversal = traverse(
                extraction,
                result.final_url,
                fetch_fn=fetch_fn,
                extract_fn=extract_fn,
                jsonld_fn=jsonld_fn,
                page_cap=page_cap,
            )
            opportunities.extend(traversal.opportunities)
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
            )
        )

    return SourcingReport(outcomes=outcomes, skipped=plan.skipped)
