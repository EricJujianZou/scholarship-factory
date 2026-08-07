import json
from html.parser import HTMLParser
from typing import Any

from pydantic import BaseModel

from .models import Opportunity, Provenance

_OPPORTUNITY_TYPES = {"Event", "JobPosting", "Offer"}


class _JsonLdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._blocks: list[str] = []
        self._in_ldjson = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self._in_ldjson = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_ldjson = False

    def handle_data(self, data: str) -> None:
        if self._in_ldjson:
            self._blocks.append(data)

    def blocks(self) -> list[str]:
        return self._blocks


def _iter_objects(raw_html: str) -> list[dict[str, Any]]:
    collector = _JsonLdCollector()
    collector.feed(raw_html)
    collector.close()

    objects: list[dict[str, Any]] = []
    for raw_block in collector.blocks():
        try:
            parsed = json.loads(raw_block)
        except json.JSONDecodeError:
            continue
        candidates = parsed if isinstance(parsed, list) else [parsed]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            graph = candidate.get("@graph")
            if isinstance(graph, list):
                objects.extend(item for item in graph if isinstance(item, dict))
            else:
                objects.append(candidate)
    return objects


def _type_set(obj: dict[str, Any]) -> set[str]:
    raw_type = obj.get("@type")
    if isinstance(raw_type, str):
        return {raw_type}
    if isinstance(raw_type, list):
        return {t for t in raw_type if isinstance(t, str)}
    return set()


def _as_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return None


def _extract_cost(obj: dict[str, Any]) -> tuple[str | None, str | None]:
    offer = _as_dict(obj.get("offers")) or obj
    price = offer.get("price")
    if price is None:
        return None, None
    currency = offer.get("priceCurrency")
    value = f"{price} {currency}".strip() if currency else str(price)
    return value, value


def _to_opportunity(obj: dict[str, Any], source_url: str) -> Opportunity | None:
    title = obj.get("name") or obj.get("title") or obj.get("headline")
    if not isinstance(title, str) or not title:
        return None

    offer = _as_dict(obj.get("offers"))
    apply_url = (offer.get("url") if offer else None) or obj.get("url") or source_url

    organization = None
    organizer = _as_dict(obj.get("organizer")) or _as_dict(obj.get("hiringOrganization"))
    if organizer:
        org_name = organizer.get("name")
        if isinstance(org_name, str):
            organization = org_name

    cost, cost_source = _extract_cost(obj)
    cost_provenance = Provenance.QUOTED if cost_source is not None else Provenance.NONE

    return Opportunity(
        title=title,
        apply_url=apply_url,
        source_url=source_url,
        organization=organization,
        cost=cost,
        cost_provenance=cost_provenance,
        cost_source=cost_source,
    )


class JobPostingFacts(BaseModel):
    """Enrichment facts read from a JSON-LD JobPosting block (GH-53).

    Each `*_source` is the exact JSON text the fact was read from, honoring the
    provenance contract: values from structured data still carry the span that
    proves them. `valid_through` is a posting expiry, not a stated application
    deadline — callers must record it as provenance `derived`.
    """

    salary: str | None = None
    salary_source: str | None = None
    valid_through: str | None = None
    valid_through_source: str | None = None
    logo: str | None = None
    organization: str | None = None

    def has_facts(self) -> bool:
        return any((self.salary, self.valid_through, self.logo))


def _format_number(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        # a zero salary is a placeholder, not a stated wage
        if float(value) == 0:
            return None
        return f"{int(value):,}" if float(value).is_integer() else f"{value:,}"
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _salary_text(base: Any) -> str | None:
    """Render a schema.org baseSalary (MonetaryAmount) as a short pay string."""
    if isinstance(base, (int, float, str)):
        return _format_number(base)
    base_dict = _as_dict(base)
    if base_dict is None:
        return None

    currency = base_dict.get("currency") or base_dict.get("priceCurrency")
    value = base_dict.get("value")
    unit = None
    if isinstance(value, dict):
        unit = value.get("unitText")
        low = _format_number(value.get("minValue"))
        high = _format_number(value.get("maxValue"))
        exact = _format_number(value.get("value"))
        if low and high and low != high:
            number = f"{low}–{high}"
        else:
            number = exact or low or high
    else:
        number = _format_number(value)
    if number is None:
        return None

    text = number
    if isinstance(currency, str) and currency.strip():
        text = f"{text} {currency.strip()}"
    if isinstance(unit, str) and unit.strip():
        text = f"{text} per {unit.strip().lower()}"
    return text


def _logo_url(org: dict[str, Any]) -> str | None:
    logo = org.get("logo")
    if isinstance(logo, dict):
        logo = logo.get("url")
    if isinstance(logo, str) and logo.strip():
        return logo.strip()
    return None


def _jobposting_facts(obj: dict[str, Any]) -> JobPostingFacts:
    salary = salary_source = None
    base = obj.get("baseSalary")
    if base is not None:
        salary = _salary_text(base)
        if salary is not None:
            salary_source = json.dumps({"baseSalary": base}, ensure_ascii=False)

    valid_through = valid_through_source = None
    raw_valid = obj.get("validThrough")
    if isinstance(raw_valid, str) and raw_valid.strip():
        valid_through = raw_valid.strip()[:10]
        valid_through_source = json.dumps(
            {"validThrough": raw_valid}, ensure_ascii=False
        )

    logo = organization = None
    org = _as_dict(obj.get("hiringOrganization"))
    if org is not None:
        logo = _logo_url(org)
        name = org.get("name")
        if isinstance(name, str) and name.strip():
            organization = name.strip()

    return JobPostingFacts(
        salary=salary,
        salary_source=salary_source,
        valid_through=valid_through,
        valid_through_source=valid_through_source,
        logo=logo,
        organization=organization,
    )


def extract_jobposting_facts(raw_html: str) -> JobPostingFacts | None:
    """First JSON-LD JobPosting on the page that states any enrichment fact.

    Returns None when the page has no JobPosting block, or has one that
    states nothing we track — absent facts stay absent.
    """
    for obj in _iter_objects(raw_html):
        if "JobPosting" not in _type_set(obj):
            continue
        facts = _jobposting_facts(obj)
        if facts.has_facts():
            return facts
    return None


def extract_jsonld(raw_html: str, source_url: str) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    for obj in _iter_objects(raw_html):
        if not _type_set(obj) & _OPPORTUNITY_TYPES:
            continue
        opportunity = _to_opportunity(obj, source_url)
        if opportunity is not None:
            opportunities.append(opportunity)
    return opportunities
