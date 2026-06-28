# Session 2 (Extract) — ticket drafts

Staging file for the three Extract tickets. Distilled from `REPO_CONTENT.md` →
*Settled design — Session 2 (Extract)*. **Not yet filed.** File as GitHub issues
(title `GH-<n>: <Title>`, labels `adw` + `feat`) once the fixtures exist; the AC
reference fixture files that must be saved first.

**Dependency order — 3 tickets, 2 waves.** The harness cuts every branch from
`main` and merge is a human gate, so dependent tickets can't stack overnight.
Build/merge **A** first; **B** and **C** both build on a `main` that has A's field
and are independent of each other (parallelizable).

**Fixtures to save first** (raw HTML, under `tests/fixtures/`):
- `lablab_executorch.html` — `https://lablab.ai/ai-hackathons/qualcomm-x-meta-executorch-hackathon`
  (hand-save in a browser, or `curl` with a desktop `User-Agent` — naive fetch 403s).
- `uwaterloo_grants.html` — `https://grants.uwaterloo.ca/`
- `oppsforyouth_grants_listing.html` — `https://opportunitiesforyouth.org/?s=grants`
- `oppsforyouth_detail.html` — one click-through detail page from that listing.

---

## Ticket A (Wave 1) — `feat`: Opportunity model — per-fact source spans + anchor

**Title:** `GH-<n>: Opportunity — store per-fact source span (provenance evidence)`

### Description

Foundation for Extract (S2). The `Opportunity` model (GH-1) records a provenance
**enum** per uncertain fact (`deadline`/`reward`/`cost` → `quoted|derived|none`) but
has **nowhere to store the evidence** — the verbatim source text a fact was read
from. Extract requires that evidence: it is the checkable receipt that separates a
legitimate `derived` value (computed later by the S6 parse layer from quoted text)
from a fabrication, and it is what lets the deterministic S6 layer resolve relative
values without a second LLM call.

This ticket **only** extends the model + store. No extraction logic. Single-user
system; no auth; no network in tests.

**Locked decisions (honor; see `REPO_CONTENT.md`):**
- Extract is **quoted-only**; derivation is deferred to S6. So the source span is
  the *verbatim quoted text*, stored alongside the existing provenance enum.
- For **relative** values ("closes Friday"), S6 needs an **anchor** (a page-stated
  date) to resolve them later; the page is gone by S6, so the anchor must be captured
  now. `first_seen` is a fallback anchor but is *when we fetched*, not *when the
  source was authored* — keep them distinct.

### Scope
1. Add nullable per-fact source-span fields mirroring the provenance fields:
   `deadline_source`, `reward_source`, `cost_source` (verbatim quoted text, or
   `null` when the fact is absent / `provenance = none`).
2. Add a nullable `source_observed_date` (the page-stated date used as the anchor for
   relative-value resolution; `null` if the page states none — S6 may fall back to
   `first_seen`).
3. Store round-trips the new fields; existing dedup/`last_seen` behavior unchanged.

### Acceptance criteria
- `Opportunity` has nullable `deadline_source` / `reward_source` / `cost_source` and
  `source_observed_date`; constructing with a `quoted` deadline + its
  `deadline_source` span is valid, and with `deadline=None`,
  `deadline_provenance="none"`, `deadline_source=None` is valid.
- A fact with `provenance != "none"` and a `null` source span is rejected (or
  documented as invalid) — a quoted/derived fact must carry its evidence.
- Store insert/get/list/update round-trips all new fields; the URL-normalization
  dedup and `last_seen` refresh behavior from GH-1 are unchanged.
- Unit tests cover the new fields incl. the null-deadline case and the round-trip; no
  network, temporary DB only.
- `uv run pytest -q` green.

---

## Ticket B (Wave 2) — `feat`: LLM extract contract (the spine)

**Title:** `GH-<n>: Extract — LLM contract: one fetched page → 0..N honest Opportunities`

**Depends on:** Ticket A merged (uses the source-span fields).

### Description

The Extract spine. Given the **already-fetched raw content of one source** (raw HTML
+ its `source_url`), produce **zero-or-more** `Opportunity` records whose facts are
honest. The LLM lives inside this box; no-fabrication + provenance are enforced here
or nowhere. Fetching, link-traversal, and real dedup are **out** (S3/S4/S5).

**Locked decisions (honor; see `REPO_CONTENT.md`):**
- **0..N** multiplicity: a detail page → one record; a listing → many **thin** items
  (title + url + whatever's on the listing). Output must distinguish "one detail"
  from "a list" via metadata.
- **Whole-record honesty:** never invent a whole opportunity; never merge two real
  ones.
- **Pipeline:** deterministic pre-clean (strip tags/boilerplate, but **preserve**
  fact-bearing structure — `<time>`, JSON-LD) → LLM for judgment (is-this-an-
  opportunity, segment, classify, provenance).
- **Quoted-only:** each fact stored as verbatim text with `provenance ∈ {quoted,
  none}` and its **source span** (Ticket A field); `derived` is **not** emitted here
  (S6's job). The LLM must also emit `source_observed_date` when the page states one.
- **Runtime LLM = Claude API** via the **official Anthropic SDK** (`anthropic`),
  model `claude-opus-4-8` (or `claude-sonnet-4-6`); structured output for the record
  shape. Spend is separate from the Claude Code subscription.

### Scope
1. A pre-clean step: raw HTML → reduced text, preserving `<time>`/JSON-LD/fact-bearing
   nodes.
2. An LLM extraction call (Anthropic SDK, structured output) producing 0..N records +
   per-fact provenance + source spans, with the no-fabrication / whole-record-honesty
   contract in the prompt.
3. A typed result that distinguishes a single detail record from a list of thin items.

### Acceptance criteria
- Given `tests/fixtures/uwaterloo_grants.html` (listing, facts inline), Extract
  returns the expected set of opportunities; each present fact carries
  `provenance="quoted"` + a source span that is a literal substring of the page; the
  multi-deadline case ("June 1st, and October 1st") is captured, not silently
  collapsed.
- Given `tests/fixtures/oppsforyouth_grants_listing.html`, Extract returns **N thin
  items** (title + url, deadline `null`/`none` because it's not on the listing),
  flagged as a *list*, with **no fabricated** deadlines.
- Given `tests/fixtures/oppsforyouth_detail.html`, Extract returns **one** record
  flagged as a *detail*.
- A fact absent from the page is `null` with `provenance="none"` and a `null` source
  span — **never** invented; no opportunity absent from the page is emitted.
- **Deterministic + offline tests:** the Anthropic SDK call is stubbed/recorded
  (e.g. a saved response per fixture); tests assert the parse → `Opportunity`
  mapping, provenance, source spans, and 0..N segmentation without network or live
  model calls.
- `uv run pytest -q` green.

---

## Ticket C (Wave 2) — `feat`: JSON-LD structured-data path

**Title:** `GH-<n>: Extract — JSON-LD path: parse opportunity-bearing schema deterministically`

**Depends on:** Ticket A merged. Independent of Ticket B.

### Description

The deterministic structured-data path. Parse `<script type="application/ld+json">`
for **opportunity-bearing** schema and map to `Opportunity` — no LLM, no tokens.
Composes with the LLM path: a JSON-LD page yields clean dates + cost while the LLM
still supplies fields the markup omits (the lablab fixture: `Event` gives dates +
free entry cost; the prize is only in prose).

**Locked decisions (honor; see `REPO_CONTENT.md`):**
- Only treat **opportunity-bearing** `@type`s as facts (`Event`, `JobPosting`,
  `Offer`); **ignore** site chrome (`WebSite`, `Organization`, `BreadcrumbList`,
  `CollectionPage`). "Has JSON-LD" ≠ "has your fields" — gate on `@type`.
- **Field mapping needs judgment, not a 1:1 copy:** an `Event`'s
  `startDate`/`endDate` are event dates, **not** the application deadline;
  `Offer.price`/`priceCurrency` is the **entry cost**, not the prize. Map
  conservatively; leave a field `null` rather than mis-assign.
- Facts read from markup are `provenance="quoted"`, with the JSON-LD value as the
  source span. JSON-LD is a *hint* (often incomplete/stale) — it passes the same
  no-fabrication gate; missing field → `null`/`none`.

### Scope
1. Extract and JSON-parse all `application/ld+json` blocks from raw HTML.
2. Select opportunity-bearing objects by `@type`; map their fields to `Opportunity`
   (title, source/apply url, cost from `Offer`, etc.) with quoted provenance + source
   spans; leave unmapped/absent fields `null`.
3. Return 0..N records (zero when only chrome schema is present).

### Acceptance criteria
- Given `tests/fixtures/lablab_executorch.html`, the `Event` block yields one record:
  `title="ExecuTorch Hackathon"`, `cost` mapped from `Offer` (free/`$0`) with
  `provenance="quoted"` + source span; `startDate`/`endDate` are **not** written into
  `deadline` (event dates ≠ deadline); the prize is **not** invented (absent → `null`,
  to be supplied by the LLM path).
- A page whose only JSON-LD is chrome (`WebSite`/`Organization`/`BreadcrumbList` — e.g.
  the oppsforyouth listing's site schema) yields **zero** opportunities from this path.
- Missing/`null` schema fields map to `null` with `provenance="none"` — never guessed.
- Tests run offline against saved fixtures; `uv run pytest -q` green.
