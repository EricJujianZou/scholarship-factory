"""Deterministic parser for vanshb03's community internship listings.

vanshb03/Summer2027-Internships publishes its board the same way Simplify
does: `.github/scripts/listings.json` on the `dev` branch. The schema is a
subset of Simplify's — company, title, url, locations, sponsorship, a
singular `season` instead of a `terms` list, and no category or degrees —
so the parser mirrors `simplify.py` minus the missing fields.

Like Simplify, the board publishes no application deadlines, so `deadline`
stays None with provenance `none`.
"""
import json
from datetime import datetime, timezone

from .models import Opportunity

#: sponsorship values that actually say something; "Other" is the unknown
_INFORMATIVE_SPONSORSHIP = {
    "Offers Sponsorship",
    "Does Not Offer Sponsorship",
    "U.S. Citizenship is Required",
}


def _iso_date(unix_ts) -> str | None:
    if not unix_ts:
        return None
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).date().isoformat()


def parse_vansh(body: str, source_url: str) -> list[Opportunity]:
    """Map vanshb03's listings JSON to `Opportunity` rows.

    Only rows the board itself considers live (`active` and `is_visible`)
    are kept. Malformed JSON raises; the pipeline records that as a failed
    target.
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
        season = item.get("season")
        if season and season != "N/A":
            description_parts.append(f"Term: {season}")
        locations = [loc for loc in (item.get("locations") or []) if loc]
        if locations:
            description_parts.append("Location: " + ", ".join(locations))

        requirements = None
        if item.get("sponsorship") in _INFORMATIVE_SPONSORSHIP:
            requirements = f"Sponsorship: {item['sponsorship']}"

        opportunities.append(
            Opportunity(
                title=title,
                apply_url=url,
                source_url=source_url,
                organization=item.get("company_name"),
                type="internship",
                description=". ".join(description_parts) or None,
                requirements=requirements,
                source_observed_date=_iso_date(
                    item.get("date_updated") or item.get("date_posted")
                ),
            )
        )

    return opportunities
