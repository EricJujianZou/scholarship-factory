## Review — GH-6: JSON-LD deterministic extract path

I verified all three lenses against the actual fixture data (test *execution* is gated in this headless session, but the test stage already ran `uv run pytest -q` → 24 passed, and I independently confirmed the data shapes that drive each criterion).

### Lens 1 — intent (acceptance criteria, walked one-by-one)

1. **lablab `Event` → one record.** I extracted the fixture's JSON-LD: a single top-level `Event` (`"name":"ExecuTorch Hackathon"`) with nested `offers` (`"price":"0","priceCurrency":"USD"`). The only opportunity-bearing `@type`s present are that `Event` and its *nested* `Offer` — and `_iter_objects` flattens only `@graph`/top-level arrays, never recursing into `offers`, so the nested Offer can't spawn a second record. → exactly 1 record. `title="ExecuTorch Hackathon"`, `cost="0 USD"` with `cost_provenance=QUOTED` + non-null `cost_source` (test asserts `"0" in cost_source`). `deadline`/`reward` are never written → stay `None`/`NONE`. `startDate`/`endDate` are correctly ignored. ✓
2. **Chrome-only → zero.** Both oppsforyouth fixtures carry only `Organization`/`WebSite`/`SearchResultsPage`/`WebPage`/`Person`/`BlogPosting`/`ImageObject`/`ContactPoint` — none intersect `{Event, JobPosting, Offer}`. Note `BlogPosting` (the detail body) is correctly *not* treated as a fact, per the locked decision. → `[]` for both. ✓
3. **Missing fields → `null`/`none`, never guessed.** `deadline`/`reward` are left at model defaults; the model's `_require_source_for_provenance` validator forbids any `quoted` fact without a source, so a guessed value can't pass silently. The `price is None` guard (not falsy) correctly keeps a free `"0"`/`0` event as a quoted cost rather than dropping it. ✓
4. **Offline against fixtures.** Pure stdlib (`json` + `html.parser`); no network, no `anthropic` import on this path; tests read saved fixtures via `Path`. ✓

### Lens 2 — quality & security
- **Correctness:** Edge handling is conservative and right — `@type` as str-or-list, `offers` as dict-or-list, `price` int-vs-str via `str()`, `price==0` kept (`is None` check), top-level `Offer` handled (`offers or obj`). Per-block `JSONDecodeError` is swallowed so one bad block can't sink a page. Mirrors `clean.py`'s `HTMLParser` idiom.
- **Security:** `json.loads` only, no `eval`/subprocess/file writes, no secrets. Clean.
- **Hygiene:** No dead code; tests assert meaningfully (provenance, source, null-ness). The mapper stays minimal — no speculative `JobPosting`/`Offer` branches, matching the "map conservatively, leave null" rule.

One minor, non-blocking robustness note (not a fix request): `_JsonLdCollector` treats every `</script>` as a block boundary and each `handle_data` call as a standalone JSON block; if a parser ever split one ld+json body across multiple data events, the fragments would fail to parse. No fixture triggers this and the established `clean.py` pattern is the same, so it's acceptable as-is.

### Lens 3 — visual
No user-facing surface — this is a pure extraction library function (`extract_jsonld`). Playwright not applicable; nothing to render.

### Branch state
The only uncommitted items are this stage's own harness observability artifacts (`iter01_review_prompt.md`, `iter01_test*.{json,md}`, `state.json`) — the normal per-stage commit pattern, not part of the feature diff. The feature itself (`jsonld.py`, `__init__.py` export, `test_jsonld.py`) is committed and clean.

Every criterion is verified with concrete evidence; no lens found a must-fix issue.

```json
{
  "stage": "review",
  "ticket_id": "GH-6",
  "outcome": "success",
  "exit_signal": true,
  "summary": "All four acceptance criteria verified against the actual fixture JSON-LD: lablab Event yields exactly one record (nested Offer not double-counted) with quoted '0 USD' cost and null deadline/reward; both chrome-only oppsforyouth fixtures yield zero; missing fields stay null/none, enforced by the model's source-required validator. Stdlib-only, offline tests, clean conservative mapper. Clean first solve of a 'deterministic structured-data extract' class — candidate for a skills/ entry.",
  "failure_reason": null,
  "files_changed": 3,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds a deterministic, LLM-free JSON-LD extraction path (`scholarship_factory/jsonld.py`, exported as `extract_jsonld`) that composes with the existing LLM extract path. It parses every `<script type=\"application/ld+json\">` block with a stdlib `HTMLParser`, flattens `@graph`/array wrappers, and maps only opportunity-bearing `@type`s (`Event`, `JobPosting`, `Offer`) to `Opportunity`, dropping site chrome (`WebSite`, `Organization`, `BreadcrumbList`, `BlogPosting`, etc.).\n\nMapping is deliberately conservative per the locked design: `cost` is taken from an `Offer`'s `price`/`priceCurrency` (e.g. free entry → `\"0 USD\"`) with `provenance=quoted` and the verbatim value as the source span; `deadline` and `reward` are always left null/none because no schema field reliably *is* the application deadline or the prize (`startDate`/`endDate` are event dates, `Offer.price` is entry cost) — those remain the LLM path's job. The model validator guarantees no quoted fact lacks a source.\n\nTradeoffs/risks: only the three opportunity-bearing types are mapped (no speculative JobPosting/Offer field branches, since no fixture exercises them); a malformed ld+json block is skipped rather than failing the page. Tests run fully offline against saved fixtures (lablab → one quoted-cost record with null deadline/reward; both oppsforyouth chrome-only pages → zero). Pure stdlib — no new dependencies, and this path never imports `anthropic`."
}
```