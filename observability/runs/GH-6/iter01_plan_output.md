I have everything needed. No new dependencies (pure stdlib `json` + `html.parser`). Here is the plan.

## Context

This adds the deterministic JSON-LD extract path alongside the existing LLM path (`scholarship_factory/extract.py`, GH-5). It touches: `scholarship_factory/models.py` (the `Opportunity` model + `Provenance` enum — note its `_require_source_for_provenance` validator: any fact with `provenance != none` **must** carry a non-null `*_source`), `scholarship_factory/clean.py` (existing `HTMLParser` idiom to mirror), and `scholarship_factory/__init__.py` (public exports). Constraints from PRIME/REPO_CONTENT: no new deps (stdlib only — `pydantic`/`fastapi` are the only runtime deps; `anthropic` is an optional extra this path must **not** require), tests must be offline against saved fixtures, and the locked no-fabrication rule governs every mapping. Confirmed fixture shapes: lablab is a single top-level `Event` with nested `offers` (a dict, `price:"0"`, `priceCurrency:"USD"`) and `startDate`/`endDate`; both oppsforyouth fixtures wrap chrome-only types (`Organization`/`WebSite`/`WebPage`/`Person`) in a Yoast `@graph`.

## Approach

Add a standalone, LLM-free function `extract_jsonld(raw_html, source_url) -> list[Opportunity]` in a new module `scholarship_factory/jsonld.py`. It (1) pulls every `<script type="application/ld+json">` block via a small `HTMLParser` subclass (mirroring `clean.py`'s approach — robust to entities, unlike regex), `json.loads` each, and flattens `@graph`/array wrappers into a flat object list; (2) keeps only objects whose `@type` (normalized — may be a string or list) intersects the opportunity-bearing set `{Event, JobPosting, Offer}`, dropping site chrome; (3) maps each surviving object to an `Opportunity` with a single conservative mapper. The mapper writes a fact only when the schema unambiguously carries it: `cost` from a `price`/`priceCurrency` (on the object itself or its nested `offers`) with `provenance=quoted` and the verbatim schema value as `cost_source`; **`deadline` and `reward` are always left `null`/`none`** because no schema field reliably *is* the application deadline or the prize (`startDate`/`endDate`/`validThrough` are event/expiry dates, `Offer.price` is entry cost) — those come from the LLM path. I rejected reusing `extract.py`'s `ExtractionResult`/LLM plumbing: the JSON-LD path shares no logic with the LLM call, and a plain `list[Opportunity]` matches the "return 0..N records" scope without dragging in the `detail`/`list` kind distinction (that's an LLM-judgment concern). I also rejected per-`@type` mapper branches for `JobPosting`/`Offer` beyond the shared generic mapper — no fixture exercises them, and the locked "map conservatively, leave `null`" rule makes the generic mapper (title + url + cost only) the correct, non-speculative behavior.

## Steps

1. Create `scholarship_factory/jsonld.py` with a `_JsonLdCollector(HTMLParser)` that captures the inner text of each `application/ld+json` script — done when feeding the lablab HTML returns exactly one raw JSON string containing `"ExecuTorch Hackathon"`.
2. Add `_iter_objects(raw_html) -> list[dict]` in `jsonld.py`: `json.loads` each block (skip blocks that raise `JSONDecodeError`), and flatten — if an object has `@graph` (list), yield its members; if a block is itself a list, yield its members; else yield the object — done when lablab yields a list containing the `Event` dict and oppsforyouth yields the chrome dicts.
3. Add `_type_set(obj) -> set[str]` in `jsonld.py` normalizing `@type` (string or list of strings) to a set — done when it returns `{"Event"}` for the lablab object and `{"Organization"}`/`{"WebSite"}`/etc. for chrome.
4. Add `_extract_cost(obj) -> tuple[str|None, str|None]` (value, source) in `jsonld.py`: read `price`/`priceCurrency` from `obj` itself or from `obj["offers"]` (dict, or first dict in a list); when `price` is present return `(f"{price} {currency}".strip(), <same verbatim string>)`, else `(None, None)` — done when lablab's Event yields `("0 USD", "0 USD")` and an object with no price yields `(None, None)`.
5. Add `_to_opportunity(obj, source_url) -> Opportunity | None` in `jsonld.py`: title ← first present of `name`/`title`/`headline` (return `None` if none — can't build a record); `apply_url` ← `offers.url` → `url` → `source_url`; `source_url` ← param; `cost`/`cost_source` from step 4 with `cost_provenance=quoted` when present else `none`; `deadline`/`reward` and their provenance/source left at model defaults (`null`/`none`); `organization` ← `organizer.name`/`hiringOrganization.name` if a dict — done when the constructed `Opportunity` passes the model validator (cost quoted ⇒ `cost_source` non-null; deadline/reward none ⇒ source null).
6. Add the public `extract_jsonld(raw_html, source_url) -> list[Opportunity]` in `jsonld.py`: for each object from step 2 whose `_type_set` intersects `{"Event","JobPosting","Offer"}`, map via step 5, dropping `None`s — done when lablab returns a 1-element list and each oppsforyouth fixture returns `[]`.
7. Export `extract_jsonld` from `scholarship_factory/__init__.py` (add to imports and `__all__`) — done when `from scholarship_factory import extract_jsonld` succeeds.
8. Add `tests/test_jsonld.py` covering all four acceptance criteria (lablab one-record + cost-quoted + no-deadline + null-reward; each chrome fixture → zero; a null/absent field → `none`) — done when `uv run pytest -q` is green.

## Acceptance criteria mapping

- "`lablab_executorch.html`: `Event` yields one record, `title="ExecuTorch Hackathon"`, `cost` from `Offer` quoted+source, `startDate`/`endDate` NOT in `deadline`, prize not invented (`null`)" -> steps 4, 5, 6; verified by a test asserting `len==1`, `title`, `cost_provenance==QUOTED` with non-null `cost_source`, `deadline is None`/`deadline_provenance==NONE`, `reward is None`.
- "Chrome-only JSON-LD yields zero opportunities" -> steps 3, 6; verified by tests asserting `extract_jsonld(...) == []` for both oppsforyouth fixtures.
- "Missing/`null` schema fields map to `null` with `provenance=\"none\"` — never guessed" -> steps 4, 5; verified by asserting the lablab record's `reward`/`deadline` are `None` with `provenance==NONE` (absent fields), and by the model validator forbidding a quoted fact without a source.
- "Tests run offline against saved fixtures; `uv run pytest -q` green" -> step 8; verified by the full suite passing with no network and no `anthropic` import on this path.

## Risks

1. **`@type` or `offers` shape variance** (string vs list, dict vs list, JSON number vs string `price`). Mitigation: steps 3–4 normalize each — `str(price)` handles `0` vs `"0"`; treat `offers`/`@type` as "dict-or-list-of-dict" / "str-or-list-of-str". If a real block still fails to parse, step 2 swallows `JSONDecodeError` so one bad block can't sink the page.
2. **Over-eager record creation from nested objects** (e.g. emitting the nested `Offer` as its own cost-only record, double-counting lablab). Mitigation: step 6 iterates only the flattened *top-level*/`@graph` objects; nested `offers` is reached solely via the parent in step 4, never iterated independently — keeping lablab at exactly one record.
3. **cost source-span format disagreement with the test author.** Mitigation: step 4 fixes the exact form (`"<price> <currency>"`, verbatim, used for both `cost` and `cost_source`) so the test in step 8 asserts against a defined value rather than guessing; the only hard contract is `provenance=quoted` + non-null source + `"0"` present.

## File manifest

```json
{
  "stage": "plan",
  "ticket_id": "GH-6",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for GH-6: deterministic JSON-LD extract path (new scholarship_factory/jsonld.py + export + tests), stdlib-only, gating on opportunity-bearing @types, mapping cost from Offer with quoted provenance while leaving deadline/reward null.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {"edit": ["scholarship_factory/jsonld.py", "scholarship_factory/__init__.py:1", "tests/test_jsonld.py"], "read": ["scholarship_factory/models.py:42", "scholarship_factory/extract.py:85", "scholarship_factory/clean.py:7", "tests/test_extract.py:13", "tests/fixtures/lablab_executorch.html", "tests/fixtures/oppsforyouth_grants_listing.html", "tests/fixtures/oppsforyouth_detail.html", "pyproject.toml"]}
}
```