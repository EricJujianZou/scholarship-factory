"""The daily digest: what changed since you last looked.

The system is meant to run unattended and spend the owner's attention only once
a day, so the digest is the product's real interface -- the dashboard is where
you go *after* it tells you there is something worth going for.

Two things earn a place in it, and nothing else does:
  - opportunities first seen since the last digest, worth a look because they
    are new;
  - deadlines closing soon on things not yet decided, worth a look because the
    window is about to shut.

Everything else is already in the dashboard and does not need to interrupt
anyone. A digest with nothing in it renders as "nothing new", which is a useful
thing to be told.
"""
import sqlite3
from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel

from .feedback import Decision
from .models import Opportunity
from .profile import ApplicantProfile
from .rank import Verdict, rank

#: a deadline this many days out is close enough to interrupt someone about
DEADLINE_HORIZON_DAYS = 14


class DigestItem(BaseModel):
    id: str
    title: str
    apply_url: str
    organization: str | None = None
    reward: str | None = None
    deadline: date | None = None
    days_left: int | None = None
    fit: str | None = None
    fit_reason: str | None = None


class Digest(BaseModel):
    generated_at: str
    since: str | None
    new_items: list[DigestItem]
    closing_soon: list[DigestItem]
    total_eligible: int
    undecided: int


_FIT_ORDER = {"high": 0, "medium": 1, "low": 2}


class RunStore:
    """When the last digest was generated, so the next one knows what's new."""

    def __init__(self, db_path: str, owner: str = "me"):
        self.db_path = db_path
        self.owner = owner
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS digest_runs (
                owner TEXT PRIMARY KEY,
                last_digest_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def last_digest_at(self) -> str | None:
        cur = self._conn.execute(
            "SELECT last_digest_at FROM digest_runs WHERE owner = ?", (self.owner,)
        )
        row = cur.fetchone()
        return row["last_digest_at"] if row else None

    def mark(self, when: str | None = None) -> str:
        when = when or datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO digest_runs (owner, last_digest_at) VALUES (?, ?)
            ON CONFLICT(owner) DO UPDATE SET last_digest_at = excluded.last_digest_at
            """,
            (self.owner, when),
        )
        self._conn.commit()
        return when


def build_digest(
    opportunities: list[Opportunity],
    profile: ApplicantProfile,
    *,
    fits: dict[str, tuple[str, str]] | None = None,
    decisions: list[Decision] | None = None,
    since: str | None = None,
    today: date | None = None,
    horizon_days: int = DEADLINE_HORIZON_DAYS,
) -> Digest:
    today = today or date.today()
    fits = fits or {}
    decided = {d.opportunity_id for d in (decisions or [])}
    ranked = rank(opportunities, profile, today=today)

    def to_item(entry) -> DigestItem:
        opp = entry.opportunity
        fit, reason = fits.get(opp.id, (None, None))
        return DigestItem(
            id=opp.id,
            title=opp.title,
            apply_url=opp.apply_url,
            organization=opp.organization,
            reward=opp.reward,
            deadline=entry.deadline,
            days_left=(entry.deadline - today).days if entry.deadline else None,
            fit=fit,
            fit_reason=reason,
        )

    eligible = [e for e in ranked.eligible if e.verdict == Verdict.ELIGIBLE]
    new_items = [
        to_item(e)
        for e in eligible
        if since is None or (e.opportunity.first_seen or "") > since
    ]
    horizon = today + timedelta(days=horizon_days)
    closing_soon = [
        to_item(e)
        for e in eligible
        if e.opportunity.id not in decided
        and e.deadline is not None
        and today <= e.deadline <= horizon
    ]

    new_items.sort(key=lambda i: (_FIT_ORDER.get(i.fit, 1), i.title))
    closing_soon.sort(key=lambda i: (i.days_left, i.title))

    return Digest(
        generated_at=datetime.now(timezone.utc).isoformat(),
        since=since,
        new_items=new_items,
        closing_soon=closing_soon,
        total_eligible=len(eligible),
        undecided=len([e for e in eligible if e.opportunity.id not in decided]),
    )


def _render_item(item: DigestItem) -> list[str]:
    bits = []
    if item.fit:
        bits.append(item.fit.upper())
    if item.deadline:
        bits.append(f"due {item.deadline.isoformat()} ({item.days_left}d)")
    if item.reward:
        bits.append(item.reward)
    lines = [f"- {item.title}"]
    if bits:
        lines.append(f"    {' | '.join(bits)}")
    if item.fit_reason:
        lines.append(f"    {item.fit_reason}")
    lines.append(f"    {item.apply_url}")
    return lines


def render(digest: Digest) -> str:
    """Plain text, so it reads the same in a console, a log file or an email."""
    lines = [f"Scholarship digest - {digest.generated_at[:10]}", ""]

    if digest.new_items:
        lines.append(f"NEW SINCE LAST DIGEST ({len(digest.new_items)})")
        for item in digest.new_items:
            lines.extend(_render_item(item))
        lines.append("")

    if digest.closing_soon:
        lines.append(f"CLOSING SOON, NOT YET DECIDED ({len(digest.closing_soon)})")
        for item in digest.closing_soon:
            lines.extend(_render_item(item))
        lines.append("")

    if not digest.new_items and not digest.closing_soon:
        lines.append("Nothing new, and nothing closing in the next two weeks.")
        lines.append("")

    lines.append(
        f"{digest.total_eligible} eligible in total, {digest.undecided} still undecided."
    )
    return "\n".join(lines)
