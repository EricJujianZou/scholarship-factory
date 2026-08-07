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


def title_org_key(title: str | None, organization: str | None) -> str | None:
    """Folded title+org identity key, or None when either half is missing.

    Stored in its own indexed column so `find_duplicate` is two index lookups
    instead of a scan of the whole table per insert."""
    folded_title = normalize_text(title)
    folded_org = normalize_text(organization)
    if folded_title is None or folded_org is None:
        return None
    return f"{folded_title}\x1f{folded_org}"


def find_duplicate(store: "OpportunityStore", opportunity: Opportunity) -> Opportunity | None:
    url_match = store.find_by_normalized_url(normalize_apply_url(opportunity.apply_url))
    if url_match is not None:
        return url_match
    key = title_org_key(opportunity.title, opportunity.organization)
    if key is None:
        return None
    return store.find_by_title_org_key(key)


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
