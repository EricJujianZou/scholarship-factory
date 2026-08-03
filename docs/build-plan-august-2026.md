# Build plan — August 2026

The engineering companion to `gtm-august-2026.md`. That doc says what to *post* and
*why*; this one says what to *build*, by when, and how you know it worked.

**How to use this:** each week has exactly one goal, a list of what to do, and a
**verification metric** that is checkable rather than felt. A week is not done because
the time ran out — it is done when its metric passes. Written at high level on purpose:
detailed implementation belongs in a fresh session per item.

**Capacity assumed:** ~16-20 hrs/week (1-2 hrs/day plus weekends), agent-parallelized.
The hours that must be the owner's own: choosing which sources are worth having, judging
whether output is real, filming, and answering DMs. Agents take everything else.

**The one rule:** do not build the things whose cost is not code. Code is cheap now;
inventory, per-user LLM spend, trust, and the owner's own hours are not.

---

## What already exists

Worth knowing before planning anything new — a lot of this is done.

| Built | Where |
|---|---|
| Extract (LLM + JSON-LD paths), provenance, no-fabrication | `scholarship_factory/` |
| Fetch + polite fetcher + robots handling | `fetch.py` |
| Link traversal, dedup on normalized `apply_url` | pipeline |
| Deterministic ranking (can I apply) + LLM relevance (would I want to) | `rank.py`, `relevance.py` |
| **`sf requirements`** — reads an apply page, returns essay prompts, word limits, documents, referees | `application.py` |
| Unattended pass (`sf poll`) + digest | `cli.py` |
| Local dashboard that shells out to the CLI, one job at a time | `jobs.py` |
| Luma scrape → enrich → rank → review gate → send | `luma-connect/` |

**Not built:** anything multi-user (every row is `owner="me"`), any hosted surface, any
generated application text, any onboarding.

---

## The feature ladder — what is in, what is out

| Layer | Status | Posture |
|---|---|---|
| Job/opportunity listings | commodity | ingest cheaply, never pitch |
| Eligibility filtering | built | keep |
| Breadth (internships + scholarships + grants, one profile) | built, thin inventory | **fix inventory** |
| What the application asks for | built | **demonstrate on ~30 rows, lock the rest** |
| Warm intro path to a human at the company | not built | **the depth play — manual first** |
| Resume rewrite | not built | manual first, only if the 10 deliveries prove demand |
| Application drafting / auto-apply | ruled out | not building |

---

## Week 1 — Aug 3-9 — **Coverage**

The only thing that matters this week. Nothing downstream is worth building against 30
opportunities, ~none of which suit the ICP.

### Do

1. **Deterministic ATS adapters.** Greenhouse, Lever and Ashby expose public per-company
   JSON endpoints (e.g. `boards-api.greenhouse.io/v1/boards/{company}/jobs`). Structured,
   free, no bot wall, **no LLM call**. One request returns every open role at a company.
   This is where volume comes from.
2. **Public GitHub internship-list ingestion.** The community Summer-2027 internship repos
   are structured markdown, updated daily, no bot wall. Parse to `Opportunity` rows and
   dedupe against the ATS rows.
3. **Keep LLM extraction for the long tail only** — prose scholarship and grant pages,
   where judgment actually earns its cost. Do not spend LLM calls on structured job data.
4. **Dogfood daily.** Run against the owner's own profile every day this week and read the
   output honestly.

### Verification metric

- **≥300 internship rows** and **≥50 scholarship/grant rows**, deduped.
- **≥80%** of rows have an `apply_url` that actually loads.
- LLM spend on job-board rows: **zero**.

### Gate — Sunday Aug 9 (blocks week 2)

Rank the corpus against the owner's own profile and read the **top 20**. At least **10**
must be things a Waterloo undergrad could genuinely apply to this cycle, each with a real
deadline (not `null`, not `"Unspecified"`) and a working apply link.

**If it fails, week 2 slips and coverage continues.** A beautiful browsable page over bad
inventory is worse than no page.

---

## Week 2 — Aug 10-16 — **The public surface**

Cheap on purpose. This is a content asset, not a product (see `gtm-august-2026.md`
Topic 4). **If it takes more than ~2 days, the wrong thing is being built.**

### Do

1. **Public browsable page.** Deployed, no auth, filter by type and deadline. Copy is
   honest about being commodity: *"here is every opportunity I found — the useful part is
   which ones are for you."*
2. **Demonstrate-publicly-deliver-privately.** Pre-run `sf requirements` on **20-30 rows**,
   one time, bounded cost. Those rows display it in full and are visible to anyone. Every
   other row shows an obvious locked state. This is the entire conversion mechanic.
3. **Email capture.** A field and a store. Nothing clever.
4. **A visual pass** so it does not read as a weekend project.

### Verification metric

- A stranger on a **phone** finds 3 opportunities relevant to them in **under 60 seconds**.
- The locked state is understood without explanation (ask 2 people, do not lead them).
- Email capture round-trips end to end, verified with a real address.

---

## Week 3 — Aug 17-23 — **Sell the full thing, by hand**

Ship almost nothing. Deliver everything. This is the week that decides what week 4 builds.

### Do

1. **Post the showcase reel** → link in comment → public DB. Cap intake publicly at
   **first 20**.
2. **Hand-deliver the full experience** to ~10 people: 10 opportunities they are eligible
   for, what each application asks for, and — for 3 of them — a named person with a
   genuine connection path.
3. **The referral path is a manual query this week.** `luma-connect`'s `state.db` already
   holds scraped, enriched people. Joining "who did I meet" against "where is this person
   now" is done by hand for 10 people. Do not build the matcher yet.
4. **Charge the AMD friend $20.** Not for the money — for the data. What someone tells you
   after paying differs from what they tell you free.
5. **Start onboarding, informed by the deliveries** — not before them. The ten deliveries
   are what tell you which fields actually matter.
6. **Strip auto-connect from luma-connect** (`send.py`). The pivot is warm-intro discovery,
   not automated invitations; removing the send path removes the ToS exposure.

### Verification metric

- **10 lists delivered**, each within **48 hours** of the request.
- **≥1 paying pilot.**
- A written note per delivery: which part they reacted to, and which part took longest to
  produce. This is the week's real output.

---

## Week 4 — Aug 24-30 — **Automate the worst part**

What gets built is **decided by week 3's notes**, not chosen now. The candidates, in
likely order:

- Onboarding / profile capture (if collecting details was the bottleneck)
- Referral matching (if the manual join was the bottleneck)
- `sf requirements` on demand at signup (if that was the reaction moment)

### Do

1. Build the single slowest manual step from week 3.
2. Multi-user only as far as that step requires. The `owner` seam already exists on every
   row; do not build full auth speculatively.
3. Launch the automated version — **once**.

### Verification metric

- The step that took longest in week 3 now takes **under 20%** of its manual time.
- One user completes the automated path end to end **without the owner touching it**.

---

## Not building — and why

| | Why not |
|---|---|
| Auto-apply / submission | Ruled out by the owner. Some awards require the applicant's own writing and some ask applicants to declare AI use. |
| Application drafting | Downstream of validation; nothing generates text in v1. |
| Full auth / multi-tenancy | Speculative until week 4 tells you how much is actually needed. |
| Recruiter contact scraping | Commodity — Apollo, Hunter, RocketReach sell it. Value anyone can buy is not a moat. |
| Resume rewrite | Only after the 10 deliveries show people ask for it. |
| A scheduler for public-DB freshness | Real, but not before there is an audience to keep it fresh for. |

---

## Open decisions that block build work

- **Where the free/paid line sits.** Browsing is free; is ranking free and requirements
  paid, or is ranking the line? Decides what the public page may show. See
  `onboarding-plan-DRAFT.md`.
- **Which onboarding approach** (RPG-style pathway / downloadable `context.toml` /
  agent-from-memory). Do not decide before the week 3 deliveries.
- **Hosting** for the public page and, later, accounts. Not chosen.
