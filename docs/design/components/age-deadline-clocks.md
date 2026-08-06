# Component: Age & deadline clocks

## Intent
Stages 3–4. Freshness-as-urgency at row level: the GitHub lists' Age column
(recency = race position) pointed at both ends of a listing's life — when it
appeared and when it closes. Plus levels.fyi's unrounded-number rule applied
to time.

## Anatomy
Per listing row/card, two time fields:
1. **Added** — relative age at build time: "today", "1d", "4d", capping at
   "2w+" (beyond that freshness stops selling). Rows ≤3 days old get a small
   "NEW" chip inline next to the role name (phone width may not fit a full
   column; the chip survives).
2. **Closes** — for deadlines under 14 days out, render "closes in 3d"
   instead of the date; ≥14 days keeps the plain date. Color ramp: neutral →
   warm at ≤7d. Never red (no arousal near money — Family 3).
Default sort stays soonest-deadline; the Added field rewards the scan, the
Closes field rewards the decision.

## States
- **Fresh row:** NEW chip + "today".
- **Closing row:** "closes in 2d" in the warm step.
- **Both:** allowed; that's the highest-urgency honest state.
- **No deadline known:** show "no deadline listed" — never invent one, never
  leave blank (blank reads as broken).
- **Day 40:** ages tick up daily with the rebuild; a frozen "2d" that stays
  "2d" across visits is the failure mode — see anti-pattern.

## Copy tone
Data, not exhortation. "closes in 3d" — never "HURRY", "closing soon!", or
countdown timers with seconds. Real strings: "today", "3d", "closes in 5d",
"no deadline listed".

## Tokens / dials
Tabular numerals. NEW chip: one small solid chip in the page's single accent
color, 11–12px caps — the only place the accent appears in a row. Warm ramp
for deadlines uses a desaturated amber, not red.

## Anti-pattern (named, never ship)
**The immortal NEW badge**: any freshness label older than its truth. All
values must be computed at build time; if the rebuild doesn't run, the site
must not pretend it did.

## Marketing reuse
"12 close in the next 5 days" is a hook-bank number (Family 4, 3.1) and a
mid-week IG broadcast line.
