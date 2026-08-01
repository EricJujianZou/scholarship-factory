"""What we've learned about the owner: their decisions on opportunities, and the
distilled preference summary those decisions produce.

Decisions are deliberately *not* stored in `Opportunity.status`. That column is
the freshness lifecycle (`new|refreshed|changed|unreachable`) and `refresh`
overwrites it, so a decision parked there would be erased by the next re-check.

Two shapes of memory, because they decay differently: individual decisions are
recent and specific (good few-shot examples), while the summary is the slow,
readable statement of taste that survives them and can be hand-edited.
"""
import sqlite3
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel


class DecisionVerdict(str, Enum):
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"


class Decision(BaseModel):
    opportunity_id: str
    verdict: DecisionVerdict
    note: str | None = None
    decided_at: str | None = None


class DecisionStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                opportunity_id TEXT PRIMARY KEY,
                verdict TEXT NOT NULL,
                note TEXT,
                decided_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def set(
        self,
        opportunity_id: str,
        verdict: DecisionVerdict | str,
        note: str | None = None,
    ) -> Decision:
        """Record (or change) the owner's call on one opportunity."""
        verdict = DecisionVerdict(verdict)
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO decisions (opportunity_id, verdict, note, decided_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(opportunity_id) DO UPDATE SET
                verdict = excluded.verdict,
                note = excluded.note,
                decided_at = excluded.decided_at
            """,
            (opportunity_id, verdict.value, note, now),
        )
        self._conn.commit()
        return self.get(opportunity_id)

    def get(self, opportunity_id: str) -> Decision | None:
        cur = self._conn.execute(
            "SELECT * FROM decisions WHERE opportunity_id = ?", (opportunity_id,)
        )
        row = cur.fetchone()
        return Decision(**dict(row)) if row else None

    def list(self) -> list[Decision]:
        """Most recent first - the ranker wants the freshest signal."""
        cur = self._conn.execute("SELECT * FROM decisions ORDER BY decided_at DESC")
        return [Decision(**dict(row)) for row in cur.fetchall()]

    def clear(self, opportunity_id: str) -> None:
        self._conn.execute(
            "DELETE FROM decisions WHERE opportunity_id = ?", (opportunity_id,)
        )
        self._conn.commit()


class PreferenceStore:
    """The single distilled statement of what the owner tends to want."""

    def __init__(self, db_path: str, owner: str = "me"):
        self.db_path = db_path
        self.owner = owner
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS preference_summaries (
                owner TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                decision_count INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def set(self, summary: str, decision_count: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO preference_summaries (owner, summary, decision_count, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(owner) DO UPDATE SET
                summary = excluded.summary,
                decision_count = excluded.decision_count,
                updated_at = excluded.updated_at
            """,
            (self.owner, summary, decision_count, now),
        )
        self._conn.commit()

    def get(self) -> str | None:
        cur = self._conn.execute(
            "SELECT summary FROM preference_summaries WHERE owner = ?", (self.owner,)
        )
        row = cur.fetchone()
        return row["summary"] if row else None

    def decision_count(self) -> int:
        """How many decisions the stored summary was distilled from."""
        cur = self._conn.execute(
            "SELECT decision_count FROM preference_summaries WHERE owner = ?",
            (self.owner,),
        )
        row = cur.fetchone()
        return row["decision_count"] if row else 0
