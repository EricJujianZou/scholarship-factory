"""Deterministic ranking (S6): stored opportunities -> eligibility + sort vs profile.

Locked decisions (owner UX call):
- Deterministic hard filters + sort. No LLM call, no fit score float.
- Unknown is never ineligible: missing/unparseable data never excludes an
  opportunity; exclusion only fires on an explicit, deterministic mismatch.
- Sort (most actionable first): deadline urgency ascending, tiebreak reward
  descending, then title. Undated opportunities sort after dated ones.
- Deadlines already in the past -> verdict `expired`, kept out of the
  eligible ordering but still returned in the results.
"""
import re
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from .models import Opportunity
from .parse_dates import typed_deadlines
from .parse_money import MoneyValue, typed_reward
from .profile import ApplicantProfile


class Verdict(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    EXPIRED = "expired"


class RankedOpportunity(BaseModel):
    opportunity: Opportunity
    verdict: Verdict
    reasons: list[str] = Field(default_factory=list)
    deadline: date | None = None
    reward: MoneyValue | None = None


class RankedResults(BaseModel):
    eligible: list[RankedOpportunity]
    excluded: list[RankedOpportunity]


_REGION_ALIASES: dict[str, str] = {
    "canada": "canada",
    "ca": "canada",
    "united states": "usa",
    "usa": "usa",
    "us": "usa",
    "eu": "eu",
    "european union": "eu",
    "germany": "eu",
    "france": "eu",
    "spain": "eu",
    "italy": "eu",
    "netherlands": "eu",
    "united kingdom": "uk",
    "uk": "uk",
}

_REGION_CONSTRAINTS: list[tuple[re.Pattern, str, frozenset[str]]] = [
    (re.compile(r"\bEU residents\b|\bEuropean Union (residents|citizens)\b", re.I), "EU residents", frozenset({"eu"})),
    (re.compile(r"\bUS|United States (residents|citizens)\b", re.I), "US residents", frozenset({"usa"})),
    (re.compile(r"\bCanadian (residents|citizens)\b|\bCanada only\b", re.I), "Canadian residents", frozenset({"canada"})),
    (re.compile(r"\bUK (residents|citizens)\b", re.I), "UK residents", frozenset({"uk"})),
]

_EDUCATION_ALIASES: dict[str, str] = {
    "high school": "high_school",
    "secondary": "high_school",
    "undergraduate": "undergraduate",
    "undergrad": "undergraduate",
    "bachelor": "undergraduate",
    "bachelors": "undergraduate",
    "graduate": "graduate",
    "masters": "graduate",
    "master's": "graduate",
    "phd": "graduate",
    "doctoral": "graduate",
}

_EDUCATION_CONSTRAINTS: list[tuple[re.Pattern, str, frozenset[str]]] = [
    (re.compile(r"\bhigh school students? only\b|\bmust be a high school student\b", re.I), "high school students only", frozenset({"high_school"})),
    (re.compile(r"\bundergraduates? only\b|\bmust be an undergraduate\b", re.I), "undergraduate students only", frozenset({"undergraduate"})),
    (re.compile(r"\bgraduate students? only\b|\bPhD (students?|candidates?) only\b", re.I), "graduate students only", frozenset({"graduate"})),
]


def _canonical(value: str | None, aliases: dict[str, str]) -> str | None:
    if not value or not value.strip():
        return None
    return aliases.get(value.strip().lower())


def _mismatch_reasons(opp: Opportunity, profile: ApplicantProfile) -> list[str]:
    text = " ".join(part for part in (opp.requirements, opp.description) if part)
    if not text:
        return []

    reasons: list[str] = []
    for constraints, profile_value, aliases, field_label in (
        (_REGION_CONSTRAINTS, profile.region, _REGION_ALIASES, "region"),
        (_EDUCATION_CONSTRAINTS, profile.education_level, _EDUCATION_ALIASES, "education_level"),
    ):
        canonical = _canonical(profile_value, aliases)
        if canonical is None:
            continue
        for pattern, label, satisfied_by in constraints:
            if pattern.search(text) and canonical not in satisfied_by:
                reasons.append(
                    f"{field_label} mismatch: requires '{label}', profile {field_label} '{profile_value}'"
                )
    return reasons


def _effective_deadline(opp: Opportunity, today: date) -> tuple[date | None, bool]:
    dates, _ = typed_deadlines(opp)
    if not dates:
        return None, False

    future = [d for d in dates if d >= today]
    if future:
        return min(future), False
    return max(dates), True


def rank(
    opportunities: list[Opportunity],
    profile: ApplicantProfile,
    *,
    today: date | None = None,
) -> RankedResults:
    today = today or date.today()

    eligible: list[RankedOpportunity] = []
    excluded: list[RankedOpportunity] = []

    for opp in opportunities:
        reasons = _mismatch_reasons(opp, profile)
        deadline, expired = _effective_deadline(opp, today)
        reward, _ = typed_reward(opp)

        if reasons:
            if expired:
                reasons = [*reasons, f"deadline {deadline.isoformat()} passed"]
            ranked = RankedOpportunity(
                opportunity=opp,
                verdict=Verdict.INELIGIBLE,
                reasons=reasons,
                deadline=deadline,
                reward=reward,
            )
            excluded.append(ranked)
        elif expired:
            ranked = RankedOpportunity(
                opportunity=opp,
                verdict=Verdict.EXPIRED,
                reasons=[f"deadline {deadline.isoformat()} passed"],
                deadline=deadline,
                reward=reward,
            )
            excluded.append(ranked)
        else:
            ranked = RankedOpportunity(
                opportunity=opp,
                verdict=Verdict.ELIGIBLE,
                reasons=[],
                deadline=deadline,
                reward=reward,
            )
            eligible.append(ranked)

    eligible.sort(
        key=lambda r: (
            r.deadline is None,
            r.deadline or date.max,
            -r.reward.amount if r.reward else float("inf"),
            r.opportunity.title,
        )
    )

    return RankedResults(eligible=eligible, excluded=excluded)
