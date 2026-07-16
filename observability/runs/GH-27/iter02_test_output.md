Working tree clean and committed. All checks re-verified this iteration; evidence per acceptance criterion:

```
- criterion: "`url` seed -> exactly one `FetchTarget` with the same URL."
  ran: tests/test_adapters.py::test_url_seed_passes_through
  result: pass — asserts len(targets)==1 and targets[0].url == seed.value

- criterion: "`reddit` seed given as bare subreddit name and as full URL both -> the `/r/<sub>/new.json` public-JSON target."
  ran: tests/test_adapters.py::test_reddit_seed_maps_to_public_json (5 parametrized variants)
  result: pass — all variants resolve to https://www.reddit.com/r/scholarships/new.json?limit=50

- criterion: "`devpost` seed -> its listing URL as a target."
  ran: tests/test_adapters.py::test_devpost_seed_passes_through
  result: pass — targets[0].url == seed.value, seed_type DEVPOST

- criterion: "`instagram` / `x` seeds -> zero targets, surfaced as explicit skipped/unsupported outcome, no exception."
  ran: tests/test_adapters.py::test_auth_walled_seeds_are_skipped (instagram, x)
  result: pass — targets_for()==[], plan.skipped has 1 entry with reason UNSUPPORTED

- criterion: "`enabled=False` seeds -> zero targets."
  ran: tests/test_adapters.py::test_disabled_seed_yields_no_targets
  result: pass — targets_for()==[], plan.skipped[0].reason == DISABLED

- criterion: "No network anywhere; `uv run pytest -q` green."
  ran: uv run pytest -q (full suite) + test_adapters_module_does_no_io
  result: pass — 78 passed in 2.49s; adapters module has no httpx in its namespace
```

```json
{
  "stage": "test",
  "ticket_id": "GH-27",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Full suite green (78 passed); all 6 acceptance criteria individually verified against test_adapters.py assertions and source code. No code defects found.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false
}
```