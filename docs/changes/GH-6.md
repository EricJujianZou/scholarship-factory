# GH-6 — JSON-LD deterministic extract path

## What shipped

Adds a deterministic, LLM-free extraction path that parses `application/ld+json`
script blocks and maps opportunity-bearing schema (`Event`, `JobPosting`, `Offer`)
to `Opportunity` records. It composes with the existing LLM extract path
(GH-5): JSON-LD supplies clean, structured fields like cost when present,
while fields the markup can't reliably carry (deadline, reward) stay `null`
for the LLM path to fill in.

## Surface changes

### CLI / workflows

No CLI surface. New public library function:

- `extract_jsonld(raw_html: str, source_url: str) -> list[Opportunity]`
  (`scholarship_factory/jsonld.py:118`), exported via
  `scholarship_factory/__init__.py`.

It:
1. Collects every `<script type="application/ld+json">` block's text via a
   stdlib `HTMLParser` subclass (`_JsonLdCollector`), `json.loads`-ing each
   and flattening `@graph`/top-level-array wrappers into flat objects.
2. Keeps only objects whose `@type` (string or list) intersects
   `{"Event", "JobPosting", "Offer"}`, dropping site chrome
   (`Organization`, `WebSite`, `BreadcrumbList`, `BlogPosting`, etc.).
3. Maps each surviving object to an `Opportunity`: `title` from
   `name`/`title`/`headline` (skip the object if none is a non-empty
   string); `apply_url` from `offers.url` → `url` → `source_url`;
   `organization` from `organizer.name`/`hiringOrganization.name`; `cost`
   from `price`/`priceCurrency` on the object or its nested `offers`, with
   `provenance=QUOTED` and the verbatim value as `cost_source` when present,
   else `provenance=NONE`. `deadline` and `reward` are always left at model
   defaults (`null`/`provenance=NONE`) — no schema field reliably *is* the
   application deadline or the prize.

## Behavior & breaking changes

None — purely additive. No existing function signatures or exports changed.

## How it was verified

- "lablab `Event` → one record, title, cost quoted from `Offer`, no
  deadline/reward fabrication" →
  `tests/test_jsonld.py::test_lablab_event_yields_one_record_with_quoted_cost_and_no_deadline_or_reward`
  asserts `len(opportunities) == 1`, `title == "ExecuTorch Hackathon"`,
  `cost_provenance == QUOTED` with `"0" in cost_source`, and
  `deadline is None` / `deadline_provenance == NONE` /
  `reward is None` / `reward_provenance == NONE`.
- "Chrome-only JSON-LD → zero opportunities" →
  `test_oppsforyouth_grants_listing_chrome_only_yields_zero` and
  `test_oppsforyouth_detail_chrome_only_yields_zero` assert
  `extract_jsonld(...) == []` against fixtures whose only JSON-LD types are
  `Organization`/`WebSite`/`Person`/`BlogPosting`/etc.
- "Missing fields → `null`/`none`, never guessed" → same lablab test
  asserts `deadline_source is None` and `reward_source is None`; the
  `Opportunity` model's `_require_source_for_provenance` validator rejects
  any quoted fact without a source, so a guessed value can't construct
  successfully.
- "Offline, `uv run pytest -q` green" → all tests read fixtures from
  `tests/fixtures/` via `Path`; no network calls; this module never imports
  `anthropic`. Test stage ran the full suite: 24 passed.

## Review notes

- Nested `offers` objects are only ever read through their parent (for
  cost), never iterated as independent top-level objects — this keeps the
  lablab fixture at exactly one record instead of double-counting the
  nested `Offer`.
- No per-`@type` mapping branches for `JobPosting`/`Offer` beyond the
  shared generic mapper (title + url + cost) — no fixture exercises type-
  specific fields, and the locked "map conservatively, leave null" rule
  makes the generic mapper the correct behavior here.
- `_JsonLdCollector` treats each `handle_data` call within a script tag as
  one JSON block; if an HTML parser ever split a single ld+json body across
  multiple data events, those fragments would each fail `json.loads` and be
  silently skipped. No fixture triggers this, and it mirrors the existing
  `clean.py` `HTMLParser` idiom, so it was left as-is rather than guarded
  against.

## File map

- `scholarship_factory/jsonld.py` — new module: `extract_jsonld` and its
  helpers (`_JsonLdCollector`, `_iter_objects`, `_type_set`, `_as_dict`,
  `_extract_cost`, `_to_opportunity`).
- `scholarship_factory/__init__.py` — export `extract_jsonld`.
- `tests/test_jsonld.py` — three tests covering all four acceptance
  criteria.
