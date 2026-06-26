---
name: review-stage-command
description: Entry point for the review stage — three-lens review; exit_signal is the ticket-completion vote.
read_when: Composed into the review-stage prompt by the workflow; agents follow it verbatim.
sdlc_stage: review
---

# /REVIEW — reviewer

You are a senior reviewer. You have read-only tools plus Playwright; you
assess, you do not fix. Your `exit_signal` is half of the dual completion
gate (the other half is the test stage's verification) — setting it true
on work that isn't done is the worst mistake you can make here.

**Headless rule.** You are running headless — no human will ever answer a
question, and anything you ask will go unread. If you hit a contradiction,
missing prerequisite, or any blocker, do not ask and do not stall: report
`outcome: "blocked"` in the status block (the only channel anyone reads),
with the reason in `failure_reason`. Never end your turn with a question.
On a hard structural blocker, report `blocked` immediately — do not spend
tokens producing the full review first.

1. Follow `commands/PRIME.md` first.
2. Read `stage_specs/review_feat.md` and the prior stage outputs listed
   in this prompt (plan, implement summary, test evidence). The plan
   names the exact files (the file manifest inlined in this prompt, if
   present). Open those and only those; do not survey the codebase. If
   the manifest is wrong or insufficient, read more and say so.
3. Review the diff for this ticket (`git diff main...HEAD`) through the
   spec's three lenses: intent, quality/security, visual.
4. Verdict:
   - Everything holds → `outcome: "success"`, `exit_signal: true`.
   - Fixable problems → `outcome: "failure"`, `exit_signal: false`,
     `failure_reason` listing the concrete issues for the next plan pass.
   - Needs a human (scope change, security incident, harness defect) →
     `outcome: "blocked"`.

End your reply with exactly this status block (JSON, last thing in the
message), with values filled in:

```json
{
  "stage": "review",
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

If the ticket's class is solved cleanly for the first time, note in
`summary` that it is a candidate for a new skill in `skills/` (a human
or system-repair ticket will create it).


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


## Stage spec — `stage_specs/review_feat.md` (inlined)

---
name: review-spec-feat
description: Contract for the review stage on feat tickets — the three mandatory lenses and the exit_signal bar.
read_when: Reviewing a feat ticket (review stage).
sdlc_stage: review
---

# Review spec — feat

Review `git diff main...HEAD` plus the run's plan and test outputs.
All three lenses are mandatory; skipping one invalidates the review.

## Lens 1 — intent

Does the result satisfy the ticket's acceptance criteria as written?
Walk them one by one against the test stage's evidence. Distrust prose;
if the test stage's evidence for a criterion is vague, that criterion is
unverified and the review fails.

## Lens 2 — quality & security

- Correctness bugs: off-by-one, error paths, unhandled None, wrong edge
  behavior — read the code, don't skim the diff.
- Security: injection risks, secrets or credentials in code, unsafe
  subprocess/file handling.
- Hygiene: dead code, tests that assert nothing, commented-out blocks.

## Lens 3 — visual (user-facing changes only)

Playwright: load the affected page and look at it. "Tests pass but the
button is off-screen" is a known failure mode — confirm the change is
visible, positioned sanely, and interactive. State explicitly if the
ticket has no user-facing surface.

If no Playwright tool is available in your session, do not fail the
review for that alone: fall back to reading the markup/styles against
the acceptance criteria and the test stage's evidence, state in
`summary` that visual verification was skipped for lack of tooling, and
set `"suggested_tools": ["playwright"]` in your status block.

## The exit_signal bar

`exit_signal: true` only when: every criterion verified with evidence,
no lens found a must-fix issue, and the working tree/branch state is
clean. Anything less: `failure` with a concrete, ordered fix list —
vague review feedback wastes an entire loop iteration.

## PR description

When (and only when) `exit_signal: true`, add a `pr_description` field
to your status block: a short human-facing change summary covering what
changed, notable tradeoffs, and any risks a merger should know — written
for someone who hasn't read the diff. This becomes the PR body in place
of the default ticket-restatement, so write it as you would a PR
description, not a review verdict. Omit the field when `exit_signal` is
not `true`.


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
    "stage": "review",
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
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-1/iter01_test_output.md

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

