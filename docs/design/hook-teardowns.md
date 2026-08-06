# UGMI Hook Teardowns (audience-hook-research phase 3)

Researched 2026-08-06. One section per mechanism family (see hook-inventory.md
for the ranked product list and evidence). Template per mechanism: where it
appears (observed UI ground truth) / why it works / preconditions vs our
constraints / ethics check / UGMI translation sketch.

Our constraints, restated: STATIC site (daily rebuild possible), no accounts,
no backend, email capture off, one Stripe link, manual weekly email/DM
delivery, acquisition via IG reels -> comment LINK -> manual DM.

Status: phase-3 output, feeds the phase-4 repurposing map. Awaiting owner
challenge of "why it works" claims.

---

# Family 1: FRESHNESS AS URGENCY

## Product 1: GitHub internship lists (SimplifyJobs/Pitt-CSC, vanshb03, speedyapply)

Observed ground truth (verified against live READMEs, Aug 2026):

- **Simplify/Pitt CSC**: header "Summer 2027 Tech Internships by Pitt CSC & Simplify", subtitle "Updated daily by Simplify and Pitt CSC". Columns: Company | Role | Location | Application | **Age**. Age renders as relative day-counts: `0d`, `1d`, `2d` … up to `1mo`. Legend: 🛂 no sponsorship, 🇺🇸 citizenship required, 🎓 advanced degree, 🔥 FAANG+, 🔒 closed. Category index with per-category counts (Software Engineering (90), Quant (63)…). Closed roles are *moved out* to `README-Inactive.md` behind a link: "🔒 **See 36 more closed roles →**". CTA: "🙏 Contribute by submitting an issue!". Email alerts outsourced to SWEList.
- **vanshb03 (Vansh & Ouckah)**: columns Company | Role | Location | Application/Link | **Date Posted** (absolute: "Aug 05"). Closed rows stay *in place*: the blue "Apply" button image replaced by a bare 🔒. Discord CTA above the table: "Join the ⬇️ **discord** ⬇️ and get your internship applications in right when they open!"
- **speedyapply**: "positions are updated daily". Columns include **Salary** ("$52/hr") and **Age** (`0d` → `120d`; older listings silently removed). Inventory counts per section: "**209** available". Sections tiered FAANG+ / Quant / Other.

### Mechanism 1: The Age column (decay clock)

- **Where it appears**: rightmost column of every row in Simplify (`0d`…`1mo`) and speedyapply (`0d`…`120d`). `0d` rows cluster at the top of each section. Because the repo rebuilds daily, every value ticks up every day — the table literally looks different every morning.
- **Why it works**: **recency heuristic + implied competition.** A `0d` label doesn't just say "new" — in a market where early applicants have better odds, it says "the race for this one just started and you're at the front." The ticking numbers also create a **daily variable-reward loop** (Hook Model trigger): checking today might surface a `0d` that wasn't there yesterday. Relative time (`2d`) beats absolute dates because it requires zero mental math and reads as a countdown.
- **Preconditions**: (1) trustworthy per-row date-added — **UGMI has this** (extraction pipeline); (2) frequent regeneration so numbers are honest — **only if rebuild is at least daily**; a static `0d` that's actually 5 days old is a lie; (3) enough genuine inflow that `0d`/`1d` rows exist most days — likely met at ~1,400 listings, but Canadian-only inflow may be lumpy.
- **Ethics check**: ethical, as long as the clock is computed at build time from real data. Gray/dark the moment "New" badges outlive their truth.
- **UGMI translation sketch**: add an **"Added" column rendered at build time** as relative age: `today`, `1d`, `4d`, capping at "2w+". Rows added within 3 days get a small "NEW" chip on mobile (inline next to the role name — full column may not fit in the IG in-app browser viewport). Pair with the soonest-deadline sort by making the deadline cell a decay clock: "**closes in 3d**" instead of "Sep 12" for anything under 14 days out, with a color ramp (neutral → warm) at ≤7d. Same psychology pointed at the other end of the listing's life — and deadlines are the one urgency signal we own that GitHub lists mostly lack. All string formatting at generation time; zero infra.

### Mechanism 2: Lock, don't delete (visible corpse handling)

- **Where it appears**: two variants. vanshb03: closed rows *stay in the table* with the Apply button swapped for 🔒 — you scroll past corpses. Simplify: corpses swept to `README-Inactive.md` but the *count* stays on the main page: "🔒 See 36 more closed roles →". speedyapply silently deletes after 120d (weakest variant — no loss signal).
- **Why it works**: **loss aversion made concrete.** An abstract "apply early!" does nothing; a table where 🔒 rows sit next to live rows is *proof* that windows close, and each corpse is a small "that could have been you." The count quantifies the loss rate. Secondary effect: groomed corpses prove a human tends the list — dead links *marked* dead build more trust than dead links never caught.
- **Preconditions**: (1) closed-detection — **partially met** (deadline passage is free; detecting quietly-pulled postings needs link checking we may not run); (2) visible week-over-week turnover — met, deadlines guarantee it.
- **Ethics check**: ethical. Honest information that happens to motivate. Dark only if the closed count is fabricated or inflated.
- **UGMI translation sketch**: hybrid of both variants, at build time. When a deadline passes: keep the listing 7 days, greyed, apply link replaced with "Closed" — then sweep. Above the table, one line: "**23 internships closed in the last 7 days.**" Computed from data we already have, and the single best static-site conversion line we can own — it leads directly to the paid pitch: the weekly list exists so you hear about things *before* they join that number. Echo the stat in reels ("23 closed this week — here's what's still open") and the DM pitch.

### Mechanism 3: The heartbeat header (maintained-by-humans signal)

- **Where it appears**: Simplify: "Updated daily by Simplify and Pitt CSC" under the H1, plus GitHub's own chrome doing free work — commit timestamp ("last commit 3 hours ago"), contribution activity, stars. speedyapply: "updated daily" plus live inventory counts that change between visits, which *proves* the cadence claim.
- **Why it works**: **freshness meta-signal / trust transfer.** Before trusting any row, the user asks "is this list even alive?" GitHub answers ambiently. The named maintainer adds accountability. This is exactly where a generated static site loses by default: no visible pulse reads as a possibly-abandoned scrape even on build day. **What makes a README table feel alive is not the table — it's the changing numbers around it.**
- **Preconditions**: (1) a real update cadence — **met only if rebuilds are scheduled, not ad hoc**; (2) a named accountable maintainer — met (the IG identity + concierge framing).
- **Ethics check**: ethical if literal. "Updated daily" on a weekly cron is dark.
- **UGMI translation sketch**: a one-line **pulse strip** directly above the table, build-time rendered: "Last checked **Aug 6** · **1,412** open · **31** added this week · **23** closed this week · hand-checked, never invented". Every number derivable by diffing the current build against the previous build's snapshot (persist one JSON per build). The deltas matter more than the totals — a returning visitor who sees "31 added" where it said "27" has watched the site breathe. The "never invented" clause is our grift-radar disarm and belongs in the same breath as the freshness claim. **Highest-leverage single element in this teardown for our constraints.**

### Mechanism 4: The commons CTA (report-a-corpse loop)

- **Where it appears**: Simplify/vanshb03: "🙏 **Contribute by submitting an issue!**" — users report new roles and dead links; contributors get merged and become part of the list's authorship.
- **Why it works**: **IKEA effect + free QA.** Users who've reported one dead link are invested; the list becomes partly *theirs*, and every report improves the freshness the other mechanisms sell. Converts passive readers into a contact channel.
- **Preconditions**: low-friction report channel + a human who responds — met: the funnel is already manual IG DMs.
- **Ethics check**: ethical.
- **UGMI translation sketch**: footer + per-row affordance: "Dead link? Wrong deadline? **DM @sleppyeric** — fixed within a day." Triple duty: QA we can't automate, a trust signal (inviting correction reads as honest), and it moves visitors into the DM channel where conversion actually happens. Minimal version is one anchor tag in the footer.

## Product 2: Discord job-ping channels (vanshb03/Ouckah server, cscareers.dev ~90k members, SpeedyApply bot)

Observed ground truth: cscareers.dev pitches "Receive intern and new grad job posting alerts **as soon as they're created** just by being a member of our Discord server", several notifications/day in peak season (Aug–Dec). SpeedyApply bot: `/start`, pick a category ("SWE Intern," "AI New Grad") + optional USA-only filter; alerts land as embeds; `/stop`, `/chart`. Ecosystem pattern: react-with-🔔-for-role opt-ins, then the bot @-mentions the role per new listing.

### Mechanism 1: Ping at the moment of opening

- **Where it appears**: dedicated alert channels where a webhook posts an embed the moment a listing lands. The sell is explicitly the *race*: "get your applications in right when they open" — positioned against LinkedIn's lag.
- **Why it works**: **urgency + first-mover advantage as an external trigger.** The GitHub list requires remembering to check (weak internal trigger); the ping inverts it — the opportunity interrupts *you*. Each ping is a variable-ratio reward (might be your dream company), the most habit-forming schedule there is. The speed claim reframes membership as a competitive weapon.
- **Preconditions**: (1) a granted push medium, (2) real-time detection, (3) volume that rewards attention without spamming. **UGMI lacks (1) and (2) entirely.**
- **Ethics check**: ethical in itself. Gray when the speed claim outruns reality.
- **UGMI translation sketch**: we cannot ping — so **sell the ping as the paid product**. The $15/mo weekly DM *is* our alert channel; frame it the way Discord servers frame theirs: "Every Monday, the new Canadian postings and everything closing that week, in your DMs — before you'd have found them yourself." Minimal push beyond that with zero infra: an **Instagram broadcast channel** (native IG, one-tap join, no email) posting 2-3 "just added" listings mid-week. That's our #intern-alerts, and its members are the retargeting pool for the paid pitch. When email capture turns on, the same mechanism becomes the "new this week" email.

### Mechanism 2: Self-segmentation via role opt-in

- **Where it appears**: SpeedyApply's `/start` flow (pick "SWE Intern" vs "AI New Grad" vs USA-only); community servers' react-🔔-for-role. The user configures their own interruption.
- **Why it works**: **commitment & consistency + endowment.** A ping you *asked for* is service; the same ping unasked is spam. The tiny configuration act creates ownership of the alert stream and makes every subsequent ping relevant.
- **Preconditions**: a moment of expressed preference and a way to honor it — met in the manual DM funnel, not on the static site.
- **Ethics check**: ethical.
- **UGMI translation sketch**: make the paid onboarding DM an explicit `/start` ritual: three questions (program, grad year, location constraints) asked *before* the first list, echoed back in the first delivery ("Your filter: CS, class of 2028, GTA or remote"). The customer co-built their product; week-2 retention lives here. On the site, the no-state analog is **link-encoded filters** (filter state serialized into the URL, client-side JS on a static page): a reel can say "link in bio is pre-filtered to first-year-friendly" and each DM can carry a personalized-looking URL. Cheap endowment without accounts.

### Mechanism 3: The ambient activity stream (market-is-moving proof)

- **Where it appears**: the alert channel's scrollback: several embeds/day in peak season, reactions, "applied" replies. cscareers' front page converts the energy into numbers: "90,000+ members, 4,000+ job offers." SpeedyApply's `/chart` turns posting volume into a trendline.
- **Why it works**: **social proof + FOMO of the feed.** A busy channel proves the market is moving, the alert system works, and other people are acting on these pings right now. The stream's density is the message. Second half of "alive vs static": GitHub's version is changing numbers; Discord's is visible other-people.
- **Preconditions**: (1) real posting volume — met; (2) visible other users — **not met**: a static site has no crowd, and at our scale we can't fake one (and must not).
- **Ethics check**: ethical when real. **Dark if simulated** (fake "someone just subscribed" toasts, invented member counts) — explicitly off-limits for this audience; one whiff of fabricated social proof kills the "never invented" positioning.
- **UGMI translation sketch**: substitute **data activity for crowd activity**. The build-time "This week" changelog strip ("+31 added · 23 closed · 4 close tomorrow") is an activity stream requiring zero users, and it's honest. The *crowd* proof lives where we actually have a crowd: IG — reels showing the list changing, story reposts of DM'd thank-yous (with permission), reply counts. Do not port member-count or testimonial-wall patterns to the site until the numbers are real and verifiable; until then the site's credibility engine is the data pulse, not the crowd.

## Family-1 cross-cutting note: why their tables feel alive and ours feels static

The GitHub lists never animate anything. The aliveness is entirely: (a) relative-time values that tick daily, (b) counts that differ between visits, (c) visible grooming of dead rows, (d) a named human on the masthead, (e) platform chrome showing recent commits. Every one of (a)–(d) is reproducible on a generated static site with a daily rebuild plus one persisted snapshot-diff — no backend, no accounts, no JS beyond what we ship. **The build cadence is the product feature**; everything above assumes a committed daily rebuild and never letting a freshness label outlive its truth.

Sources: github.com/SimplifyJobs/Summer2027-Internships · github.com/vanshb03/Summer2027-Internships · github.com/speedyapply/2027-SWE-College-Jobs · docs.speedyapply.com/discord · cscareers.dev

---

# Family 2: CURATION / EFFORT COLLAPSE

Products: Simplify (simplify.jobs, inventory #3) and NeetCode (neetcode.io,
inventory #8). Family thesis: both sell exactly what UGMI sells — *someone
already did the exhausting part* — and both win by (a) making the **size** of
the collapsed effort a visible number, and (b) making the curation feel
**authored and accountable** rather than arbitrary. Neither hides the raw
corpus (LeetCode's 3,000+ problems; the whole ATS internet); both position the
branded thing as *labor on top of* an open corpus. That is already UGMI's
shape — this family is where the pitch copy gets its mechanics.

## Product 1: Simplify (Copilot autofill + tracker)

Observed ground truth (site + help docs fetched 2026-08-06; UI details from
2026 reviewer testing where noted):

- **Landing** (simplify.jobs): hero "Your AI job search partner. Powered by
  one profile." · "Join 1,500,000+ job seekers who use Simplify" · CTA "Join
  Now - It's Free!". Social-proof band: "Join over 1,500,000 candidates that
  hear back **25% more** with Simplify". Curated-lists section: "Explore our
  expert-curated job lists" / "**Our team handpicks** the most exciting
  opportunities into lists for you to discover - **updated daily**" (e.g.
  "Top Summer 2026 Internships"). FAQ: base version "is and will be free
  forever"; sourcing checks "**50,000+ companies every hour**".
- **Copilot page**: "Autofill job application questions in 1-click" ·
  "**200,000,000+** applications submitted" · users "saved **500,000+ hours**
  this year" · supports "over 100 job boards and application portals
  including Workday, Greenhouse, iCIMS, Taleo, Avature, Lever, and
  SmartRecruiters".
- **First-run** (help docs): install → "Pin the extension to your browser
  toolbar" → create account, upload resume once to build the profile → on any
  supported job page "Copilot detects the form automatically and starts
  matching fields using your Simplify profile"; popup has sections for
  Resume / Cover Letter / Common Questions / Unique Questions and an
  "Autofill this page" action; "After submission, Copilot can automatically
  add the job to your Job Tracker with the application details already filled
  in." Docs tell you to test immediately on a real application.
- **Reviewer-measured collapse** (2026 tests): ~90% autofill accuracy on
  Greenhouse/Lever; a 15–25 minute application drops to 1–2 minutes. Free
  core; Simplify+ premium is $39.99/mo.

### Mechanism 1: The effort receipt (quantify the collapse, never describe it)

- **Where it appears**: every marketing claim is a *number pair or total*,
  never an adjective: "200,000,000+ applications submitted", "saved 500,000+
  hours this year", reviewer-echoed "15–25 min → 1–2 min per application".
  The collapse has arithmetic: before-cost, after-cost, cumulative pile.
- **Why it works**: **anchoring + loss aversion on the counterfactual.** A
  named foregone cost ("the 20 minutes you'd have typed") converts an
  invisible saving into a felt loss avoided. The cumulative totals double as
  scale social proof. "Fast and easy" claims are what grifters say; arithmetic
  is what tools say.
- **Preconditions**: (1) real, auditable before/after numbers — **UGMI has**:
  corpus count (~1,400 live), list size (10), our own reading time, all
  build-time derivable; (2) scale totals — **UGMI lacks** (no telemetry, tiny
  base) and must not fake; use per-week per-user arithmetic instead.
- **Ethics check**: ethical when real. Simplify's "hear back 25% more" is the
  **gray** edge — an unverifiable *outcome* delta. UGMI copies only the
  *effort*-delta form (we can prove it); outcome deltas are banned by our own
  claims-audit discipline and would trip the grift radar.
- **UGMI translation sketch**: state the pair **1,427 → 10** at every stage.
  Reel hook (stage 1): "1,427 internships are live. You're eligible for maybe
  40. I read all of them so you read 10." Site (stage 3), one build-time line
  above the paid pitch: "This week: 1,427 postings live · ~9 hrs to read them
  all · your list: 10 · ~15 min" (hours = count × honest per-posting minutes,
  labeled). Weekly email/DM (stage 6): close with a labor receipt — "This
  week I read 212 new postings, killed 34 dead links, 10 made your list."
  Manual delivery makes this free: it's the operator's actual week, written
  down. The receipt re-justifies the $15 every Monday — and renewal, not
  purchase, is where the price gets re-examined (audience.md §1).

### Mechanism 2: First-run demo on the user's own task (aha in minutes, in context)

- **Where it appears**: onboarding order: one resume upload builds the
  profile → docs push you to a real application immediately → the popup
  *appears unprompted* on the job page ("Copilot detects the form
  automatically") and the form visibly fills itself. The demo is not a tour
  or video — it is the user's actual next application getting 20 minutes
  shorter inside the first session.
- **Why it works**: **Fogg — collapse the ability barrier at the moment of
  motivation** (mid-application), plus peak-end: the first session ends on a
  visceral win, which is the story that gets retold to friends.
- **Preconditions**: value demonstrable on the visitor's own case in seconds
  with near-zero input. **UGMI half-meets**: the free DB is instant proof and
  the 3 qualifying lines (work auth, term, location) are already the intake —
  but today every visitor sees the same 1,427 rows; the collapse is *claimed*
  in copy, not *demonstrated* on them.
- **Ethics check**: ethical — it's a working demo, nothing hidden.
- **UGMI translation sketch (stage 3 — biggest build implied by this
  family)**: a client-side **3-tap eligibility collapse** on the free DB, no
  typing: "I can work in: [Canada] [US] [both]" · "Term: [Summer 2027] […]" ·
  "Location: [remote ok] [city…]". On tap the table collapses live —
  "**Showing 43 of 1,427 you're actually eligible for**" — with the three
  answers persisted in localStorage so return visits reopen pre-collapsed.
  Five seconds, one-handed, works in the IG webview. It converts the core
  paid claim ("you are eligible for a fraction of it") from copy into a
  watched event, and hands stage 2 its script: "you saw the 43 — I'll get you
  to the 10, each with a named contact."

### Mechanism 3: Auto-accumulating system of record (state you didn't build, won't abandon)

- **Where it appears**: "After submission, Copilot can automatically add the
  job to your Job Tracker with the application details already filled in."
  The tracker populates as a *side effect* of applying; after two weeks it
  holds the user's whole pipeline. Reviews consistently cite "no more messy
  spreadsheets" as the reason they stay.
- **Why it works**: **endowment effect + compounding switching cost.** State
  the user got for free is still *theirs*; leaving means abandoning it. This
  is the Notion-tracker desire from the cut list (students crave a tracked
  pipeline) minus the DIY effort our audience won't spend.
- **Preconditions**: somewhere durable to accumulate per-user state. **UGMI
  lacks** accounts/backend; **meets two partials**: localStorage, and — the
  concierge's unfair advantage — the operator's own memory, since delivery is
  a manual 1:1 thread.
- **Ethics check**: ethical (lock-in as a side effect of genuine utility).
  Gray only if state is held hostage; never block anyone from leaving with
  their info.
- **UGMI translation sketch**: static minimal version (stage 3/4):
  tap-to-check "applied" marks on DB rows in localStorage with a quiet count
  ("you've marked 7 applied"), honestly labeled "saved in this browser only".
  Concierge version (stage 6 — the real moat): **the operator is the system
  of record.** Keep a per-subscriber note file; open each weekly DM with
  continuity — "Last week you said you sent 4 of the 10 — the PitchBook one
  closes Friday. Here's this week's 10." No software can replicate it, and it
  compounds like Simplify's tracker: cancelling means losing the one person
  who knows your pipeline.

### Mechanism 4: Industrialized labor illusion ("50,000+ companies every hour")

- **Where it appears**: two stacked layers. Machine scale: sourcing "checks
  50,000+ companies every hour" (FAQ). Human judgment: "Our team handpicks
  the most exciting opportunities … updated daily" (curated lists). Coverage
  alone would read as a firehose; judgment alone as arbitrary taste; together
  they answer "who picked these and why believe them."
- **Why it works**: **operational transparency / labor illusion (Buell &
  Norton)** — showing the work being done raises perceived value and trust
  even for identical output. The daily-updated stamp also feeds Family 1's
  freshness ritual.
- **Preconditions**: real labor to show. **UGMI meets fully** — the one
  mechanism where a one-person concierge outguns a 1.5M-user platform: our
  scale layer is the real pipeline (scan counts, dead-link kills, Family 1's
  pulse strip) and our judgment layer is a *named human*, not "our team."
- **Ethics check**: ethical if literal; **dark if simulated** (invented scan
  counts, fake spinners). Build-time numbers from the actual pipeline only.
- **UGMI translation sketch**: mostly already designed in Family 1
  (pulse strip, visible corpse handling) — this teardown adds the *pricing
  frame*: sell the labor, not access. Stage-5 copy: "$15/mo is me reading
  ~200 postings a week so you don't." Stage-2 DM script: "give me your 3
  lines and 48h — I read the new postings every morning." Never "unlock"
  language; the thing being bought is hours, and we can name how many.

## Product 2: NeetCode (the 150 roadmap)

Observed ground truth (site is a JS SPA — structure corroborated via its
practice URLs, user screenshots, and 2025–26 reviews):

- **The artifact is a named finite list**: "NeetCode 150" — set against
  LeetCode's 3,000+ catalog. 18 topic buckets with visible per-topic counts
  (Arrays & Hashing 9, Two Pointers 5, Stack 7, Sliding Window 6, Binary
  Search 7, Linked List 11, Trees 15, Tries 3, Heap 7, Backtracking 9,
  Graphs 19, DP 23 across 1-D/2-D, Intervals 6, Greedy 8, Math & Geometry 8,
  Bit Manipulation 7); difficulty split 28 Easy / 97 Medium / 25 Hard.
- **Practice page**: tabs Blind 75 / NeetCode 150 / NeetCode 250 / all; one
  overall progress bar (a user writeup screenshots "**64 of 150**");
  per-difficulty counts; solving a problem "automatically marks it as
  solved." Free sign-in gates only progress *sync*, not content.
- **Roadmap page**: a top-down dependency graph of rounded topic nodes joined
  by arrows — Arrays & Hashing at the root, fanning out toward Graphs/DP —
  each node carrying its own completion fraction ("0/9") that fills green as
  problems are checked. The overwhelming grind is drawn as a finishable map
  with an entry point.
- **Trust chassis**: founder Navdeep Singh, ex-Google/ex-Amazon, started by
  posting free YouTube solution walkthroughs while unemployed after failing
  interviews; every one of the 150 links to his free video. Reviews explain
  the trust plainly: "these are the 150 problems that matter most", the list
  "eliminates decision fatigue", problems are "selected … so they build on
  each other." The 150 + roadmap + videos are free forever; Pro (~$119/yr,
  ~$219 lifetime) sells courses and convenience on top.

### Mechanism 1: Subtractive value framing ("150, not 3,000" — sell the exclusions)

- **Where it appears**: the product's *name* is the mechanism. The number
  lives in the URL, the tab label, the progress denominator, and every
  third-party mention. The value proposition is never "we have more" — it is
  "you may ignore 95% of the corpus, on my authority."
- **Why it works**: **choice-overload relief (Iyengar & Lepper) + decision
  fatigue.** An unbounded task ("grind LeetCode") produces avoidance; a
  bounded named task ("do the 150") produces starts. The fixed number makes
  the promise falsifiable and finishable — and becomes community shorthand,
  which is free distribution every time someone says it.
- **Preconditions**: (1) a corpus the audience already knows is overwhelming
  — **UGMI meets** (1,427 visible listings, "40 tabs" is our own sign-off);
  (2) the nerve to commit to a fixed small number publicly — **UGMI
  half-meets**: "10" exists in pitch copy but is not yet a *name*.
- **Ethics check**: ethical — honest editorial judgment stated as such. Gray
  only if the excluded 95% is hidden or trash-talked; NeetCode links to
  LeetCode, and our full free DB stays open (load-bearing per audience.md).
- **UGMI translation sketch**: name the deliverable **"the UGMI 10"** and
  never vary the count — ten every week even when eleven are good; the
  constraint is the product. Reel hook (stage 1), verbatim-usable for a CS
  audience that already reveres the pattern: "LeetCode has 3,000 problems;
  everyone does the NeetCode 150. There are 1,427 internships live; here's
  your 10." Email subject (stage 6): "Your UGMI 10 — week of Aug 10." The
  paid pitch (stage 5) inherits falsifiability as a *process* promise: "10
  per week, each with a named contact" — never an outcome promise.

### Mechanism 2: The finishable map (chunked denominators + progress fractions)

- **Where it appears**: roadmap nodes each carry a small local denominator
  ("0/9", "0/5") with green fill per checked problem; the practice page rolls
  it up to one bar ("64 of 150"). Two choices do the work: prerequisite
  *ordering* deletes "where do I start?", and chunking 150 into 18 sub-goals
  means one evening visibly moves a bar.
- **Why it works**: **goal-gradient effect** (effort accelerates near sub-goal
  completion) + **Zeigarnik** (an open 7/9 nags to be closed) + implementation
  intentions (the map turns "prep for interviews" into "next: Two Pointers,
  problem 3"). Saved progress is also the return-visit trigger: the map
  remembers you.
- **Preconditions**: (1) persistent per-user state — **UGMI lacks** (NeetCode
  needs sign-in for this; we have only localStorage and paper); (2) a bounded
  chunk size — **UGMI meets** naturally: the week is the node, the 10 is the
  denominator.
- **Ethics check**: ethical — progress tied to real chosen work. Gray if
  padded with junk sub-tasks to fake momentum.
- **UGMI translation sketch (minimal static/email versions)**: stage 6 —
  format the weekly email/DM literally as a checklist: header "Week of Aug 10
  — 0/10", rows "☐ 1. PitchBook — DM Sarah Chen (closes Fri)…", and ask for
  the fraction back next week ("how many did you send? I'll carry the
  count") — the operator carrying the tally *is* the progress bar (same
  muscle as Simplify mechanism 3). Stage 4 — each weekly list also lives at
  an unlisted static page with tap-to-check rows and a plain "6/10 applied"
  localStorage counter; the 6/10 line doubles as the shareable IG-story
  artifact (Wordle family will pick this up). **Do not port the dependency
  graph itself** — applications have no prerequisite structure; forcing a
  tree would be decoration. Steal the fractions, not the tree.

### Mechanism 3: Curator with receipts (every pick carries its proof-of-work)

- **Where it appears**: all 150 problems link to a free video in which the
  curator personally derives the solution — years of them, posted publicly
  before any paid platform existed. Trust in the *list* is downstream of
  visible work on each *item*: "covers the patterns that actually appear" is
  believed because an identifiable ex-Google engineer — who openly failed
  interviews while unemployed first — demonstrably did every problem himself.
  The answer to "who picked these?" is a face, a history, and 150 receipts.
- **Why it works**: **authority + costly signaling.** 150 free explanations
  are unfakeable effort — a grifter monetizes before producing them. The
  underdog origin converts authority into kinship, which is what a
  grift-radar-maxed audience actually requires; credentials alone
  pattern-match to "LinkedIn bro" (audience.md §6).
- **Preconditions**: a real named curator with a checkable history +
  willingness to attach a rationale to every pick. **UGMI meets** the first
  (one-person voice is the brand; @sleppyeric is the checkable identity; the
  68k contact-finding reel is existing public proof-of-work) and **lacks**
  the second: today a listing is a row, not a *pick*.
- **Ethics check**: ethical — this is the anti-grift mechanism; it works
  precisely because it can't be faked cheaply.
- **UGMI translation sketch**: stage 6, the core move — every item in the
  UGMI 10 ships with one plain **"why this one"** line: "picked because: they
  take 1st-years, posted 2d ago, and the recruiter (named below) replied to a
  student DM last month." One sentence per pick is our video-per-problem: it
  proves a human read it, makes the curation auditable, and pre-loads the
  outreach the pick exists to enable. Stage 1 — keep filming the labor:
  screen-recorded "I read 200 postings today, 9 were ghost jobs, here's a
  real one and the person to message"; the free-videos-then-paid-platform arc
  is exactly NeetCode's. Stage 3 — a short "how the 10 get picked" block in
  the curator's voice, *including what gets a posting killed*; stating
  rejection criteria is the cheapest credibility on the page.

### Mechanism 4: Paywall above an intact free core

- **Where it appears**: the famous thing — the 150, the roadmap, every
  solution video — is free forever; free sign-in gates only progress sync;
  Pro sells courses/convenience on top. Simplify runs the identical shape
  (autofill + tracker "free forever", Simplify+ $39.99/mo above). Neither
  ever claws back the free core.
- **Why it works**: **reciprocity + an observed trust floor.** The free core
  does years of reputation work; payment reads as upgrade, not toll. For an
  audience trained to expect the rug-pull ("your email is the product"), the
  *observed stability* of the free thing is the strongest anti-grift signal —
  and it accrues with every unpaywalled week.
- **Preconditions**: a free core good enough to be someone's whole solution,
  plus the discipline to never regress it. **UGMI meets** — the
  no-account/no-email/no-paywall DB is already this and audience.md marks it
  load-bearing. Nothing to build; this mechanism is confirmation.
- **Ethics check**: ethical.
- **UGMI translation sketch**: a standing rule, not a feature: the free DB
  never shrinks, never gates, never nags. Paid sells only labor and
  personalization (the reading, the 10, the named contacts, the 1:1 thread)
  — never data access. Say it at stage 5: "the full database stays free
  either way; $15 is for me doing your reading. Cancel anytime — it's a
  Stripe link."

## Family-2 cross-cutting note: the two questions every collapse-seller answers

1. **"How big is the pile you're saving me from?"** Simplify answers with
   effort arithmetic (200M apps, 500k hours, 20 min → 2 min); NeetCode with a
   named ratio (150 vs 3,000). UGMI's answer is the visible pair
   **1,427 → 10**, computed from real build data and restated at every
   stage, with the weekly labor receipt as its retention form. Never the
   outcome-delta form ("hear back 25% more") — the one gray pattern in this
   family, and a head-on collision with our audience's grift radar.
2. **"Who picked these, and why believe them?"** Simplify: machine coverage +
   "our team handpicks" + daily stamps. NeetCode: one named human with
   per-item receipts. UGMI is structurally NeetCode, not Simplify: one
   checkable person, a "why this one" line on every pick, rejection criteria
   in public, reels that film the labor. The site shows the pruning
   (Family 1); the DM proves a human read your 3 lines.

Biggest single build implied: the **3-tap eligibility collapse** on the free
DB (Simplify mechanism 2) — it turns the core paid claim into a 5-second
demonstrated experience inside every constraint we have. Biggest copy change:
naming **"the UGMI 10."**

Sources: simplify.jobs · simplify.jobs/copilot ·
help.simplify.jobs/articles/1749022-installing-and-setting-up-copilot ·
help.simplify.jobs/articles/2415391-using-copilot-to-autofill-applications ·
resumehog.com/blog/posts/simplify-copilot-review-june-2026-does-the-free-autofill-tool-actually-work.html ·
jobcopilot.com/simplify-jobs-review · crackr.dev/neetcode150 (category/difficulty
counts) · dev.to/caresle/neetcode-roadmap-part-1-1fn3 ("64 of 150" screenshot) ·
lodely.com/blog/neetcode-review (founder, Pro pricing, curation rationale) ·
codeintuition.io/blogs/neetcode-pro-review ·
leetcopilot.dev/blog/leetcode-premium-vs-neetcode-which-is-better-2025 ·
neetcode.io/practice + neetcode.io/roadmap (SPA; structure corroborated via
the writeups above)

---

# Family 3: TRUST VIA SPECIFICITY + CALM TRUST

Products: levels.fyi (#5), Wealthsimple (#6). Researched against live pages —
Wealthsimple's type/color facts extracted from their production CSS bundle,
not blog lore.

## levels.fyi

### L1. The unrounded number (precision-as-brand)

- **Where it appears**: everywhere the product touches money the number is suspiciously specific. Canada SWE page: median **CA$136,423** — not CA$136K, not "~$135K" — plus "average range from CA$101,977 to CA$185,278." Even city aggregates keep odd digits (Vancouver median CA$172,810). The page `<title>` carries the range, so the number is the first thing Google shows.
- **Why it works**: **precision-implies-knowledge heuristic** — people rate precise numeric claims as more credible and their sources as more competent than round ones (Jerez-Fernandez et al.; Mason et al. on precise first offers). A round number reads as an estimate; an unrounded number reads as a *measurement* — the trailing digits are implicit proof real data underlies it. This is the exact answer to "what makes $131,250 more credible than 'competitive'": *competitive* is chosen; *$131,250* looks computed, and computed numbers can't be flattering you.
- **Preconditions**: real underlying data so the numbers are true — **has** (pipeline scans real postings); consistency across surfaces or precision backfires — **can meet** (numbers regenerate from one dataset). Does NOT need volume — one true specific number beats a big vague one.
- **Ethics check**: ethical; dark edge = inventing precision (fake decimals on made-up stats). Only surface numbers the pipeline actually computed.
- **UGMI translation sketch**: *Stage 1/2:* never "tons of internships" — the computed truth: "1,046 postings scanned this week. 37 pay over $40/hr. 12 close in 5 days." The DM template carries one unrounded number in its first line. *Stage 3:* hero subline gets a build-time stat row: "1,046 postings · 214 Canadian · updated Aug 6, 7:00am ET". *Stage 5:* the paid pitch is a precision claim: "Your 10 matches from this week's 1,046, every Monday." Specific numerator/denominator does the selling.

### L2. The decomposed claim (show-the-work table)

- **Where it appears**: the comp table never shows one number; it shows the arithmetic: Level | Total | Base | Stock | Bonus ("L3 · $199K = $158K + $34.1K + $6.6K"), percentile pickers, itemized vesting schedules.
- **Why it works**: **verifiability heuristic** — a claim that exposes its parts *invites* audit, and claims that invite audit rarely get audited; the invitation is the proof. Also **self-referential encoding**: the reader locates themselves in the structure ("I'd be L3"), and personally-indexed information is trusted and remembered better. Showing the spread kills ambiguity aversion.
- **Preconditions**: structured honest fields — **has** (company, role, location, pay, deadline, age); domain-fluent readers — **has**; mobile screen space — **partially lacks** (IG webview is narrow; needs card-per-row, not a wide table).
- **Ethics check**: ethical.
- **UGMI translation sketch**: *Stage 3:* the free list already IS this mechanism — protect it. Every row keeps its decomposition visible at phone width: company / role / pay / location / closes-in / found-date as labeled fields in a card, never collapsed to "Software Intern — Apply." Rule: **no field-dropping for aesthetics.** *Stage 5:* decompose the offer next to the Stripe button: "$15/mo = 4 Monday lists · ~10 matches each · your filters applied · cancel anytime." Price shown as arithmetic reads as measured, not marketed.

### L3. Provenance ladder (timestamp + raw rows + verification tiers)

- **Where it appears**: three visible rungs: (a) "Last updated: 8/6/2026" same-day stamp; (b) a "Recently Submitted Salaries" table — individual data points beneath the aggregate; (c) document verification (Offer Letter, W-2) with a "Verified Salaries" section and stated removal of suspicious data.
- **Why it works**: Fogg's **earned credibility** — trust accumulated by letting the user check you repeatedly and finding you right. Raw rows under the aggregate are a nothing-to-hide signal. The verification tier is **costly signaling**: faking a W-2 pipeline is expensive, so its existence implies honesty of the whole. The timestamp converts "is this stale?" (the #1 doubt about any list) into a checkable fact.
- **Preconditions**: a pipeline that refreshes — **has** (daily poll); per-item source links — **has**: apply links go to the employer's own posting, which *is* the W-2 equivalent — the employer's careers page verifies the row for free.
- **Ethics check**: ethical. Dark variant to avoid: a "last updated" stamp that updates without the data updating.
- **UGMI translation sketch**: *Stage 3:* "Last checked Mon Aug 6, 7:04am ET · next update Monday" baked in at build time — exact minute, not "updated daily" (the unrounded-number rule applied to time). Apply links labeled "apply on <Company>'s site" — outbound-to-source as proof we invented nothing. *Stage 5:* above the Stripe button: "Lists are generated from the same pipeline as the free page above — audit this week's free list before paying." The free list is the verification document.

### L4. Mission-framed give-to-get

- **Where it appears**: "Contribute Your Salary" framed as worker solidarity ("Empower workers like yourself"); the paid layer (Negotiation Coaching, Resume Review) sits *beside* the free data, never inside it — the reference data stays free.
- **Why it works**: **reciprocity + identity framing** — contribution recruits the user's self-image. The free-data/paid-service split is a **trust firewall**: because the reference data is never paywalled, the paid offer can't be suspected of distorting it.
- **Preconditions**: contribution benefiting the contributor's own community — **partially has** (dead-link reports); a receiving endpoint — no backend, but a DM link costs nothing. The "submit to unlock" gate needs accounts — skip it.
- **Ethics check**: gray at the gate (manufactured scarcity of already-collected data); the firewall and contribution loop are ethical. Take those, skip the gate.
- **UGMI translation sketch**: *Stage 3/4:* one line under the free list: "Dead link? Missing an internship? DM @sleppyeric — fixes ship same week." *Stage 5:* keep the firewall explicit: the free list never degrades to sell the paid one. Copy near the button: "The full list stays free. $15/mo buys your *shortlist* — we read the 1,046 so you read 10."

## Wealthsimple

### W1. Institutional calm (the specific type/space/color moves)

- **Where it appears**: the whole landing system — concrete, from their shipped CSS:
  - **Color**: background bone `#F5F3EF` (the single most-used color in the homepage payload), never stark white. Text soft near-black `#1C1B1B` — peak contrast slightly cushioned. Accents are desaturated pastels used as full section blocks (pale gold `#EEE3B1`, peach `#FFDCC4`, blush `#FBDCD1`, pale pink `#F4DCE4`, lilac `#D6C9DC`) plus one deep forest green `#0C330D` for weight. Zero saturated "urgency" hues; **no red anywhere near money**.
  - **Type**: The Future (Futura-descendant geometric sans, Regular + Medium) for display, Tiempos Text (quiet book serif) for editorial body, custom sans for UI. Lineage: Caslon Graphique + Futura — "heritage bank" and "app" in one system. **Headline weight is Medium, not Bold — nothing shouts.**
  - **Rhythm**: one idea per viewport; each block a single flat pastel field with a single image; short declarative sentences; sections separated by whitespace measured in screen-heights.
- **Why it works**: **processing fluency → judged truthfulness** (easy-to-parse layouts are literally rated more trustworthy), compounded by **counter-signaling against the scam schema**: the career/finance grift aesthetic is high-arousal (countdowns, red, bold caps, dense claims). The grift detector keys on arousal cues, so cushioned contrast, muted hues, one claim per screen and slow rhythm read as "has nothing to prove" — the visual grammar of an institution. The serif does borrowed-heritage work; the geometric sans keeps it from reading as boomer.
- **Preconditions**: restraint budget (few elements, real whitespace, no stacked CTAs) — **can meet**; enough content quality that emptiness reads as confidence — **has** (the live table is the substance). Custom fonts not required — the *moves* transfer with free faces.
- **Ethics check**: ethical. Gray only when calm dresses up terms that aren't calm — avoided by pairing with W2.
- **UGMI translation sketch**: *Stage 3 (main payload):* against the existing Light Marketplace system: bone-family background instead of white; near-black not `#000`; exactly one desaturated accent; hero = h1 + one stat line + one CTA above the fold; the "who makes this" paragraph set in a serif — one human paragraph in serif does the Waterloo-student trust work. Kill anything that raises arousal: no exclamation marks, no countdowns, no bold-red. *Stage 5:* the payment section is the *calmest* block on the page, not the loudest: generous padding, price stated once in plain weight, single button in the accent, nothing animated within a viewport of it. **Maximum user vigilance gets minimum visual pressure — that inversion is the Wealthsimple signature.**

### W2. Zero-stated pricing (name the feared fee, print a number on it)

- **Where it appears**: an exhaustive grid of exact numbers, especially the zeros: "Monthly account fees: $0 · Account minimums: $0 · ATM fees: $0 · Commission fees: $0 · FX fees: 0%." Non-zero numbers just as bare ("USD accounts $10/month, 30-day free trial"). The asterisk resolves honestly in the footnote.
- **Why it works**: **inoculation / objection pre-emption** — printing "$0" beside every fee the audience has been burned by answers the suspicion before it's voiced. An exhaustive fee grid is a **costly signal** (a company hiding something doesn't build a table that invites line-item comparison). The honest asterisk is a **two-sided argument** — a visible concession that makes every other claim more believable.
- **Preconditions**: genuinely simple pricing — **has** (one price, one link, simpler than Wealthsimple); a known list of audience fears to zero out — **has** (audience.md §6: auto-renew traps, card harvesting, fake "cancel anytime").
- **Ethics check**: ethical — the anti-dark-pattern. Never do the inversion: hiding the one real cost among decorative zeros.
- **UGMI translation sketch**: *Stage 5 (primary):* a four-line fee grid directly above the button: "**$15/mo** — that's everything · Sign-up fee: **$0** · Cancellation: **anytime, from the Stripe receipt email, no DM needed** · Your card: **handled by Stripe — we never see it**." Naming the cancel *mechanism* (not just "cancel anytime") defuses the auto-renew fear IG career-grifts trained into this audience. *Stage 2:* the DM price-reveal uses the same grid verbatim — word-for-word consistency between DM and site is itself a trust signal.

### W3. Borrowed institutional trust (with the honest limitation)

- **Where it appears**: a non-bank selling to people nervous about non-banks, candid about the seams: "Although **Wealthsimple is not a CDIC member institution**, under the trust framework, funds must be spread across up to 10 CDIC member institutions…" Above it all, one earned number: "Trusted by over 4 million Canadians."
- **Why it works**: Fogg's **reputed credibility** (trust transferred from a third party the user already trusts) plus the **blemish effect**: leading with the limitation makes the protective claim that follows dramatically more believable — a grift would never volunteer the weakness. Converts "who even are you?" into "who stands behind you?", which has a checkable answer.
- **Preconditions**: a genuinely trusted third party in the transaction — **has**: Stripe *is* the CDIC of this checkout; plus the Waterloo affiliation. An honest limitation worth volunteering — **has** several (solo operator, new product). **Lacks**: any large user count — "trusted by 4 million" has no honest analog yet; do not fake one.
- **Ethics check**: ethical as practiced. Dark inversions: implying Stripe endorses rather than processes; invented testimonials/user counts.
- **UGMI translation sketch**: *Stage 5:* under the button, small quiet text: "Checkout runs on **Stripe** — your card details go to Stripe, never to me." First person ("me") on purpose — the solo-operator admission *is* the blemish that makes the Stripe umbrella credible. *Stage 3:* the about-paragraph does the same shape: "I'm one Waterloo student with a scraper, not a company. The data is checkable (every row links to the employer's own posting); the payment is Stripe's; the only thing you're trusting me with is $15 and your Monday morning."

### W4. Home-turf specificity (Canadian identity as trust wedge)

- **Where it appears**: nationality worn as product spec, not flavor: "Canada's most rewarding chequing account", growth claims scoped and dated ("in Canadian online brokerages in 2025, as of April 21, 2026"), CDIC/CIPF as protection vocabulary, TFSA/RRSP as product vocabulary. Superlatives always scoped to Canada — small enough to be true and checkable.
- **Why it works**: **in-group identity** plus a second-order specificity effect: precisely *scoped* claims read as audited; unscoped superlatives read as marketing. For a young Canadian audience whose alternatives are US-defaulted, localized vocabulary is proof of effort no grifter would bother with — **generic scams don't know what a TFSA is.**
- **Preconditions**: real localized substance — **has** (Canadian sources are the pivot's critical path; the GitHub lists' US-heaviness is the stated wedge); vocabulary fluency — **has** (co-op streams, PGWP, citizens/PR-only flags).
- **Ethics check**: ethical.
- **UGMI translation sketch**: *Stage 1/3:* claims scoped the Wealthsimple way — never "the best internship list", always "214 Canadian internships this week — the big GitHub lists carry ~30." Scoped, dated, checkable. *Stage 3:* Canadian-ness as a *field*, not a banner: "CAD" suffix on pay, a citizens/PR-eligibility label column, co-op-term filters ("Winter 2027"). The vocabulary carries the identity; no maple-leaf theming — Wealthsimple's palette contains no red for a reason. *Stage 5:* "$15/mo **CAD**" — one token that says "priced for you, not converted at you."

## Family-3 synthesis

The two products are one mechanism at two altitudes. levels.fyi earns trust with **specificity of evidence** (unrounded numbers, decomposed tables, timestamps, raw rows); Wealthsimple with **specificity of terms inside visual calm** (exact zeros, scoped claims, admitted limitations, low-arousal design). For UGMI both collapse into a single page law: **every claim gets a number, a date, or a link — and the page around those claims stays quiet.** Stage 3 is won by levels.fyi moves (the free list as self-verifying evidence); stage 5 by Wealthsimple moves (the calmest block on the page, zero-stated terms, Stripe as the borrowed institution, one honest first-person limitation). Shared anti-pattern: anything that raises arousal (urgency, countdowns, bold superlatives, hidden terms) burns both mechanisms at once — the grift detector keys on arousal, and calm-plus-precision is precisely what it cannot pattern-match to a scam.

Sources: levels.fyi (home, Google SWE, Canada SWE, heatmap, salaries/add, about) · wealthsimple.com/en-ca (incl. production CSS bundle: TheFuture-Regular/Medium.woff2, TiemposText-Regular.woff2; hex `#F5F3EF`, `#1C1B1B`, accents `#EEE3B1` `#FFDCC4` `#FBDCD1` `#F4DCE4` `#D6C9DC` `#0C330D`) · wealthsimple.com/en-ca/pricing · /about · fontmeme.com + typewolf.com (wordmark lineage)

---

# Family 4: BOUNDED RITUAL + STREAK + ATTENTION

Products: Duolingo (#4), Wordle/NYT Games (#9), IG Reels feed mechanics (#2).
This family serves **stage 6 (weekly retention/renewal)** more than any other —
the least-designed part of UGMI — plus stages 1–2 for Reels. Standing rule
applied throughout: **personality is charming, fabricated state is fatal.** A
streak counter UGMI shows must be a fact the sender actually tracks.

## Product 1: Duolingo

### Mechanism 1.1 — Protected streak (loss aversion with a forgiveness valve)

- **Where it appears**: the flame icon + day count permanently in the top bar; lit once today's lesson is done. **Streak Freeze**: 200 gems in the shop, max 2 equipped, auto-applied on a missed day — the count doesn't reset, it just doesn't grow. At 100 days, **Streak Society** grants 3 bonus freezes that can't be re-bought. PMs credit streaks as the single biggest DAU lever; 7+ day streakers are ~2.3x likelier to engage daily.
- **Why it works**: **loss aversion** — after ~2 weeks the accumulated streak is worth more psychologically than any single lesson is costly. The freeze is the critical second half — **failure forgiveness** prevents the what-the-hell effect (one lapse → total abandonment) that kills pure streaks. Milestones add **goal gradient**.
- **Preconditions**: (a) server-side per-user state — **UGMI lacks** (no accounts); (b) a natural repeating cadence — **has** (weekly list); (c) *someone* who tracks state — **has**: delivery is manual, and the sender's spreadsheet is the state store. The streak lives in the sender's ledger, not the user's browser.
- **Ethics check**: **gray.** The base streak is ethical (real behavior, honestly counted). The gray part: Duolingo's streak measures *opening the app*, not learning — attachment to the number over the outcome. A UGMI copy must count something the student actually values, or it's decoration that trips the grift-radar.
- **UGMI translation sketch**: **the sender-tracked streak, stated as fact in the weekly email.** First line: "Week 4 of your list, Priya." Zero infrastructure — one column in the tracking sheet — and unfakeable *because the student can verify it against their own inbox*. That inversion makes it safe: Duolingo's streak is the platform's number about you; UGMI's is a shared fact between two people. Freeze analog: a pause or missed payment never resets — "paused at week 6, back at week 7." At the renewal moment (audience.md §1: renewal, not purchase, is where $15 gets re-examined), "you're 8 weeks in — 80 roles have crossed your inbox" does loss-aversion work honestly: cancelling stops the *accumulated relationship*, not just a subscription. Stage 6. Do NOT surface any streak on the static site — no state there means any number would be fake.

### Mechanism 1.2 — Character-voiced reminder (the guilt owl)

- **Where it appears**: push/email in Duo the owl's voice ("Spanish isn't going to learn itself"; the meta-guilt "These reminders don't seem to be working. We're going to stop sending them for now."). The iOS widget escalates visually — Duo's face decays as the day runs out. The passive-aggression is deliberate brand strategy; the "evil Duo" meme ecosystem is free stage-1 distribution.
- **Why it works**: **parasocial obligation** (guilt only lands from a *character*, not a corporation) + **pattern interrupt** (every other reminder is neutral; a voice gets read) + **reactance** ("we'll stop sending these" makes users re-engage to keep the attention).
- **Preconditions**: (a) an established character the audience likes — **has** (@sleppyeric; "one Waterloo student who got tired of 40 tabs" is already the site's sign-off); (b) a push channel — **partially**: the weekly manual email/DM is a recurring owned touchpoint; DMs to followers are push-equivalent.
- **Ethics check**: **gray, honestly: the guilt mechanics are engineered emotional manipulation.** Duolingo gets a cultural pass because it's self-aware and users are in on the joke. For UGMI: **the voice transfers, the guilt must not.** Guilt-tripping an anxious student about applications isn't a meme — it's punching down at the exact anxiety they're paying you to reduce.
- **UGMI translation sketch**: **the weekly email is a character, not a digest.** Same 10 rows, but the wrapper is Eric's actual voice: one line of commentary per pick ("small team, the recruiter replied to me in a day"), a P.S. that sounds like a person. A voiced email gets opened where a digest gets archived. Deadline callbacks do the *ethical* version of urgency: "the PitchBook role from last week closed Friday — three from this week close before next Monday." Never: "you didn't apply to anything last week 😢". Stages 4, 6 — and 1: self-aware personality bits ("I am the guy who reads 400 postings so you don't") are reel material.

### Mechanism 1.3 — One-small-ask session (daily quest)

- **Where it appears**: Duolingo's daily quest panel: 1–3 micro-goals with progress bars and a chest reward; the daily contract is deliberately tiny — never "learn Spanish," always "do one lesson."
- **Why it works**: **Fogg tiny habits** (shrink the ask until motivation is never the bottleneck) + **goal gradient** (a bar at 1/2 gets finished). Completing a small bounded goal delivers a clean win that gets associated with the product.
- **Preconditions**: a defined session with a visible finish line — **UGMI has one by construction**: 10 roles, weekly. No accounts needed; the bound lives in the artifact.
- **Ethics check**: **ethical** — the asked behavior aligns with the user's actual goal.
- **UGMI translation sketch**: **the email states the contract: "Pick 2 of these 10 this week."** Not "here are 10 opportunities" (a to-do pile → "beat the pile" despair) but a bounded ask that makes the list *finishable*. Format the 10 rows as a checklist — the student's reply ("did 3") becomes both streak data for 1.1 and a weekly conversation hook the manual-DM model uniquely supports. Duolingo can't ask "how'd it go?"; a human sender can. Stage 6.

## Product 2: Wordle / NYT Games

### Mechanism 2.1 — Bounded synchronized drop (one puzzle a day)

- **Where it appears**: exactly one puzzle/day, resetting at midnight; no "play another." Everyone gets the *same* numbered word ("Wordle 1,492"). ~4M daily players sustained years after peak; anchored NYT's games-subscription funnel.
- **Why it works**: **scarcity** — the daily cap makes the ritual precious and *finishable*; you leave wanting more instead of scrolled-out and ashamed (the anti-feed). **Synchronization** — same puzzle for everyone manufactures a shared daily conversation object. BeReal's one surviving mechanic is this one.
- **Preconditions**: (a) a fixed, *kept* cadence — the mechanism is trust in the drop; (b) identical artifact across users — **UGMI deliberately violates** (lists are personalized), so sync transfers partially; (c) no accounts needed — met; scarcity is a property of the publishing schedule.
- **Ethics check**: **ethical** — bounding consumption is arguably the most pro-user retention mechanic in this research.
- **UGMI translation sketch**: **"Your list lands Monday morning. Every Monday."** Works with manual delivery via two adjustments: promise the *day*, not the minute (a kept "Monday" beats a missed "Monday 8:00am" — the drop is an SLA; one silent miss costs more than the ritual earns), and build Sunday + Gmail schedule-send so the drop is achievable at 10 subscribers without automation. Say the scarcity out loud: 10 roles, once a week, no firehose — NeetCode's "150 not 2,000" on a clock, and the counter-position to the free GitHub lists' always-on churn: "you don't need to check daily; that's the product." Partial sync recovery: a shared "this week's #1 pick" across subscribers seeds the water-cooler effect for a future group chat/Discord. Stages 4, 6 — and 1: "one list every Monday, that's the whole product" is a reel-sized promise.

### Mechanism 2.2 — Braggable grid (spoiler-free shareable result artifact)

- **Where it appears**: Wordle's Share button copies plain text: `Wordle 1,492 3/6` + rows of 🟩🟨⬛ showing the *path* but never the letters. Deliberately low-tech (text pastes anywhere) and spoiler-free (shows skill, ruins nothing). This grid made Wordle viral: every share is an ad only players can decode.
- **Why it works**: **costly signaling / identity display** ("3/6" = "I'm sharp today") + **in-group legibility** (illegible to outsiders, so sharing recruits *and* affirms membership). Self-reported plain text proves a share artifact needs **zero verification infrastructure** — trust rides on the social graph.
- **Preconditions**: (a) a completed bounded unit — has (the weekly 10); (b) a format that hides paid content while showing progress — matters doubly: must not leak *which companies* (the paid product; students guard leads anyway); (c) no backend — met by construction.
- **Ethics check**: **ethical.** Self-reported, opt-in. Dark variant = manufacturing fake shares as social proof — off-limits.
- **UGMI translation sketch**: **weekly email footer carries a copy-paste emoji row:** `UGMI wk 4 — applied 6/10` + `🟩🟩🟩🟩🟩🟩⬜⬜⬜⬜`. Plain text beats a static image for v1: pastes into an IG story text box, group chat, or Discord with zero hosting, exactly as verifiable as Wordle's (i.e., not at all — fine, the sharer stakes their own credibility). Stage 6: a student who types 6/10 has told *themselves* the subscription worked (self-perception theory). Stage 1: every posted grid is an in-group-legible ad generating the "what's that?" DM. The 10-slot format only works because the list is exactly 10 — 2.1/2.2/1.3 interlock: bounded drop → checklist ask → grid receipt. A static "make your card" canvas page later is polish, not core.

### Mechanism 2.3 — Stats mirror (accumulated identity)

- **Where it appears**: Wordle's stats modal: Played, Win %, Current/Max Streak, guess distribution. Persisting stats requires a free NYT account — the stats panel *is* the account funnel; fed the 2025 Spotify-Wrapped-style "Year in Games." One hard puzzle in 2024 ended 5.6M streaks and made news — that's how much identity players store in the number.
- **Why it works**: **endowed progress + sunk-cost identity** — accumulated stats become a possession; abandoning the game means abandoning the record. Histogram adds self-benchmarking.
- **Preconditions**: durable per-user state — **lacks client-side, has sender-side.** The manual ledger can accumulate exactly these stats per subscriber: weeks active, roles delivered, applications self-reported, interviews.
- **Ethics check**: **ethical** as a mirror of real behavior; **gray** when zeroing is punitive (Wordle's midnight cliff vs Duolingo's cushion — hence 5.6M people mourning a puzzle).
- **UGMI translation sketch**: **a monthly one-line "wrapped" inside the normal email:** "4 weeks in: 40 roles delivered, you reported 14 applications, 2 interviews." Hand-compiled from the ledger — five minutes at 10 subscribers — and it's the *renewal-moment artifact*: converts the $15 question from "do I feel like it" to "do I want this record to keep going" (endowed progress, every number auditable against the student's inbox). Never zero anyone: Duolingo's cushion, not Wordle's cliff — a skipped week reads "paused." An annual Wrapped in August (return-offer season) is the same mechanic at yearly scale and doubles as a 2.2-style shareable. Stages 6 and 5 (the stats line is the strongest honest testimonial material, with permission).

## Product 3: Instagram Reels (the feed as product — the content→site bridge)

### Mechanism 3.1 — Frame-one contract (first-2-seconds hook grammar)

- **Where it appears**: the Reels feed is a variable-reward slot machine where the swipe is free; a reel earns retention in its opening beat or dies. Surviving-reel grammar: **on-screen text from frame one** (5–8 words, legible on mute — lifts 3-second retention ~50%), **mid-action start** (greeting intros are retention death), and hooks from a small formula set: audience callout, specific-number outcome ("I found 47 internships that pay $40/hr"), contrarian, mistake, DM-integrated ("comment X and I'll send Y"). UGMI's own 68k PitchBook outlier is a specific-number outcome hook.
- **Why it works**: **variable-ratio reward** runs the feed; within it a hook works by **pattern interrupt + information gap** (Loewenstein): frame-one text opens a specific loop the viewer must watch to close. Specificity sharpens the gap *and* signals verifiability — the trust-via-specificity family operating inside stage 1.
- **Preconditions**: (a) owner makes the reels — met, with a proven outlier to reverse-engineer; (b) the hook's claim must be cashable by the content and downstream — with maxed grift-radar, an overclaimed hook converts views into distrust, the most expensive possible impression.
- **Ethics check**: **ethical** when the promise is true; **gray→dark** as curiosity-gap inflates into bait. This audience pattern-matches hustle-bro grammar as grift — UGMI's ceiling on hook aggression is lower than the platform's.
- **UGMI translation sketch**: codify a **hook bank** in the content-machine queue keyed to proven formulas, always with a real number from the actual DB: "1,427 internships are on this site. You're eligible for maybe 60." / "The recruiter's name is in this reel." / "I read 400 postings this week so you don't." **Every hook must be a claim the landing page's first viewport can repeat verbatim** (enforced at hook-writing time — see 3.3). Stage 1, sets the contract for 2–3.

### Mechanism 3.2 — Comment tollgate ("comment LINK" → DM)

- **Where it appears**: creator withholds the link, asks for a keyword comment. At scale this runs on ManyChat: comment trigger → auto-DM in seconds → button-flow to the link — the standard 2025 creator funnel, outperforming link-in-bio. Side effects: hundreds of identical keyword comments are **public social proof**, and comment volume buys the reel more distribution. The automated DM has a recognizable vending-machine feel: instant, emoji-cheery, obviously scripted.
- **Why it works**: **foot-in-the-door** (a tiny *public* commitment makes accepting the DM consistent behavior) + **reciprocity** (the DM frames the link as a favor delivered) + the **algorithmic flywheel** (comments → reach). The keyword self-qualifies the funnel.
- **Preconditions**: (a) reach — met; (b) something worth gating — met (free DB, template); (c) DM capacity — **manual by design**: minutes-to-hours latency, survivable at current scale. The binding constraint: manual works below a comment-volume ceiling; a viral reel creates a backlog, and unanswered "LINK" comments are a *public* trust cost.
- **Ethics check**: **gray.** Engagement-bait by construction — culturally accepted, viewers know the game. The dark versions are near: gating content that doesn't exist, bait-and-switch DMs that open a sales script, follow-gating before releasing the link. For this audience the DM *is* the first trust checkpoint — a scripted blast contradicts the "one real Waterloo student" positioning.
- **UGMI translation sketch**: keep the tollgate, **weaponize the manual-ness.** The DM every student has received is the ManyChat vending machine; a reply that is visibly a person — references their comment in one clause, delivers the link in the first message, no follow-gate, no emoji confetti, signed like a text — is a **pattern interrupt inside the DM channel** and the actual start of the 1:1 sales relationship. Mechanics: reply publicly ("sent!") for the social-proof trail; batch DM sessions twice a day so latency is bounded; deliver the free thing *unconditionally* — the paid pitch belongs later in the conversation, not in the toll. Scale valve: if a reel outruns capacity, pin a comment with the raw link — losing that cohort's DM entry is cheaper than a thousand-person backlog. Stages 1→2. (ManyChat later isn't forbidden, but it forfeits the differentiator; revisit only when volume forces it.)

### Mechanism 3.3 — Unbroken scent trail (reel promise → DM → first viewport)

- **Where it appears**: not one screen but the seam between three: the reel's hook makes a promise, the DM link carries it, and whatever loads first either re-states it or breaks it. High-converting creator funnels keep the *exact wording* alive across all three. The failure mode is the generic homepage: viewer arrives from a specific promise, sees a brand-shaped landing, smells a funnel, leaves.
- **Why it works**: **information scent** (Pirolli & Card, information foraging): users follow a trail of cues and abandon the moment the scent weakens. Under grift-radar it's diagnostic, not just confusing — bait-and-switch is the signature move of every hustle-bro funnel this audience has learned to flee.
- **Preconditions**: (a) control of all three surfaces — **fully met, unusually**: the same person writes the reel, sends the DM, owns the site; (b) per-promise landing states — partially: static site, but static ≠ single-state (`#` fragment anchors into the DB, client-side query-param reads, or a first viewport built around the one proven recurring promise).
- **Ethics check**: **ethical** — this is the anti-dark-pattern of the family: promise-keeping enforced across the funnel.
- **UGMI translation sketch**: hard rule in the content queue: **no hook ships unless its key phrase appears in (a) the DM template for that reel and (b) the first viewport it links to.** Contact-finding reels (the proven genre) must land where "the actual person to contact" is visible in the first screen; the DM is the adapter when the site can't be. The human DM is UGMI's scent-continuity superpower: a manual sender can restate the promise *in the viewer's own context* ("you commented on the PitchBook reel — same method works for these"). Cheap static upgrades when a genre recurs: fragment links that pre-scroll the DB to the relevant filter; a one-line H1 variant reading a `?from=` param client-side. Stages 2→3, back-stopping 5: the Stripe click inherits whatever trust the trail accumulated. The weekly email is itself a scent trail — the "week 4" streak line only pays off because every prior email kept its promise.

## Family-4 synthesis: the weekly loop stage 6 actually gets

The three products interlock into one loop UGMI can run **today, with zero new infrastructure**, because every piece of state lives in the sender's ledger and every artifact is plain text:

1. **Bounded drop** (2.1): 10 roles, lands Monday, promised by day not minute; schedule-send keeps the ritual keepable while manual.
2. **Voiced email with a tiny ask** (1.2 + 1.3): Eric's voice, "pick 2 of these 10," deadline-callback urgency, zero guilt.
3. **Sender-tracked streak** (1.1): "Week 4 of your list" — verifiable against the student's own inbox, paused-never-zeroed.
4. **Self-scored receipt** (2.2): copy-paste `applied 6/10` emoji row; the reply doubles as ledger data and conversation.
5. **Monthly stats mirror** (2.3): "40 roles, 14 applications, 2 interviews" — the honest renewal argument.
6. **Reels bridge** (3.1–3.3) feeds the loop's front door and shares its constitution: every number real, every promise repeated verbatim downstream.

The family's non-negotiable: **every displayed number must be a fact someone can audit.** Duolingo can afford a streak that measures attachment; UGMI's audience will renew for a record and churn instantly on a prop.

Sources: duoplanet.com · duolingo.fandom.com · japm.substack.com (Duolingo streak psychology) · blog.duolingo.com · dailydot.com (Duo memes) · en.wikipedia.org/wiki/Wordle · aol.com (5M streaks ended) · manychat.com · chatimize.com · inro.social + opus.pro + billo.app (reel hook data)

---

