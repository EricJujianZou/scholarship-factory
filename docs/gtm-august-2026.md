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

---

## Topic 2 — what each content type is for **CONFIRMED**

### The four types

| Type | What it's for | Platform | Metric | Needs |
|---|---|---|---|---|
| **1. Resource** | Buying attention from the ICP with something free and useful | IG, daily | Follows + **sends** (the #1 IG signal per `learnings.md`) | Nothing — product-independent |
| **2. Proof-of-work / research** | Credibility with people who hire or would cover you | LinkedIn, X | Inbound DMs; 600+ impressions is the bar | An artifact |
| **3. Build-in-public** | Anticipation, and being interesting to builders | X mainly | Replies from people worth knowing | A decision or a shipped thing |
| **4. Launch** | Converting accumulated audience into users, once | IG + LinkedIn + X | Signups | Something a stranger can use unaided |

### Why they are sequential, not parallel

```
resource content  ->  audience
proof-of-work     ->  credibility
build-in-public   ->  anticipation   (consumes audience)
launch            ->  conversion     (consumes all three)
```

Types 3 and 4 spend what types 1 and 2 produce. Launching before there is an audience is
not a smaller launch — it is shouting in a room of 40, and there is roughly one good
launch per product per platform. The problem was never volume of work; it was order.

### Build-in-public reaches builders, not buyers

The buyers are 19-year-olds hunting internships. They will never read a post about the
extraction pipeline. So build-in-public serves the internship/network goal and barely
touches the product-users goal.

| Type | Goal A: inbound internships | Goal B: product users |
|---|---|---|
| Resource (IG) | — | **primary** |
| Proof-of-work (LI/X) | **primary** | — |
| Build-in-public (X) | secondary | barely |
| Launch | — | **primary** |

Goal A and Goal B share almost no content. That is the actual source of the
spread-thin feeling: two campaigns for two audiences, treated as one. They do not have
to compete — A owns X + LinkedIn in weeks 1-2, B owns Instagram throughout and takes
X + LinkedIn in weeks 3-4.

### Platform rules

- **Instagram** — type 1 only, always; plus type 4 at launch, because that is where the
  buyers are. Never build-in-public.
- **LinkedIn** — type 2 primarily. Type 3 only when the post carries a shipped artifact
  plus an image; "day 4 of building" with no artifact is a reflection post in a hoodie,
  and reflection posts do ~500 impressions.
- **X** — types 2 and 3. The only place raw build-in-public works.

### Build-in-public: decision posts vs progress posts

- **Decision posts** need no product and are safe now. The pivot itself is one: *"I built
  a scholarship finder. My only paying signal wants internships. So I'm rebuilding it."*
  Same DNA as the benchmark — publishing the thing that did not go your way.
- **Progress posts** imply a product exists. Every person who goes looking and cannot use
  it is a person who cannot be re-activated at launch. Hold until the public DB is live.

### On the raised MVP bar

The bar moved on **polish**, not scope. When anyone can ship a landing page in an hour,
rough reads as lazy rather than scrappy. So the standard is **narrow and finished**: a
browsable public database plus one genuinely good personalized list is a finished
product. "Coming soon" on five features is not.

### Two-week content map

| | Type 1 (IG) | Type 2 (LI/X) | Type 3 (X) | Type 4 |
|---|---|---|---|---|
| **Aug 3-9** | daily, from backlog | benchmark x2 LI + X craft | — | — |
| **Aug 10-16** | daily + 1-2 scholarship trials | benchmark finale + HN | 1 decision post (the pivot) | — |
| **Aug 17-23** | daily + soft offer | 1 repurposed | progress posts begin | — |
| **Aug 24-30** | launch support | launch post | — | **launch, once** |
