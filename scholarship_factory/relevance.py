"""LLM relevance ranking against the owner's profile and past decisions.

This is a deliberate extension of the ranking design, not a replacement.
`rank.py` stays exactly as it was -- deterministic hard filters that answer
*can I apply for this at all*, where a wrong answer silently hides a real
opportunity. Relevance answers a different, softer question -- *would I want
to* -- where being wrong only reorders a visible list. Only the second question
gets an LLM.

Two memories feed the prompt, because they decay differently (see `feedback.py`):
recent decisions as verbatim examples, and the distilled preference summary for
long-run taste. With neither, ranking falls back to the profile alone.

Facts are never touched here. This layer reads stored opportunities and writes
only an ordering plus a written reason -- it cannot invent a deadline.
"""
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .feedback import Decision, DecisionStore, DecisionVerdict, PreferenceStore
from .llm import structured_call
from .models import Opportunity
from .profile import ApplicantProfile

#: decisions quoted verbatim into the prompt; beyond this the summary carries the load
FEW_SHOT_LIMIT = 12
#: opportunities judged per LLM call; a bulk import (Simplify is ~1,500 rows)
#: cannot fit one prompt or one 8k-token reply, so `score` batches transparently
SCORE_BATCH_SIZE = 80
#: re-distil the summary once this many decisions have accumulated since the last one
SUMMARY_REFRESH_EVERY = 5

_RANK_SYSTEM_PROMPT = """You rank funding opportunities by how well they fit one \
specific applicant.

You are given the applicant's profile, an optional written summary of their \
preferences, optional examples of opportunities they previously accepted or \
rejected, and a numbered list of opportunities.

Rules:
- Score fit as `high`, `medium`, or `low`. Judge fit to *this* applicant, not the \
quality or prestige of the opportunity.
- An opportunity aimed at a different country, career stage, or field than the \
applicant's is a low fit even when it is excellent in the abstract.
- Give a one-sentence reason naming the concrete thing that decided it.
- Never invent facts about an opportunity. Judge only what you are shown; if the \
listing is too thin to judge, say so and score `medium`.
- Return exactly one entry per opportunity, using the index you were given."""

_SUMMARY_SYSTEM_PROMPT = """You write a short, factual summary of what kinds of \
funding opportunities one applicant tends to accept and reject.

Write 2-4 sentences in the second person ("You tend to..."). Name concrete \
patterns you can actually see in the decisions -- region, field, award size, \
career stage, format. Do not speculate beyond the evidence, and do not repeat \
the applicant's profile back to them. If the decisions are too few or too mixed \
to show a pattern, say that plainly."""


class Fit(BaseModel):
    index: int = Field(description="the opportunity's index in the list you were given")
    fit: str = Field(description="one of: high, medium, low")
    reason: str


class FitResult(BaseModel):
    """Fit judgments, one per opportunity."""

    fits: list[Fit]


class PreferenceSummary(BaseModel):
    """A short written summary of the applicant's demonstrated preferences."""

    summary: str


class ScoredOpportunity(BaseModel):
    opportunity: Opportunity
    fit: str
    reason: str


_FIT_ORDER = {"high": 0, "medium": 1, "low": 2}


def _describe(index: int, opp: Opportunity) -> str:
    parts = [f"[{index}] {opp.title}"]
    for label, value in (
        ("organization", opp.organization),
        ("reward", opp.reward),
        ("deadline", opp.deadline),
        ("eligibility", opp.requirements),
        ("about", opp.description),
    ):
        if value:
            parts.append(f"    {label}: {value[:400]}")
    return "\n".join(parts)


def _profile_block(profile: ApplicantProfile) -> str:
    fields = [
        ("region", profile.region),
        ("education level", profile.education_level),
        ("field of study", profile.field_of_study),
        ("interests", ", ".join(profile.tags) if profile.tags else None),
        ("bio", profile.bio),
    ]
    stated = [f"- {label}: {value}" for label, value in fields if value]
    return "\n".join(stated) if stated else "- (the applicant has not filled in a profile)"


def _examples_block(decisions: list[Decision], titles: dict[str, str]) -> str:
    lines = []
    for decision in decisions[:FEW_SHOT_LIMIT]:
        title = titles.get(decision.opportunity_id)
        if not title:
            continue  # the opportunity is gone; the decision is no longer evidence
        verb = "ACCEPTED" if decision.verdict == DecisionVerdict.INTERESTED else "REJECTED"
        note = f" (they said: {decision.note})" if decision.note else ""
        lines.append(f"- {verb}: {title}{note}")
    return "\n".join(lines)


def score(
    opportunities: list[Opportunity],
    profile: ApplicantProfile,
    *,
    decisions: list[Decision] | None = None,
    preference_summary: str | None = None,
    client=None,
    model: str | None = None,
    provider: str | None = None,
    on_batch: Callable[[list[ScoredOpportunity]], None] | None = None,
) -> list[ScoredOpportunity]:
    """Order opportunities by fit. One LLM call per `SCORE_BATCH_SIZE` batch.

    `on_batch` is called with each batch's results as it lands, so a caller can
    persist incrementally -- a quota/outage death mid-run then keeps every batch
    already judged instead of losing the whole pass.
    """
    if not opportunities:
        return []

    titles = {opp.id: opp.title for opp in opportunities}
    context_sections = [f"APPLICANT PROFILE:\n{_profile_block(profile)}"]
    if preference_summary:
        context_sections.append(f"WHAT THEY TEND TO WANT:\n{preference_summary}")
    examples = _examples_block(decisions or [], titles)
    if examples:
        context_sections.append(f"THEIR PAST DECISIONS:\n{examples}")

    scored: list[ScoredOpportunity] = []
    for start in range(0, len(opportunities), SCORE_BATCH_SIZE):
        batch_scored = _score_batch(
            opportunities[start : start + SCORE_BATCH_SIZE],
            context_sections,
            client=client,
            model=model,
            provider=provider,
        )
        if on_batch is not None:
            on_batch(batch_scored)
        scored.extend(batch_scored)
    scored.sort(key=lambda s: (_FIT_ORDER.get(s.fit, 1), s.opportunity.title))
    return scored


def _score_batch(
    batch: list[Opportunity],
    context_sections: list[str],
    *,
    client,
    model: str | None,
    provider: str | None,
) -> list[ScoredOpportunity]:
    listing = "\n".join(_describe(i, opp) for i, opp in enumerate(batch))
    sections = [*context_sections, f"OPPORTUNITIES:\n{listing}"]

    result = structured_call(
        _RANK_SYSTEM_PROMPT,
        "\n\n".join(sections),
        FitResult,
        client=client,
        model=model,
        provider=provider,
        tool_name="report_fit",
        max_tokens=8192,
    )

    by_index = {f.index: f for f in result.fits if 0 <= f.index < len(batch)}
    return [
        ScoredOpportunity(
            opportunity=opp,
            # an opportunity the model skipped is unjudged, not a bad fit
            fit=(by_index[i].fit.lower() if i in by_index else "medium"),
            reason=(by_index[i].reason if i in by_index else "not judged by the ranker"),
        )
        for i, opp in enumerate(batch)
    ]


def distil_preferences(
    decisions: list[Decision],
    titles: dict[str, str],
    profile: ApplicantProfile,
    *,
    client=None,
    model: str | None = None,
    provider: str | None = None,
) -> str:
    """Compress accept/reject history into a short written statement of taste."""
    examples = _examples_block(decisions, titles)
    if not examples:
        raise ValueError("no decisions to distil")

    result = structured_call(
        _SUMMARY_SYSTEM_PROMPT,
        f"APPLICANT PROFILE:\n{_profile_block(profile)}\n\nDECISIONS:\n{examples}",
        PreferenceSummary,
        client=client,
        model=model,
        provider=provider,
        tool_name="report_summary",
        max_tokens=1024,
    )
    return result.summary


def refresh_summary_if_due(
    decision_store: DecisionStore,
    preference_store: PreferenceStore,
    titles: dict[str, str],
    profile: ApplicantProfile,
    *,
    client=None,
    model: str | None = None,
    provider: str | None = None,
) -> str | None:
    """Re-distil the summary once enough new decisions have landed.

    Returns the new summary, or None when the existing one is still current --
    so the caller can report whether it spent a call.
    """
    decisions = decision_store.list()
    if not decisions:
        return None
    if len(decisions) - preference_store.decision_count() < SUMMARY_REFRESH_EVERY:
        return None

    summary = distil_preferences(
        decisions, titles, profile, client=client, model=model, provider=provider
    )
    preference_store.set(summary, len(decisions))
    return summary


class RelevanceStore:
    """Persisted fit scores, so the dashboard reads a ranking instead of paying
    for an LLM call on every page load. `sf rank` is what refreshes them."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relevance (
                opportunity_id TEXT PRIMARY KEY,
                fit TEXT NOT NULL,
                reason TEXT NOT NULL,
                scored_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def replace(self, scored: list[ScoredOpportunity]) -> None:
        """Overwrite the scores for exactly the opportunities just judged.

        Scores for opportunities not in this batch are left alone rather than
        wiped: a decided opportunity keeps whatever the last run thought of it.
        """
        now = datetime.now(timezone.utc).isoformat()
        self._conn.executemany(
            """
            INSERT INTO relevance (opportunity_id, fit, reason, scored_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(opportunity_id) DO UPDATE SET
                fit = excluded.fit,
                reason = excluded.reason,
                scored_at = excluded.scored_at
            """,
            [(s.opportunity.id, s.fit, s.reason, now) for s in scored],
        )
        self._conn.commit()

    def all(self) -> dict[str, tuple[str, str]]:
        """`{opportunity_id: (fit, reason)}` for everything scored so far."""
        cur = self._conn.execute("SELECT opportunity_id, fit, reason FROM relevance")
        return {r["opportunity_id"]: (r["fit"], r["reason"]) for r in cur.fetchall()}
