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
    "id": "GH-32",
    "type": "feat",
    "title": "Fetch - per-host politeness: rate limit + robots.txt",
    "description": "Session 3 (Fetch) chain. Depends on the static fetcher (GH-26, `scholarship_factory/fetch.py`: `fetch_url`, `FetchResult`) - MERGED. Adds the good-citizen layer: one rate limiter **per host** + respect for `robots.txt`. Cheap insurance against IP bans (locked default from the S3 design).\n\n## Locked decisions (honor)\n\n- **Per-host min-interval rate limiting** (default ~2s between requests to the same host, configurable). Different hosts do not block each other.\n- **Respect robots.txt**: before fetching a URL, consult the host's robots.txt (fetched once per host per run, cached in memory; use stdlib `urllib.robotparser` semantics for our User-Agent falling back to `*`). A disallowed URL is **not fetched** and yields an honest `FetchResult` (`ok` False, `error` naming robots as the reason) - never an exception.\n- robots.txt itself unreachable/malformed -> **fail open** (treat as allowed); politeness is insurance, not a gate that can wedge the whole run.\n- No global queue/scheduler - this wraps single fetches; v1 runs are sequential.\n\n## Scope\n\n1. A `PoliteFetcher` (or equivalent thin layer) over `fetch_url`: same signature/return, adding per-host spacing + robots check. Sleep/clock injectable for tests (no real sleeping in the suite).\n2. In-memory per-host state (last-request time, parsed robots); no persistence.\n3. Wire nothing else - callers opt in by using the polite layer (the pipeline ticket composes it).",
    "acceptance_criteria": [
      "Two consecutive fetches to the same host are spaced by the configured interval (asserted via injected clock/sleep - no real sleep in tests); fetches to different hosts are not delayed.",
      "A URL disallowed by the host's robots.txt is not fetched (underlying transport never called) and returns a `FetchResult` with `ok` False and a robots-specific `error`.",
      "robots.txt returning 404/timeout -> the fetch proceeds (fail open).",
      "robots.txt is requested at most once per host per fetcher instance.",
      "All tests offline (`httpx.MockTransport` / injected fakes); `uv run pytest -q` green."
    ],
    "skill_match": null
  },
  "state": {
    "stage": "plan",
    "iteration": 1,
    "branch": "adw/GH-32",
    "last_failure": null
  }
}
```
