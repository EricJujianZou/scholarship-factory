# audience.md — UGMI (ugmi.ca)

Who actually buys a $15/mo concierge internship list, in their own words. Every claim is
tagged: **[T1]** = our own behavioral data (content-machine repo, site), **[T2]** =
community ethnography (Blind threads, press quoting r/csMajors / r/uwaterloo culture;
direct Reddit crawl is blocked to our tooling, so exact-thread citations are thin —
treat [T2] phrasing as strongly attested but re-verify before quoting in ad copy),
**[T3]** = published research (source named), **[inference]** = our reasoning.

Researched 2026-08-06 (audience-hook-research phase 1). Status: **owner-reviewed 2026-08-06.**
Owner corrections: no DM sales conversations have happened yet — §1's who-pays
claims describe the *designed* funnel and are untested against real buyers
[owner]. Owner's working assumption: college students can spare ~$20/mo, so
budget is not the binding constraint; trust is [owner assumption, untested].

## 1. Who decides and pays

- **The student decides.** The entire funnel is a 1:1 DM sales conversation with the
  student — reel → "comment LINK" → manual DM → Stripe link [T1: strategy.md funnel].
  The site's pitch addresses "you" directly and asks for *their* resume + 3 lines [T1:
  site/index.html]. There is no parent-facing surface anywhere in the funnel.
- **The money is often parent-subsidized, but invisibly.** Fewer than half of 18–24s
  fully self-pay their subscriptions; they rotate, share, and split [T3: Chargeback/Resubs
  subscription data 2025–26]. ~50% of parents financially support an adult child; working
  Gen Z receives the most, avg $1,813/mo [T3: Savings.com via Fortune, Mar 2025]. $15/mo
  sits under the "don't have to ask" threshold — roughly one food-delivery order
  [inference].
- **Parents are validators, not deciders.** strategy.md already encodes this: LinkedIn is
  "where a student (or their parent) who found him on IG goes to decide he's real" [T1].
  Expect a pre-purchase background check of @sleppyeric, not a parental veto on price
  [inference].
- **Waterloo-style co-op students have their own income** from paid work terms; for them
  $15 is trivially affordable and the constraint is trust, not budget [T2 + inference].
- **Implication:** price is not the objection. The objection is "is this guy real / is
  this a grift" (see §6). Renewal, not purchase, is where the $15 gets re-examined
  [inference; matches strategy.md Phase 2 retention question, T1].

## 2. Jobs-to-be-done (in their words)

- **"Just tell me which ones I'm actually eligible for."** The free DB is 1,427 listings;
  the paid pitch's own copy is "you are eligible for a fraction of it" [T1: site]. The 3
  qualifying lines the product asks for (work auth, target terms, location) *are* the
  eligibility anxieties [T1].
- **"Find me the actual person to contact."** The only repeat-outlier content is the 68k
  PitchBook *contact-finding* reel and its 37k repost — not listings, not scholarships
  [T1: strategy.md]. The paid offer ships "the actual person to contact at each company"
  [T1: site]. This is the proven hook of the whole business.
- **"Get me out of the 40 tabs."** The site's own sign-off: "Built by one Waterloo student
  who got tired of 40 tabs" [T1]. The job is outsourcing the spreadsheet, not learning to
  make a better one.
- **"Make my cold message not cringe."** Free outreach template for referrals and coffee
  chats [T1: site]; cold outreach is a known skill gap they'll watch a reel about but
  freeze on executing [T2].
- **"Don't let me miss a deadline."** Deadlines are the product's built-in urgency [T1:
  strategy.md]; "soonest deadline" is the DB's default sort [T1: site].
- **"Get the return offer."** Late-August return-offer decisions are a timed anxiety the
  content calendar already targets [T1: queue/2026-08-05-return-offer-side-quests.md].
- **"Beat the pile."** The template's own line: "before I send my application into the
  pile" [T1: site]. Volume feels futile — class of 2025 submitted 24% more applications
  than 2024, which submitted 64% more than 2023 [T3: Handshake].
- **Status job: have an answer to "what are you doing this summer?"** The deliverable is
  partly a talking point — proof they're being proactive [T2 comparison culture +
  inference].

## 3. Anxieties and status pressures

- **The market is objectively the worst of their lifetime.** Returning-student
  unemployment averaged 17.9% May–Aug 2025 — worst since 2009 excluding 2020 [T3:
  Statistics Canada LFS]. Youth unemployment hit 14.7% in Sept 2025, worst since 2010
  [T3: StatCan]. 37% of Canadian 18–24s now name jobs/unemployment a top national issue,
  double the prior year's 18% [T3: Angus Reid]. 61% of the class of 2026 find job-market
  news pessimistic, up from 50% for 2024 [T3: ZipRecruiter/NACE-cited grad reports].
- **Ghosting is universal and radicalizing.** 100% of job seekers report being ghosted at
  least once [T3: Jobright]; "career catfishing" is Gen Z's named revenge behavior [T3:
  Fortune, Jan 2025]. They apply into a void and know it.
- **Comparison culture is the sharpest pressure.** Offer announcements are public
  ("thrilled to announce my incoming internship at ___"), co-op cohorts are legible
  rankings, "Cali or bust" is a live Waterloo status hierarchy [T2]. The social failure
  mode is not poverty — it's being the one still searching when the group chat has
  offers, doing a visible "unemployed arc" [T2].
- **Experience compounds and they know it.** Grads with internship/co-op experience are
  hired at 81.6% vs 40.7% without [T3: academicjobs.com 2026 grad report] — each missed
  summer feels like a permanent fork.
- **International students carry a second-tier anxiety: work authorization.** It's the
  first eligibility wall and often unstated in postings — exactly why "I can work in
  [Canada]" is one of the product's 3 onboarding lines [T1: site; T2].
- **Desperation raises, not lowers, scam vigilance.** This cohort has been farmed by
  no-essay-scholarship sweepstakes and course-selling grifters for years; they treat
  urgency + payment as a predator signature [T2; T1: the no-essay-raffle reel exists
  *because* teaching the tell earns trust].

## 4. Context of use

- **Device and route:** phone, inside the Instagram in-app browser, arriving from a
  manual DM link seconds after commenting "LINK" on a reel [T1: funnel]. Assume
  one-handed mobile, mediocre in-app-browser performance, and no saved passwords —
  Stripe checkout must survive the IG webview [inference].
- **Mental state:** mid-doomscroll, half-anxious, half-entertained. They just watched a
  weird 34s resource reel and made a micro-commitment (the comment). The DM that follows
  is a peer conversation, not a checkout — the sale's warmth lives there [T1: strategy.md
  "every DM is a sales conversation"].
- **Attention budget: seconds, spent front-loaded.** Own data: ~11s avg watch on the
  winning reel arm; losses concentrate in the FIRST seconds; 3-second skip rate is the
  gating metric [T1: learnings.md]. The landing page inherits this — the free DB must
  demonstrate value before any scroll commitment [T1: site is built this way — hero
  clears a 900px fold into listings].
- **Time of day:** evenings/late night, deadline-adjacent panic windows; seasonality
  peaks Aug–Sep (fall recruiting for Summer 2027 opens; return-offer decisions land late
  Aug) [T1: queue timing notes; T2 recruiting calendar; inference].
- **This is already their career channel, not an interruption:** 76% of Gen Z use
  Instagram for career advice (only 34% use LinkedIn); 46% report securing a job or
  internship via TikTok; but 55% admit they've followed misleading guidance there [T3:
  Zety Gen Z Career Trends, Feb 2025] — high receptivity, high learned skepticism,
  simultaneously.
- **Sends are the distribution physics:** reels get DMed to a friend ("sends are the #1
  signal") [T1: learnings.md] — expect second-hand arrivals with zero context who never
  saw the original reel [inference].

## 5. Vocabulary

Glossary mined from the communities and our own assets. **(A)** = audience-native, use
freely in reels/DMs; **(O)** = already in our own copy, keep consistent. All community
terms [T2] unless tagged.

| Term | Meaning / usage |
|---|---|
| **cooked** (A) | Doomed. "The market is cooked," "I'm cooked." Default mood-word of r/csMajors. |
| **cracked** (A) | Exceptionally skilled. "Cracked intern shipped a whole feature." Aspirational identity. |
| **locked in** (A) | In deep focus mode. "Time to lock in for intern szn." |
| **return offer** (A) | Full-time/next-term offer from a current internship. The scoreboard metric of a summer. [Also T1: our reel uses it verbatim.] |
| **OA** (A) | Online assessment — the automated coding test gate. "Got an OA, then ghosted." |
| **ghosted** (A) | No response after application/interview. Universal experience [T3: Jobright 100%]. |
| **PFO** (A, Waterloo) | The rejection email ("please f— off"). Waterloo co-op slang: "collected 30 PFOs this cycle." High-value insider signal for content. |
| **WaterlooWorks / WW** (A, Waterloo) | The co-op job board; "continuous round," "rankings," "first round" are its mechanics and its complaint surface. |
| **Cali or bust** (A, Waterloo) | The status hierarchy: US/Bay-Area internship or failure. |
| **the mines** (A) | Grinding applications/LeetCode; "back to the mines." |
| **500 applications** (A) | The stock figure for spray-and-pray futility; application counts are trauma-flex currency [T3: Handshake volume data]. |
| **spray and pray** (A) | Mass-applying without targeting — what UGMI replaces. |
| **LeetCode / grinding LC** (A) | Interview-prep problem grind; "LC hards" as a status tier. |
| **referral** (A) | Internal employee vouch — widely believed to be the only way past the pile. The 68k reel's engine [T1]. |
| **coffee chat** (A) | Low-stakes networking call; what the free template books [T1: site]. |
| **cold outreach / cold DM** (A) | Unsolicited message to a stranger at a target company. |
| **the pile** (O/A) | Where un-referred applications go [T1: site template copy]. |
| **ATS** (A) | Applicant tracking system; "the ATS auto-rejected me" — the faceless enemy. |
| **ghost job** (A) | A posting that's up but never hiring. 2025-era distrust term; our "facts extracted, never invented" freshness panel answers it [T1: site]. |
| **new grad** (A) | The role category and the identity crisis; "new grad market" = the fear horizon. |
| **intern szn** (A) | Fall recruiting season for next summer. |
| **it's over / we're back** (A) | The bipolar market-sentiment meme pair; usable as hook framing. |
| **skill issue** (A) | Mock-dismissal of someone's struggle; self-deprecating when applied to self. |
| **nepo hire** (A) | Got the job through connections; the resentment word for referral culture's dark side. |
| **TC** (A, Blind-adjacent) | Total compensation; "TC or GTFO" energy leaks into csMajors. |
| **glazing** (A) | Excessive unearned hype; our anti-glazing voice is built against it [T1: no-essay-raffle reel]. |
| **AI slop** (A) | Low-effort AI-generated content; an accusation that kills reels in seconds [T1: the AI-edit arm lost first-seconds retention]. |
| **LinkedIn bro / cringefluencer** (A) | Hustle-culture poster monetizing motivation; the archetype we must never resemble [T2: r/LinkedInLunatics, Blind]. |
| **side quest** (O) | Unassigned side project that earns the return offer [T1: owner's reel vocabulary — a brandable term]. |
| **40 tabs** (O) | The manual-search pain state [T1: site sign-off]. |
| **u gon make it** (O) | The brand name expansion — riffs on "we're gonna make it" (WAGMI) crypto-meme optimism [T1: site; T2 meme lineage]. |

## 6. Disqualifiers (instant-bounce signals)

- **AI-content smell.** Our own A/B: generic hard-burned captions "reading as AI content"
  lost the first 3 seconds decisively (5s vs 11s avg watch) [T1: learnings.md]. On-page:
  stock hero images, em-dash-heavy corporate prose, "Unlock your potential" framing = slop
  flag [T2 + inference].
- **The career-coaching grift pattern.** This audience has a trained detector for:
  paywalled "secrets," blurred-name testimonials, countdown timers, "book a free call,"
  income-claim screenshots, "DM me 'BLUEPRINT'" auto-funnels [T2: Blind — coaches "just
  bring scam as value"; r/LinkedInLunatics]. The manual-DM rule (no automation) is
  already the antidote: an obviously-human reply is the differentiator [T1: strategy.md
  rule 2].
- **Email-before-value.** The no-essay-scholarship economy taught them "your email is the
  product" [T1: no-essay-raffle reel says it in their language]. The site's "no account,
  no email, no paywall on the list" is load-bearing trust copy — never regress it [T1].
- **Fabricated or fuzzy numbers.** They cross-check. Our own claims-audit discipline
  (never state an unverified number, no soft deadlines) exists because one caught
  fabrication ends the account [T1: queue-file claims audits].
- **Overpromised outcomes.** "Guaranteed interviews," "land FAANG in 30 days" = instant
  grift classification [T2]. The site promises a *process* (48h, one person, weekly list),
  never an outcome [T1] — keep it that way.
- **Corporate polish itself.** Too-slick reads as an ad; the weird one-person voice ("I
  read these myself. It is one person") is the trust asset, and sanding it off "optimizes
  for an audience he doesn't want" [T1: strategy.md non-goals].
- **Effort walls before proof.** Sign-up gates, multi-step forms, or an empty-feeling DB
  before value is shown → bounce within the seconds-long attention budget [T1 attention
  data + inference]. The free searchable DB *is* the proof; the paid pitch must stay
  downstream of it.
- **Subscription-trap smell.** Hard-to-find cancel terms trigger the same radar as grift;
  55% have already been burned by misleading career advice on these platforms [T3: Zety]
  — a one-line "cancel anytime, it's a Stripe link" defuses it cheaply [inference].

## Sources

[StatCan LFS Dec 2025](https://www150.statcan.gc.ca/n1/daily-quotidien/260109/dq260109a-eng.htm) ·
[StatCan youth labour](https://www.statcan.gc.ca/o1/en/plus/8640-youth-faced-challenging-labour-market-summer-and-september) ·
[Angus Reid](https://angusreid.org/economic-focus-concern-over-jobs-and-unemployment-skyrockets-among-young-people/) ·
[Fortune career catfishing](https://fortune.com/2025/01/09/career-catfishing-gen-z-ghost-interview-no-response-hiring-recruiter-work-interview-employer) ·
[Zety Gen Z Career Trends](https://zety.com/blog/genz-career-trends-report) ·
[Fortune parental support](https://www.fortune.com/2025/03/26/millennial-gen-z-adult-children-parents-monthly-payments-retirement) ·
[Chargeback subscription data](https://www.joinchargeback.com/blogs/subscription-spending-by-generation) ·
[2026 grad market](https://www.academicjobs.com/ca/higher-education-news/canada-post-secondary-graduates-job-challenges-2026-academicjobs-11341) ·
[ZipRecruiter grad report](https://www.ziprecruiter-research.org/annual-grad-report) ·
[Blind: coach grift](https://www.teamblind.com/post/career-whispererlife-coach-nonsense-8zus2ohk) ·
[Blind: LinkedIn cringe](https://www.teamblind.com/post/reddit-group-on-linkedin-cringe-influencers-xpbjxhw3) ·
[The Hub summer postings](https://thehub.ca/2025/05/31/chart-storm-three-charts-on-the-stark-decline-in-summer-job-postings-causing-sky-high-youth-unemployment/)

**Method note:** T1 files read: content-machine strategy.md, learnings.md,
analytics/x-profile-audit-2026-08-02.md, ideas/backlog.md, three student-facing queue
files, scholarship-factory site/index.html. Reddit is inaccessible to our crawler, so
Tier 2 rests on Blind threads and press quoting these communities — spot-check exact
phrases before using them in paid copy. Strongest through-line: proven demand is
contact-finding (68k/37k reels), and the dominant filter is grift-detection — every T1
asset that works leans into anti-glazing, no-email, one-person-voice positioning.
