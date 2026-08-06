# Component: 3-tap eligibility collapse

## Intent
Stage 3 — the family's biggest build. Simplify's first-run lesson: demo the
collapse on the visitor's own case, in seconds, instead of claiming it in
copy. Turns the paid pitch's core line ("you are eligible for a fraction of
it") into a watched event, and hands stage 2 its script.

## Anatomy
Three tap-only questions above the table (no typing — one-handed IG-webview
use):
1. "I can work in:" [Canada] [US] [both]
2. "Term:" [Summer 2027] [Fall 2026] [Winter 2027] [any]
3. "Location:" [remote ok] [Toronto/GTA] [Vancouver] [anywhere]
On each tap the table collapses live and the result line updates:
"**Showing 43 of 1,427 you're actually eligible for.**"
Answers persist in localStorage; return visits reopen pre-collapsed with a
one-tap "reset" affordance. Client-side JS on the static page — no accounts,
no backend, no data leaves the browser.

## States
- **Untouched (first visit):** full table, questions visible, no default
  selections (a pre-selected filter would be a claim about the visitor).
- **Partially answered:** collapse applies what's known; result line shows
  the current denominator honestly.
- **Zero results:** the critical state — never a dead end. "0 of 1,427 match
  all three — loosen one?" plus one-tap undo of the last answer. A zero with
  no exit is a bounce.
- **Returning visitor:** pre-collapsed + "showing your filters — reset"
  label ("saved in this browser only" on first return, then quiet).
- **Day 40:** counts change weekly with the data; the saved filters make the
  pulse-strip deltas personal ("31 added" → some appear in *their* 43).

## Copy tone
The visitor's own words from the DM intake (work auth, term, location) —
the questions ARE the product's 3 qualifying lines, seen before they're
asked. Real strings above. Never: "personalize your experience", "tell us
about yourself".

## Tokens / dials
Tap targets ≥44px, pill buttons, selected state in the single accent.
The result line is the emotional payload — give it one size step up and
tabular numerals; everything else stays quiet.

## Anti-pattern (named, never ship)
**The fake funnel**: using the taps to gate content, capture data, or delay
the table. The table is visible and complete before any tap; the component
only ever *narrows*, unconditionally reversibly.

## Marketing reuse
Screen-record the collapse for a reel: "1,427 internships. Watch what
happens when I tap 'can work in Canada' + 'Summer 2027'... 43." The DM
script inherits it: "you saw the 43 — I'll get you to the 10, each with a
named contact."
