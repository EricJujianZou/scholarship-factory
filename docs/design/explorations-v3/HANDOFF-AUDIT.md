# HANDOFF-AUDIT — explorations v3, external orchestrator (audit + redesign 11-20)

You are the orchestrator that generated files 11-20 in
`docs/design/explorations-v3/originals/` (see MANIFEST.md). Those originals
are frozen; do not touch them. Your counterpart already audited and
redesigned 01-10. Now do the same for your ten, and wire the results into
the gallery yourself this time.

Read first, in this order:

1. `docs/design/explorations-v3/AUDIT.md` — findings format and verdict vocabulary from the 01-10 round
2. `docs/design/explorations-v3/REDESIGN-SPEC.md` — the binding spec for every "after" file
3. `docs/design/audience.md` — who this is for; §6 is the disqualifier list
4. `docs/design/repurposing-map.md` — banned patterns and component specs
5. `docs/design/theme-explorations/BRIEF.md` — constitution and text budget
6. `docs/design/theme-explorations/tactile-calm-v2.html` — reference implementation of the required anatomy

The generation round was deliberately blind to this research; this round is
the opposite. Naive design converges on the exact grift patterns this
audience is trained to bounce off (see AUDIT.md's headline result), so
assume your originals contain violations and hunt for them.

## Phase 1 — audit

For each of 11-20: list every violation of audience.md §6,
repurposing-map.md banned patterns, and BRIEF.md budgets. Assign a verdict
from {keep-with-fixes, heavy-rework, theme-fights-audience}. Append ONE
section to AUDIT.md titled `## Verdicts — files 11-20 (external group)`
using the same table format as the 01-10 verdicts.

Standing ruling (already made for 01-10, applies to you): a
theme-fights-audience verdict does NOT mean abandon the costume. Every
theme gets redesigned in-costume. Identity survives; the dishonesty dies.

## Phase 2 — redesign

For each original, produce `redesigns/<same-filename>.html` implementing
REDESIGN-SPEC.md in full: identity rule, kill-on-sight list, required
anatomy items 1-6 with their exact strings (pulse strip, 3-tap eligibility
filter with live count line, closed-rows bridge, UGMI 10 pitch with the
single sanctioned example contact, calm checkout as the quietest block on
the page, footer report line), budgets and floors. Single file, inline
CSS/JS, zero external requests, system fonts, first line
`<!-- INTERNAL DESIGN MOCKUP - sample listing data -->`.

## Phase 3 — gallery

Edit `docs/design/explorations-v3/index.html`: for each theme 11-20 whose
redesign shipped and passed QA, flip its `hasAfter` to `true` in the THEMES
array. Touch nothing else in that file — no restructuring, no new features,
entries 01-10 stay exactly as they are.

## QA gate (run per file before declaring done)

- ends with `</html>`, markup balanced, JS parses and runs
- zero external requests (no http(s) src/href/fetch/@import/url())
- eligibility filter actually filters, count line updates, localStorage persists, zero-state has undo
- no em dashes in visible strings anywhere
- every `hasAfter: true` you set has a matching file in `redesigns/`
- at 390px: no horizontal scroll, H1 within 2 lines, 44px touch targets

## Process constraints

Parallelize subagents at max effort, but AUDIT.md and index.html are shared
files: apply those edits serially from the orchestrator, never from
parallel subagents. Modify nothing outside
`docs/design/explorations-v3/` except reading the docs listed above. Do not
modify `originals/`, files 01-10 in `redesigns/`, MANIFEST.md, SEED.md,
HANDOFF.md, or REDESIGN-SPEC.md.
