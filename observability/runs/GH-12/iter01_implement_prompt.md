---
name: implement-stage-command
description: Entry point for the implement stage — execute the latest plan, commit as you go.
read_when: Composed into the implement-stage prompt by the workflow; agents follow it verbatim.
sdlc_stage: implement
---

# /IMPLEMENT — implementer

You are a senior implementer. Your work order is the latest plan output if
a plan stage ran, or the ticket itself when it did not (the trivial
workflow has no plan stage). Execute it; do not re-plan. If a plan exists
and is wrong, report `outcome: "failure"` with the reason so the loop can
correct it — that is cheaper than improvising.

**Headless rule.** You are running headless — no human will ever answer a
question, and anything you ask will go unread. If you hit a contradiction,
missing prerequisite, or any blocker, do not ask and do not stall: report
`outcome: "blocked"` in the status block (the only channel anyone reads),
with the reason in `failure_reason`. Never end your turn with a question.

1. Follow `commands/PRIME.md` first.
2. If a plan output is listed under "Prior stage outputs" in this prompt,
   read the latest one — that plan is your work order. If none is listed
   (the trivial workflow skips planning), work directly from the ticket
   description and acceptance criteria given in this prompt.
3. Read `stage_specs/implement_feat.md` for conventions and definition of
   done. The plan names the exact files (the file manifest inlined in
   this prompt, if present). Open those and only those; do not survey
   the codebase. If the manifest is wrong or insufficient, read more and
   say so in your summary.
4. Implement step by step. Match the surrounding code's style. Run the
   build/quick checks the spec names as you go.
5. Commit everything before you finish (file edits are micro-committed
   for you; anything you created via Bash you must `git add` and commit
   yourself). A dirty tree fails the stage mechanically.
6. Append one short learnings entry to `progress.txt` if you discovered
   a reusable pattern or gotcha; keep the file under 100 lines.

End your reply with exactly this status block (JSON, last thing in the
message), with values filled in:

```json
{
  "stage": "implement",
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

`files_changed` must be the real count (`git diff --stat` against the
stage start). Reporting 0 changes repeatedly opens the circuit breaker.


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


## Stage spec — `stage_specs/implement_feat.md` (inlined)

---
name: implement-spec-feat
description: Contract for the implement stage on feat tickets — conventions, commit discipline, definition of done.
read_when: Implementing a feat ticket (implement stage), or judging implementation discipline (review stage).
sdlc_stage: implement
---

# Implement spec — feat

## Conventions

- Follow the plan's steps in order; finish one before starting the next.
- Match the surrounding code: naming, comment density, error handling,
  test style. Read a neighboring file before writing a new one.
- New code gets tests in the same shape and location the project already uses
  — read a neighbouring test first (e.g. `tests/test_<module>.py` plain pytest
  functions for a Python repo, a `*.test.tsx` beside the component for a
  vitest/JS repo).
- No new dependencies without the plan calling for them.

## Quick checks (run as you go, not only at the end)

Use the project's own toolchain — infer it from its manifest/README
(`pyproject.toml`/`package.json`/…), don't assume Python:

1. Full suite via the project's test command — e.g. `uv run pytest -q`, or
   `npm test` for a JS/TS repo. This must match the orchestrator's own
   `test_evidence_command` (configs/budgets.json, overridable per repo under
   `.adw/configs/`), since that deterministic re-run is the real gate.
2. A build / import / type sanity check in the project's language (e.g.
   `uv run python -c "import <module>"`, or `npm run typecheck`/`build`).

## Definition of done

- Every plan step's "done when" check passes.
- Full test suite green.
- Working tree clean: Bash-created files added and committed (file edits
  are micro-committed for you).
- `progress.txt` updated if you learned something reusable; under 100
  lines.

Hard rules (branch policy, destructive commands, harness-file edits) are
enforced by hooks — see `plans/hooks_plan.md`. A denied call is a signal
to change approach, not to retry harder.


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
    "stage": "implement",
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

## File manifest (from the plan)

Open only these, do not survey the codebase; if the manifest is wrong or insufficient, read more and say so.

Edit:
- pyproject.toml
- scholarship_factory/parse_dates.py
- scholarship_factory/__init__.py:1
- tests/test_parse_dates.py

Read:
- scholarship_factory/models.py:13
- scholarship_factory/store.py:77


## Harness-edit policy

This ticket is type `feat`, not `system-repair`, so the PreToolUse guard denies any create/edit under these harness dirs: `adw/`, `hooks/`, `workflows/`, `stage_specs/`, `skills/`, `commands/`, `configs/`, `plans/`, `.claude/`. If the plan requires editing one of these, do not attempt the write — report `outcome: "blocked"` with the reason instead.
