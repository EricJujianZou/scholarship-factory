"""On-demand refresh (Session 8, last v1 slice): re-check one opportunity's
facts against its live source page. No scheduler, no automatic refresh -
refresh only runs when asked, and it always bypasses the fetch cache
(`cache.py`), since the whole point is to see what the live page says now.
"""
from enum import Enum

from pydantic import BaseModel

from .extract import ExtractFn, PageKind, extract
from .fetch import FetchFn, fetch_url
from .models import Opportunity
from .store import OpportunityStore
from .urls import normalize_apply_url

_FACT_TRIPLES = (
    ("deadline", "deadline_provenance", "deadline_source"),
    ("reward", "reward_provenance", "reward_source"),
    ("cost", "cost_provenance", "cost_source"),
)


class RefreshStatus(str, Enum):
    NEW = "new"
    REFRESHED = "refreshed"
    CHANGED = "changed"
    UNREACHABLE = "unreachable"


class FieldChange(BaseModel):
    field: str
    old_value: str | None
    new_value: str | None
    old_source: str | None
    new_source: str | None


class RefreshOutcome(BaseModel):
    opportunity_id: str
    status: str
    changed_fields: list[FieldChange] = []
    no_longer_found: list[str] = []
    fetch_status_code: int | None = None
    error: str | None = None


def _pick_candidate(extraction, opportunity: Opportunity) -> Opportunity | None:
    target = normalize_apply_url(opportunity.apply_url)
    for candidate in extraction.opportunities:
        if normalize_apply_url(candidate.apply_url) == target:
            return candidate
    if len(extraction.opportunities) == 1 and extraction.kind is PageKind.DETAIL:
        return extraction.opportunities[0]
    return None


def refresh_opportunity(
    store: OpportunityStore,
    opportunity_id: str,
    *,
    fetch_fn: FetchFn = fetch_url,
    extract_fn: ExtractFn = extract,
) -> RefreshOutcome:
    opp = store.get(opportunity_id)
    if opp is None:
        raise KeyError(opportunity_id)

    result = fetch_fn(opp.source_url)
    if not result.ok:
        store.set_status(opp.id, RefreshStatus.UNREACHABLE.value)
        return RefreshOutcome(
            opportunity_id=opp.id,
            status=RefreshStatus.UNREACHABLE.value,
            fetch_status_code=result.status_code,
            error=result.error,
        )

    extraction = extract_fn(result.body, result.final_url)
    candidate = _pick_candidate(extraction, opp)

    updates: dict[str, object] = {}
    changed_fields: list[FieldChange] = []
    no_longer_found: list[str] = []

    for value_field, provenance_field, source_field in _FACT_TRIPLES:
        old_value = getattr(opp, value_field)
        old_source = getattr(opp, source_field)
        new_value = getattr(candidate, value_field) if candidate is not None else None
        new_source = getattr(candidate, source_field) if candidate is not None else None

        if new_value is None:
            if old_value is not None:
                no_longer_found.append(value_field)
            continue

        if new_value != old_value or new_source != old_source:
            updates[value_field] = new_value
            updates[provenance_field] = getattr(candidate, provenance_field)
            updates[source_field] = new_source
            changed_fields.append(
                FieldChange(
                    field=value_field,
                    old_value=old_value,
                    new_value=new_value,
                    old_source=old_source,
                    new_source=new_source,
                )
            )

    status = (
        RefreshStatus.CHANGED
        if (changed_fields or no_longer_found)
        else RefreshStatus.REFRESHED
    )
    store.update(opp.model_copy(update={**updates, "status": status.value}))

    return RefreshOutcome(
        opportunity_id=opp.id,
        status=status.value,
        changed_fields=changed_fields,
        no_longer_found=no_longer_found,
    )
