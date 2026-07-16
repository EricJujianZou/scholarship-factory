import re
from typing import TYPE_CHECKING

from .models import Opportunity
from .urls import normalize_apply_url

if TYPE_CHECKING:
    from .store import OpportunityStore

_FACT_TRIPLES = (
    ("deadline", "deadline_provenance", "deadline_source"),
    ("reward", "reward_provenance", "reward_source"),
    ("cost", "cost_provenance", "cost_source"),
)
_FILL_FIELDS = ("organization", "requirements", "type", "description", "source_observed_date")


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    folded = re.sub(r"[^\w\s]", " ", value.lower())
    folded = " ".join(folded.split())
    return folded or None


def find_duplicate(store: "OpportunityStore", opportunity: Opportunity) -> Opportunity | None:
    normalized_url = normalize_apply_url(opportunity.apply_url)
    normalized_title = normalize_text(opportunity.title)
    normalized_org = normalize_text(opportunity.organization)

    title_org_match = None
    for row in store.list():
        if normalize_apply_url(row.apply_url) == normalized_url:
            return row
        if (
            title_org_match is None
            and normalized_title is not None
            and normalized_org is not None
            and normalize_text(row.title) == normalized_title
            and normalize_text(row.organization) == normalized_org
        ):
            title_org_match = row
    return title_org_match


def merge_into(existing: Opportunity, incoming: Opportunity) -> Opportunity:
    updates: dict[str, object] = {}

    for value_field, provenance_field, source_field in _FACT_TRIPLES:
        if getattr(existing, value_field) is None:
            updates[value_field] = getattr(incoming, value_field)
            updates[provenance_field] = getattr(incoming, provenance_field)
            updates[source_field] = getattr(incoming, source_field)

    for field in _FILL_FIELDS:
        if getattr(existing, field) is None:
            updates[field] = getattr(incoming, field)

    return existing.model_copy(update=updates)
