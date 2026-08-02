"""What an application actually asks for: prompts, limits, documents, referees.

Extraction (`extract.py`) answers *what is this opportunity* -- the facts that
decide whether it is worth applying. This answers *what would applying involve*,
which is a different question asked of a different page (the apply URL, not the
listing) and only worth asking about opportunities the owner has said yes to.

Same honesty contract as extraction, and for the same reason: a fabricated word
limit or an invented essay prompt would send a draft off in a direction the real
form never asked for. Everything here is quoted or absent -- if the page does not
state a limit, the limit is null, not a guess.
"""
import sqlite3
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .clean import clean_html
from .llm import structured_call

_SYSTEM_PROMPT = """You read a scholarship or grant application page and report \
what the application requires an applicant to submit.

Rules:
- Report only what the page states. If it does not state a word limit, a \
document, or a number of referees, leave that field null. Never guess a limit or \
invent a prompt.
- Quote essay/short-answer prompts verbatim as they appear. Do not paraphrase, \
summarize, or merge two prompts into one.
- `word_limit` is a number only when the page states one for that prompt.
- List required documents (transcript, CV, portfolio, proof of enrolment, ...) \
exactly as named on the page.
- If the page is not an application page at all (a login wall, a 404, a news \
article), set `is_application_page` to false and leave everything else empty."""


class EssayPrompt(BaseModel):
    prompt: str
    word_limit: int | None = None


class ApplicationRequirements(BaseModel):
    """What one application asks the applicant to supply."""

    is_application_page: bool = True
    essay_prompts: list[EssayPrompt] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    referees: int | None = None
    other_requirements: list[str] = Field(default_factory=list)
    notes: str | None = None


def read_requirements(
    raw_html: str,
    url: str,
    *,
    client=None,
    model: str | None = None,
    provider: str | None = None,
) -> ApplicationRequirements:
    page_text = clean_html(raw_html)
    return structured_call(
        _SYSTEM_PROMPT,
        f"application url: {url}\n\npage text:\n{page_text}",
        ApplicationRequirements,
        client=client,
        model=model,
        provider=provider,
        tool_name="report_requirements",
    )


class RequirementsStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS application_requirements (
                opportunity_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                read_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def set(
        self, opportunity_id: str, requirements: ApplicationRequirements
    ) -> ApplicationRequirements:
        self._conn.execute(
            """
            INSERT INTO application_requirements (opportunity_id, payload, read_at)
            VALUES (?, ?, ?)
            ON CONFLICT(opportunity_id) DO UPDATE SET
                payload = excluded.payload,
                read_at = excluded.read_at
            """,
            (
                opportunity_id,
                requirements.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()
        return requirements

    def get(self, opportunity_id: str) -> ApplicationRequirements | None:
        cur = self._conn.execute(
            "SELECT payload FROM application_requirements WHERE opportunity_id = ?",
            (opportunity_id,),
        )
        row = cur.fetchone()
        return ApplicationRequirements.model_validate_json(row["payload"]) if row else None

    def all(self) -> dict[str, ApplicationRequirements]:
        cur = self._conn.execute(
            "SELECT opportunity_id, payload FROM application_requirements"
        )
        return {
            r["opportunity_id"]: ApplicationRequirements.model_validate_json(r["payload"])
            for r in cur.fetchall()
        }
