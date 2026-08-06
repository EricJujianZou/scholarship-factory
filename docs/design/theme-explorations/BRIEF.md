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
