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
    "id": "GH-42",
    "type": "feat",
    "title": "Identity - cross-source dedup: merge the same opportunity seen via different URLs",
    "description": "Session 5 (Identity). Replaces the v1 placeholder where opportunity-identity == normalized `apply_url` (a `UNIQUE` index, GH-1). Traverse (S4) makes this real: the same opportunity now arrives from a listing thin item and from its detail page, or from two different sources with different tracking URLs. Distilled from `REPO_CONTENT.md` (locked: the URL heuristic is *not* true identity; cross-source dedup was deferred to here).\n\n## Design (standard call - keep boring, no ML)\n\n- **Identity key, in order of trust:** (1) normalized `apply_url` equality (existing `urls.py` normalization - keep as the primary key); (2) a **secondary match**: same normalized `title` + same normalized `organization` (case/whitespace/punctuation-folded, both non-null). Nothing fuzzier: no edit distance, no embeddings - a miss is acceptable, a false merge is not (whole-record honesty).\n- **Merge policy on an identity hit:** field-wise \"richer wins\": a non-null fact beats null; if both non-null they conflict -> keep the EXISTING value and do not overwrite (facts are receipts - never silently replace a quoted fact with a different one), but always refresh `last_seen`. `source_url` of the record that contributed a new fact is preserved with that fact's source span (already stored per-fact).\n- Never merge two records that share only a title (different orgs) or only an org.\n\n## Scope\n\n1. `scholarship_factory/identity.py`: `find_duplicate(store, opportunity) -> Opportunity | None` (the identity probe) and a `merge_into(existing, incoming) -> Opportunity` implementing the field-wise policy.\n2. Wire the store's upsert path (or the pipeline's store step) to consult identity before insert: URL-dedup hit -> existing behavior; else secondary-match hit -> merge; else insert new.\n3. No retroactive dedup sweep of existing rows (out of scope).",
    "acceptance_criteria": [
      "Two records with different `apply_url`s (tracking params vs clean) still dedup via URL normalization (regression guard).",
      "Two records with different hosts but identical normalized title + organization -> ONE stored row; the merged row has the union of facts (null filled from incoming), `last_seen` refreshed, and no existing non-null fact overwritten.",
      "Same title but different organization -> two rows (no merge). Same org, different title -> two rows.",
      "A thin listing item (title+url only) followed by its rich detail record (same normalized apply_url) -> one row carrying the detail facts.",
      "All tests offline, temp db; `uv run pytest -q` green."
    ],
    "skill_match": null
  },
  "state": {
    "stage": "test",
    "iteration": 1,
    "branch": "adw/GH-42",
    "last_failure": null
  }
}
```

## Prior stage outputs this run

Read the ones relevant to your stage (the latest plan output is your work order):
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-42/iter01_implement_output.md
- C:/Users/zouju/Coding Projects/scholarship-factory/observability/runs/GH-42/iter01_plan_output.md

## File manifest (from the plan)

Open only these, do not survey the codebase; if the manifest is wrong or insufficient, read more and say so.

Edit:
- scholarship_factory/identity.py
- scholarship_factory/store.py:77
- scholarship_factory/__init__.py:1
- tests/test_identity.py

Read:
- scholarship_factory/models.py:13
- scholarship_factory/models.py:42
- scholarship_factory/urls.py:6
- scholarship_factory/pipeline.py:93
- scholarship_factory/traverse.py:90
- tests/test_store.py:39
- tests/test_pipeline.py:170
- tests/test_pipeline.py:245
- REPO_CONTENT.md:110

