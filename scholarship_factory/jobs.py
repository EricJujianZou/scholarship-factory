"""Run a CLI command on behalf of the dashboard and stream its output back.

Every button on the dashboard is a command that already exists -- sourcing,
ranking, importing context, reading an application page. Rather than
reimplement each one behind an endpoint, a job shells out to
`python -m scholarship_factory.cli ...` and collects its output into a buffer
the browser polls. One implementation per action, and the CLI stays the place
where behaviour is defined.

One job at a time. These jobs fetch pages and spend LLM calls, so two at once
would double the cost of a mis-click and interleave writes to the same rows.
State is in memory and a restart forgets it, which is correct: a job that was
running when the server died is not running now.
"""
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

#: keep the tail of a long sourcing run, not all of it
_MAX_LINES = 400


class JobState(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Job(BaseModel):
    name: str
    label: str
    state: JobState = JobState.RUNNING
    lines: list[str] = Field(default_factory=list)
    started_at: str
    finished_at: str | None = None
    exit_code: int | None = None


class JobBusy(Exception):
    """A job is already running; the caller should not start a second one."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobRunner:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._job: Job | None = None

    def current(self) -> Job | None:
        with self._lock:
            return self._job.model_copy(deep=True) if self._job else None

    def start(self, name: str, label: str, args: list[str]) -> Job:
        with self._lock:
            if self._job and self._job.state == JobState.RUNNING:
                raise JobBusy(self._job.label)
            self._job = Job(name=name, label=label, started_at=_now())
            job = self._job
        threading.Thread(target=self._run, args=(job, args), daemon=True).start()
        return job.model_copy(deep=True)

    def _run(self, job: Job, args: list[str]) -> None:
        env = {
            **os.environ,
            "SF_DB_PATH": self.db_path,
            # The child inherits a pipe, so its own currency symbols would hit
            # the same cp1252 wall the CLI already works around for a console.
            "PYTHONIOENCODING": "utf-8",
        }
        try:
            # -u so output arrives while the job runs rather than at the end.
            process = subprocess.Popen(
                [sys.executable, "-u", "-m", "scholarship_factory.cli", *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
        except OSError as exc:
            self._finish(job, JobState.FAILED, None, [f"could not start: {exc}"])
            return

        for line in process.stdout:
            with self._lock:
                job.lines.append(line.rstrip())
                del job.lines[:-_MAX_LINES]
        code = process.wait()
        self._finish(
            job, JobState.SUCCEEDED if code == 0 else JobState.FAILED, code, []
        )

    def _finish(
        self, job: Job, state: JobState, code: int | None, extra: list[str]
    ) -> None:
        with self._lock:
            job.lines.extend(extra)
            job.state = state
            job.exit_code = code
            job.finished_at = _now()


class Action(BaseModel):
    """A button on the dashboard: what it runs, and what it costs to press."""

    id: str
    title: str
    description: str
    cost: str
    args: list[str]
    needs_llm: bool = True


#: The dashboard renders these; the copy lives here so the button and the thing
#: it runs cannot drift apart.
ACTIONS: list[Action] = [
    Action(
        id="poll",
        title="Find new opportunities",
        description=(
            "Fetches every enabled seed, extracts the opportunities it finds, "
            "ranks them against your profile, then reports what is new and what "
            "closes soon."
        ),
        cost="A few minutes · roughly 100-150 LLM calls",
        args=["poll", "--seeds", "seeds.toml", "--page-cap", "15", "--max-pages", "3"],
    ),
    Action(
        id="rank",
        title="Re-rank everything",
        description=(
            "Scores every opportunity you have not decided on against your "
            "profile, your past decisions and your preference summary. Run it "
            "after editing your profile."
        ),
        cost="Under a minute · one LLM call",
        args=["rank"],
    ),
    Action(
        id="context",
        title="Reload my context",
        description=(
            "Re-reads context.toml: the profile ranking filters on, plus your "
            "facts, awards, essays and referees. Run it whenever you edit that "
            "file."
        ),
        cost="Instant · no LLM calls",
        args=["context", "import", "context.toml"],
        needs_llm=False,
    ),
]

#: shown when no provider key is set, in place of every LLM-spending button
LLM_HINT = (
    "No LLM key found, so anything that reads a page is switched off. Set "
    "GEMINI_API_KEY (setx GEMINI_API_KEY \"your-key\"), then close this window "
    "and reopen the dashboard."
)

ACTIONS_BY_ID = {action.id: action for action in ACTIONS}
