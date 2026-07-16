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
    "stage": "test",
    "iteration": 1,
    "branch": "adw/GH-32",
    "last_failure": null
  }
}
```

## Prior stage outputs this run

Read the ones relevant to your stage (the latest plan output is your work order):
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-32/iter01_implement_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-32/iter01_plan_output.md

## File manifest (from the plan)

Open only these, do not survey the codebase; if the manifest is wrong or insufficient, read more and say so.

Edit:
- scholarship_factory/polite.py
- tests/test_polite.py
- scholarship_factory/__init__.py:3

Read:
- scholarship_factory/fetch.py:64
- scholarship_factory/fetch.py:42
- scholarship_factory/urls.py:6
- scholarship_factory/adapters.py:1
- tests/test_fetch.py:110
- tests/test_fetch.py:139
- pyproject.toml

