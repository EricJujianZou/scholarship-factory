# decisions.md — owner calls on the live site, dated

Running log of product decisions shipped to ugmi.ca. Newest first.

## 2026-08-06 — Price is now $19.29/mo (was $15/mo)

Owner call, set during the post-launch iteration session. Displayed price,
docs, and any future mockups should read $19.29/mo.

**Open follow-up: the Stripe payment link on the page still charges $15.**
A new payment link at $19.29 needs to be created in the Stripe dashboard
and swapped into the checkout CTA href. Until then, checkout undercharges.

## 2026-08-06 — Offer copy reframed from curation to time + access

Old pitch (shipped with the Highlighter design) led with the mechanism:
"send resume, get matched shortlist weekly + contact + template." First ICP-adjacent
feedback (see feedback.md, Parmigiano) showed readers priced it as "10
recommendations vs free Ctrl-F" and walked.

New offer block:

- Hook: "We can save you 10 hours of mass-applying to jobs with 0
  interviews. How much is your time worth?"
- "What's included:" 1) Personalized contacts per job, get out of the ATS.
  2) Proven referral outreach template. 3) Resume review from a coach who
  spoke to recruiters from Apple & Nvidia.
- CTA label: "Invest in your Next Internship" (was "Get your list ($15/mo)").

Removed in the same pass: the Stripe handoff line, the "Not sure what to
say?" DM message box, the footer builder credit line, the "saved on this
device" note, the hero facts card, the "Also in here" lede, the hero
gradient wash, and the native select arrow on the sort control.

Note for future audits: the resume-review claim (item 3) references a
specific coach credential. Owner-supplied; keep it accurate to whoever is
actually doing the reviews.

## 2026-08-06 — Live design is soft-premium, listings first

Theme 01 (soft-premium, post-audit redesign skin) spliced over the live
site's real data and search core. Listings board sits directly under a
one-line hero. Deployed from master; the 20-theme gallery stays on the
test branch (test.ugmi.ca).
