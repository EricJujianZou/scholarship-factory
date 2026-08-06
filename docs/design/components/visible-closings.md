# Component: Visible closings

## Intent
Stages 3 and 5. Loss aversion made concrete (vanshb03's in-place 🔒 +
Simplify's swept-but-counted closed roles): proof that windows close, which
is the free site's strongest argument for the paid list.

## Anatomy
1. **Row treatment:** when a deadline passes, the listing stays in the table
   for 7 days — greyed (reduced contrast, not struck through), apply link
   replaced with the word "Closed". After 7 days, swept out of the page.
2. **The counter line:** above the table (adjacent to or inside the pulse
   strip): "**23 internships closed in the last 7 days.**" Computed from
   build snapshots.
3. **The bridge:** in the paid-pitch section, the same number returns as the
   reason the product exists: "The weekly list exists so you hear about
   things before they join that number."

## States
- **Recently closed (≤7d):** greyed row, "Closed" label, still scannable —
  the corpse does the persuading.
- **Swept (>7d):** gone. No archive page (that's maintenance surface without
  a funnel stage).
- **Zero closings this week:** show "0 closed this week" — an honest quiet
  week; do not hide the line (its disappearance and reappearance reads as
  manipulation).
- **Day 40:** the counter is different every week because it's real; that
  variance is the feature.

## Copy tone
Facts that happen to motivate. Real strings:
- "23 internships closed in the last 7 days."
- "Closed" (row label — the word, not just a lock emoji; costs nothing,
  reads clearer through the grift-radar)
Never: "You missed these!", "Don't let this happen to you" — the data does
the guilt-free version of that sentence by existing.

## Tokens / dials
Greyed rows: drop foreground to ~50% contrast against the page, keep layout
identical (no collapse — the row's shape is part of the proof). Counter line
in the same quiet style as the pulse strip; the number may be tabular-bold.

## Anti-pattern (named, never ship)
**The inflated graveyard**: padding the closed count with duplicates,
re-listings, or postings we never showed while open. The number must
reconcile against what a returning visitor saw last week.

## Marketing reuse
The weekly closings number is the strongest recurring reel stat ("23 closed
this week — here's what's still open") and the natural DM follow-up to
anyone who commented on a listing that has since closed.
