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

---

## Topic 3 — the benchmark: small content vs the artifact **CONFIRMED**

### R1-4 sell the method. R5 sells the finding.

Round 5 (60 hardest SWE-bench Pro instances, Opus 5 and Sonnet 5, 2x2) is the real
claim, because it is the first round on current frontier models and therefore the first
that speaks to Cherny's statement directly. Rounds 1-4 ran on Devin's cloud models.

So the earlier rounds are not "the arc" — they are **credibility for a claim that has not
landed yet**. Every remaining angle is a method/integrity angle (pre-registration, the
fabricated timing reports, contamination, benchmark gaming, the infra incidents), and
none of them need R1-4 to be decisive. They only need to show the work is honest, so the
R5 number is believed when it appears.

### Framing constraints — three hard rules

1. **Never frame R2-4 as waste or as a mistake to be embarrassed about.** The honest and
   better version is owning the miss: *"I underestimated how good the models already were,
   which is why round 4 came back null at the ceiling."* That is a finding, not a failure.
2. **Never disparage Devin's model quality.** There is a warm relationship with Devin
   DevRel and a complimentary post that did ~7k views. Devin is a relationship asset, not
   a foil. The factual framing needs no dig: *"rounds 1-4 ran on Devin. Round 5 is the
   first on current frontier models."* That bounds the earlier rounds honestly and makes
   R5 the main event without a claim about anyone's quality.
3. **Teasers promise a result, never a verdict.** No interim numbers, no predicted
   direction. Two weeks of teasers pointed at a result that has not graded is the one way
   this breaks.

**Both R5 outcomes have a good post.** If it is null too, the story is "I ran five
pre-registered rounds trying to prove my own scaffolding was necessary; it won 1 of 5" —
a *better* HN post than a win, because a win is a normal result and a null against your
own tool is counter-consensus and self-critical. Be genuinely indifferent.

### The artifact is the destination; each post is standalone

The artifact (`scaffold-bench` README + `ericzou.dev/scaffold-bench.html`) is permanent,
single, and complete — built for someone who has already decided to take the work
seriously. The posts are traffic, and **each must be independently valuable**: a reader
who never clicks should still have gotten something.

**Do not serialize the paper.** "Part 3 of 6" makes every post depend on the others and
asks the audience to opt into a series; post 4 underperforms post 1 every time. One
artifact, many independent stories, the artifact as the receipt at the bottom.

### Post inventory and platform assignment

Ranked two ways, because the rankings differ and that difference *is* the assignment:
travelers go to X where reach compounds through reposts, hiring-signal goes to LinkedIn
where the conversion audience is.

| Angle | Travels | Hiring signal | Assigned |
|---|---|---|---|
| **The agent that lied** — R2's unscaffolded arm fabricated 3/3 of its own timing reports | 1st | 4th | X + the IG reel |
| **Contamination** — 72/100 instances partly memorized | 2nd | 3rd | X, then LinkedIn |
| **Benchmark gaming** — Apr 2026, ~100% on 7/8 benchmarks, zero tasks solved | 3rd | 6th | X |
| **The self-refutation** — R4 null at the ceiling | 4th | 1st | *already posted as R1 — see below* |
| **The infra war story** — 135GB VHDX, C: at 2GB, docker socket dropping | 5th | 5th | LinkedIn |
| **Why pre-register** — goalposts committed in git | 6th | 2nd | LinkedIn |

**"The agent that lied" is promoted out of the spares.** It is the only piece with
genuine crossover to people who have never heard of SWE-bench, and it is the strongest
argument *for* scaffolding — a useful counterweight in a series that mostly concedes.

**The R1 concession (posted ~Jul 26) becomes setup, not content.** Do not re-post it.
Do call back to it explicitly: *"a week ago I told you he won round one. Here's rounds
two through four."* Continuity is what makes an audience follow a series. It also makes
the R2 post (scaffolding wins, McNemar p = 0.039) land harder — a concession followed by
a win reads as honest; a win alone reads as marketing.

### Cross-posting: same idea and asset, different text

Duplication is not the problem (160 X vs 1.2k LinkedIn barely overlap). Two real reasons
to reformat:

1. **Format differs.** X rewards compression and a reply-able hook; LinkedIn rewards an
   artifact + image + a conversation handle (`[strong]`: no artifact ≈ 500 impressions).
   A pasted tweet reads as low-effort on LinkedIn; a pasted LinkedIn post reads as
   LinkedIn-brained on X.
2. **X returns signal in ~2h.** LinkedIn is the conversion asset and deserves the framing
   that already tested, not the first guess. So X leads by 1-2 days.

Reformatting costs ~5 minutes via `repurpose.py`. The cheapest cross-post is one where an
**image carries the post** — same asset, different body copy.

### Instagram: one reel, and it is not a benchmark explainer

Trial reels distribute to non-followers resembling current engagers — college students.
Instagram has no "AI researcher" segment to route into, so a technical framing tests
whether jargon works on IG, and the answer is already known.

Run exactly one, and make it **"I caught an AI lying about its own homework"** — the
agent-that-lied story, zero jargon, general audience. If it flops the lesson was cheap;
if it hits, it hit on a story rather than a niche.

### HN is decoupled from the teasers

The campaign doc assumed week 1 warms an audience for a week-2 HN launch. That is wrong:
**HN traffic is not a function of follower count.** It is title, timing, and artifact
quality; 160 X followers contribute ~nothing to whether it lands.

So the only gate on HN is **artifact readiness + R5 grading**, not audience warming. If
R5 grades Tuesday and the repo and site page are ready Thursday, fire Thursday. The
LinkedIn/X teasers run on their own clock serving inbound, which is a separate goal.

Post the **repo**, not a blog post. Lead the title with the finding, not the framework —
HN is allergic to self-promotion and fond of negative results and methodology. The
`Show HN:` tag has no measured advantage after controls. Fires once.

### Visual assets — brief for a separate agent

Benchmark content lives or dies on the images. **These are not generated here** — this
section is the brief to hand a fresh agent.

**Hard technical constraint:** the repo uses committed SVG (GitHub strips `<style>`,
`<script>`, inline SVG), but **X and LinkedIn cannot render SVG in a post**. Every chart
therefore needs a PNG export sized for social alongside the SVG for the repo.
`assets/make_charts.py` already generates light/dark from one definition — keep that so
themes cannot drift, and add the social PNG as a third output.

| Asset | Used by | Notes |
|---|---|---|
| **Rounds results table** (arms x rounds, verdict column) | LinkedIn hero, social preview | The most reused asset. Must be legible at phone width. |
| **R5 2x2** — Opus 5 / Sonnet 5 x scaffolded / not | The R5 launch, HN, everything | The most important image in the campaign. Worth disproportionate effort. |
| **Contamination distribution** — 72/100 instances partly recalled | Contamination post | Should make "most of this benchmark is memorized" visible in one glance. |
| **Fabricated-timing evidence** — reported vs actual | Agent-that-lied post, IG reel | A diff or side-by-side. The story is the evidence; make the receipt the image. |
| **Pre-registration receipt** — git commit timestamp before the run | Why-pre-register post | The screenshot of the commit is the whole argument. |
| **Infra incident** — disk at 2GB, the 135GB VHDX | Infra war story | Real screenshots the owner already has. |
| **Social preview card** 1280x640 | Every link posted anywhere | Exists at `assets/social-preview.png`. **No API** — upload by hand at Settings → General → Social preview. |

**Design constraints:** exactly two semantic colors (arm A, arm B); everything else is
text. Charts must read at phone size, since most LinkedIn and X consumption is mobile.
Charts and page must look like one document — independently-styled SVGs inside a
differently-styled page is the most common cause of "it looks off."

### Vocabulary for critiquing the site page

For when the page looks bad and the problem is hard to name:

1. **Where does the eye land first?** Same visual weight everywhere means no entry point.
   The results table should dominate the first screen with nothing competing.
2. **Vertical rhythm.** Is each heading visibly closer to the text it owns than to the
   section above it? When that is off the page reads as mush though nothing is wrong.
3. **Accent count.** `--armA`, `--armB`, `--cotton-candy`, `--blush-rose`, `--platinum` is
   too many. Past ~2 accents, color stops meaning anything.
4. **Do charts and page look like the same document?**
5. **Measure.** 74ch is right. Do not let it grow.
6. **Table and link styling** — inherited defaults are the tell that a page was assembled
   rather than designed.

One change at a time.

---

## Topic 4 — positioning, and build vs pre-sell vs deliver by hand **CONFIRMED**

### The public database is not a product. It is a content asset.

A website showing the same listings as the community GitHub internship repos has **zero**
value — those are free, updated daily, and already canonical. Do not try to win there.

The public DB's three jobs:

1. A URL the reels can point to that is not a signup wall.
2. Proof the sourcing is real — people believe a thing they can look at.
3. A permanent, visible argument for signing up.

The third is the trick, and it means the page should be **honest about being commodity**:
*"here is every opportunity I found. The useful part is which ones are for you."* Its own
uselessness is the pitch. If it takes more than ~2 days to build, the wrong thing got built.

### Where the value actually is

| Layer | Value | Defensible | Who else has it |
|---|---|---|---|
| Job listings | high, commodity | **no** | everyone |
| Eligibility filtering (can *I* apply) | medium | weak | partially |
| Breadth — internships + scholarships + grants against one profile | medium-high | medium | basically nobody |
| What the application actually asks for (`sf requirements`) | high | medium-high | **nobody** |
| **Warm intro path to a human at that company** | **very high** | **high** | badly, expensively |

**The depth play is the warm intro.** Everything above it is table stakes that gets you
in the door.

### Which warm intro — the distinction that matters

- *"Here's the recruiter's contact"* — Apollo, Hunter and RocketReach all sell this. Value
  anyone can buy is not a moat. Keep as a fallback, never as the pitch.
- *"You met this person at an event in March; they now work where you're applying"* —
  nobody has that data. It exists only because he was in the room, and it is the
  difference between a cold email and a real one. **This is the product.**

### Demonstrate publicly, deliver privately

The question was whether `sf requirements` belongs in the public DB or only in the
hand-made lists. Neither:

- On every row → the differentiator is given away and paid for forever.
- Only in the DM → nobody browsing knows it exists, and friction kills it.
- **Run it once on ~20-30 rows, show those in full, lock the rest.** Bounded one-time
  cost, the value is *demonstrated rather than described*, and several hundred locked rows
  are a standing reason to sign up.

No scarcity theater is needed on the demo. Scarcity applies only to manual fulfillment
("first 20"), where it is simply the truth.

This is also the answer to the hackathon-project fear. Those die because value was
*described* on a landing page. A visible, working, obviously useful thing on 30 rows
cannot be described away.

### The builder trap — where it actually is

Building the three things the customer named (agent-filled profile, referral connections,
resume rewrite) is not the trap; that is a spec. **The trap would be polishing onboarding
and a dashboard before knowing whether the referral play lands.**

### Sell the full thing by hand, at full price, on Aug 17

The reframe: **you sell the outcome manually first, and building is only reducing your own
cost to deliver it.** The test for having a product is not "is it built" — it is *can you
do it once, by hand, for one person, and get a real reaction.*

Hand the AMD friend 10 internships he is eligible for, what each application demands, and
for three of them a named person he has a genuine connection path to. If he reacts, there
is a product, and it can be charged for that day with nothing automated.

**"The full thing" is defined as: personalized opportunity feed + the referral path for
each one.** Resume rewrite and drafting are later. Listings are table stakes.

| | What |
|---|---|
| **Aug 17-23** | Deliver the full experience by hand to ~10 people. Charge the friend. This *is* selling the full thing. |
| **Aug 24-30** | Automate whichever part hurt most to do manually. |
| **September** | The automated version is the product; a pricing page makes sense then. |

Too eager would be building onboarding *before* ten hand-deliveries — because those
deliveries are what tell you what onboarding must collect.

### Manual fulfillment is honest; implied automation is not

Delivering by hand is fine. Implying automation that does not exist is not. *"I ran my
tool and checked every result myself"* is true, and a better pitch than "it's automated" —
it says a human verified it.

### The flow, so the sequence is unambiguous

```
reel showcasing the product  ->  link in comment  ->  public DB (free, browsable)
                                                          |
                                    "want yours personalized?" -> DM
                                                          |
                                        run their profile -> send the list
                                                          |
                              (meanwhile building the automated version)
```

The hand-made lists are **fulfillment, not content** — they are never posted. One
exception worth taking: screenshot one list and post it. *"Here's what I sent someone who
asked"* beats any feature list, and proves the thing works.

### Cap the intake

The risk at scale is not cost, it is **latency**. If 200 people comment and lists take
four days, the goodwill is gone before the product exists. Cap publicly at **first 20** —
honest, and scarcity for free.

### Capacity

~16-20 hrs/week, 1-2 hrs/day plus weekends, agent-parallelized. The binding constraint is
not hours but **which hours must be his**: choosing which sources are worth having,
judging whether output is real, filming, and answering DMs. Agents take the rest.
