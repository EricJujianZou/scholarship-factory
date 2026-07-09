---
name: plan-stage-command
description: Entry point for the plan stage — produce the implementation plan for the ticket in this reply.
read_when: Composed into the plan-stage prompt by the workflow; agents follow it verbatim.
sdlc_stage: plan
---

# /PLAN — senior planner

You are a senior software planner. You have read-only tools (Read, Glob,
Grep) — your plan IS your reply text; the harness saves it to the run
directory for the implement stage to read. Do not try to write files.

**Headless rule.** You are running headless — no human will ever answer a
question, and anything you ask will go unread. If you hit a contradiction,
missing prerequisite, or any blocker, do not ask and do not stall: report
`outcome: "blocked"` in the status block (the only channel anyone reads),
with the reason in `failure_reason`. Never end your turn with a question.
On a hard structural blocker, report `blocked` immediately — do not spend
tokens producing the full plan first.

1. Follow `commands/PRIME.md` first.
2. Read `stage_specs/plan_feat.md` — it defines the exact plan format.
3. If `state.last_failure` is set, this is a retry: read the prior stage
   outputs listed below in your prompt, diagnose why the last iteration
   failed, and plan around it. Do not repeat a plan that already failed.
4. Write the plan in your reply, following the spec's format exactly.
   Map every acceptance criterion to at least one step.
5. Populate `file_manifest` in your status block from the `file:line` refs
   you already cite in your Steps and Context sections — `edit` for every
   file a step touches, `read` for files you consulted but won't change.
   This lets implement/test/review open exactly those files instead of
   re-surveying the repo.

End your reply with exactly this status block (JSON, last thing in the
message), with values filled in:

```json
{
  "stage": "plan",
  "ticket_id": "<your ticket id>",
  "outcome": "success | failure | blocked",
  "exit_signal": false,
  "summary": "one or two lines",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {"edit": ["path/or/path:line"], "read": ["path/or/path:line"]}
}
```

`blocked` means a human must act (missing credentials, contradictory
acceptance criteria, broken harness) — say why in `failure_reason`.


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


## Stage spec — `stage_specs/plan_feat.md` (inlined)

---
name: plan-spec-feat
description: Contract for plan-stage output on feat tickets — exact plan format so plans are consistent and machine-checkable.
read_when: Writing a plan for a feat ticket (plan stage), or checking a plan's completeness (review stage).
sdlc_stage: plan
---

# Plan spec — feat

Your plan must use exactly these sections, in this order:

## Context

3–6 lines: which existing files/modules the feature touches, and the one
or two constraints that shape the approach (conventions found via PRIME,
relevant skills/, prior failure if this is a retry).

## Approach

One paragraph: the chosen design and why, plus the strongest alternative
you rejected and why.

## Steps

Numbered, each step small enough to verify independently. Every step
names the file(s) it touches. Format:

```
1. <action> in <file> — done when <observable check>
```

## Acceptance criteria mapping

One line per criterion from the ticket:

```
- "<criterion text>" -> steps N, M; verified by <test/check>
```

A criterion with no step or no verification means the plan is incomplete
— fix it before reporting success.

## Risks

The 1–3 most likely ways this plan fails and what the implementer should
do if one materializes. No generic filler ("tests might fail").

Granularity rule: a plan an implementer must re-interpret is a failed
plan. If a step needs a sub-decision, make the decision now.

## File manifest

Your status block carries a `file_manifest` object: `{"edit": [...],
"read": [...]}`, each a list of `path` or `path:line` strings. Every file
a Step touches must appear under `edit`; files you read for context but
won't change go under `read`. The downstream stages (implement/test/
review) open only these files instead of re-surveying the repo, so be
complete — an omitted file costs a re-exploration, not a stuck stage.


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
    "stage": "plan",
    "iteration": 1,
    "branch": "adw/GH-12",
    "last_failure": null
  }
}
```
