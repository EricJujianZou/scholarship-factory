# value-prop-pass.md — the offer-section redesign

Requested by the owner 2026-08-07 after the first watch session. Problem
first, then the proposed redesign, then the three approved directions
whose UI positioning is still open. The redesign ships as a MOCKUP for
owner review (`docs/design/offer-redesign-mockup.html`), not straight to
prod.

## The problem

Seven symptoms from the watch session (plus the earlier Parmigiano
feedback), one root cause.

1. "Get recruiter contact" leads to a paywall the reader didn't expect.
   The click reads as a feature, lands as a pitch; the user never
   connected it to the "named contact per job" tile (he didn't see the
   tile at all until it was pointed out).
2. Personalization is unclear. A reader can't say how the paid list
   differs from clicking a few filter chips on the free board.
3. "Contact" reads as a promised reply. The user's stated fear: pay $20,
   send the message, get silence, feel scammed.
4. The $19.29 ask carries no probability argument. Nothing on the page
   says WHY this path is likelier to produce interviews than the pile.
5. The recruiter quotes sit below the tiles as a self-contained carousel:
   evidence detached from the claim it proves. The "Don't spray and
   pray" card, the strongest bridge to the paid CTA, doesn't touch it.
6. The free template's looks poison the association: if the free thing
   looks half-done, the paid thing inherits the smell. (Template CONTENT
   rework is a separate later task; the visual is the urgent part.)
7. "If the free version isn't as good as Simplify or Indeed, why pay?"
   Decision on file: don't chase breadth parity; the free tier owes
   credibility, not parity, and its edge is the niche (Canadian co-op
   depth, term filters, first-year facet = HANDOFF Task 2).

**Root cause: the offer block lists deliverables but never argues the
case.** The reader is left to derive "referral beats the pile" on their
own, and the deliverables read as items, not as a system that changes
their odds.

## Proposed redesign

One narrative spine, top to bottom: **pain, mechanism, proof, risk
removal, price.**

1. **Pain** (the pile is rigged): the six-seconds and 20%-reviewed
   quotes move inline here as evidence under the claim, not a carousel
   aside.
2. **Mechanism** (referral goes around the pile): the attributed stat —
   referred candidates are **7x more likely to be hired** (Pinpoint,
   analysis of 4.5M applications; the "up to 10x" variant is Zippia's
   2%-of-applicants-11%-of-hires) — plus the campus recruiter's "apply,
   then email" quote sitting right next to it.
3. **Proof** (a person who walked this path): the owner's own story,
   3/3 return offers using this exact playbook, first person. Pairs
   with the existing coach line (interviewed recruiters at Apple and
   NVIDIA).
4. **Deliverables reframed as a system**: named contact per job, the
   outreach message already written, follow-up cadence, coffee-chat
   playbook. This is also the honest answer to symptom 3: we never
   promise replies; we promise the system that maximizes them.
5. **Risk removal**: the land-an-interview-get-the-month-refunded
   promise moves up next to the CTA instead of living as a footnote.
6. **Personalization contrast** (symptom 2): filters narrow the same
   public list anyone sees; the paid list is matched to your resume,
   work authorization, and term, and carries the access layer no filter
   can produce.
7. **Free template restyled** to the page's production quality so the
   association helps instead of hurts.
8. Quotes not used inline (WSP, EQ Bank leftovers) stay as a small
   strip; easier scroll on mobile, static stack on desktop.

## Approved directions, UI positioning TBD (owner, 2026-08-07)

1. **Referral pill.** Rename the per-card "Get recruiter contact" CTA to
   "Referral" with a star/Pro marker. Honest premium signaling: the
   reader knows it's the paid thing before clicking; fewer clicks,
   better clicks, no bait feeling.
2. **Free contact trial.** Owner floated 3 free credits; recommendation
   on file is **1 free referral contact, fulfilled by DM** ("Your first
   referral contact is free. DM me the job."). Zero build, no credit
   infrastructure (there is no contacts DB; every contact is manual
   concierge work), and it routes through the DM, which is the sales
   conversation by design. It also answers "will I actually get the
   contact?" with evidence instead of copy. Count is the owner's call.
3. **The referral odds message.** Sourced versions only:
   - Safe headline: "Referred candidates are 7x more likely to be
     hired" — Pinpoint, 4.5M applications analyzed.
   - Aggressive variant: "up to 10x" — Zippia (referrals are 2% of
     applicants, 11% of hires). Must carry attribution.
   - Never an unattributed "10x!!" — that is the invented-stat slop the
     page has avoided so far (standing rule 5).

## Claim-boundary notes for whoever builds this

- External stats always attributed, never presented as UGMI data.
- The owner's story is HIS outcome ("this is what I did"), never a
  promised outcome ("you'll get interviews").
- Never promise that a contact will reply.
- "posted Xd ago" ships only when the row carries a real posted date
  (HANDOFF Task 3); until then the accurate word is "added".

## Status

- **Implemented 2026-08-07** directly in `ugmi.ca/index.html` (local commit
  only, NOT pushed — push = deploy; owner said "stay local for now"). No
  separate mockup file: the owner's go came with the implement instruction,
  so the local working copy is the review artifact.
- Placement calls made in the build:
  - All five quotes landed inline, so no leftover strip was needed: WSP +
    Dover/Lyft under the pain claim, EQ Bank + Input Club under the
    mechanism claim, and Elio's "Don't spray and pray" moved into the buy
    column directly above the price, touching the CTA (symptom 5).
  - The carousel and its JS/CSS are deleted.
  - Referral pill (direction 1) shipped as "✦ Referral" — the ✦ is the
    page's existing paid-feature glyph (Personalize chip), teal kept.
    aria-label says "part of the paid plan."
  - The odds message (direction 3) shipped in its safe form only: "7x more
    likely to be hired," cited "Pinpoint, analysis of 4.5 million
    applications."
  - Free contact trial (direction 2) NOT shipped — count and positioning
    still the owner's call.
  - Proof beat is first person and now names the owner ("I'm Eric. I went
    3 for 3 on return offers…"), which also serves the real-person trust
    signal; the Apple/NVIDIA coach line sits in the same beat, so the
    resume-review tile caption no longer repeats the brandchips.
  - Refund moved above the checkout button; one line added beyond the doc:
    "Checkout happens on Stripe. We never see your card." (Baymard:
    security reassurance belongs adjacent to the payment action.)
  - Free template restyled: body font on white, bold subject line,
    `{placeholders}` highlighted as accent chips. Text content is
    byte-identical so the copy button copies exactly what it did before.
- Sources for the stats: pinpointhq.com (7x, 4.5M applications),
  zippia.com/advice/employee-referral-statistics (2% → 11%).

## Round 2 — owner live-feedback pass (2026-08-07, same day)

Owner watched the implemented page and redirected. All shipped locally:

- **Quotes reversed course**: out of the offer section entirely (including
  Elio from the buy column), into a purple-themed scrollable card strip
  between the hero and the search bar. Drag-scrub like the chip row, no
  wheel hijack (it sits in page flow).
- **Offer top**: h2 is now "Stop mass applying, start landing
  referral-based interviews"; the light-purple 7x component sits directly
  under it and carries "We'll save you more than $20 of applying." on its
  own line (replaces the "save you 10 hours" sub).
- **"It's the playbook I used myself" beat removed** (the 3/3 proof story
  is off the page for now). Coach + Apple/NVIDIA chips went back to the
  resume-review tile.
- **⚠ Attribution removed from the 7x stat by owner instruction.** This
  leaves the stat unattributed on the page, in tension with standing
  rule 5 / the claim-boundary note ("external stats always attributed").
  Flagged to the owner at implementation time; rule stands for future
  copy, owner override recorded here.
- **Card typography**: exactly three sizes (1.1rem org / .9rem title /
  .8rem everything incl. buttons); org name de-bolded to 600, title 400;
  site header de-bolded (brand 600, nav 500).
- **Metadata unified into plain pills** (white bg, ink text, weight 400,
  no color coding): term, location, degrees, sponsorship (amber dropped),
  salary, "closes in Xd", "added Xd ago". The green "added" chip, the
  red closes-in tags, and the green salary pill are gone.
- **Salary display**: `fmtPay()` in index.html keeps only the first
  currency variant and renders bare $number + period ("$3,850/week",
  "$6K-$8K/month"). Underlying data untouched.
- **Deadline strings**: parseable `deadline` dates now render as the same
  "closes in Xd" pill as `due`; unparseable ones ("11:59pm PT on July
  26") fall back to "closes <text>".
