I have what I need. Here's the plan.

## Context

- `scholarship_factory/extract.py:33` already returns `ExtractionResult(kind, opportunities)` with `PageKind.LIST`/`DETAIL`, and `_to_opportunity` (extract.py:93) sets a thin item's `apply_url` to the item's own url — so **a listing's thin items already carry their detail-page URL in `apply_url`**. That is the traversal target; no new link-scraping is needed.
- `pipeline.py:72-75` currently stores *every* opportunity from both extract paths, ignoring `kind`. This is the integration point (`pipeline.py` is on main, so Scope item 2 applies, not the standalone fallback).
- **Load-bearing constraint:** `store.insert` (store.py:93) upserts `ON CONFLICT(normalized_apply_url) DO UPDATE SET last_seen = excluded.last_seen` — it updates *only* `last_seen`, never the fact fields. So if a thin item is stored before its detail record, the detail's deadline can never overwrite the thin `NULL`, and AC 1 fails. The plan therefore does not store thin items at all; a LIST extraction's items are traversal input, not records. Merge logic in `store` is explicitly Session 5's job ("do not build identity logic").
- `run_sourcing` composes injected `fetch_fn`/`extract_fn`/`jsonld_fn`; tests stub them with recording fakes (`tests/test_pipeline.py:26-59`). Traverse follows the same contract.
- `REPO_CONTENT.md:85` locks `source_url` (where seen) vs `apply_url` (where to apply) diverging once traversal lands — traversal is what makes them differ.

## Approach

`traverse.py` gets one pure function, `traverse(result, listing_url, *, fetch_fn, extract_fn, jsonld_fn, page_cap=25)`. It takes an already-extracted `ExtractionResult` of kind LIST, resolves each thin item's `apply_url` against the listing URL, fetches and re-extracts each detail page, and returns the detail-extracted `Opportunity` records plus a per-link report. It touches no store, so it adds no identity logic and stays trivially testable; `run_sourcing` remains the only thing that writes. Within `run_sourcing`, a LIST extraction's thin items are handed to `traverse` and only the returned detail records are inserted — the thin items themselves are dropped, which is what makes the detail's deadline the version that lands given the `last_seen`-only upsert. A DETAIL extraction stores as it does today.

The strongest alternative was letting `traverse` upsert directly and teaching `store.insert` to merge richer facts over thin ones. Rejected on two counts: fact-merging is field-level identity/refresh work the ticket explicitly defers (Sessions 5/8), and it would make traverse's tests require a store. Not storing thin items gets AC 1 with no store change at all.

Two sub-decisions made now so the implementer doesn't have to:
- **Relative URLs:** resolve with `urljoin(listing_url, item.apply_url)`. Listing hrefs are commonly relative; unresolved they'd fetch-fail and silently drop the opportunity. `urljoin` returns absolute URLs unchanged, so it is safe.
- **Dedup key:** `normalize_apply_url` (the store's own key), tracked in a per-call `set`, so AC 4 dedups the same way the store does. The *original* absolute URL is what gets fetched; the normalized form is only the key.

## Steps

1. **Create `scholarship_factory/traverse.py`** with module docstring (Session 4 / Traverse, depth-1) and `TRAVERSE_PAGE_CAP = 25` — done when the file imports cleanly.
2. **Define the report models** in `scholarship_factory/traverse.py`: `LinkOutcome(url: str, ok: bool, status_code: int | None = None, error: str | None = None, opportunities_found: int = 0)`; `TraverseReport(outcomes: list[LinkOutcome], links_discovered: int, cap_reached: bool)` with a `links_traversed` computed field (`len(outcomes)`, matching `SourcingReport`'s `computed_field` style at pipeline.py:37); `TraverseResult(opportunities: list[Opportunity], report: TraverseReport)`. Done when `TraverseReport(outcomes=[], links_discovered=0, cap_reached=False).links_traversed == 0`.
3. **Implement `traverse(result, listing_url, *, fetch_fn=fetch_url, extract_fn=extract, jsonld_fn=extract_jsonld, page_cap=TRAVERSE_PAGE_CAP)`** in `scholarship_factory/traverse.py`. Iterate `result.opportunities`; for each, `url = urljoin(listing_url, item.apply_url)`; skip if `normalize_apply_url(url)` is in the seen-set, else add it; stop before fetching once `len(outcomes) == page_cap` and set `cap_reached=True`. `links_discovered` counts unique post-dedup links, so `cap_reached` means "unique links remained unfetched". Done when the function returns a `TraverseResult` for a stub LIST result.
4. **Per-link handling** in `scholarship_factory/traverse.py`: on `not fetch_result.ok` append `LinkOutcome(url, ok=False, status_code=..., error=fetch_result.error)` and `continue` — never raise. Otherwise collect `jsonld_fn(body, final_url)` + `extract_fn(body, final_url).opportunities` (mirroring pipeline.py:72-73; the detail extraction's `source_url` is the detail page, satisfying the "same opportunity, richer facts" decision, and no recursion happens because the returned result's `kind` is ignored). If the combined list is empty, append `LinkOutcome(url, ok=False, status_code=..., error="extraction yielded no opportunities", opportunities_found=0)`; else `ok=True` with the count, and extend the records. Done when a fake fetch returning a 404 for one of two links still processes the other.
5. **Wire traversal into `run_sourcing`** in `scholarship_factory/pipeline.py:72-75`: keep `opportunities = list(jsonld_fn(...))`; assign `extraction = extract_fn(result.body, result.final_url)`; if `extraction.kind == PageKind.LIST`, call `traverse(extraction, result.final_url, fetch_fn=fetch_fn, extract_fn=extract_fn, jsonld_fn=jsonld_fn, page_cap=page_cap)`, extend `opportunities` with `traversal.opportunities`, and keep `traversal.report`; else extend with `extraction.opportunities`. Add `page_cap: int = TRAVERSE_PAGE_CAP` to `run_sourcing`'s keyword-only params. Done when a LIST extraction stores detail records and no thin item.
6. **Surface traversal on the sourcing report** in `scholarship_factory/pipeline.py:25`: add `traversal: TraverseReport | None = None` to `TargetOutcome` and populate it on the success path. Done when a non-listing target's outcome has `traversal is None` and a listing target's does not.
7. **Export the new names** in `scholarship_factory/__init__.py:1-53`: import and add `traverse`, `TraverseResult`, `TraverseReport`, `LinkOutcome`, `TRAVERSE_PAGE_CAP` to `__all__`, keeping the existing import/`__all__` ordering style. Done when `from scholarship_factory import traverse, TraverseResult` works.
8. **Report the early stop in the CLI** in `scholarship_factory/cli.py:55` (after the `opportunities stored` line): collect `[o.traversal for o in report.outcomes if o.traversal]`; if non-empty print `traversed: <sum links_traversed> of <sum links_discovered> links`, and for each capped one print `  cap reached on <url> -> <n> links not followed`. Done when a stubbed capped run prints the cap line and an untraversed run prints neither.
9. **Write `tests/test_traverse.py`** reusing the `FakeFetch`/`ok_result`/`make_opp` shapes from tests/test_pipeline.py:20-59 (copy them locally; they are per-module helpers today, so don't refactor them into a shared conftest). Cover: (a) N thin items → each URL fetched, detail records returned, and the deadline + `deadline_source` + `Provenance.QUOTED` from the stubbed detail extraction present on the record, `source_url` == detail page (AC 1, traverse level); (b) `page_cap=2` with 5 thin items → `len(fetch_fn.calls) == 2`, `report.cap_reached is True`, `links_discovered == 5`, `links_traversed == 2` (AC 2); (c) one link 404s and one extracts empty → both get `ok=False` outcomes with distinct `error`s while the third still yields a record (AC 3); (d) two thin items whose URLs differ only by a trailing slash / `utm_` param → one fetch (AC 4); (e) a relative `apply_url` resolves against the listing URL. Done when `uv run pytest -q tests/test_traverse.py` is green.
10. **Add pipeline-level tests** to `tests/test_pipeline.py`: extend `RecordingExtract` to return a per-URL `PageKind` (default `DETAIL` so the four existing tests keep passing unchanged) — done when the existing suite still passes; then a test where the seed URL extracts as LIST with a thin item (no deadline) and the detail URL extracts as DETAIL *with* a deadline, asserting `store.list()` has exactly one record carrying the deadline and `source_url` == detail page (AC 1, the upsert path), plus one asserting `TargetOutcome.traversal.cap_reached` is exposed.
11. **Run `uv run pytest -q`** — done when the whole suite is green (AC 5).

## Acceptance criteria mapping

- "A stubbed listing extraction with N thin items -> traverse fetches each item URL (asserted via fake fetch fn) and upserts the detail-extracted records; a thin item whose detail page states the deadline ends up stored WITH that deadline (quoted provenance + source span, from the stubbed detail extraction)." -> steps 3, 4, 5; verified by test_traverse.py case (a) for the fetch/enrichment half and the test_pipeline.py LIST test in step 10 for the *stored-with-deadline* half (the store assertion is what proves the thin item was not written first).
- "Page cap: with cap=2 and 5 thin items, only 2 detail fetches happen and the report flags the early stop." -> steps 3, 8; verified by test_traverse.py case (b) asserting `len(fetch_fn.calls) == 2` and `cap_reached is True`.
- "A detail fetch failure or empty extraction is reported for that link; remaining links still process." -> step 4; verified by test_traverse.py case (c).
- "No fetch of the same detail URL twice within one traverse call." -> step 3 (normalized seen-set); verified by test_traverse.py case (d).
- "All tests offline with stubbed fetch/extract; `uv run pytest -q` green." -> steps 9, 10, 11; verified by the full suite. No test constructs a real client — `traverse`'s defaults are only exercised through injection.

## Risks

1. **The thin-item drop is the whole AC-1 mechanism, and it's easy to "fix" backwards.** If the implementer stores thin items too (mirroring today's pipeline.py:74 loop), AC 1 fails in a confusing way: the store shows one record with a `NULL` deadline and no error anywhere, because the `last_seen`-only upsert silently discards the detail facts. If the deadline assertion fails, check whether the thin item reached `store.insert` first — do **not** respond by adding fact-merging to `store.insert`.
2. **`extract_fn`'s return contract differs between call sites.** `ExtractFn` is typed `Callable[[str, str], "object"]` (pipeline.py:22), so a stub returning a bare list instead of an `ExtractionResult` type-checks but blows up on `.kind` inside traverse. Tighten the alias to return `ExtractionResult` when wiring step 5, and if an existing test breaks, fix the stub rather than defensively `getattr`-ing `kind`.
3. **A detail page that itself extracts as LIST must not recurse.** Step 4 ignores the returned `kind` deliberately. If the implementer branches on it "for symmetry", v1's depth-1 lock breaks and a fixture with paginated listings could loop. The `page_cap` bounds damage but is not the guard — the flat call is.

```json
{
  "stage": "plan",
  "ticket_id": "GH-35",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for depth-1 traversal: a pure traverse() in a new traverse.py returns detail-extracted records + a per-link report (cap, dedup, per-link failures), and run_sourcing routes LIST extractions through it while storing only the detail records. Key finding: store.insert upserts last_seen only, so thin items must never be stored or the detail's deadline can never land (AC 1).",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/traverse.py",
      "scholarship_factory/pipeline.py:22",
      "scholarship_factory/pipeline.py:25",
      "scholarship_factory/pipeline.py:72",
      "scholarship_factory/__init__.py:9",
      "scholarship_factory/cli.py:55",
      "tests/test_traverse.py",
      "tests/test_pipeline.py:50"
    ],
    "read": [
      "scholarship_factory/extract.py:33",
      "scholarship_factory/extract.py:93",
      "scholarship_factory/fetch.py:31",
      "scholarship_factory/store.py:93",
      "scholarship_factory/models.py:13",
      "scholarship_factory/urls.py:6",
      "scholarship_factory/cli.py:49",
      "scholarship_factory/cache.py:1",
      "scholarship_factory/polite.py:1",
      "REPO_CONTENT.md:85",
      "REPO_CONTENT.md:166"
    ]
  }
}
```