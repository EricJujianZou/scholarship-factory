"""Applicant profile model + SQLite store (S6 ranking foundation).

The single applicant's profile that opportunities are ranked/filtered against.
v1 shape: a minimal structured core (region / education level / field) covering
the common eligibility gates, plus interest/eligibility tags and a free-text bio
for a future LLM ranker. Mirrors the Opportunity model + OpportunityStore
patterns (GH-1); single-user (`owner="me"`), no auth. No ranking/matching here.
"""
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class ApplicantProfile(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    owner: str = "me"
    region: str | None = None
    education_level: str | None = None
    field_of_study: str | None = None
    tags: list[str] = Field(default_factory=list)
    bio: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


_COLUMNS = [
    "id",
    "owner",
    "region",
    "education_level",
    "field_of_study",
    "tags",
    "bio",
    "created_at",
    "updated_at",
]


class ProfileStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applicant_profiles (
                id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                region TEXT,
                education_level TEXT,
                field_of_study TEXT,
                tags TEXT NOT NULL,
                bio TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def _to_row(self, profile: ApplicantProfile) -> dict:
        row = profile.model_dump()
        row["tags"] = json.dumps(row["tags"])  # list <-> text
        return row

    def insert(self, profile: ApplicantProfile) -> ApplicantProfile:
        now = datetime.now(timezone.utc).isoformat()
        row = self._to_row(profile)
        row["created_at"] = now
        row["updated_at"] = now
        placeholders = ", ".join("?" for _ in _COLUMNS)
        columns = ", ".join(_COLUMNS)
        self._conn.execute(
            f"INSERT INTO applicant_profiles ({columns}) VALUES ({placeholders})",
            [row[c] for c in _COLUMNS],
        )
        self._conn.commit()
        return self.get(profile.id)

    def get(self, id: str) -> ApplicantProfile | None:
        cur = self._conn.execute("SELECT * FROM applicant_profiles WHERE id = ?", (id,))
        row = cur.fetchone()
        return self._row_to_profile(row) if row else None

    def list(self) -> list[ApplicantProfile]:
        cur = self._conn.execute("SELECT * FROM applicant_profiles ORDER BY created_at")
        return [self._row_to_profile(row) for row in cur.fetchall()]

    def update(self, profile: ApplicantProfile) -> ApplicantProfile:
        now = datetime.now(timezone.utc).isoformat()
        row = self._to_row(profile)
        row["updated_at"] = now
        set_clause = ", ".join(f"{c} = ?" for c in _COLUMNS if c != "created_at")
        values = [row[c] for c in _COLUMNS if c != "created_at"]
        self._conn.execute(
            f"UPDATE applicant_profiles SET {set_clause} WHERE id = ?",
            (*values, profile.id),
        )
        self._conn.commit()
        return self.get(profile.id)

    def _row_to_profile(self, row: sqlite3.Row) -> ApplicantProfile:
        data = dict(row)
        data["tags"] = json.loads(data["tags"])
        return ApplicantProfile(**data)
