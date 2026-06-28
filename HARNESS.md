# HARNESS.md — how this repo gets built

Context for any agent working in `scholarship-factory`. This repo is **built by**
the *agentic-sdlc harness* (the "engine"), a separate repo that builds *any*
target repo from a backlog of tickets. You don't need to read the engine to work
here — this file is the distilled version. Read the engine source only for a deep
dive (see *Reaching the engine* below).

This file describes the **stable model**, not live state. For what's actually
happening right now — which ticket is in flight, what's merged — read `prd.json`
and `git log`. Those are the source of truth; this file does not duplicate them
(so it can't rot).

## Two kinds of "me"

The harness is not one agent per ticket. It runs a **pipeline of separate,
non-interactive Claude Code invocations**, one per stage:

```
plan → implement → test → review → document
```

Each stage is a fresh Claude instance with a stage-specific prompt and the
engine's `AGENTS.md` as its contract, working on the ticket's `adw/<id>` branch.

- A **stage-me** is one of those automated builders. It runs overnight/headless.
- An **interactive-me** is a Claude you're pairing with in a terminal (design
  sessions, setup).

**The consequence that matters:** a stage-me **never sees the interactive chat.**
It gets only the ticket body + the repo. So **tickets must be self-contained** —
every decision a builder needs goes in the issue body, distilled from
`REPO_CONTENT.md`. Never assume the overnight builder read a conversation.

## The build queue

Work enters through **GitHub issues** labeled **`adw` + exactly one type label**
(`feat` / `bug` / `chore` / `system-repair`). Missing the type label, or having
more than one, → the issue is **skipped**. The harness syncs open `adw` issues
into `prd.json` (the backlog ledger) and works the highest-priority open ticket.

**This repo gets its own hourly build.** A dedicated Windows Task Scheduler job
runs `poll_once` against *this* repo with **`ADW_REPO` set to its path** —
separate from the engine's own `\ADW\` job, which targets the **engine** (`ADW_REPO`
unset) and never touches this repo. Each pass syncs open `adw` issues and builds
the highest-priority one (`--max-tickets`). So once an issue is filed + labeled,
expect the next tick to pick it up and update `prd.json`. (The dedicated job is
registered once this repo has an open backlog.) The command a pass runs:

```bash
ADW_REPO="C:/Users/zouju/Coding Projects/scholarship-factory" \
  uv run --project "C:/Users/zouju/Coding Projects/agentic-sdlc" \
  python "C:/Users/zouju/Coding Projects/agentic-sdlc/workflows/poll_once.py" \
  --max-tickets 1
```

`poll_once.py` = one pass: sync issues → build N tickets (`--max-tickets`). See the
engine's `ONBOARDING.md` for the full reference.

## Branch & merge model

- Every ticket branch is **cut from `main`**.
- **Merge is a human-only gate** — the agent opens the PR; a person merges it.
- ⟹ **dependent tickets cannot stack overnight.** A ticket branched tonight only
  sees what was in `main` when it was cut. The dependency edge is therefore
  **merge cadence**: merge the foundation, and the *next* run's tickets branch
  from the updated `main`. Scope and sequence tickets accordingly — don't file
  two tickets the same night where one needs the other's code.

## Naming convention

Keep these aligned by ID: GitHub issue `GH-<n>: <Title>` · branch `adw/<id>` ·
PR `<id>: <summary>` · `prd.json` story id `GH-<n>`. (Add the `GH-<n>:` prefix to
the issue title *after* filing — GitHub assigns the number.)

## Hooks (don't fight them)

`.claude/settings.json` wires three engine hooks **by absolute path** (the path
contains a space — keep it quoted): a **PreToolUse guard**, a **PostToolUse
auto-commit** (git-as-memory), and a **Stop clean-tree checklist**. They are not
optional — without them, stage runs fail with dirty-tree errors.

The **guard** blocks, among others: push to `main`/`master`, any push while the
current branch *is* `main`, force-push, `git reset --hard`, rebase/amend/
filter-branch, `--no-verify`. Know this so you don't burn a turn on a blocked op.

## Filing issues / PRs

There is **no `gh` auth, by design**. Use the git-credential token + GitHub REST
API (the engine's `adw/github.py` has helpers: `get_token()`, `repo_slug()`,
`open_or_update_pr()`, `comment_on_issue()`, …). `git push` works via the
credential helper; PRs and issue edits go through the API.

## Reaching the engine

The engine lives at the sibling path
`C:/Users/zouju/Coding Projects/agentic-sdlc`. You almost never need it — this
file is the summary. For a genuine deep dive into engine source, launch with
`--add-dir "C:/Users/zouju/Coding Projects/agentic-sdlc"` (one grant, no per-file
prompts). Reaching a path costs nothing; *reading* files costs tokens — so prefer
this summary and open the engine only when you truly need its internals.

## Traps already paid for

Borrowed from the engine's `CLAUDE.md` *Operational facts*; the engine list stays
the source of truth. Repo-specific ones marked ★.

- **The guard scans the literal command string.** A benign command that merely
  *contains* a blocked pattern (`git push … main`, `git reset --hard`,
  `--no-verify`, `rm -rf <abs>`) is denied even inside an `echo`, heredoc, or
  quoted string. Put such content in a file and read it, or split the tokens.
- **`prd.json` is saved `ensure_ascii=True`** by the harness — don't fight the
  unicode escaping; write it the same way or let the harness rewrite it.
- **Platform: Windows / PowerShell, CRLF.** `zoneinfo` has no tz database on
  Windows, so `tzdata` is a real runtime dependency.
- **Hooks are wired into interactive sessions too**, so the guard applies to you,
  not just stage agents.
- ★ **Hooks reference the engine by absolute path with a space** in
  `.claude/settings.json` — keep every such path double-quoted.
- ★ **cwd is the project boundary.** Reading the sibling engine repo prompts for
  permission per file unless you launched with `--add-dir` (above).
