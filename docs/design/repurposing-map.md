# UGMI Repurposing Map (audience-hook-research phase 4)

Synthesized 2026-08-06 from hook-teardowns.md. Every adopted mechanism names
the funnel stage it serves; mechanisms serving no stage are cut, in writing.
Component column links to the phase-5 spec in `components/`.

Funnel stages: (1) IG reel, (2) DM, (3) free-site first visit, (4) return
visits, (5) Stripe conversion, (6) weekly retention/renewal.

## The page law (from Family 3, governs everything below)

**Every claim gets a number, a date, or a link — and the page around those
claims stays quiet.** The audience's grift detector keys on arousal;
calm-plus-precision is what it cannot pattern-match to a scam. Corollary
(Family 4): every displayed number must be a fact someone can audit.

## Adopted mechanisms

| Stage | Mechanism (source) | Translation | Component |
|---|---|---|---|
| 3, 4 | Heartbeat header (GitHub lists) + labor illusion (Simplify) + timestamp provenance (levels.fyi) | Build-time pulse strip above the table: last-checked minute, open count, added/closed deltas, "never invented" clause | `pulse-strip.md` |
| 3, 4 | Age column / decay clock (GitHub lists) + unrounded numbers (levels.fyi) | "Added" relative age + "closes in 3d" deadline clocks + NEW chips, all build-time | `age-deadline-clocks.md` |
| 3, 5 | Lock-don't-delete (vanshb03/Simplify) | Closed rows greyed 7 days then swept; "23 closed in the last 7 days" line feeding the paid pitch | `visible-closings.md` |
| 3 | First-run demo on own task (Simplify) + decomposed claim (levels.fyi) | 3-tap eligibility collapse: "Showing 43 of 1,427 you're eligible for", localStorage-persisted. **Biggest build.** | `eligibility-collapse.md` |
| 5 | Institutional calm + zero-stated pricing + borrowed trust (Wealthsimple) + decomposed offer (levels.fyi) + free-core firewall (NeetCode) | The calmest block on the page: fee grid with zeros, cancel *mechanism* named, Stripe blemish line, $15/mo CAD | `calm-checkout.md` |
| 6, 5 | Bounded drop (Wordle) + voiced email + tiny ask (Duolingo) + curator receipts + labor receipt (NeetCode/Simplify) + sender streak + share grid + stats mirror | "The UGMI 10": Monday drop, checklist 0/10, "why this one" per pick, week-N streak, `applied 6/10` share row, monthly wrapped | `ugmi-10-weekly.md` |
| 2 | Human tollgate (vs ManyChat) + /start self-segmentation (SpeedyApply) + verbatim price grid (Wealthsimple) | The DM playbook: visibly-human reply, unconditional link delivery, 3-line intake ritual, batched sessions | `dm-playbook.md` |
| 1→3 | Frame-one contract + scent continuity (Reels) + subtractive framing (NeetCode) + effort receipt (Simplify) | Hook bank with real DB numbers; hard rule: no hook ships unless its phrase appears in the DM template AND the landing first viewport | `hook-scent-rule.md` |
| 3, 4 | Report-a-corpse loop (GitHub lists) + give-to-get (levels.fyi) | Footer line: "Dead link? Wrong deadline? DM @sleppyeric — fixed within a day" | folded into `pulse-strip.md` |
| 4 | Mid-week ping (Discord, adapted) | IG broadcast channel as #intern-alerts: 2-3 "just added" posts mid-week; retargeting pool for the paid pitch | operational, no site component — noted in `dm-playbook.md` |

## Standing rules adopted (not components — constitutions)

1. **The free DB never shrinks, never gates, never nags** (NeetCode/Simplify
   free-core; audience.md marks it load-bearing). Paid sells labor and
   personalization, never data access.
2. **Build cadence is a product feature** (Family 1): freshness labels must
   never outlive their truth → daily scheduled rebuild is a prerequisite for
   pulse-strip, age clocks, and closings. If the rebuild is weekly, the labels
   must say week-granularity. No exceptions.
3. **Effort deltas only, never outcome deltas** ("I read 212 postings" yes;
   "hear back 25% more" banned — unverifiable, trips grift radar, violates
   our claims-audit discipline).
4. **No arousal near money**: no countdown timers, no red, no exclamation
   marks, nothing animated within a viewport of the Stripe button.
5. **The count is the brand**: exactly 10 in the weekly list, even when 11
   are good. The constraint is the product.

## Cut list (considered, rejected, with reasons)

- **NeetCode's dependency tree** — applications have no prerequisite
  structure; a tree would be decoration. Kept the fractions, cut the tree.
- **ManyChat / DM automation** — forfeits the visibly-human differentiator
  that is our main trust asset at current scale. Revisit only when volume
  forces it; the interim scale valve is a pinned comment with the raw link.
- **Duolingo's guilt mechanics** — the voice transfers, the guilt doesn't;
  guilt-tripping an anxious student about applications punches down at the
  anxiety they're paying to reduce.
- **Wordle's streak-zeroing cliff** — Duolingo's cushion instead: paused,
  never reset.
- **On-site streaks/counters of any kind** — no client state that survives;
  any number the static site can't compute at build time would be fake.
- **"Submit to unlock" gates (levels.fyi)** — manufactured scarcity of
  already-collected data; also needs accounts.
- **Member counts / testimonial walls / activity toasts** — no honest numbers
  yet; fabricating any is fatal. The site's credibility engine is the data
  pulse, not the crowd, until real numbers exist.
- **Simplify's outcome-delta claim shape** — see standing rule 3.
- **Betting/prediction-app stake mechanics** — cut at inventory stage,
  confirmed cut here.

## What this map asks of the owner (walkthrough decision points)

1. **Daily rebuild commitment** — the freshness family is conditional on it
   (standing rule 2). Without it, adopt week-granularity labels instead.
2. **"The UGMI 10" naming** — the count-as-brand move. Approve/rename.
3. **Visual direction shift** — Family 3 (W1) implies moving the site toward
   bone-background institutional calm; current system is "Light Marketplace".
   This is a taste call: adopt, blend, or keep.
4. **The 3-tap eligibility collapse** — the one real build (client-side JS +
   localStorage on the static page). Prioritize or defer.
5. **IG broadcast channel** — operational commitment (2-3 posts mid-week).
