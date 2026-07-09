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
    "stage": "review",
    "iteration": 1,
    "branch": "adw/GH-11",
    "last_failure": null
  }
}
```

## Prior stage outputs this run

Read the ones relevant to your stage (the latest plan output is your work order):
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-11/iter01_implement_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-11/iter01_plan_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-11/iter01_test_output.md

## File manifest (from the plan)

Open only these, do not survey the codebase; if the manifest is wrong or insufficient, read more and say so.

Edit:
- scholarship_factory/fetch.py
- scholarship_factory/__init__.py:1
- tests/test_fetch.py

Read:
- scholarship_factory/models.py:1
- scholarship_factory/extract.py:125
- scholarship_factory/store.py:78
- tests/test_models.py

