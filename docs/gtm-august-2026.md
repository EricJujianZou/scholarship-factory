# GTM plan — August 2026

Built with the owner 2026-08-03, one topic at a time. Each section is written down
only after he confirmed it. Sections marked **CONFIRMED** are decided; anything else
is still open.

This is a content/GTM doc living in a product repo because it is about *this* product.
It can move to `content-machine/` later if that reads better.

---

## Topic 1 — high-level roadmap **CONFIRMED**

### The thesis: one product, one ICP

There are not three projects. There is one product for one audience — **students hunting
opportunities** — and two of the three repos are already most of a feature each.

| Repo | Its role |
|---|---|
| **scholarship-factory** | The sourcing + ranking engine. Already generic by design ("scholarships, fellowships, hackathons, grants…"), so pointing it at internships is a seeds-and-positioning change, not a rebuild. |
| **luma-connect** | The referral-discovery feature, **pivoted**: find people you actually met at a Luma event who could be a future referral. Auto-connect is stripped out, which removes the LinkedIn ToS violation; what remains is read-only research on your own session. The value is the warm opener ("we met at this event") and the higher acceptance that follows, not the automation. |
| **content-machine** | Internal ops. Never a product, never launched. Its *experiments* are content; the machine itself is not. |

**Long-term vision:** one site holding every resource a student needs to get an
opportunity, personalized to them. Not a scholarship tool.

### Internships-first, scholarships riding along

Two independent signals point the same way:

1. **The only willingness-to-pay evidence is for internships.** A friend at an AMD ML
   internship said $20/month, mainly for internship sourcing plus general opportunities.
   n=1 — do not over-rotate — but it is a real number from someone inside the ICP.
2. **The best-performing content ever is job-adjacent.** The 68k reel was company → email
   website; its repost just did ~20k views and +70 followers (800 → ~870). The proven
   niche is not "scholarships for students," it is **free resources that get students
   opportunities**, and the top performer is job-adjacent.

Supporting reasons: internship listings are public and abundant while the Canadian
scholarship aggregators are 403-walled (`seeds.toml`); Aug–Oct *is* 2027 summer
recruiting season, so the audience is in-market this month; and the owner is his own
user, which makes the content authentic rather than researched.

**Scholarships and grants stay** — they are the differentiator, not the headline.
Everyone has a job board; nobody has honest deadline extraction plus `sf requirements`
("what does this application actually ask for"). That combination is what stops this
being another Simplify clone.

**Test, don't assume:** run 1–2 scholarship trial reels inside the existing daily IG
lane. Judge them against the job-adjacent reels on retention and follows, not views.

### The four-week shape

| Week | X + LinkedIn | Instagram | Build |
|---|---|---|---|
| **Aug 3–9** | Benchmark. LinkedIn 3× (Tue/Wed/Thu) = **2 benchmark + 1 repurposed**. X ~3 craft posts. | Daily, resource lane, from the repost backlog. Zero product mention. | Internship sourcing + populate the public DB. |
| **Aug 10–16** | Benchmark finale + the one HN shot. Same 2+1 ratio. | Same. | Public DB browsable + the site/waitlist page. |
| **Aug 17–23** | Benchmark done. X switches to build-in-public. | Same, plus a soft offer. | Personalization tier + onboarding. |
| **Aug 24–30** | Launch. | Same. | Customer calls drive what is next. |

**Load logic.** Weeks 1–2 the benchmark carries all public content — it is already
written and it serves the internship goal on its own seasonal deadline. Scholarship-factory
gets **zero content and all build time** in that window. It does not need content yet:
Instagram is building its audience the whole time, for free, out of an existing backlog.

**LinkedIn ratio.** 2 benchmark + 1 repurposed per week, not 3 benchmark. Uses 4 of the
6 campaign angles and keeps 2 as spares; the repurposed post is free
(`scripts/repurpose.py`, 121 posts already fit-scored in `analytics/x-backlog.json`).
It also makes the account read as active rather than one-note.

### Sequencing rule: audience before offer

Pre-selling to an audience that does not exist yet does not work. At ~870 IG followers a
great post yields maybe 20–40 hands up. Weeks 1–2 exist to make that number worth
selling to; the pre-sell happens week 3, by which point two weeks of build time means
"2–3 days to finish it" is not a bluff.

**Target to hit:** ~10 ICP followers/day through Aug 16 → roughly +140, putting IG near
1,000 before any offer goes out. That number is the pre-sell base and is worth tracking
deliberately, not incidentally.

### Deferred — not decided here

- Whether luma-connect eventually folds into a single platform or stays separate.
- Where the free/paid line sits (see `onboarding-plan-DRAFT.md`).
- Scholarships-first vs internships-first is **decided** (internships), which unblocks
  the onboarding draft.
