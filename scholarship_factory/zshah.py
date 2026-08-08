"""Deterministic parser for zshah101's automated internship board.

zshah101/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships crawls
ATS boards on its own schedule and publishes the result as
`docs/api/jobs.json`: an envelope (`generated_at`, `count`) wrapping a `jobs`
list. Unlike Simplify and vanshb03 it is not a hand-curated README dump but a
crawler's output, which is why it carries two facts the other boards don't —
**stated pay** (37 of 161 rows on 2026-08-08) and a machine-read `posted_at`.

Pay is the reason this source earns its keep: it is the only board of the
three that publishes a salary at all, so its rows reach the site with a pay
pill already filled while the enrichment ladder is still working through the
rest of the store.

`docs/api/jobs.json` is the *open* roles only; `data/jobs.json` is the full
archive including closed ones (346 vs 161). We read the open file, matching
the `active`/`is_visible` filter the other two board parsers apply — a closed
role is not an opportunity.

Like the other boards it publishes no application deadline, so `deadline`
stays None with provenance `none`.
"""
import json
from datetime import datetime

from .models import Opportunity, Provenance

#: sponsorship values that actually say something; "unknown" is the board's null
_SPONSORSHIP_TEXT = {
    "offers": "Offers Sponsorship",
    "no-sponsorship": "Does Not Offer Sponsorship",
    "citizens-only": "U.S. Citizenship is Required",
}


def _iso_date(timestamp) -> str | None:
    """`2026-08-07T00:00:00Z` -> `2026-08-07`; anything unparseable -> None."""
    if not isinstance(timestamp, str) or not timestamp.strip():
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def parse_zshah(body: str, source_url: str) -> list[Opportunity]:
    """Map zshah101's jobs JSON to `Opportunity` rows.

    Malformed JSON raises; the pipeline records that as a failed target.
    """
    payload = json.loads(body)
    listings = payload.get("jobs") if isinstance(payload, dict) else payload
    opportunities: list[Opportunity] = []

    for item in listings or []:
        url = item.get("url")
        title = item.get("title")
        if not url or not title:
            continue

        description_parts = []
        if item.get("category"):
            description_parts.append(f"{item['category']} internship")
        # the board writes "Not stated" where it could not read a term
        seasons = [s for s in (item.get("seasons") or []) if s] or (
            [item["season"]] if item.get("season") not in (None, "", "Not stated") else []
        )
        if seasons:
            description_parts.append("Term: " + ", ".join(seasons))
        if item.get("location"):
            description_parts.append("Location: " + item["location"])
        if item.get("remote"):
            description_parts.append("Remote")

        requirement_parts = []
        sponsorship = _SPONSORSHIP_TEXT.get(item.get("sponsorship"))
        if sponsorship:
            requirement_parts.append(f"Sponsorship: {sponsorship}")
        skills = [s for s in (item.get("skills") or []) if s]
        if skills:
            requirement_parts.append("Skills: " + ", ".join(skills))

        # pay is stated by the source, so it is quoted with the field it was
        # read from as its span; absent pay stays null, never inferred
        salary = item.get("salary")
        salary = salary.strip() if isinstance(salary, str) and salary.strip() else None

        opportunities.append(
            Opportunity(
                title=title,
                apply_url=url,
                source_url=source_url,
                organization=item.get("company"),
                type="internship",
                description=". ".join(description_parts) or None,
                requirements=". ".join(requirement_parts) or None,
                reward=salary,
                reward_provenance=Provenance.QUOTED if salary else Provenance.NONE,
                reward_source=(
                    json.dumps({"salary": salary}, ensure_ascii=False) if salary else None
                ),
                source_observed_date=_iso_date(
                    item.get("posted_at") or item.get("first_seen_at")
                ),
            )
        )

    return opportunities
