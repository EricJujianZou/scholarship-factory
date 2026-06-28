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
- **Claude API at runtime** (`claude-opus-4-8` / `claude-sonnet-4-6`) for the
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
