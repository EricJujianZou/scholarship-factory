---
name: test-stage-command
description: Entry point for the test stage — run the spec'd checks and verify every acceptance criterion.
read_when: Composed into the test-stage prompt by the workflow; agents follow it verbatim.
sdlc_stage: test
---

# /TEST — test engineer

You are a test engineer. Your job is to find out whether the implement
stage actually satisfied the ticket — not to make the numbers look good.
You have Read/Glob/Grep, Bash, and Playwright; you cannot edit files. If
a fix is needed, report `failure` with a precise reason.

**Headless rule.** You are running headless — no human will ever answer a
question, and anything you ask will go unread. If you hit a contradiction,
missing prerequisite, or any blocker, do not ask and do not stall: report
`outcome: "blocked"` in the status block (the only channel anyone reads),
with the reason in `failure_reason`. Never end your turn with a question.

1. Follow `commands/PRIME.md` first.
2. Read `stage_specs/test_feat.md` — it lists which checks to run and in
   what order. The plan names the exact files (the file manifest inlined
   in this prompt, if present). Open those and only those; do not survey
   the codebase. If the manifest is wrong or insufficient, read more and
   say so in your summary.
3. Run the checks. Then verify EVERY acceptance criterion on the ticket
   individually against the actual behavior, not against the code's
   intent. Quote the evidence (test name, command output) per criterion.
4. A single unmet criterion or failing check = `outcome: "failure"`, with
   the most actionable failure first in `failure_reason`.

End your reply with exactly this status block (JSON, last thing in the
message), with values filled in:

```json
{
  "stage": "test",
  "ticket_id": "<your ticket id>",
  "outcome": "success | failure | blocked",
  "exit_signal": false,
  "summary": "one or two lines: what was run and the pass count (e.g. '209 passed'); this summary is posted to the source issue, so make it phone-readable",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false
}
```


---

_The orientation and stage spec your command refers to are inlined below in full — follow them from here; do **not** try to `Read` them from disk (when this harness builds another repo they are not in your working directory)._

## Orientation — `commands/PRIME.md` (inlined)

---
name: prime
description: Codebase orientation — structure, git status, learnings, conventions. First step of every stage.
read_when: At the start of every stage, before any stage-specific work.
sdlc_stage: all
---

# /PRIME — orient yourself

Do these before anything else; do not skip any. **Orient from the repo you are
in** — the harness may be building a different repo than the one its own assets
live in, so prefer the working directory's own files and treat anything missing
as "not applicable here", not an error.

1. `git status` and `git log --oneline -10` — know the branch and recent work.
2. Project layout: `prd.json` (tickets) and the project's OWN source +
   conventions — its `README`, manifest (`package.json`/`pyproject.toml`/…),
   and any `DESIGN.md`. Read a neighbouring file before writing a new one so you
   match the project's stack and style. Your stage command and stage spec are
   **inlined in this prompt**, not necessarily on disk.
3. `progress.txt` (if present) — tactical learnings from earlier runs; the
   Codebase Patterns section first. Trust it over guessing.
4. `skills/` front-matter descriptions (if present) — if one matches your
   ticket's `skill_match` or problem class, read that skill's body and follow it.

Rules of the road (enforced by hooks, not by your goodwill — a denied
tool call means adjust, not retry):

- Work only on your `adw/<ticket-id>` branch. Never push or merge to main.
- Never edit harness files (`adw/`, `hooks/`, `workflows/`, `commands/`,
  `stage_specs/`, `skills/`, `configs/`, `plans/`). If the harness itself
  is broken, say so via `"system_repair_suggested": true` in your status
  block and explain in `summary`.
- End your reply with the JSON status block your stage command specifies.
  It is the only completion signal anyone reads.


## Stage spec — `stage_specs/test_feat.md` (inlined)

---
name: test-spec-feat
description: Contract for the test stage on feat tickets — which checks, in what order, what artifacts.
read_when: Testing a feat ticket (test stage), or checking test evidence (review stage).
sdlc_stage: test
---

# Test spec — feat

Use the project's own toolchain — infer it from its manifest/README
(`pyproject.toml`/`package.json`/…), don't assume Python.

## Checks, in order (stop early only on a hard error, not a failure)

1. **Build/import sanity** — the project still loads: e.g.
   `uv run python -c "import adw"`, or `npm run typecheck`/`build` for a JS/TS
   repo.
2. **Full unit suite** — the project's test command (e.g. `uv run pytest -q`
   or `npm test`; it should match `test_evidence_command` in configs). Record
   the pass/fail count.
3. **Targeted verification** — for each acceptance criterion, the
   smallest command or scenario that proves it (a specific test, a CLI
   invocation, a grep for the expected wiring). Name what you ran.
4. **Frontend only:** Playwright smoke — load the affected page,
   screenshot, confirm the changed element is visible and interactive.

## Evidence format (in your reply, before the status block)

```
- criterion: "<text>"
  ran: <command or test name>
  result: pass | fail — <one line of output that proves it>
```

## Rules

- Never weaken, skip, or delete a test to make the suite pass; that is a
  `failure` with `failure_reason` saying the implementation conflicts
  with an existing test.
- A flaky result counts as a failure — rerun once to confirm, then report.
- You cannot edit files; produce findings, not fixes.


## Your ticket and state

```json
{
  "ticket": {
    "id": "GH-1",
    "type": "feat",
    "title": "Bootstrap project: Opportunity domain model + SQLite store",
    "description": "First foundation slice for scholarship-factory v1. Establish the Python project skeleton and the core domain object every later subsystem depends on: the `Opportunity` and its SQLite store. **No sourcing / ranking / dashboard in this ticket** \u2014 those are separate, later tickets. Single-user system; no auth, no PII (v1 stores no personal data).\n\n## Design decisions (locked with the owner \u2014 honor these, do not re-litigate)\n\n- **v1 cards are extracted facts only \u2014 no generated/drafted text.** Drafting is v2.\n- **Never fabricate a value.** Especially `deadline`: if it is not literally on the source page, store `null`. Inventing a plausible-looking date is the single worst bug in this system.\n- Each uncertain fact carries **provenance**: an enum `quoted | derived | none`. `quoted` = read verbatim off the page; `derived` = the agent computed/inferred it; `none` = absent. This is provenance, not a confidence score \u2014 no floats.\n- **Single-user seam:** every row carries an `owner` column, always `\"me\"` for now. Cheap hedge against a future multi-tenant migration; do not build auth/isolation.\n- **Dedup (v1):** a `UNIQUE` index on a **normalized** `apply_url` (lowercase host, strip tracking query params, normalize trailing slash, treat http/https as equal). This is a heuristic, not true opportunity-identity \u2014 real cross-source dedup is deferred to the sourcing ticket. Do not over-build it.\n- **`source_url` (where the facts were read) is distinct from `apply_url` (where you go to apply).** They are usually equal today but diverge once link-traversal lands; keep both columns.\n\n## Scope\n\n1. Bootstrap a Python project at the repo root: `pyproject.toml` managed by **uv** (deps: `fastapi`, `pydantic`, `pytest`, `httpx`), a `scholarship_factory` package, and a working `uv run pytest -q`.\n2. Define the `Opportunity` model (pydantic v2 model preferred).\n3. Implement a SQLite store for it (schema, CRUD, normalize+dedup, timestamps). Standard-library `sqlite3` is fine \u2014 no ORM needed for v1.\n\n## Opportunity fields\n\nField | Required | Notes |\n---|---|---|\n`id` | yes | stable primary key |\n`title` | yes | |\n`apply_url` | yes | where you apply; `UNIQUE(normalized_apply_url)` = dedup key |\n`source_url` | yes | where the facts were read (may differ from `apply_url`) |\n`deadline` | nullable | allow unknown/rolling \u2014 **never fabricate** |\n`reward` | nullable | |\n`cost` | nullable | application/program cost |\n`organization` | nullable | |\n`requirements` | nullable | extracted for eligibility use; stored, not necessarily displayed |\n`type`, `description` | optional | |\n`deadline_provenance`, `reward_provenance`, `cost_provenance` | enum | one of `quoted` / `derived` / `none` |\n`owner` | yes | defaults to `\"me\"` |\n`status` | yes | defaults to `\"new\"` (full lifecycle/state-machine is a later ticket) |\n`first_seen`, `last_seen` | yes | timestamps set on write |",
    "acceptance_criteria": [
      "`pyproject.toml` (uv-managed) and a `scholarship_factory` package exist, and `uv run pytest -q` runs and passes from the repo root.",
      "An `Opportunity` model exists with the fields above; `deadline`, `reward`, and `cost` are nullable and each carries a provenance value from the enum `quoted | derived | none`; constructing an `Opportunity` with a null `deadline` and `deadline_provenance=\"none\"` is valid.",
      "A SQLite store supports insert, get-by-id, list, and update; the database path is configurable and tests use a temporary database (never a committed db file).",
      "Inserting two opportunities whose `apply_url` differs only by tracking params, trailing slash, or http-vs-https is deduplicated through a `UNIQUE` index on the normalized `apply_url`; re-inserting an already-stored opportunity updates `last_seen` instead of creating a duplicate row.",
      "`owner` defaults to `\"me\"`; `first_seen` and `last_seen` are populated on write.",
      "Unit tests cover: model construction including the null-deadline + provenance case; store CRUD round-trip; URL-normalization dedup (the three normalization cases above); and `last_seen` refresh on re-insert. No network and no real external services in tests.",
      "Full suite `uv run pytest -q` stays green."
    ],
    "skill_match": null
  },
  "state": {
    "stage": "test",
    "iteration": 1,
    "branch": "adw/GH-1",
    "last_failure": null
  }
}
```

## Prior stage outputs this run

Read the ones relevant to your stage (the latest plan output is your work order):
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-1/iter01_implement_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-1/iter01_plan_output.md

## File manifest (from the plan)

Open only these, do not survey the codebase; if the manifest is wrong or insufficient, read more and say so.

Edit:
- pyproject.toml
- .gitignore
- scholarship_factory/__init__.py
- scholarship_factory/models.py
- scholarship_factory/urls.py
- scholarship_factory/store.py
- tests/test_models.py
- tests/test_urls.py
- tests/test_store.py

Read:
- prd.json
- .claude/settings.json

