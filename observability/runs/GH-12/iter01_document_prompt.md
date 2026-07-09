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
    "id": "GH-12",
    "type": "feat",
    "title": "Parse layer - typed deadline dates over the stored string field (deterministic S6)",
    "description": "The **deterministic date parse layer** for Session 6. Independent of Fetch \u2014 operates on the `Opportunity` fields that already exist (GH-1/GH-4). This ticket builds the **date** half only; the money half is a separate ticket. **No LLM, no network, no ranking.**\n\n## Context\n\nGH-1's carried-forward note: `deadline` is stored as a **verbatim string**, not a typed date. Ranking and refresh need a deterministic layer that turns the stored quoted text into an absolute date. Extract is **quoted-only by design**; the risky transform (\"closes Friday\" + anchor -> a real date) is deferred to **this** deterministic S6 layer (a library, `dateparser`/`dateutil` \u2014 **not** a second LLM call).\n\n## Locked decisions (honor; see `REPO_CONTENT.md` -> carried-forward notes + Session 2 quoted-only/derive split)\n\n- **The parse layer sets provenance `derived`** when it computes a value from quoted text. **Unresolvable -> `None`** (the deterministic boundary self-enforces no-fabrication). Never guess a date.\n- **Relative values resolve against the stored anchor** (`source_observed_date` from GH-4, falling back to `first_seen`) \u2014 **not** against \"today\". The source page is gone by S6; only the stored source span + anchor remain.\n- **Multi-deadline strings are not collapsed.** GH-5 captures e.g. `\"June 1st, and October 1st\"` verbatim; this layer returns **both** dates, not one.\n\n## Scope\n\n1. A module `scholarship_factory/parse_dates.py` with a pure function: given a stored deadline string + an anchor `date`, return an absolute `date` (or a list of dates for multi-deadline strings), or `None` when unresolvable.\n2. Use `dateparser` (handles relative + absolute; `tzdata` is already a declared dep for Windows). Resolve relative expressions against the passed anchor, not the system clock.\n3. Optionally expose a helper taking an `Opportunity` and returning the typed deadline(s) + the `derived`/`none` provenance. **No store mutation, no ranking** in this ticket.",
    "acceptance_criteria": [
      "`\"June 1st, and October 1st\"` + a 2024 anchor -> `[2024-06-01, 2024-10-01]` (both, not collapsed).",
      "A relative expression (e.g. `\"closes Friday\"`) + an anchor date resolves to the correct absolute date **relative to the anchor**, not to the current day.",
      "An unparseable or absent string -> `None`; a computed value is provenance `derived`, an unresolvable one is `none` \u2014 never guessed.",
      "Deterministic + offline: no network, no LLM. Unit tests cover the multi-deadline case, a relative-vs-anchor case, an absolute-date case, and the `None`/unresolvable case.",
      "`uv run pytest -q` green."
    ],
    "skill_match": null
  },
  "state": {
    "stage": "document",
    "iteration": 1,
    "branch": "adw/GH-12",
    "last_failure": null
  }
}
```

## Prior stage outputs this run

Read the ones relevant to your stage (the latest plan output is your work order):
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-12/iter01_document_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-12/iter01_implement_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-12/iter01_plan_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-12/iter01_review_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-12/iter01_test_output.md
