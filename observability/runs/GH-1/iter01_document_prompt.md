---
name: document-stage-command
description: Entry point for the document stage — write and commit the per-ticket change doc after the dual gate passes.
read_when: Composed into the document-stage prompt by the workflow; agents follow it verbatim.
sdlc_stage: document
---

# /DOCUMENT — documenter

You are a technical writer. Your sole job is to write and commit
`docs/changes/<ticket-id>.md` — an organized delta document for the
merge-gate human. You have exactly one shot; nobody will answer
questions. **Headless rule: this agent runs headless — if you are
blocked, record it in the status block and stop. Do not ask questions.**

**Commit-before-stop: you must `git add` and `git commit` the doc before
stopping. The Stop checklist's clean-tree rule applies to this stage.**

1. Follow `commands/PRIME.md` first.
2. Read `stage_specs/document_feat.md` — that is the contract for
   the doc's structure and rules.
3. Read the ticket (from the prompt context), run `git diff main...HEAD`,
   and read the run's prior stage outputs listed in this prompt (plan,
   implement, test, review).
4. Write `docs/changes/<ticket-id>.md` using the conditional section
   template from the spec. Include only sections for change-kinds that
   actually exist in the diff.
5. Commit: `git add docs/changes/<ticket-id>.md` then
   `git commit -m "docs: add change doc for <ticket-id>"`.

End your reply with exactly this status block (JSON, last thing in the
message), with values filled in:

```json
{
  "stage": "document",
  "ticket_id": "<your ticket id>",
  "outcome": "success | failure | blocked",
  "exit_signal": false,
  "summary": "one or two lines",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false
}
```

`files_changed` must be the real count (`git diff --stat HEAD~1` after
committing). A doc that was not committed counts as failure.


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


## Stage spec — `stage_specs/document_feat.md` (inlined)

---
name: document-spec-feat
description: Contract for the document stage — conditional section template, anchoring rules, and definition of done.
read_when: Writing the change doc (document stage), or judging doc quality (review stage, post-gate).
sdlc_stage: document
---

# Document spec — feat

## Purpose

Produce an organized technical delta for the merge-gate human. The doc
must let the reviewer understand what changed and why it is correct
without reading the raw diff.

## Conditional section template

Include a section **only** when that change-kind exists in the diff.
Omit sections that have nothing to say — an empty section is worse than
no section.

### What shipped

One short paragraph: the ticket's goal and the approach taken. Anchored
in what the diff actually contains, not what the plan intended.

### Surface changes

Include only the subsections that apply:

#### Endpoints / APIs

New or changed HTTP endpoints, RPC methods, SDK public functions. For
each: signature, HTTP method + path, what it does, any auth requirement.

#### Schemas & data

New or changed database tables, JSON schemas, dataclass/Pydantic models,
serialization formats. For each: name, fields added/removed/changed,
migration notes if any.

#### Components / pages

New or changed UI components or pages. For each: component name, where
it renders, key props/state, visual behavior.

#### CLI / workflows

New or changed CLI commands, flags, scripts, or automation workflows.
For each: command, flags, what it does, example invocation.

### Behavior & breaking changes

Changes that alter observable behavior or break callers/consumers:
removed fields, changed defaults, renamed symbols, altered control flow.
If none: omit this section entirely.

### How it was verified

Map each acceptance criterion to the test evidence from the test stage's
output. Format: criterion → evidence (test name, assertion, or
observation). Vague evidence ("tests pass") does not satisfy this
section — name the specific test or output line.

### Review notes

Anything the reviewer should pay special attention to: non-obvious design
decisions, deferred items, known edge cases left in place.

### File map

One line per changed file: `path/to/file.py — why it changed`.
Omit generated files (lock files, compiled assets) unless they carry
semantic meaning.

---

## Contract rules

1. **Anchored in the actual diff.** Every claim in the doc must be
   verifiable from `git diff main...HEAD`. Do not document the plan's
   intentions — document what the diff contains.

2. **Organized delta, not a diff dump.** Prose explains intent; code
   snippets are short and purposeful. Copying multi-hundred-line hunks
   into the doc violates this rule.

3. **Bounded length.** The doc should be readable in under ten minutes.
   Prefer one clear sentence over three hedging ones. No padding.

4. **No future-work speculation.** Do not describe what could be added
   next, what the system will eventually support, or what is planned for
   later. If README or architecture docs are now stale, note that as a
   suggested follow-up in `Review notes` — do not edit those files.

## Definition of done

- `docs/changes/<ticket-id>.md` exists and is committed on the ticket
  branch.
- Every included section is anchored in the diff.
- All four contract rules satisfied.
- Working tree clean after the commit.


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
    "stage": "document",
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
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-1/iter01_review_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-1/iter01_test_output.md
