"""Deterministic parser for Simplify's community internship listings.

SimplifyJobs publishes its internship board as JSON in the open
(`.github/scripts/listings.json` in the Summer20XX-Internships repos). The
rows are structured facts — company, title, url, locations, terms,
sponsorship — so this path needs no LLM call and no traversal: one fetch,
one parse, N rows. Attribution is deliberate: the site and digests credit
Simplify as a source rather than disguising it (`source_url` records it,
as it does everywhere else).

Simplify does not publish application deadlines, so `deadline` stays None
with provenance `none` — the no-fabrication rule applies to imports too.
"""
import json
from datetime import datetime, timezone

from .models import Opportunity

#: sponsorship values that actually say something; "Other" is Simplify's unknown
_INFORMATIVE_SPONSORSHIP = {
    "Offers Sponsorship",
    "Does Not Offer Sponsorship",
    "U.S. Citizenship is Required",
}


def _iso_date(unix_ts) -> str | None:
    if not unix_ts:
        return None
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).date().isoformat()


def parse_simplify(body: str, source_url: str) -> list[Opportunity]:
    """Map Simplify's listings JSON to `Opportunity` rows.

    Only rows Simplify itself considers live (`active` and `is_visible`) are
    kept — the archive is huge and closed roles would drown the store.
    Malformed JSON raises; the pipeline records that as a failed target.
    """
    listings = json.loads(body)
    opportunities: list[Opportunity] = []

    for item in listings:
        if not (item.get("active") and item.get("is_visible")):
            continue
        url = item.get("url")
        title = item.get("title")
        if not url or not title:
            continue

        description_parts = []
        if item.get("category"):
            description_parts.append(f"{item['category']} internship")
        terms = [t for t in (item.get("terms") or []) if t and t != "N/A"]
        if terms:
            description_parts.append("Term: " + ", ".join(terms))
        locations = [loc for loc in (item.get("locations") or []) if loc]
        if locations:
            description_parts.append("Location: " + ", ".join(locations))

        requirement_parts = []
        if item.get("sponsorship") in _INFORMATIVE_SPONSORSHIP:
            requirement_parts.append(f"Sponsorship: {item['sponsorship']}")
        degrees = [d for d in (item.get("degrees") or []) if d]
        if degrees:
            requirement_parts.append("Degrees: " + ", ".join(degrees))

        opportunities.append(
            Opportunity(
                title=title,
                apply_url=url,
                source_url=source_url,
                organization=item.get("company_name"),
                type="internship",
                description=". ".join(description_parts) or None,
                requirements=". ".join(requirement_parts) or None,
                source_observed_date=_iso_date(
                    item.get("date_updated") or item.get("date_posted")
                ),
            )
        )

    return opportunities
