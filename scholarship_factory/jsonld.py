import json
from html.parser import HTMLParser
from typing import Any

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


def extract_jsonld(raw_html: str, source_url: str) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    for obj in _iter_objects(raw_html):
        if not _type_set(obj) & _OPPORTUNITY_TYPES:
            continue
        opportunity = _to_opportunity(obj, source_url)
        if opportunity is not None:
            opportunities.append(opportunity)
    return opportunities
