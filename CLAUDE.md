# CLAUDE.md

Loaded every session — keep it short; it's a **router**, not a container. Deep
context lives in the linked docs below, read only when its task comes up.

**This repo:** `scholarship-factory` — an agentic opportunity-sourcing system,
**built by** the agentic-sdlc harness. What it is and why → `REPO_CONTENT.md`.

## Where to look (read on demand)

| When you're… | Read |
|---|---|
| Understanding the product (direction, UX, requirements, decisions) | `REPO_CONTENT.md` |
| Wondering how this repo gets built (tickets, branches, hooks, the engine) | `HARNESS.md` |
| Working with GitHub (issues, PRs) or other env gotchas | `notes_for_claude.md` |
| In a **system-design / pair-design session** with the owner | `mentor.md` *(temporary; deleted when design settles)* |
| Needing engine internals | the sibling `agentic-sdlc` repo — see `HARNESS.md` → *Reaching the engine* |

Live state (current ticket, what's merged) is in `prd.json` + `git log`, not in
these docs.

---

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
