import sqlite3
from datetime import datetime, timezone

from .models import Opportunity, Provenance
from .urls import normalize_apply_url

_COLUMNS = [
    "id",
    "title",
    "apply_url",
    "source_url",
    "deadline",
    "reward",
    "cost",
    "organization",
    "requirements",
    "type",
    "description",
    "deadline_provenance",
    "reward_provenance",
    "cost_provenance",
    "deadline_source",
    "reward_source",
    "cost_source",
    "source_observed_date",
    "owner",
    "status",
    "first_seen",
    "last_seen",
    "normalized_apply_url",
]


class OpportunityStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                apply_url TEXT NOT NULL,
                source_url TEXT NOT NULL,
                deadline TEXT,
                reward TEXT,
                cost TEXT,
                organization TEXT,
                requirements TEXT,
                type TEXT,
                description TEXT,
                deadline_provenance TEXT NOT NULL,
                reward_provenance TEXT NOT NULL,
                cost_provenance TEXT NOT NULL,
                owner TEXT NOT NULL,
                status TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                normalized_apply_url TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunities_normalized_apply_url "
            "ON opportunities(normalized_apply_url)"
        )
        self._conn.commit()

    def insert(self, opp: Opportunity) -> Opportunity:
        now = datetime.now(timezone.utc).isoformat()
        normalized = normalize_apply_url(opp.apply_url)
        row = opp.model_dump()
        row["first_seen"] = now
        row["last_seen"] = now
        row["normalized_apply_url"] = normalized
        row["deadline_provenance"] = Provenance(row["deadline_provenance"]).value
        row["reward_provenance"] = Provenance(row["reward_provenance"]).value
        row["cost_provenance"] = Provenance(row["cost_provenance"]).value

        placeholders = ", ".join("?" for _ in _COLUMNS)
        columns = ", ".join(_COLUMNS)
        self._conn.execute(
            f"""
            INSERT INTO opportunities ({columns}) VALUES ({placeholders})
            ON CONFLICT(normalized_apply_url) DO UPDATE SET last_seen = excluded.last_seen
            """,
            [row[c] for c in _COLUMNS],
        )
        self._conn.commit()

        cur = self._conn.execute(
            "SELECT * FROM opportunities WHERE normalized_apply_url = ?",
            (normalized,),
        )
        return self._row_to_opp(cur.fetchone())

    def get(self, id: str) -> Opportunity | None:
        cur = self._conn.execute("SELECT * FROM opportunities WHERE id = ?", (id,))
        row = cur.fetchone()
        return self._row_to_opp(row) if row else None

    def list(self) -> list[Opportunity]:
        cur = self._conn.execute("SELECT * FROM opportunities ORDER BY first_seen")
        return [self._row_to_opp(row) for row in cur.fetchall()]

    def update(self, opp: Opportunity) -> Opportunity:
        now = datetime.now(timezone.utc).isoformat()
        normalized = normalize_apply_url(opp.apply_url)
        row = opp.model_dump()
        row["last_seen"] = now
        row["normalized_apply_url"] = normalized
        row["deadline_provenance"] = Provenance(row["deadline_provenance"]).value
        row["reward_provenance"] = Provenance(row["reward_provenance"]).value
        row["cost_provenance"] = Provenance(row["cost_provenance"]).value

        set_clause = ", ".join(f"{c} = ?" for c in _COLUMNS if c != "first_seen")
        values = [row[c] for c in _COLUMNS if c != "first_seen"]
        self._conn.execute(
            f"UPDATE opportunities SET {set_clause} WHERE id = ?",
            (*values, opp.id),
        )
        self._conn.commit()
        return self.get(opp.id)

    def _row_to_opp(self, row: sqlite3.Row) -> Opportunity:
        data = dict(row)
        data.pop("normalized_apply_url", None)
        return Opportunity(**data)
