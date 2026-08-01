# REPO_CONTENT.md — product north star

The canonical statement of **what** scholarship-factory is and **why** — direction,
UX, requirements, and high-level architectural decisions. **Not** system design or
implementation (those live in `architecture.md` once we design them). This is the
doc that ticket bodies are distilled *from*; if a decision matters, it belongs
here, not only in a chat or a single issue.

**Living document.** It's grown through the owner's design sessions; refine it as
decisions settle. Mark anything still open rather than inventing it.

## What we're building

An **agentic opportunity-sourcing system**. A research agent takes a seed list
(Instagram/X accounts, subreddits, Devpost, scholarship platforms), fetches and
extracts structured **opportunities** (scholarships, fellowships, hackathons,
grants…), **follows links to discover more** opportunities beyond the seeds,
dedupes them, and keeps a fresh local database. A simple dashboard lets the owner
view them, filtered and ranked against their own profile.

**It is not just a scraper.** The "follow links to discover more" and the
extraction-with-judgment are why there's an agent in the loop.

## Who it's for

**Single user — the owner** (maybe a few friends later). This justifies the major
simplifications: SQLite, lenient security, no multi-tenant isolation, optimize for
development speed over scale. One cheap hedge is preserved against a future
multi-user world: every record carries an `owner` field (always `"me"` for now),
so going multi-tenant later is a non-migration rather than a schema rewrite. We do
**not** build auth/isolation now.

## v1 scope boundary

**In v1:**

- Source → fetch → extract opportunities as **structured facts**, with
  link-traversal discovery.
- Dedupe and persist to a fresh, queryable store.
- **Filter and rank** opportunities against an **applicant profile** for
  eligibility/fit.
- A **simple dashboard** to view the ranked opportunities.
- **On-demand refresh** of facts and status (deadline, availability).

**Out of v1 (deferred to v2 — these are *direction*, not commitments):**

- **No generated text.** v1 cards are **extracted facts only**. Drafting an
  application is v2.
- **No auto-apply.** The eventual direction is draft-only → semi-autonomous apply;
  none of it is in v1.
- **No scheduler / automatic refresh.** v1 refreshes only on demand.

## User journey (high level)

1. **Setup:** the owner provides a seed list of sources and an applicant profile.
2. **Source:** the agent works the seeds, extracts opportunities, follows links to
   discover more, dedupes, and stores them.
3. **Present:** the dashboard shows opportunities filtered + ranked against the
   profile; the owner browses what they're eligible for.
4. **Refresh:** on demand, the owner re-checks facts/status (e.g. a deadline) for
   opportunities they care about.

(Details of each step are design-session territory; this is the shape.)

## Locked design decisions

These are settled — honor them; don't re-litigate.

- **Never fabricate a value.** Especially `deadline` (the owner's #1 named bug): if
  it isn't literally on the source page, store nothing. A plausible-looking
  invented date is the worst possible failure of this system.
- **Provenance, not confidence.** Each uncertain fact carries a provenance enum
  `quoted | derived | none` (`quoted` = read verbatim; `derived` = the agent
  inferred/computed it; `none` = absent). This is **not** a confidence float —
  floats are false precision on a transformer and were explicitly rejected.
- **Facts are extracted, not generated** (see scope boundary). A `derived` fact is
  a computed inference (e.g. a relative date resolved to absolute), never invented
  prose.
- **`owner` seam** (above): every row carries it, always `"me"` for now.
- **Dedup (v1) = a heuristic** `UNIQUE` index on a **normalized** `apply_url`
  (lowercase host, strip tracking params, normalize trailing slash, http≡https).
  This is *not* true opportunity-identity — real cross-source dedup is a sourcing
  design topic, still open.
- **`source_url` (where facts were read) is distinct from `apply_url` (where you
  apply).** Usually equal today; they diverge once link-traversal lands. Keep both.

## Stack & architectural decisions (with rationale)

- **Python core + FastAPI** for the HTTP layer. Single language end-to-end; FastAPI
  is light and well-suited to a single-user local service.
- **SQLite** for storage. Single-user scale makes a server database unnecessary
  overhead; a file-backed DB is the right tool.
- **Claude API at runtime** (`claude-sonnet-5`; opus reserved if quality demands) for the
  research/extraction agent. Note this spend is **separate** from the Claude Code
  subscription that *builds* the repo. *(Open in the parking lot: whether to use a
  Claude subscription / headless instead of metered API to manage cost — revisit
  at the runtime-LLM decision.)*
- **The research system is multi-agent by direction.** Sourcing, crawling, and
  extraction are *not* assumed to be a single agent or a single LLM call — the
  topology is a system-design topic, still open. **v1 may ship with just one LLM
  element**; the multi-agent shape is the direction, not a v1 requirement.

## Carried-forward notes (from the foundation)

From GH-1 (the `Opportunity` model + store), two things later sessions must handle:

- `deadline` / `reward` / `cost` are stored as **strings**, not typed dates or
  decimals. Ranking ("sort by most money") and refresh (date math) will need a
  **parse layer** over these.
- On a dedup hit, the store refreshes only `last_seen`. **Field-level refresh on
  re-sight** (did the deadline change?) is the refresh session's job.

## v1 design-session roadmap

The remaining v1 topics, **ordered into design sessions**. Strategy locked:
**Fork A — pipeline-first / breadth.** Build the sourcing engine coherently
*first*, then surface it; accept that there's no visible product until ~Session 7.
Consequence: each sourcing session must be crisply testable on its own (fixtures +
unit contracts), since there's no UI to sanity-check against until late. This is a
plan, not a contract — each session re-cuts the next.

**Sourcing arc (the heart):**

1. **Session 2 — Extract.** Fixture page → trustworthy `Opportunity` facts;
   no-fabrication + provenance enforced here or nowhere. The spine — everything
   downstream consumes its output. Goes first despite being runtime-downstream of
   Fetch, because it's the only piece testable with zero upstream built.
   Precondition: collect a few *real* saved pages first (IG caption, Devpost
   listing, scholarship detail) so the contract is designed against real input.
2. **Session 3 — Fetch + Source adapters.** Seed list → normalized fetch targets →
   bytes. Where the ugly reality lives: rate limits, the IG/X auth wall, what "raw
   content" is per source type. *(May split — auth-walled adapters could be their
   own session.)*
3. **Session 4 — Traverse.** Link-discovery — the agentic core, the reason this
   isn't just a scraper. Depends on Extract (find candidate links) + Fetch (pull
   them).
4. **Session 5 — Identity / dedup.** Real cross-source opportunity-identity,
   replacing the URL-equality placeholder — meaningful now that Traverse produces
   the same opportunity from two sources.

→ End of Session 5: a real corpus flows into the store.

**Consumer side:**

5. **Session 6 — Parse layer + Ranking vs. Profile.** Typed dates/money over the
   string fields, plus the applicant-profile model and eligibility/fit matching.
6. **Session 7 — FastAPI endpoints + Dashboard.** First time the owner *sees* it.
7. **Session 8 — On-demand refresh / lifecycle state machine.** Re-check a
   deadline, field-level refresh on re-sight. *(Lighter than the rest — v1 refresh
   is on-demand only.)*

Parking lot (owner's project memory `scholarship-factory-v1-design`):
subscription-vs-API cost, persistent personal context, quota/idempotency mid-run,
IG/X auth-walled adapters, self-healing.

## Settled design — Session 2 (Extract)

Output of the Extract design session. Ticket bodies (`docs/s2-extract-tickets.md`)
distil from here. The box: **given the already-fetched raw content of one source,
produce zero-or-more `Opportunity` records whose facts are honest.** The LLM lives
inside this box; no-fabrication + provenance are enforced here or nowhere.

**Locked decisions:**

- **Multiplicity is 0..N.** One page may yield zero, one, or many opportunities. A
  *detail* page → one; a *listing* page → many **thin** items (title + url +
  whatever's on the listing; the deadline often isn't — it lives on the detail
  page, which is **Traverse's (S4)** job to reach). Output must distinguish "one
  detail" from "a list" via metadata so downstream can tell them apart.
- **Whole-record honesty.** Never fabricate a whole opportunity that isn't on the
  page; never merge two real ones into one. This is the 0..N analogue of the
  per-field no-fabrication rule.
- **Two paths, by source shape.** (a) **Structured/JSON-LD** — deterministically
  parse `<script type="application/ld+json">` for *opportunity-bearing* `@type`s
  (`Event`, `JobPosting`, `Offer` — **not** `WebSite`/`Organization`/`BreadcrumbList`,
  which are site chrome) and map to the model. (b) **LLM** — deterministic
  pre-clean (strip tags/boilerplate → reduce noise *without shredding fact-bearing
  structure like `<time>` or JSON-LD*) then an LLM for the judgment a selector
  can't make: is-this-an-opportunity, segment into N, classify fields, assign
  provenance. The two compose: a JSON-LD page can give clean dates + cost while the
  LLM still supplies the prize from prose (see the lablab fixture).
- **Why LLM, not a deterministic scraper:** the niche, prose-only sources with no
  structured data are the gold mines (well-structured sources are the most-competed).
  Judgment — segmenting, classifying, deciding is-this-an-opportunity — is where the
  LLM earns its keep. The deterministic pre-clean is a *cost* decision (raw HTML is
  5–10× the tokens of cleaned text), not a quality one.
- **Extract is quoted-only; derivation is deferred to S6.** Extract stores facts as
  the **verbatim quoted text** (`deadline = "closes Friday"`, provenance `quoted`)
  plus, per fact, **the source span it was read from** and, for relative values, the
  **anchor** needed to resolve them later (e.g. a page-stated date). The risky
  transform ("closes Friday" + anchor → a date; "$5k/yr × 4" → total) is done by the
  **deterministic** S6 parse layer (`dateparser`/`dateutil` + arithmetic), which sets
  provenance `derived`. **No second LLM call** — the LLM does the reading once; S6 is
  a library. Unresolvable → `null` (the deterministic boundary self-enforces
  no-fabrication). The captured source span is the checkable receipt that separates a
  legitimate derivation from a fabrication.
- **Field mapping needs judgment even from JSON-LD.** Schema fields don't map 1:1 —
  e.g. an `Event`'s `startDate`/`endDate` are event dates, **not** the application
  deadline; `Offer.price` is the *entry cost*, not the prize. JSON-LD is a *hint*,
  often incomplete or stale, not ground truth — it still passes the no-fabrication /
  provenance gate.
- **Access is not Extract's problem.** Auth walls / 403s (lablab's anti-bot, IG/X)
  are **S3 Fetch**. Extract works on already-fetched content; fixtures are hand-saved
  raw HTML. (Noted S3 intel: lablab's 403 is a `User-Agent` check, not real auth.)

**Fixture set (the acceptance tests):** raw HTML, saved under `tests/fixtures/`.
- `lablab` ExecuTorch hackathon — JSON-LD `Event`+`Offer` (dates + free cost) **plus**
  prize only in prose → exercises the JSON-LD path, the LLM path, and the seam.
- `grants.uwaterloo.ca` — static prose listing, facts inline (`Up to $7,500`,
  `Application Deadline (2 annually): June 1st, and October 1st`) → LLM path, 0..N,
  multi-deadline mess.
- `opportunitiesforyouth.org/?s=grants` — listing (thin items, deadline on detail
  pages → traversal coupling) **plus** one click-through detail page (rich 0..1).

**Ticket shape — 3 tickets, 2 waves** (the harness cuts every branch from `main`
and merge is a human gate, so dependent tickets can't stack overnight; split by
dependency layer, sequence by merges):
- **Wave 1 — Ticket A:** add per-fact **source-span** fields (+ anchor) to the
  `Opportunity` model + store. Shared dependency; merges first.
- **Wave 2 (after A merges; B and C are then independent):**
  - **Ticket B** — the LLM extract spine (clean → LLM → 0..N, provenance, source
    spans, fixture-tested).
  - **Ticket C** — the JSON-LD structured path.

## Settled design — relevance + the feedback loop

Added once a real corpus existed and the problem turned out to be *relevance*,
not extraction: 30 honestly-extracted opportunities, almost none of them aimed
at the owner. Deterministic filters could not fix it — nothing on those pages
says "not for Canadians", they are simply aimed elsewhere.

**Locked decisions:**

- **Two questions, two mechanisms.** `rank.py` stays deterministic and answers
  *can I apply at all* — a wrong answer there silently hides a real
  opportunity, so it keeps hard filters, no LLM, no score float. `relevance.py`
  answers *would I want to*, where being wrong only reorders a visible list.
  Only the second question gets an LLM. The earlier "no LLM in ranking"
  decision is therefore narrowed, not overturned.
- **Fit is `high|medium|low` with a written reason**, never a float — same
  objection to false precision that produced the provenance enum. An
  opportunity the model skips is `medium` ("not judged"), never `low`: silence
  is not a negative judgment.
- **Relevance never touches facts.** It reads stored opportunities and writes
  only an ordering plus a reason, so it cannot invent a deadline.
- **Scores are persisted** (`relevance` table, refreshed by `sf rank`). The
  dashboard reads them, so opening the page costs nothing.
- **The feedback loop learns by prompt, not by training.** Two memories,
  because they decay differently: recent decisions quoted verbatim as few-shot
  examples, plus a distilled written preference summary re-generated every few
  decisions. The summary is human-readable and hand-editable on purpose — the
  owner can see and correct what the system thinks they want.
- **Decisions are their own dimension**, not `Opportunity.status`: that column
  is the freshness lifecycle and `refresh` overwrites it, which would erase a
  decision parked there.
- **Pagination is deterministic** (`rel="next"` only). Link *text* ("Next",
  "older posts") is not consulted — a missed page is much cheaper than walking
  a run into the wrong part of a site.

**Known open:** thin listing items with no eligibility text rank `medium`
("too thin to judge") — the ranker is honest about it, but the fix is
traversing to their detail pages, i.e. a higher `--page-cap`/`--max-pages`,
which costs calls. Also open: sources aimed at Canadian students; the
aggregators that serve that audience mostly sit behind 403 bot walls.

## Direction change — toward the daily loop and drafting (owner decision)

The owner's stated target: the system runs unattended, and they spend ~20
minutes a day approving what it flagged and reviewing drafts it prepared. That
crosses three v1 boundaries above, deliberately and on the owner's instruction.
Recorded here rather than left to drift:

- **"No scheduler / automatic refresh" is lifted.** `sf poll` is one unattended
  pass (source -> score -> digest) intended for Task Scheduler; see
  `docs/operating.md`. On-demand refresh still exists and is unchanged.
- **"v1 stores no personal data" is lifted**, narrowly. `context.py` stores the
  applicant's own material - facts, education, awards, experience, projects,
  past essays, referees, documents - because a draft cannot be written without
  it. Same local SQLite file, unencrypted, single user. The database and
  `context.toml` are gitignored; nothing personal leaves the machine except
  inside the prompts sent to the LLM provider, which the owner should know.
- **"No generated text" still holds.** The two *inputs* to drafting now exist -
  the applicant's context, and `application.py` reading what a given
  application asks for - but nothing generates an application yet.
- **Auto-submission is ruled out, not deferred.** The owner chose draft-only:
  the system prepares text against the real prompts and the owner pastes it.
  No browser automation, no submission. Beyond the engineering cost, many
  awards require the applicant's own writing and some ask applicants to declare
  AI use (the DLGS form we tested asks exactly that), so an unattended
  submission is the one failure mode that could disqualify a real application.

**Maturity, honestly:** sourcing and triage work end to end. Drafting does not
exist. The gap between "it found this for you" and "it applied for you" is
still most of the remaining work.
