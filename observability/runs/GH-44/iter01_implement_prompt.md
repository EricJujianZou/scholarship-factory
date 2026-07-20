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
    "id": "GH-44",
    "type": "feat",
    "title": "Refresh - on-demand re-check of an opportunity's facts",
    "description": "Session 8, the last v1 slice: on-demand refresh. The owner asks \"is this deadline still right?\" for opportunities they care about. **No scheduler, no automatic refresh** - v1 refreshes only on demand (locked scope boundary). Composes merged pieces: fetch (`fetch_url`/`PoliteFetcher`), extract (`extract.py`/`jsonld.py`), store, cache (bypassed here - a refresh must hit the live page), identity merge policy (GH-XX identity ticket) if merged.\n\n## Locked decisions (honor)\n\n- Refresh = re-fetch the opportunity's `source_url`, re-extract, and do a **field-level compare** on the uncertain facts (`deadline`/`reward`/`cost` + their source spans): unchanged -> just bump `last_seen`; changed -> update the fact, its provenance, and its source span honestly; fact disappeared from the page -> keep the old value but record that the re-check no longer found it (a `status`/note, not a silent delete and not a fabricated null).\n- A fetch failure (404/timeout) marks the refresh outcome honestly (e.g. status `unreachable`) - it does NOT delete or blank the record.\n- The store's `status` field (default `\"new\"`, GH-1) gets its first real states here - keep the machine tiny: `new | refreshed | changed | unreachable`. No bigger lifecycle.\n- LLM extractor injectable/stubbed in tests, as everywhere.\n\n## Scope\n\n1. `scholarship_factory/refresh.py`: `refresh_opportunity(store, opportunity_id, *, fetch_fn, extract_fn, ...) -> RefreshOutcome` implementing the compare/update policy.\n2. API + UI hook: `POST /api/opportunities/{id}/refresh` on the FastAPI app and a per-card refresh button on the dashboard (if the dashboard ticket is merged; otherwise ship the function + endpoint-ready signature).\n3. CLI: `sf refresh <id>`.",
    "acceptance_criteria": [
      "Stubbed re-extract with an unchanged deadline -> `last_seen` bumped, status `refreshed`, fact untouched.",
      "Stubbed re-extract with a NEW deadline string -> fact + source span updated, status `changed`, old value gone from the row but the change visible in the outcome object.",
      "Stubbed re-extract where the fact is absent -> old value retained, outcome records it as no-longer-found (no silent delete, no fabricated value).",
      "Fetch failure -> status `unreachable`, record otherwise untouched.",
      "Cache is bypassed (asserted: fetch fn called even with a fresh cache entry present).",
      "All tests offline, temp db; `uv run pytest -q` green."
    ],
    "skill_match": null
  },
  "state": {
    "stage": "implement",
    "iteration": 1,
    "branch": "adw/GH-44",
    "last_failure": null
  }
}
```

## Prior stage outputs this run

Read the ones relevant to your stage (the latest plan output is your work order):
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-44/iter01_plan_output.md

## File manifest (from the plan)

Open only these, do not survey the codebase; if the manifest is wrong or insufficient, read more and say so.

Edit:
- scholarship_factory/refresh.py
- scholarship_factory/store.py:136
- scholarship_factory/api.py:35
- scholarship_factory/cli.py:97
- scholarship_factory/static/index.html:75
- scholarship_factory/__init__.py:12
- tests/test_refresh.py
- tests/test_api.py:79
- tests/test_cli.py:69

Read:
- scholarship_factory/models.py:13
- scholarship_factory/fetch.py:31
- scholarship_factory/extract.py:125
- scholarship_factory/cache.py:88
- scholarship_factory/identity.py:26
- scholarship_factory/pipeline.py:50
- scholarship_factory/urls.py
- tests/test_pipeline.py:26
- tests/test_store.py
- progress.txt:5


## Harness-edit policy

This ticket is type `feat`, not `system-repair`, so the PreToolUse guard denies any create/edit under these harness dirs: `adw/`, `hooks/`, `workflows/`, `stage_specs/`, `skills/`, `commands/`, `configs/`, `plans/`, `.claude/`. If the plan requires editing one of these, do not attempt the write — report `outcome: "blocked"` with the reason instead.
