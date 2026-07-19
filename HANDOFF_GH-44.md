# HANDOFF: Close out GH-44 (final v1 ticket)

Self-contained brief for the cloud Devin session. The interactive planning
session that wrote this is not visible to you — everything you need is here or
in the repo. Read `CLAUDE.md` (router), `HARNESS.md`, and `notes_for_claude.md`
for background.

## Situation

- This repo is built by the agentic-sdlc harness (see `HARNESS.md`). GH-44
  ("Refresh — on-demand re-check of an opportunity's facts") is the **last open
  v1 ticket**. All 19 other tickets in `prd/*.json` are `done` and merged.
- The harness run for GH-44 was **quota-interrupted mid test-stage** (not
  failed): `prd/GH-44.json` says `"status": "quotad", "passes": false`, and
  `state.json` is frozen at `stage: test`. The review/document stages never ran
  — their observability logs are legitimately absent.
- The implementation is complete on branch `adw/GH-44` (tip `fbdb559`), and the
  full suite was verified green locally on 2026-07-19: **146 passed** via
  `uv run pytest -q`.
- The owner has **explicitly authorized you to merge the PR yourself** for this
  final ticket, overriding the "merge is a human-only gate" convention in
  `HARNESS.md`. This authorization is for GH-44 only.

## Your task

Work on branch `adw/GH-44`. Do these in order:

1. **Verify**: run `uv run pytest -q` — must be green (146 tests as of the
   branch tip).
2. **Review** the diff vs `main` against the acceptance criteria in
   `prd/GH-44.json`. Two intentional design points that may look like
   deviations but are correct (see `progress.txt` tail):
   - A re-check where a fact is no longer found sets status `changed` (the
     4-state machine `new|refreshed|changed|unreachable` has no separate state
     for it; the outcome object records `no_longer_found`).
   - `unreachable` is written via the narrow `store.set_status()` which does
     NOT bump `last_seen` — deliberate, since the record wasn't actually seen.
3. **Close-out commits on `adw/GH-44`** (before opening the PR):
   - `prd/GH-44.json`: `"status": "quotad"` → `"done"`, `"passes": false` →
     `true`. Preserve the file's existing JSON formatting/escaping.
   - `state.json`: set to the terminal-run convention (mirror what `main` has
     for GH-43):
     `stage` → `"document"`, `last_failure` → `null`, `cooldown_until` →
     `null`; keep `ticket_id`, `iteration`, `branch`, `budget_used_tokens`
     as they are.
   - `progress.txt`: append a short entry — GH-44 closed out manually after a
     quota interruption at test stage; review/document harness stages were
     skipped; tests verified green; plus any real learnings from your review.
   - **Delete this file (`HANDOFF_GH-44.md`)** so it never reaches `main`.
4. **Push** `adw/GH-44`, then **open a PR** to `main`:
   - Title: `GH-44: Refresh — on-demand re-check of an opportunity's facts`
   - Body: summary of the change, your review findings, and `Closes #44` so
     the GitHub issue auto-closes.
5. **Merge the PR** with a **merge commit** (prior PRs in `git log` on `main`
   are merge commits, e.g. PR #47 — do not squash or rebase).
6. **Post-merge check**: `main` contains the refresh feature; `prd/GH-44.json`
   on `main` says done; `state.json` on `main` is the terminal state; issue
   #44 is closed; this handoff file does not exist on `main`.

## Hard constraints

- **Merge ONLY via the PR.** Never `git push` to `main` directly, never
  force-push, never rewrite history, never use `--no-verify`.
- `notes_for_claude.md` documents GitHub access via REST API because `gh` is
  unauthenticated on the owner's machine; its token-extraction trick (Windows
  Credential Manager) will NOT work in your environment. Use whatever
  authenticated GitHub mechanism your session provides (REST API preferred);
  the constraint that matters is: PR-based merge only.
- `.claude/settings.json` wires hooks by absolute Windows paths that won't
  resolve in your environment. If they fail to load, that's expected — but
  still obey the rules they enforce (listed in `HARNESS.md` → Hooks).
- Leave the repo so `prd/`, `state.json`, GitHub issues, and `git log` all
  agree.

## Explicitly out of scope (owner handles locally)

- The end-to-end sourcing smoke run (needs the owner's Anthropic API key).
- The Windows Task Scheduler job `\ADW\ADW-scholarship-factory` (already
  Disabled; stays disabled).
