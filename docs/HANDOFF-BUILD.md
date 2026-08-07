# HANDOFF-BUILD.md — delegable build tasks (Aug 6, 2026)

The owner delegates these to coding agent threads. Each task is self-contained:
what to read, what to build, how to know it's done. Priority order is the order
below. Context: hard target is 3 paying subscribers by Aug 17; the owner is
doing DMs/Reddit/content himself and delegating everything buildable.

---

## Task 1 — Ship the production ugmi.ca page (value-prop rewrite + analytics)

**Why this is #1:** `docs/design/feedback.md` shows the current page sells
*curation* ("10 recommendations/week") when the product is *access* (a
recruiter/referral contact + a drafted outreach message per posting). A
sympathetic reader priced the wrong product and concluded it was worthless,
then flipped to positive when the real offer was explained in DM. This is a
conveyance bug, not a concept bug, and it blocks every DM the owner sends.
More explorations do not fix it; one shipped page does.

**Read, in order:**
1. `docs/design/feedback.md` — the signal driving this task, plus the open
   questions the page should help answer (can a first-time reader describe
   the deal back correctly?)
2. `docs/design/explorations-v3/AUDIT.md` + `redesigns/01-soft-premium.html`
   (current theme vote leader; `18-orbital-mission.html` is the other vote —
   note it is unaudited)
3. `docs/design/components/` — ugmi-10-weekly.md, calm-checkout.md,
   pulse-strip.md, eligibility-collapse.md, hook-scent-rule.md,
   visible-closings.md, dm-playbook.md (the DM copy must match the page copy)
4. `docs/design/analytics-plan.md` — the instrumentation spec; the v2 mockup
   already stubs every event as `track(name, props)`
5. `docs/design/audience.md`, then the current production source: `site/` +
   `site.toml`
6. Repo `CLAUDE.md` (behavioral rules) and the `design-core` skill before any
   visual work

**Build:**
- One production page (replacing the current static site) in the 01-soft-premium
  direction, with the pitch rewritten so the named-contact + drafted-message
  mechanism leads and "10/week" is the delivery detail, not the headline.
- Wire analytics per `analytics-plan.md`: Umami Cloud script tag + the 7-event
  schema. The Umami website ID requires a human step (owner creates the Umami
  Cloud site) — build against a placeholder, surface the step clearly at the end.
- Keep every on-page number build-time computed from the dataset. Never
  analytics-derived, never invented.
- No em dashes and no fragment-pair taglines anywhere on the page — the
  AI-tell blacklist applies to shipped surfaces.

**Done when:**
- Deployed to ugmi.ca (deploy = build the site, push to
  `git@git.skullheadx.com:ugmi.ca.git`).
- A first-time reader answering "what do you get for the money?" would say
  "a real contact at the company plus a written outreach message," not
  "10 job recommendations."
- `contact_open`, `stripe_click`, `apply_click`, `email_submit` etc. fire in
  Umami (verified live, or verified locally with the placeholder swapped and
  the human step documented).

---

## Task 2 — Canadian sources + multi-profile (scholarship-factory runtime)

**Why:** the paid product is a personalized list delivered within 48h of
signup. Today the runtime is single-profile and Canadian scholarship supply is
thin — the UGMI `deadline` content series literally refuses to generate under
3 relevant rows. This task is what makes a sale deliverable.

**Read:** `REPO_CONTENT.md`, `prd.json` (live state), `HARNESS.md`,
`context.toml` vs `context.example.toml` (multi-profile shape), and the
source/ranking code under `scholarship_factory/`.

**Build:**
- Support N customer profiles (program, grad year, work auth, location
  constraints — the three /start questions in
  `docs/design/components/dm-playbook.md`) so one poll run can produce one
  ranked list per profile.
- Add Canadian scholarship/internship sources so the DB has real Canadian
  depth (this also unblocks the content pipeline next door).
- Add an eligibility/year facet. Checked Aug 6: of 1,364 internship rows,
  1,083 have requirements text and ZERO match "first year" / "freshman" /
  "early talent" — yet the commenting audience on IG skews first-year. Extract
  year-level eligibility where the posting states it, and add sources that
  carry first-year-friendly postings (early-talent programs, research
  assistantships). Do not infer eligibility the posting doesn't state.

**Done when:** a second profile can be added in minutes, `poll_once` produces
a per-profile ranked list, and the deadline series in content-machine
generates without refusing.

---

## Task 3 — posted dates + card descriptions (enrich v2 + expandable cards)

**Why:** watch-session feedback (Aug 7). Users expect "posted X days ago"
and a card that expands into a real description. The page currently says
"added Xd ago" (accurate: `seen` is when WE found the row) and the `desc`
field is boilerplate ("Software internship. Term: X.") that would make an
expanded card embarrassingly empty.

**Build on GH-53's `sf enrich`** (built + closed 2026-08-07: JSON-LD
JobPosting + Lever/Ashby/Greenhouse APIs + capped LLM fallback, with
`sf splice <index.html>` rewriting only the live page's data line):

- Extract a `posted` date: JSON-LD `datePosted`; ATS fallbacks: Lever
  `createdAt`, Ashby `publishedDate`, Greenhouse `first_published`.
  Never infer it; absent stays absent.
- Extract a `summary`, capped ~300 chars, from the posting description
  (JSON-LD `description` first, since the fetch already happens).
- Page side: prefer "posted Xd ago" when `posted` exists, else keep
  "added Xd ago"; add an expand affordance on the card showing summary +
  full requirements text.
- Watch page weight: the embedded JSON is ~600KB raw; the 300-char cap
  exists so the gzipped delta stays under ~150KB.
- Note: ~1,300 of 1,364 rows are still unattempted by enrich; growing
  coverage = re-run `sf enrich` + `sf splice` + push.

**Done when:** coverage percentages reported (posted/summary), card
expand live on phone width, gzipped page delta measured and under the
cap.

## Explicit non-goals (do not build these now)

- Reddit tooling — playbook says none until a paying customer comes from Reddit.
- TikTok tooling — decision says zero until the 30-day signal read.
- Video pipeline v2 (cuts[] re-mapping) — content side, not blocking sales.
- More theme explorations — the exploration phase is over; ship Task 1.
- Self-serve SaaS (auth, hosting, billing) — Oct 1 decision per strategy.
