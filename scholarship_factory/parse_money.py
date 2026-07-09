"""Deterministic money parse layer (S6): stored reward/cost strings -> typed amounts.

Mirrors parse_dates.py: Extract stores money as verbatim quoted text
("Up to EUR 7,500", "Free", "$5,000/yr for 4 years"); this library turns that
into a normalized amount + currency + bound, or None when unparseable. No LLM,
no network. A computed value is provenance `derived`; unresolvable -> None/`none`
(the deterministic boundary self-enforces no-fabrication).
"""
import re
from enum import Enum

from pydantic import BaseModel

from .models import Opportunity, Provenance


class MoneyBound(str, Enum):
    EXACT = "exact"
    UPPER = "upper"  # "up to 7,500"
    LOWER = "lower"  # "from 1,000"


class MoneyValue(BaseModel):
    amount: float  # total value (per_period * periods when a period is stated)
    currency: str | None = None
    bound: MoneyBound = MoneyBound.EXACT
    per_period: float | None = None  # e.g. 5000 for "$5,000/yr"
    periods: int | None = None  # e.g. 4 for "for 4 years"


_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP"}
_CURRENCY_CODES = {"USD", "EUR", "GBP", "CAD", "AUD"}
_NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_PERIOD_RE = re.compile(
    r"/\s*(?:yr|year|annum)|\bper\s+(?:year|annum|month)\b|\bannually\b", re.I
)
_FOR_N_RE = re.compile(r"(?:for|over|x|×)\s*(\d+)\s*(?:year|yr|month|mo)s?\b", re.I)


def _detect_currency(text: str) -> str | None:
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in text:
            return code
    for m in re.finditer(r"\b([A-Z]{3})\b", text):
        if m.group(1) in _CURRENCY_CODES:
            return m.group(1)
    return None


def _detect_bound(low: str) -> MoneyBound:
    if re.search(r"\bup to\b|\bmax(?:imum)?\b|\bno more than\b", low):
        return MoneyBound.UPPER
    if re.search(r"\bfrom\b|\bat least\b|\bmin(?:imum)?\b|\bstarting at\b", low):
        return MoneyBound.LOWER
    return MoneyBound.EXACT


def parse_money(text: str | None) -> MoneyValue | None:
    """Parse a stored reward/cost string into a MoneyValue, or None if unparseable."""
    if not text or not text.strip():
        return None
    low = text.lower()
    currency = _detect_currency(text)
    bound = _detect_bound(low)

    numbers = [float(m.group(0).replace(",", "")) for m in _NUMBER_RE.finditer(text)]
    if not numbers:
        if re.search(r"\bfree\b|\bno cost\b|\bno charge\b", low):
            return MoneyValue(amount=0.0, currency=currency, bound=MoneyBound.EXACT)
        return None

    amount = numbers[0]
    period = _PERIOD_RE.search(text)
    span = _FOR_N_RE.search(text)
    if period and span:
        periods = int(span.group(1))
        return MoneyValue(
            amount=amount * periods,
            currency=currency,
            bound=bound,
            per_period=amount,
            periods=periods,
        )
    return MoneyValue(amount=amount, currency=currency, bound=bound)


def _typed(text: str | None) -> tuple[MoneyValue | None, Provenance]:
    value = parse_money(text)
    return (value, Provenance.DERIVED) if value is not None else (None, Provenance.NONE)


def typed_reward(opp: Opportunity) -> tuple[MoneyValue | None, Provenance]:
    return _typed(opp.reward)


def typed_cost(opp: Opportunity) -> tuple[MoneyValue | None, Provenance]:
    return _typed(opp.cost)
