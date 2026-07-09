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
    "id": "GH-11",
    "type": "feat",
    "title": "Fetch \u2014 FetchResult contract: the typed Fetch\u2192Extract seam",
    "description": "The typed hand-off object between **Fetch (Session 3)** and **Extract (Session 2)**. Foundation slice: this ticket defines the `FetchResult` contract **only** \u2014 no fetching, no adapters, no network. It is the S3 analogue of GH-1/GH-4: a shared data shape the rest of the fetch chain (static fetcher, politeness, adapters, cache) depends on, so it merges first and the next wave branches from it.\n\n## Context\n\nExtract (S2) already consumes \"the already-fetched raw content of one source (raw HTML + its `source_url`)\". Session 3 produces exactly that. `FetchResult` is the seam: Fetch fills it, Extract reads it. Fetching logic and source adapters are **separate, later tickets** \u2014 do not build them here.\n\n## Locked decisions (honor; see `REPO_CONTENT.md`)\n\n- **`source_url` (where facts were read) is distinct from `apply_url` (where you apply).** Fetch produces `source_url`. Keep the **final URL after redirects** distinct from the **requested URL** \u2014 they diverge when a short-link or redirect lands elsewhere; Extract's `source_url` is the *final* one.\n- **Never fabricate.** A failed fetch is represented **honestly** (status + error), never as empty-but-successful content. Downstream must be able to tell \"fetched, page was empty\" from \"fetch failed\".\n- **`fetched_at` is \"when we fetched\", not \"when the source was authored\"** \u2014 keep it distinct from `source_observed_date` (GH-4). It is the fallback anchor the S6 parse layer uses for relative dates.\n\n## Scope\n\n1. A typed `FetchResult` (pydantic v2, matching the style in `scholarship_factory/models.py`) with:\n   - `requested_url` \u2014 the URL we asked for.\n   - `final_url` \u2014 after redirects; equals `requested_url` when there was none. **This is Extract's `source_url`.**\n   - `status_code: int | None` \u2014 `None` when the request never completed (DNS/connection error/timeout).\n   - `content_type: str | None` \u2014 from the response header (distinguishes HTML vs JSON bodies).\n   - `body: str | None` \u2014 decoded response text; `None` on failure.\n   - `fetched_at` \u2014 timestamp set on creation.\n   - `error: str | None` \u2014 short exception summary when the request failed; `None` on success.\n   - `ok: bool` \u2014 derived: `True` iff `status_code` is 2xx **and** `body` is present.\n2. Construction / validation for the type and its `ok` derivation. **No `httpx` call, no network in this ticket** \u2014 the fetcher that *produces* a `FetchResult` is a later ticket.",
    "acceptance_criteria": [
      "`FetchResult` exists (pydantic v2) with `requested_url`, `final_url`, `status_code` (nullable), `content_type` (nullable), `body` (nullable), `fetched_at`, `error` (nullable), and a derived `ok`.",
      "A success result (2xx status + body present) has `ok=True`; a failure (status `None`, or 4xx/5xx, or no body) has `ok=False` and may carry an `error` string. Constructing a failure with `body=None` is valid.",
      "`final_url` equals `requested_url` when no redirect occurred; the two are allowed to differ.",
      "`fetched_at` is populated on construction.",
      "Unit tests cover: a success result, a 404/403 result, a connection-failure result (`status_code=None` + `error`), and the `ok` derivation. **No network.**",
      "`uv run pytest -q` green."
    ],
    "skill_match": null
  },
  "state": {
    "stage": "plan",
    "iteration": 1,
    "branch": "adw/GH-11",
    "last_failure": null
  }
}
```
