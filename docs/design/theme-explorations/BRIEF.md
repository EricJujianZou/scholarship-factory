# Theme exploration brief (shared by all variants)

Internal design mockups for the owner's taste decision. Each variant is ONE
self-contained HTML file in this directory. Same content and components in
all; only the visual world differs.

## Hard requirements

- **Single file**, inline CSS + JS. **Zero external requests** (no CDN, no
  webfonts, no remote images) — must render offline via file://. Use system
  font stacks that approximate the theme; note the intended production
  webfont in an HTML comment at the top.
- **Mobile-first at 390px** (IG in-app browser is the primary arrival), then
  desktop. No horizontal scroll at any width; the table/cards must work
  one-handed on a phone.
- File starts with `<!-- INTERNAL DESIGN MOCKUP - sample listing data -->`.

## Content (identical across variants — real product facts)

- Title/H1: "Every internship we can find, in one searchable list."
- Facts: 1,427 listings · free, no account, no email · also 11 fellowships,
  7 scholarships, 3 competitions, 3 grants, 1 award · $15/mo CAD paid tier ·
  resume + 3 lines onboarding · first list within 48 hours · built by one
  Waterloo student ("tired of 40 tabs") · IG @sleppyeric · Stripe payment.
- ~14 sample listing rows: realistic Canadian-skewed internships (company,
  role, location, pay in CAD where shown, deadline, added-age). Sample data
  is fine in a mockup; keep it plausible.

## Components to integrate (specs in ../components/)

1. **Pulse strip** (pulse-strip.md): "Last checked Wed Aug 6, 7:04am ET ·
   1,427 open · 31 added this week · 23 closed this week · hand-checked,
   never invented" + footer report line "Dead link? Wrong deadline? DM
   @sleppyeric - fixed within a day."
2. **Age & deadline clocks** (age-deadline-clocks.md): "Added" relative ages,
   NEW chip on ≤3d rows, "closes in 3d" with warm (never red) ramp.
3. **Visible closings** (visible-closings.md): 1-2 greyed "Closed" rows in
   the sample + the "23 internships closed in the last 7 days." line
   bridging to the paid pitch.
4. **3-tap eligibility collapse** (eligibility-collapse.md): FUNCTIONAL
   client-side — three tap-pill questions, live-filtering the sample rows,
   result line "Showing N of 1,427 you're actually eligible for."
   localStorage persistence + reset. Zero-results state included.
5. **The UGMI 10 pitch** (ugmi-10-weekly.md intent only): paid section
   selling the weekly 10 — "10 per week, each with a named contact. I read
   the 1,427 so you read 10." Include one example pick with its
   "why this one" line as a visual sample (labeled as example).
6. **Calm checkout** (calm-checkout.md): decomposed offer, fee grid with the
   zeros, cancel mechanism named, "You'll be taken to Stripe to pay.", one
   button "Get my first list", first-person blemish line. THE CALMEST BLOCK
   ON THE PAGE in every theme — even loud themes go quiet here. No motion
   within a viewport of it.

## Page constitution (from ../repurposing-map.md — applies to every theme)

- Every claim gets a number, a date, or a link; the page stays quiet.
- No arousal near money: no countdowns, no red near the checkout, no
  exclamation marks, nothing animated near the Stripe button.
- NO invented social proof: no member counts, no testimonials, no star
  ratings, no logo walls. The data pulse is the credibility engine.
- No em-dashes in any visible string (use commas, periods, or middle dots).
- Max 1 eyebrow-style label per 3 sections; no section numbers.
- One CTA intent for the paid product, one label, repeated not varied.
- Hero fits the first viewport: H1 ≤2 lines at 390px, one sub-line, the
  free-list proof starts within the first scroll.
- WCAG AA contrast everywhere; visible focus states; 44px touch targets;
  `min-h-[100dvh]`-equivalent (never 100vh) if full-height is used.
- Copy voice: one real person, plain and specific. No "unlock", no
  "supercharge", no marketese.

## Section order (all variants)

1. Hero: H1 + one-line sub (free, no account, no email) + pulse strip
2. Eligibility collapse pills
3. The table/cards (sample rows incl. closed examples)
4. Closings line → paid pitch (the UGMI 10)
5. Calm checkout
6. About/blemish ("one Waterloo student...") + footer (report line, IG)

## V2 synthesis (owner review, Aug 6 2026) — `tactile-calm-v2.html`

Owner's taste call: tactile + calm merged; **data-brutal vetoed permanently,
terminal-dark vetoed** (black/gray/white reads depressing, accent too late).
V2 deltas against this brief:

- Hero and filter sections compressed hard; first card lands at/near the
  first 390px fold. Filters are three tight label+pill rows; once answered
  they echo into a sticky summary bar over the list (count + edit + reset).
- Cards over table (owner call: more inviting). Card = tactile press
  grammar on calm's bone paper; serif kept for blemish/about only.
- **The contact wedge**: every open card carries "who to contact" next to
  Apply. It opens a sheet with the referral pitch, one real free sample
  pick (contact visible, weekly, for everyone), two cited stats, and the
  single paid CTA. The Apply link itself is never intercepted or gated.
- Stats are real, scoped, linked, and never derived into outcome promises:
  NY Fed (Brown/Setren/Topa): referrals 6% of applications / 27% of offers,
  job boards 60% / 24%. Handshake: 2025 sent 24% more applications than
  2024. Banned: "our plan cuts X to Y" / "saves you N hours" arithmetic.
- Free block after checkout ("Free either way"): the outreach template
  on-page + copy button, ungated (email-gating it would regress the
  "no email" trust copy), and the Monday email signup as the decline path
  (what opened/closed + the week's free pick, one email, one-click out).
- One paid CTA intent page-wide ("Get my first list"), reachable from the
  pitch, the checkout, and the contact sheet.
- Analytics hooks stubbed as `track()` events: filter_answered,
  apply_click, contact_open, sheet_cta_click, template_copy, email_submit.
  See `../analytics-plan.md`. (Owner: design first, analytics later.)

### The text budget (owner: "way too much text", Aug 6)

Researched against wealthsimple.com and levels.fyi: Wealthsimple runs
heading + at most one sub-line per section with body prose exactly once on
the whole homepage; levels.fyi has almost no prose at all, the data is the
interface. The teardown already said it: one claim per screen, processing
fluency reads as trustworthiness. Rules now in force for every iteration:

1. Heading + max ONE sentence per section. If a section needs two, it's
   two sections or it's disclosure.
2. Numbers render as data (grids, chips, tables), never as sentences.
   The sheet's referral stat is a 3-row grid, not a paragraph.
3. Explanation lives behind progressive disclosure (the contact sheet,
   `<details>` for the template), never inline.
4. Duplicated reassurance is deleted: the fee grid says Stripe once, so
   the blemish line doesn't say it again.
5. Page prose outside listing data stays under ~150 words.
