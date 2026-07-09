# Session 3 — Fetch: design log (open, resume here)

Working doc for the Session 3 design. **Not settled.** It captures where the
Socratic design session paused so it can resume without re-deriving. Settled
decisions graduate to `REPO_CONTENT.md`; this file is deleted when S3 is done.

## Scope cut (locked with owner)

- **Take the split:** *open-web fetch* this session; **auth-walled adapters
  (Instagram / X) deferred to their own later session.** A seed list that can't
  reach IG/X is acceptable for now.
- The box: **seed list -> (adapters) -> normalized fetch targets -> (fetcher) ->
  raw bytes**, one target at a time. Hands `FetchResult` to Extract (S2).
- **Out:** extraction (S2, done), link-traversal/discovery (S4), dedup/identity
  (S5). Fetch pulls *one* target; it does not decide what to fetch next.

## How this session is being run (owner's calibration)

The owner gives **high-level UX only** and does **not** design the internals —
this is standard agent-scrape/rank/apply engineering with near-zero
wheel-reinvention. Claude (senior eng) makes the standard calls; the Socratic
loop is for the owner's **learning + critique after the fact**, not the source of
the design. So: default to the boring industry-standard answer for each fork
below, ship it as a ticket, and let the owner shred it Socratically later.

## The open problem (where the Socratic loop paused)

Posed to the owner, not yet answered: **where does `httpx.get(url).text` break
when it meets the real open web, at scale, across the four fixtures
(grants.uwaterloo static / oppsforyouth WordPress / lablab UA-gated / Devpost
JS-heavy), on a repeat run?** Produce the *taxonomy of problems* first — the
solution shape (one generic fetcher? per-source? headless? queue?) falls out of
which categories are real for v1.

**Resume by having the owner enumerate the failure categories, then reality-check
against the defaults below.**

## The five forks + Claude's default calls (critique these)

These are **provisional senior defaults**, chosen to be standard, not novel.
Each becomes a ticket only after GH-11 (the contract) merges (they depend on it).

1. **Static HTTP vs headless browser (JS-rendered — Devpost).**
   *Default:* `httpx` static GET first; add Playwright **only** when a real
   fixture proves the static path returns an empty SPA shell. Don't pay the
   headless weight on spec. → optional 6th ticket, deferred.
2. **Anti-bot / blocking on the "open" web.**
   *Default:* `User-Agent` override (kills lablab's 403 — already diagnosed as a
   UA check, not real auth), honest failure surfaced in `FetchResult`. No
   fingerprint-spoofing arms race in v1.
3. **Politeness / good citizen.**
   *Default:* one rate-limiter **per host** + respect `robots.txt`. Avoids IP
   bans; cheap insurance.
4. **Failure taxonomy + retry.**
   *Default:* exponential backoff (`tenacity`) on 429/5xx + timeouts; 4xx is a
   hard fail (don't retry a 404). Every outcome represented honestly in
   `FetchResult` (see GH-11).
5. **Caching / idempotency across repeat runs.**
   *Default:* cache raw responses keyed by URL + fetch-day; skip refetch within a
   freshness window so reruns mid-batch are cheap and safe. Field-level refresh
   ("did the deadline change?") stays S8's job.

**Adapter<->fetcher seam** (the session's central question, still open): default
is **adapters yield target URLs; one generic fetcher pulls them** — an adapter
knows "this seed type -> these URLs" (plain URL, Reddit public JSON, Devpost,
WordPress listing), the fetcher is source-agnostic. Confirm this seam before
building the adapters ticket.

## Ticket program (the ~10-ticket map)

**DONE — all six merged to `main` (2026-07-09):**

- **GH-11** — `FetchResult` contract (`fetch.py`). *Fetch foundation.*
- **GH-12** — Parse layer: typed deadline **dates** (`parse_dates.py`).
- **GH-13** — Parse layer: typed reward/cost **money** (`parse_money.py`).
- **GH-14** — Applicant **profile** model + store (`profile.py`). UX call:
  *minimal profile + tags* (region / education_level / field / tags / bio).
- **GH-15** — Seed-list model + TOML loader (`seeds.py`; adapters consume it).
- **GH-16** — Store-inspection dev CLI (`cli.py`, `sf` script).

GH-11/12 built by the harness overnight; GH-13–16 built **manually** after the
harness stalled (it re-ran completed-but-unmerged tickets instead of advancing —
root-caused + filed as engine `system-repair` **agentic-sdlc #92** (advance
without merge) and **#93** (don't commit per-run `state.json` / prd-shard merge
conflicts)). The `\ADW\ADW-scholarship-factory` task is **disabled** pending
those fixes — re-enabling before #92 lands will just churn again.

*Considered and declined (owner held the pipeline-first line):* FastAPI read
endpoints + a dashboard UI over the existing schema — both front-run the locked
"no visible product until S7" decision, so deferred.

**Next when design resumes:** the fetch chain proper — static fetcher (httpx +
UA + retry) → per-host politeness → source adapters → cache — all cut from the
now-merged `FetchResult` contract. Pick up the Socratic loop at the open problem
above.

**Queued — file only after their parent merges (dependency = merge cadence;
do NOT file early or the hourly build builds them against a stale `main`):**

- **Static fetcher** (httpx + UA + timeout + retry) — after GH-11 merges.
- **Per-host politeness** (rate-limit + robots.txt) — after the static fetcher.
- **Source adapters (open-web)** (plain URL / Reddit / Devpost / WordPress) —
  after GH-11 merges.
- **Fetch cache / idempotency** — after the static fetcher.
- **Ranking / eligibility vs. profile** — after GH-12+GH-13+GH-14 merge. *(Needs
  owner UX on what "fit/eligible" means — a genuine design input, not standard.)*
- *(optional)* **Headless/JS fetch** — only if a fixture proves it's needed.

## Throughput facts (why the plan is shaped this way)

- Hourly build runs `--max-tickets 1` → **~1 ticket/hour**, highest-priority
  first, each branched from *current* `main`.
- **Merge is a human-only gate** (HARNESS.md) → dependent tickets can't stack
  overnight; the dependency edge is **merge cadence**. Merge a parent in the
  morning → the next hourly run's child branches from the updated `main`.
- **Auto-merge** was considered: it *would* unlock overnight dependency-stacking
  but spends the human review gate and lets errors compound on `main`.
  **Decision: not for the first chain.** Load independent breadth instead;
  revisit once the test/review stages have proven trustworthy.

## Parking lot (deferred tangents)

- IG/X auth-walled source adapters → their own session (the split).
- Whether to bump `--max-tickets` on the scheduled job for more throughput/hour
  (still won't stack dependencies).
- Ranking "fit/eligibility" semantics → owner UX input needed before that ticket.
