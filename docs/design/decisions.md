# decisions.md — owner calls on the live site, dated, with rationale

Running log of product decisions shipped to ugmi.ca, and WHY, straight from
the owner. Future agents: these are settled calls, not accidents to fix.
Newest first.

## Standing rules (owner-confirmed 2026-08-06, apply until revoked)

1. **Usage first, always.** Anything standing between a visitor and the
   search box loses, trust copy included. This deliberately overrides the
   earlier "trust anatomy above the fold" instinct from the research docs:
   trust signals may live lower on the page or in the footer, but the fold
   belongs to the product. Do not re-add hero fact panels, method lines,
   or explainer paragraphs above the listings.
2. **The price is $19.29/mo and the digits are deliberate.** Logic: anchor
   under the $20 ceiling, reads teens. Do NOT "correct" it to $19.99,
   $19, or $20 in any copy, mockup, or doc.
3. **Voice: "we" in selling contexts only.** The offer block speaks as
   "we" for credibility. Casual surfaces (DMs, IG, replies) stay "I".
   The solo-builder identity is not dead; it just doesn't run checkout.
4. **CTA case: title case, everything capitalized except "in".**
   "Invest in Your Next Internship". Owner-specified pattern; do not
   sentence-case it.
5. **Claim boundary (refines never-fabricate).** Listing data, counts,
   stats, and social proof must remain real and auditable, no exceptions.
   Directional rhetoric in sell copy ("save you 10 hours of
   mass-applying") is accepted marketing hyperbole, owner-approved, and
   is not a data claim. Keep the two categories separate: if a number
   describes THE PRODUCT or THE DATA, it must be true; if it dramatizes
   THE PAIN, plausible rhetoric is allowed.

## 2026-08-06 — Price is now $19.29/mo (was $15/mo)

Owner call. Anchoring: stays under $20, reads as teens. Displayed price,
docs, and future mockups read $19.29/mo.

**Open follow-up: verify the Stripe payment link amount matches.** The
page's CTA points at the original payment link. Whether it still charges
$15 is only visible in the Stripe dashboard (the public page loads price
client-side; agents cannot verify it by fetching). Stripe payment links
keep their URL when edited, so if the owner already updated the line item,
nothing needs swapping. UNVERIFIED as of this entry.

## 2026-08-06 — Offer copy reframed from curation to time + access

Old pitch led with the mechanism ("send resume, get matched shortlist
weekly"). First ICP-adjacent feedback (see feedback.md, Parmigiano) showed
readers priced it as "10 recommendations vs free Ctrl-F" and walked. The
actual differentiator (contacts + outreach that beats the ATS) never
landed. New pitch leads with the cost of the alternative.

Shipped offer block:

- Hook: "We can save you 10 hours of mass-applying to jobs with 0
  interviews. How much is your time worth?" (rhetorical, directional; not
  a measured number, see standing rule 5)
- "What's included:" 1) Personalized contacts per job, get out of the ATS.
  2) Step-by-step outreach template + playbook + coffee chat + follow-up
  guide. 3) Resume review from a coach who spoke to recruiters from
  Apple & Nvidia.
- CTA label: "Invest in Your Next Internship" (was "Get your list ($15/mo)").

**The coach in item 3 is the owner himself.** He has spoken to Apple and
Nvidia recruiters directly. The claim is auditable; keep it accurate to
whoever actually delivers reviews if that ever changes.

## 2026-08-06 — Clutter purge (the "usage first" pass)

All owner calls, same session, rationale per item:

- Hero gradient wash: removed. Rendered as a hard-edged purple/green
  rectangle; decorative backgrounds that read as boxes are bugs.
- "Also in here" lede + hero facts card + "Facts are extracted" method
  line: removed. Standing rule 1; the count survives in the search bar
  readout, sources survive in the footer.
- "Saved on this device only" note: removed. Same rule.
- Native select arrow on the sort control: removed (appearance:none). It
  crowded the pill border; looked broken.
- Stripe handoff line ("You'll be taken to Stripe to pay"): removed.
  Calm-checkout copy lost to the clutter rule.
- "Not sure what to say? Copy this" DM message box: removed. Reason:
  visual clutter in the buy column, NOT a funnel decision. The DM link
  itself stays. The copy-message pattern is not banned; it just can't
  bloat the buy column.
- Footer "Built by one Waterloo student" credit: removed. Ties to the
  voice rule: the selling surface speaks as "we" now, and the solo-builder
  blemish line was part of the retired "I" framing on this page.

## 2026-08-06 — Live design is soft-premium, listings first

Theme 01 (soft-premium, post-audit redesign skin) spliced over the live
site's real data and search core. Listings board sits directly under a
one-line hero. Chosen after first outside feedback picked 01 (and 18) and
called the rest "corny"; owner had independently favored the same
direction. The 20-theme gallery stays on the test branch (test.ugmi.ca)
for continued friend/ICP review.

Parallel session, same day (context for the git log): purple wordmark
logo + favicon, 63 retired regional-scraper rows dropped, recommended
sort default (Canada > marquee orgs > remote, then deadline), retired
scrapers removed from footer sources.
