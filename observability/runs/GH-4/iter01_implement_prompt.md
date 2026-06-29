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
    "id": "GH-4",
    "type": "feat",
    "title": "Opportunity \u2014 store per-fact source span (provenance evidence)",
    "description": "Foundation for Session 2 (Extract). Distilled from `REPO_CONTENT.md` -> *Settled design \u2014 Session 2 (Extract)*; full draft in `docs/s2-extract-tickets.md`.\n\nThe `Opportunity` model (GH-1) records a provenance **enum** per uncertain fact (`deadline`/`reward`/`cost` -> `quoted|derived|none`) but has **nowhere to store the evidence** \u2014 the verbatim source text a fact was read from. Extract requires it: it is the checkable receipt separating a legitimate `derived` value (computed later by the S6 parse layer from quoted text) from a fabrication, and it lets the deterministic S6 layer resolve relative values without a second LLM call. This ticket **only** extends the model + store \u2014 no extraction logic.\n\n## Locked decisions (honor; see REPO_CONTENT.md)\n- Extract is **quoted-only**; derivation is deferred to S6. The source span is the *verbatim quoted text*, stored alongside the existing provenance enum.\n- Relative values (\"closes Friday\") need an **anchor** (a page-stated date) for S6 to resolve later; the page is gone by S6, so capture it now. `first_seen` is a fallback anchor but is *when we fetched*, not *when the source was authored* \u2014 keep them distinct.\n\n## Scope\n1. Add nullable per-fact source-span fields mirroring the provenance fields: `deadline_source`, `reward_source`, `cost_source` (verbatim quoted text, or `null` when the fact is absent / `provenance = none`).\n2. Add a nullable `source_observed_date` (the page-stated anchor date; `null` if none \u2014 S6 may fall back to `first_seen`).\n3. Store round-trips the new fields; existing dedup / `last_seen` behavior unchanged.",
    "acceptance_criteria": [
      "`Opportunity` has nullable `deadline_source` / `reward_source` / `cost_source` and `source_observed_date`; constructing with a `quoted` deadline + its `deadline_source` is valid, and with `deadline=None`, `deadline_provenance=\"none\"`, `deadline_source=None` is valid.",
      "A fact with `provenance != \"none\"` and a `null` source span is rejected (or documented invalid) \u2014 a quoted/derived fact must carry its evidence.",
      "Store insert/get/list/update round-trips all new fields; URL-normalization dedup and `last_seen` refresh from GH-1 unchanged.",
      "Unit tests cover the new fields incl. the null-deadline case and the round-trip; no network, temporary DB only.",
      "`uv run pytest -q` green."
    ],
    "skill_match": null
  },
  "state": {
    "stage": "implement",
    "iteration": 1,
    "branch": "adw/GH-4",
    "last_failure": null
  }
}
```

## Prior stage outputs this run

Read the ones relevant to your stage (the latest plan output is your work order):
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-4/iter01_plan_output.md

## File manifest (from the plan)

Open only these, do not survey the codebase; if the manifest is wrong or insufficient, read more and say so.

Edit:
- scholarship_factory/models.py:13
- scholarship_factory/store.py:7
- tests/test_models.py
- tests/test_store.py

Read:
- scholarship_factory/__init__.py
- docs/s2-extract-tickets.md:22
- prd.json:23


## Harness-edit policy

This ticket is type `feat`, not `system-repair`, so the PreToolUse guard denies any create/edit under these harness dirs: `adw/`, `hooks/`, `workflows/`, `stage_specs/`, `skills/`, `commands/`, `configs/`, `plans/`, `.claude/`. If the plan requires editing one of these, do not attempt the write — report `outcome: "blocked"` with the reason instead.
