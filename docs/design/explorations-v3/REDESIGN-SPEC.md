# REDESIGN-SPEC — explorations v3 "after" files

Applies to every file in `redesigns/`. Goal: same visual world as the
original, dishonesty and clutter removed, trust anatomy installed.

## Identity rule

Keep the original theme recognizable at a glance: palette, type character,
texture, signature layout moves. You are fixing the product truth inside the
costume, not swapping costumes.

## Kill on sight (from audience.md §6 + repurposing-map.md)

- Fake liveness: animated counters, LIVE badges, tickers, invented
  timestamps, sparkline trends, fake publication history. Every number is a
  build-time fact.
- Red or urgency theatrics anywhere near listings or money. Deadline ramps
  use a warm amber, never red.
- Invented social proof: contact names (except the one sanctioned example
  below), member counts, testimonials, tab-counters, KPI deltas.
- Blur/veil/"upon request" obfuscation of anything, especially price.
- Any form before value: no name/email/programme fields anywhere. The one
  email field allowed is the optional Monday-email block AFTER checkout.
- Em dashes in visible strings. Use commas, periods, middle dots.
- Marketese: unlock, upgrade, level up, supercharge.

## Required anatomy (reference implementation: ../theme-explorations/tactile-calm-v2.html)

1. Pulse strip near the top, themed to taste, content fixed:
   "Last checked Wed Aug 6, 7:04am ET · 1,427 open · 31 added this week ·
   23 closed this week · hand-checked, never invented"
2. 3-tap eligibility filter (Work in / Term / Location pills), live-filters
   the sample rows, result line "Showing N of 1,427 you're actually
   eligible for." (scale sample proportion to 1,427), zero-state with undo,
   localStorage persistence.
3. Listings include 1-2 greyed "Closed" rows; the line "23 internships
   closed in the last 7 days." bridges into the paid pitch.
4. Paid pitch: "The UGMI 10", lede "10 per week, each with a named contact.
   I read the 1,427 so you read 10.", ONE example pick labeled as example
   ("PitchBook, Software Engineering Intern · Toronto · $38/hr CAD · closes
   Fri · contact: Sarah Chen, campus recruiting" + why-line). This is the
   only named contact allowed on the page.
5. Calm checkout, the quietest block on the page in every theme: fee grid
   (You get / Monthly $15 CAD / Sign-up fee $0 / Cancellation anytime from
   Stripe receipt email / Card handled by Stripe), "You'll be taken to
   Stripe to pay.", ONE CTA labeled "Get my first list" (same label
   everywhere), blemish line "I'm one Waterloo student, not a company."
   No motion within a viewport of it.
6. Footer: "Dead link? Wrong deadline? DM @sleppyeric, fixed within a day."

## Budgets and floors

- Page prose outside listing data: under ~150 words. Heading + max one
  sentence per section. Numbers as data (grids/chips), not sentences.
- Hero: H1 ≤2 lines at 390px, one sub-line, first listing at/near the fold.
- WCAG AA contrast, 44px touch targets, visible focus, reduced-motion
  honored, no horizontal scroll at 390px.
- Single file, inline CSS/JS, zero external requests, system fonts, first
  line `<!-- INTERNAL DESIGN MOCKUP - sample listing data -->`.
- Ship complete: balanced markup, JS parses and runs.
