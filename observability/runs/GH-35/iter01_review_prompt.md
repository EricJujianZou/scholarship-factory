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
    "id": "GH-35",
    "type": "feat",
    "title": "Traverse - follow listing links to detail pages (depth-1 discovery)",
    "description": "Session 4 (Traverse): the link-discovery step - the reason this system is an agent, not a scraper. Depends on extract (MERGED: `extract.py` returns a typed result distinguishing a *detail* record from a *list* of thin items) and the fetcher (MERGED). Distilled from `REPO_CONTENT.md` (v1 roadmap, Session 4; listing/thin-item decisions in *Settled design - Session 2*).\n\n## Locked decisions (honor)\n\n- **v1 traversal is depth-1**: a listing page's thin items (title + url, deadline usually absent) get their detail pages fetched and extracted; detail-page output is NOT traversed further. No open-ended crawling.\n- A thin item and its detail extraction concern the SAME opportunity: after extracting the detail page, the record upserted must carry the detail page's richer facts; `source_url` is the detail page. (True cross-source identity is Session 5 - here the store's normalized `apply_url` dedup is still the merge point; do not build identity logic.)\n- **Budget-bounded:** a per-run cap on traversed pages (configurable, default ~25). When the cap stops traversal early, the report says so honestly.\n- Traversal failures (fetch error, extract yields nothing) are recorded per-link in the report, never fatal, never fabricated.\n- Fetch callable injectable (composes with politeness/cache layers); extractors injectable/stubbed in tests, same as the pipeline ticket.\n\n## Scope\n\n1. `scholarship_factory/traverse.py`: given a *list* extraction result (thin items) + a fetch fn + extract fns, fetch each item's URL, extract, and return the enriched records + a per-link outcome report. Respect the page cap.\n2. Integrate into the sourcing pipeline **if** `pipeline.py` (the composition ticket) is already on main - a listing extraction triggers traversal of its thin items. If pipeline is not present, ship traverse standalone with the same injectable contract.\n3. No recursion beyond depth 1, no new identity/dedup logic, no scheduler.",
    "acceptance_criteria": [
      "A stubbed listing extraction with N thin items -> traverse fetches each item URL (asserted via fake fetch fn) and upserts the detail-extracted records; a thin item whose detail page states the deadline ends up stored WITH that deadline (quoted provenance + source span, from the stubbed detail extraction).",
      "Page cap: with cap=2 and 5 thin items, only 2 detail fetches happen and the report flags the early stop.",
      "A detail fetch failure or empty extraction is reported for that link; remaining links still process.",
      "No fetch of the same detail URL twice within one traverse call.",
      "All tests offline with stubbed fetch/extract; `uv run pytest -q` green."
    ],
    "skill_match": null
  },
  "state": {
    "stage": "review",
    "iteration": 1,
    "branch": "adw/GH-35",
    "last_failure": null
  }
}
```

## Prior stage outputs this run

Read the ones relevant to your stage (the latest plan output is your work order):
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-35/iter01_implement_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-35/iter01_plan_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-35/iter01_test_output.md

## File manifest (from the plan)

Open only these, do not survey the codebase; if the manifest is wrong or insufficient, read more and say so.

Edit:
- scholarship_factory/traverse.py
- scholarship_factory/pipeline.py:22
- scholarship_factory/pipeline.py:25
- scholarship_factory/pipeline.py:72
- scholarship_factory/__init__.py:9
- scholarship_factory/cli.py:55
- tests/test_traverse.py
- tests/test_pipeline.py:50

Read:
- scholarship_factory/extract.py:33
- scholarship_factory/extract.py:93
- scholarship_factory/fetch.py:31
- scholarship_factory/store.py:93
- scholarship_factory/models.py:13
- scholarship_factory/urls.py:6
- scholarship_factory/cli.py:49
- scholarship_factory/cache.py:1
- scholarship_factory/polite.py:1
- REPO_CONTENT.md:85
- REPO_CONTENT.md:166

