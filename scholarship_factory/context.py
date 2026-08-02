"""The applicant's own material: the things an application asks them to supply.

`ApplicantProfile` (profile.py) stays what it was -- the few structured fields
ranking filters on. This is the other half: the corpus a draft is written *from*
-- awards, experience, projects, past essays, referees, and the plain facts
eligibility questions ask ("are you a Canadian citizen?").

Deliberately one table of typed entries rather than forty columns. What an
application asks for varies enormously, and a schema that tried to anticipate it
would need migrating every time a new form asked something new. An entry is a
titled piece of the applicant's history; `kind` says what sort, `tags` make it
retrievable, and `body` holds the actual text a draft can draw on.

**This stores personal data**, unlike every other table in the system -- see the
note in REPO_CONTENT.md. It lives in the same local SQLite file, unencrypted,
single-user. Do not commit the database, and do not commit a filled-in context
file (both are gitignored).
"""
import sqlite3
import tomllib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from .profile import PROFILE_SECTION


class ContextKind(str, Enum):
    FACT = "fact"  # "citizenship: Canadian" - the answers eligibility questions want
    EDUCATION = "education"
    AWARD = "award"
    EXPERIENCE = "experience"
    PROJECT = "project"
    ESSAY = "essay"  # a past answer, reusable when a prompt is close enough
    REFERENCE = "reference"
    DOCUMENT = "document"  # a pointer: transcript, CV, portfolio


class ContextEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    owner: str = "me"
    kind: ContextKind
    title: str
    body: str | None = None
    tags: list[str] = Field(default_factory=list)
    started: str | None = None
    ended: str | None = None
    url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


_COLUMNS = [
    "id",
    "owner",
    "kind",
    "title",
    "body",
    "tags",
    "started",
    "ended",
    "url",
    "created_at",
    "updated_at",
]


class ContextStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS context_entries (
                id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                tags TEXT NOT NULL,
                started TEXT,
                ended TEXT,
                url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(owner, kind, title)
            )
            """
        )
        self._conn.commit()

    def upsert(self, entry: ContextEntry) -> ContextEntry:
        """Insert, or update the entry with the same owner/kind/title.

        Title is the identity so re-importing an edited context file updates in
        place instead of accumulating near-duplicates.
        """
        now = datetime.now(timezone.utc).isoformat()
        row = entry.model_dump()
        row["kind"] = entry.kind.value
        row["tags"] = "\n".join(entry.tags)
        row["created_at"] = now
        row["updated_at"] = now
        self._conn.execute(
            f"""
            INSERT INTO context_entries ({", ".join(_COLUMNS)})
            VALUES ({", ".join("?" for _ in _COLUMNS)})
            ON CONFLICT(owner, kind, title) DO UPDATE SET
                body = excluded.body,
                tags = excluded.tags,
                started = excluded.started,
                ended = excluded.ended,
                url = excluded.url,
                updated_at = excluded.updated_at
            """,
            [row[c] for c in _COLUMNS],
        )
        self._conn.commit()
        return self.get_by_title(entry.kind, entry.title)

    def get_by_title(self, kind: ContextKind, title: str) -> ContextEntry | None:
        cur = self._conn.execute(
            "SELECT * FROM context_entries WHERE kind = ? AND title = ?",
            (ContextKind(kind).value, title),
        )
        row = cur.fetchone()
        return self._to_entry(row) if row else None

    def list(self, kind: ContextKind | None = None) -> list[ContextEntry]:
        if kind is None:
            cur = self._conn.execute(
                "SELECT * FROM context_entries ORDER BY kind, title"
            )
        else:
            cur = self._conn.execute(
                "SELECT * FROM context_entries WHERE kind = ? ORDER BY title",
                (ContextKind(kind).value,),
            )
        return [self._to_entry(row) for row in cur.fetchall()]

    def delete(self, entry_id: str) -> None:
        self._conn.execute("DELETE FROM context_entries WHERE id = ?", (entry_id,))
        self._conn.commit()

    def facts(self) -> dict[str, str]:
        """`{title: body}` for FACT entries - the quick-answer lookup."""
        return {e.title: (e.body or "") for e in self.list(ContextKind.FACT)}

    def _to_entry(self, row: sqlite3.Row) -> ContextEntry:
        data = dict(row)
        data["tags"] = [t for t in (data["tags"] or "").split("\n") if t]
        return ContextEntry(**data)


def load_context_file(path: str | Path) -> list[ContextEntry]:
    """Parse a context TOML file into entries.

    Editing one file is the only realistic way to enter a career's worth of
    material, so this is the primary entry path; the store is what reads it back.

        [[award]]
        title = "..."
        body = "..."
        tags = ["research"]
    """
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    entries: list[ContextEntry] = []
    for kind in ContextKind:
        for item in data.get(kind.value, []):
            entries.append(ContextEntry(kind=kind, **item))

    # `[profile]` shares the file but belongs to profile.py -- see load_profile_file.
    unknown = set(data) - {k.value for k in ContextKind} - {PROFILE_SECTION}
    if unknown:
        raise ValueError(
            f"unknown context section(s): {', '.join(sorted(unknown))}; "
            f"expected one of {', '.join(k.value for k in ContextKind)}"
        )
    return entries
