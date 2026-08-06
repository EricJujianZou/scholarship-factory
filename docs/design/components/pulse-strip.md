# Component: Pulse strip

## Intent
Stages 3–4. Answers "is this list even alive?" before any row is trusted —
the heartbeat-header mechanism (GitHub lists) + labor illusion (Simplify) +
timestamp provenance (levels.fyi). Highest-leverage single element for a
static site: aliveness without a backend.

## Anatomy
One line directly above the listings table, build-time rendered. Slots, in
order (fixed):
1. Last-checked stamp, exact minute: "Last checked Mon Aug 6, 7:04am ET"
2. Open count: "1,412 open"
3. Week deltas: "31 added · 23 closed this week"
4. Provenance clause: "hand-checked, never invented"
Separator: middle dot. On phone width the strip wraps to two lines max;
deltas never drop (they're the aliveness signal — drop the totals first).
Directly below or in the footer, the report loop: "Dead link? Wrong deadline?
DM @sleppyeric — fixed within a day."

Data source: diff of the current build against the previous build's persisted
JSON snapshot. All numbers computed, none typed.

## States
- **Normal:** as above.
- **Quiet week (deltas near zero):** show the truth ("2 added · 1 closed") —
  small honest numbers beat hidden ones; the stamp still proves the check ran.
- **Stale build (rebuild missed):** the stamp shows its real date. Never
  advance it without a run. If cadence becomes weekly, the strip must say
  "checked weekly" — labels never outlive their truth.
- **Day 40:** identical. The strip's value compounds with return visits — a
  returning viewer who sees the deltas change has watched the site breathe.

## Copy tone
Plain, computed, zero adjectives. Real strings:
- "Last checked Mon Aug 6, 7:04am ET · 1,412 open · 31 added · 23 closed this week · hand-checked, never invented"
- "Dead link? Wrong deadline? DM @sleppyeric — fixed within a day."
Never: "updated in real-time!", "always fresh", any claim without a number.

## Tokens / dials
design-core read: Persuade × B2C × unknown-brand trust floor → calm.
Small text (13–14px), muted foreground, no background band, no icon. It
should read as chrome, not a banner. Monospace or tabular numerals for the
figures.

## Anti-pattern (named, never ship)
**The fake pulse**: a "last updated" stamp that advances without the data
updating, or a "live" badge on a static page. One caught lie kills the
"never invented" positioning permanently.

## Marketing reuse
The weekly deltas are reel material verbatim: "23 internships closed this
week — here's what's still open." The strip is also a screenshot-able proof
artifact for DMs.
