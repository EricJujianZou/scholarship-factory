from datetime import date, datetime, time

import dateparser.search

from .models import Opportunity, Provenance


def parse_deadline_dates(text: str | None, anchor: date) -> list[date] | None:
    if not text or not text.strip():
        return None

    matches = dateparser.search.search_dates(
        text,
        languages=["en"],
        settings={
            "RELATIVE_BASE": datetime.combine(anchor, time.min),
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": False,
        },
    )
    if not matches:
        return None

    dates: list[date] = []
    for _, dt in matches:
        d = dt.date()
        if d not in dates:
            dates.append(d)
    return dates or None


def _parse_anchor(raw: str | None) -> date | None:
    if not raw or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        pass
    dt = dateparser.parse(raw, languages=["en"])
    return dt.date() if dt else None


def typed_deadlines(opp: Opportunity) -> tuple[list[date] | None, Provenance]:
    anchor = _parse_anchor(opp.source_observed_date) or _parse_anchor(opp.first_seen)
    if not opp.deadline or anchor is None:
        return None, Provenance.NONE

    dates = parse_deadline_dates(opp.deadline, anchor)
    if dates:
        return dates, Provenance.DERIVED
    return None, Provenance.NONE
