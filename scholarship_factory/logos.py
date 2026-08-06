"""Org logo registry (GH-53).

One logo URL per organization, keyed by normalized org name, so a single
posting page that states its company logo fills every row for that company.
Hotlinks only — no downloading or re-hosting in v1. Logos are never derived
from favicon services keyed on the apply_url host: most apply_urls are ATS
domains, which would stamp the ATS logo on every card.
"""
import sqlite3
from datetime import datetime, timezone


def normalize_org(name: str | None) -> str | None:
    if name is None:
        return None
    normalized = name.strip().lower()
    return normalized or None


class OrgLogoStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS org_logos (
                org TEXT PRIMARY KEY,
                logo_url TEXT NOT NULL,
                source TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def set(self, org: str | None, logo_url: str, source: str | None = None) -> bool:
        """Record a logo for an org; returns False for unusable inputs."""
        key = normalize_org(org)
        if key is None or not logo_url.lower().startswith(("http://", "https://")):
            return False
        self._conn.execute(
            """
            INSERT INTO org_logos (org, logo_url, source, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(org) DO UPDATE SET
                logo_url = excluded.logo_url,
                source = excluded.source,
                updated_at = excluded.updated_at
            """,
            (key, logo_url, source, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()
        return True

    def get(self, org: str | None) -> str | None:
        key = normalize_org(org)
        if key is None:
            return None
        row = self._conn.execute(
            "SELECT logo_url FROM org_logos WHERE org = ?", (key,)
        ).fetchone()
        return row["logo_url"] if row else None

    def all(self) -> dict[str, str]:
        return {
            row["org"]: row["logo_url"]
            for row in self._conn.execute("SELECT org, logo_url FROM org_logos")
        }
