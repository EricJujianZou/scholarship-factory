# HANDOFF — explorations v3, external orchestrator (10 originals)

You are one of two orchestrators generating naive design explorations for
ugmi.ca in this repo. Your counterpart (Claude) is producing files 01-10;
you own 11-20.

Read exactly ONE file: `docs/design/explorations-v3/SEED.md`. Do NOT read
anything else under `docs/design/` — this is a naive-generation experiment
and the audience research there would contaminate it. An audit against
that research happens downstream, not by you.

Deliverables: 10 single-file HTMLs in `docs/design/explorations-v3/originals/`,
named `11-<slug>.html` through `20-<slug>.html`. Each is a complete landing
page satisfying SEED.md's hard requirements, and each is a distinct visual
and UX world — different layout logic, not just different colors. Diversity
beats audience-fit; a few deliberately wrong-for-the-audience directions
are welcome. These slugs are taken by your counterpart, avoid their
territory: soft-premium, bank-calm, playful-arcade, notion-doc,
vaporwave-night, campus-poster, ios-native, newspaper-classified,
map-dashboard, luxury-fashion.

Parallelize across your subagents at max effort. Internet research for
design reference is allowed, read-only; download nothing, install nothing;
finished files keep zero external requests (SEED.md rule). Ship complete
files only: no truncation, balanced markup, any JS actually runs.

When done, append to `docs/design/explorations-v3/originals/MANIFEST.md`:
one line per file — `NN-slug — one-sentence design intent`. Touch nothing
else: `index.html` (the gallery) is maintained by your counterpart and
picks up your files afterward.
