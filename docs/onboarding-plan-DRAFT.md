# Onboarding & public-database plan — TO BE FINALIZED

**Status: draft, not decided.** Captured 2026-08-03 from the owner's thinking so it
survives the conversation. Nothing here is locked; `REPO_CONTENT.md` stays the north
star and this file does not override it. When these decisions settle, the survivors
move into `REPO_CONTENT.md` and this file is deleted.

## The shape

Two tiers, with the account as the wall between them.

**Tier 1 — the public generic database.** Anyone can browse it, no account. It shows
what the system has sourced, unfiltered and unpersonalized. Its job is threefold:
proof the thing is real, the reason a post has somewhere to point, and the surface
that gets found without a post. It deliberately does *not* customize — the gap
between "here is everything" and "here are the ten you can actually win" is the
reason to sign up.

**Tier 2 — the account.** Personalization, ranking against your own profile, and
(later) anything that writes on your behalf. Requires the applicant profile, which
is the thing that today lives in `context.toml` and is filled in by hand.

## The onboarding problem

Ranking is only as good as the profile, and the profile is a chore. Today it is a
TOML file the owner edits himself — fine for one user, fatal for signup. Every new
account has to produce that same object without a text editor. Three candidate
approaches, none chosen:

**Option A — "pick your class" (RPG-style pathway).** Onboarding as a sequence of
choices rather than a form: pick your path, and each pick writes a filter field
(citizenship, program, year, gender, race, financial need, etc.). The bet is that a
form people abandon becomes a flow people finish when it reads as character
creation. It also front-loads the highest-signal fields instead of burying them on
page three of a form.

**Option B — downloadable `context.toml` + "ask your AI agent to fill it out."**
Ship the schema, let the user's own agent populate it from their resume/LinkedIn,
they upload the result. Near-zero build cost. Assumes the user has an agent and is
comfortable driving it — true for a Waterloo CS audience, probably false past it.

**Option C — an `.md` agent setup built from memory, so no human fills anything.**
Raised by the first potential customer. The agent assembles the profile from what it
already knows about the user rather than asking. Least friction, most speculative,
hardest to get right without being wrong in ways the user cannot see or correct.

A and B are not exclusive: A as the default path, B as an "I'd rather do it myself"
escape hatch, is a plausible ship. C is a later upgrade to whichever wins.

## Open questions

- **Sensitive attributes.** Identity-based awards are a large share of the corpus, so
  gender/race/nationality genuinely improve matching. But asking for them in onboarding
  needs care: make them optional, say plainly why they are asked and that they are used
  only to match awards, and never block progress on them. A flow that demands race
  before showing value will lose people who would have converted.
- **Minimum viable profile.** What is the smallest set of fields that produces a list
  worth paying for? Everything past that is optional and can be filled in later. This
  is worth measuring, not guessing.
- **Where the free tier ends.** Browsing is free. Is ranking free and drafting paid?
  Is ranking the paid line? Undecided, and it determines what the public database is
  allowed to show.
- **Multi-user is not built.** Every row carries `owner`, always `"me"` today. Accounts
  mean real auth, isolation, and per-user LLM cost. The `owner` seam makes it a
  non-migration, but it is still real work that has not started.
- **Keeping the public database fresh** is an unattended-sourcing problem, and today
  nothing is scheduled (`docs/operating.md`: the 6am poll is not registered).

## Not captured here

The positioning question this plan sits inside — whether the product is
scholarships-first or internships-first — is being decided separately. It changes
what the public database contains and therefore what onboarding asks for, so settle
that before finalizing anything above.
