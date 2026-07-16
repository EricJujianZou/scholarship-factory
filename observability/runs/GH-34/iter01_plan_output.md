I have everything I need. Writing the plan now.

## Context

Every part this ticket composes is merged and read: `seeds.py:33` (`load_seeds`), `adapters.py:60` (`targets_for_seeds` → `AdapterPlan{targets, skipped}`), `fetch.py:65` (`fetch_url(url)` → `FetchResult` with a computed `ok` at `fetch.py:43`), `extract.py:125` (`extract(raw_html, source_url, *, client=None)` → `ExtractionResult`), `jsonld.py:113` (`extract_jsonld(raw_html, source_url)` → `list[Opportunity]`), `store.py:77` (`insert` upserts on `normalized_apply_url`), and `cli.py:44` (`main(argv)`, argparse subcommands with a shared `--db` parent).

Two constraints shape the approach. First, `store.insert`'s conflict clause (`store.py:93`) updates **only** `last_seen` — the first record inserted for a given normalized URL keeps its `id`, `first_seen`, and all its fields; a later record with the same URL is not merged. Second, `extract` is the only path that can touch the network/LLM (`extract.py:74` lazily imports `anthropic`), so both `run_sourcing` and the CLI must pass the extractor by reference for tests to substitute it. `tests/test_store.py:60` already establishes the exact assertion shape for the dedup criterion, and `tests/test_extract.py:25` establishes the stub-client pattern.

## Approach

Add `scholarship_factory/pipeline.py` with `run_sourcing(seeds, store, *, fetch_fn=fetch_url, extract_fn=extract, jsonld_fn=extract_jsonld) -> SourcingReport`: plan targets via `targets_for_seeds`, call `fetch_fn(target.url)` per target, and on `result.ok` run the JSON-LD path then the LLM path against `result.body`, upserting every `Opportunity` from both into the store. `SourcingReport` holds `outcomes: list[TargetOutcome]` and `skipped: list[SkippedSeed]`, with `targets_attempted` and `opportunities_stored` as pydantic `computed_field` properties derived from `outcomes` — the same idiom as `FetchResult.ok` (`fetch.py:41`), and it makes the counts structurally unable to drift from the per-target detail. Non-`ok` fetches record `status_code`/`error` on their `TargetOutcome` and continue. The CLI's `source` subcommand passes `fetch_url` and `extract` into `run_sourcing` explicitly by module-global name, so `monkeypatch.setattr(cli, "fetch_url", …)` keeps the CLI test offline without adding test-only parameters to `main`.

The alternative I rejected was giving `run_sourcing` a `client` parameter to thread into `extract`. That hard-codes the LLM path to `extract`'s exact signature, whereas an `extract_fn` callable also lets the future politeness/cache/traversal tickets wrap it; the client then only appears where it belongs, in a real run's default `extract(body, url)` call resolving its own client via `_default_client()`.

Two sub-decisions I am making now so the implementer does not have to. **`source_url` is `result.final_url`**, not `target.url` — `fetch_url` follows redirects, so the body genuinely came from `final_url`, and that is what provenance should record; `TargetOutcome.url` keeps `target.url` so the report maps back to the adapter plan. **JSON-LD runs before the LLM path**, following the ticket's stated flow order; see Risks for the consequence.

## Steps

1. Create `scholarship_factory/pipeline.py` with `TargetOutcome(BaseModel)` — fields `url: str`, `ok: bool`, `status_code: int | None = None`, `error: str | None = None`, `opportunities_stored: int = 0` — done when the model imports and `TargetOutcome(url="u", ok=True)` validates.
2. Add `SourcingReport(BaseModel)` in `scholarship_factory/pipeline.py` — fields `outcomes: list[TargetOutcome]`, `skipped: list[SkippedSeed]`; plus `@computed_field @property targets_attempted -> int` returning `len(self.outcomes)` and `@computed_field @property opportunities_stored -> int` returning `sum(o.opportunities_stored for o in self.outcomes)` — done when a report built from two outcomes storing 2 and 3 reports `targets_attempted == 2` and `opportunities_stored == 5`.
3. Add `run_sourcing(seeds, store, *, fetch_fn=fetch_url, extract_fn=extract, jsonld_fn=extract_jsonld) -> SourcingReport` in `scholarship_factory/pipeline.py`: call `targets_for_seeds(seeds)`; for each `target` in `plan.targets` call `fetch_fn(target.url)`; if not `result.ok`, append `TargetOutcome(url=target.url, ok=False, status_code=result.status_code, error=result.error)` and continue; else collect `jsonld_fn(result.body, result.final_url)` followed by `extract_fn(result.body, result.final_url).opportunities`, `store.insert(...)` each one, and append an `ok=True` outcome carrying `status_code` and the count stored. Return `SourcingReport(outcomes=outcomes, skipped=plan.skipped)` — done when step 6's tests pass.
4. Export `run_sourcing`, `SourcingReport`, `TargetOutcome` from `scholarship_factory/__init__.py:1` (import line and `__all__` at `__init__.py:15`, matching the existing per-module import style) — done when `from scholarship_factory import run_sourcing` succeeds.
5. Add the `source` subcommand in `scholarship_factory/cli.py`: import `load_seeds`, `fetch_url`, `extract`, `run_sourcing` at module level; register `p_source = sub.add_parser("source", parents=[common], ...)` with a required `--seeds` argument next to the existing parsers at `cli.py:52`; add `_cmd_source(store, seeds_path)` that calls `run_sourcing(load_seeds(seeds_path), store, fetch_fn=fetch_url, extract_fn=extract)` and prints the report; dispatch it in `main` at `cli.py:59` and update the module docstring's usage block at `cli.py:7` (it currently says "read-only" — `source` writes, so that line needs correcting). Print exactly:

   ```
   targets attempted: <n>
   opportunities stored: <n>
   skipped: <n>
     <seed.type.value>:<seed.value> -> <reason.value>     # one line per skipped seed
   failures: <n>
     <url> -> status=<status_code> error=<error>          # one line per outcome where not ok
   ```

   Return `0` unconditionally — a run that reports its failures honestly succeeded at running. Done when `sf source --help` lists `--seeds` and step 7's test passes.
6. Create `tests/test_pipeline.py` covering, with a `FakeFetch` returning canned `FetchResult`s keyed by url and recording call urls, and stub `jsonld_fn`/`extract_fn` that record `(body, url)` calls:
   - one `url` seed + one `instagram` seed → `targets_attempted == 1`, `skipped` has one entry with `SkipReason.UNSUPPORTED`, and the stubbed opportunities are in `store.list()` (AC1);
   - a two-target run where one fetch returns `status_code=403, body=None` → that outcome has `ok is False` and `status_code == 403`, the other target still stores, and no exception escapes (AC2);
   - calling `run_sourcing` twice against the same store with the same stubs → `len(store.list())` unchanged, and per `tests/test_store.py:60`: same `id`, same `first_seen`, `last_seen >= ` the first run's (AC3);
   - a run over `tests/fixtures/lablab_executorch.html` with the real `extract_jsonld` and a stub `extract_fn` returning one prose-only record with a *different* `apply_url` → both stubs recorded a call and `store.list()` holds the union of both paths' records (AC4).

   Done when `uv run pytest -q tests/test_pipeline.py` is green.
7. Add `test_source_prints_summary` to `tests/test_cli.py`: write a seeds TOML via the `_write_toml` helper pattern from `tests/test_seeds.py:10` (one `url` seed, one `instagram` seed), `monkeypatch.setattr(cli, "fetch_url", fake)` and `monkeypatch.setattr(cli, "extract", stub)`, run `main(["source", "--seeds", path, "--db", str(tmp_path / "t.db")])`, assert `rc == 0` and that `capsys` output contains `targets attempted: 1` and `skipped: 1` — done when `uv run pytest -q` is green overall.

## Acceptance criteria mapping

- "With a fake fetch fn (fixture HTML) and stubbed extractors: a seed list of one url seed + one instagram seed yields a report showing 1 target attempted, the instagram seed skipped-unsupported, and the extracted opportunities present in the store." -> steps 1, 2, 3; verified by the first test in step 6.
- "A target whose fetch fails (e.g. 403) appears in the report with its status/error; other targets still process; nothing raises." -> step 3 (the `not result.ok` branch); verified by the second test in step 6.
- "Re-running the same run against the same store does not duplicate rows (store dedup); `last_seen` refreshes." -> step 3 (`store.insert` upsert); verified by the third test in step 6, asserting `id`/`first_seen` stability and `last_seen >=` per the existing `tests/test_store.py:60` precedent.
- "Both extract paths run: a fixture with JSON-LD + prose yields the union (existing lablab fixture behavior) - assert via stubs that both are invoked." -> step 3 (both paths called unconditionally on `ok`); verified by the fourth test in step 6.
- "CLI `sf source` with a seeds file + temp db prints the summary and exits 0 (test via the CLI's existing test pattern)." -> step 5; verified by step 7.
- "All tests offline (no network, no real LLM); `uv run pytest -q` green." -> steps 6, 7 inject every network-touching callable; verified by the full `uv run pytest -q` at step 7. Note `extract.py:74` only imports `anthropic` inside `_default_client`, so importing `cli`/`pipeline` never reaches the SDK.

## Risks

1. **A thin JSON-LD record can shadow a richer LLM record.** Because `store.py:93` updates only `last_seen` on conflict, if both paths yield the same normalized `apply_url`, whichever is inserted first wins every field. JSON-LD records carry no deadline or reward (`jsonld.py:102`), so the JSON-LD-first order I chose means the poorer record persists on collision. I chose it anyway: fixing it means a merge/field-preference policy, which is exactly the "new judgment logic" this ticket excludes and which belongs with refresh. The implementer should **not** add merge logic here — if the lablab test surfaces a collision, give the stub a distinct `apply_url` so the union is observable, and leave the shadowing to the refresh ticket.
2. **`extract_fn` raising mid-run aborts the whole run.** Only fetch failures are caught, per the ticket's locked decision; a live LLM error would propagate. That is deliberate — a blanket `except` around the extractors would swallow real bugs and no criterion asks for it. If the implementer feels pressure to add one, that is a signal to raise a follow-up ticket, not to widen this diff.
3. **`final_url` as `source_url` requires fakes to set it.** A `FetchResult` built in a test without `final_url` will fail validation (it is a required field at `fetch.py:33`), which fails loudly rather than silently — but if a fake sets `final_url` to something other than the requested url, the stub-call assertions in step 6 must expect the final one.

```json
{
  "stage": "plan",
  "ticket_id": "GH-34",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for run_sourcing in a new pipeline.py (targets -> fetch -> jsonld+LLM extract -> upsert, honest SourcingReport with computed counts) plus an `sf source` subcommand, with offline tests via injected fetch/extract callables.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/pipeline.py",
      "scholarship_factory/cli.py:7",
      "scholarship_factory/cli.py:52",
      "scholarship_factory/cli.py:59",
      "scholarship_factory/__init__.py:1",
      "scholarship_factory/__init__.py:15",
      "tests/test_pipeline.py",
      "tests/test_cli.py"
    ],
    "read": [
      "scholarship_factory/adapters.py:60",
      "scholarship_factory/seeds.py:33",
      "scholarship_factory/fetch.py:31",
      "scholarship_factory/fetch.py:65",
      "scholarship_factory/extract.py:74",
      "scholarship_factory/extract.py:125",
      "scholarship_factory/jsonld.py:113",
      "scholarship_factory/store.py:77",
      "scholarship_factory/models.py:13",
      "scholarship_factory/cache.py:88",
      "tests/test_store.py:60",
      "tests/test_extract.py:25",
      "tests/test_seeds.py:10",
      "tests/test_jsonld.py:9",
      "tests/fixtures/lablab_executorch.html",
      "pyproject.toml:13"
    ]
  }
}
```