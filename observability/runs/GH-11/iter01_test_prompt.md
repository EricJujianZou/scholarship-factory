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
    "stage": "test",
    "iteration": 1,
    "branch": "adw/GH-11",
    "last_failure": null
  }
}
```

## Prior stage outputs this run

Read the ones relevant to your stage (the latest plan output is your work order):
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-11/iter01_document_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-11/iter01_implement_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-11/iter01_plan_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-11/iter01_review_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-11/iter01_test_output.md

## File manifest (from the plan)

Open only these, do not survey the codebase; if the manifest is wrong or insufficient, read more and say so.

Edit:
- scholarship_factory/fetch.py
- scholarship_factory/__init__.py:2
- tests/test_fetch.py

Read:
- scholarship_factory/models.py:1
- scholarship_factory/extract.py
- tests/test_models.py

