Test execution was denied in my session, so I verified the criteria by reading the code and tests directly and cross-checking against the test stage's per-criterion evidence.

## Lens 1 — intent

I traced each acceptance criterion to a specific assertion rather than trusting the summary prose:

| Criterion | Verification |
|---|---|
| `url` seed → one target, same URL | `adapters.py:49-50` returns a single `FetchTarget(url=seed.value)`; asserted in `tests/test_adapters.py:15-20` |
| `reddit` bare name + full URL → public JSON | `adapters.py:52-55`; 5 parametrized variants at `tests/test_adapters.py:23-38` |
| `devpost` → listing URL | Same passthrough branch; `tests/test_adapters.py:41-46` |
| `instagram`/`x` → zero targets, explicit skip | `adapters.py:46-47` and `67-68`; `tests/test_adapters.py:49-59` asserts `reason is SkipReason.UNSUPPORTED` |
| `enabled=False` → zero targets | `adapters.py:46` and `65-66`; `tests/test_adapters.py:62-70` |
| No network | Confirmed by my own grep — `adapters.py` imports only `collections.abc`, `enum`, `pydantic`, and `.seeds` |

I hand-traced `_subreddit_name` (`adapters.py:39-42`) against each parametrized input, since string-slicing helpers are where off-by-one bugs hide. All five resolve to `scholarships`: the bare name has no `r/` substring and falls through to `strip("/").split("/")[0]`; the URL forms rsplit on the last `r/`, which is unambiguous because subreddit names cannot contain slashes.

## Lens 2 — quality & security

No correctness or security issues. No network calls, no subprocess, no secrets, no user-controlled path handling. The seam holds — the adapter decides *what* to fetch and never calls `fetch_url`. The `enabled`/auth-walled guard is duplicated between `targets_for` and `targets_for_seeds`, but that's warranted since `targets_for` is independently public and the criteria demand it return `[]` on its own.

Two minor notes, neither must-fix: `test_adapters_module_does_no_io` (`tests/test_adapters.py:97-98`) asserts `"httpx" not in dir(adapters_module)`, which is close to asserting nothing — the real guarantee comes from the import list. And the trailing `return []` at `adapters.py:57` is unreachable today, though it's a sane fallback if a `SeedType` member is added later.

## Lens 3 — visual

Not applicable. This ticket adds a pure library module with no user-facing surface — no page to load, no markup or styles. Playwright was not needed and not used.

## Verdict

The one gap worth flagging: I could not execute the suite myself, as `uv run pytest` was denied in this session. I'm relying on two independent prior runs (implement and test stages both reported 78 passed) plus my own line-by-line trace of every criterion through the source. Since each criterion maps to a named test whose assertions I read and confirmed match the claim, the evidence is specific rather than vague, and I'm satisfied the bar is met. The working tree holds only this review stage's own harness artifacts.

Passing. This is a clean first solve of the "seed-to-target adapter table" class and a reasonable candidate for a skill.

```json
{
  "stage": "review",
  "ticket_id": "GH-27",
  "outcome": "success",
  "exit_signal": true,
  "summary": "All 6 acceptance criteria verified by tracing each to a named test assertion I read directly; adapter seam holds (no network imports, confirmed by grep). No user-facing surface, so visual lens N/A. Could not execute pytest myself (tool permission denied) — relied on two independent prior-stage green runs (78 passed) plus line-by-line source tracing of _subreddit_name against all 5 parametrized inputs. Clean first solve of the seed-to-target adapter class: candidate for a new skill in skills/.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "pr_description": "Adds the source-adapter layer for the Fetch chain: adapters map a `Seed` to the target URL(s) a generic fetcher should pull, doing no network I/O themselves.\n\n**What changed**\n- New `scholarship_factory/adapters.py` with `FetchTarget` (url + originating seed type + optional label), `targets_for(seed)`, and `targets_for_seeds(seeds) -> AdapterPlan`.\n- `AdapterPlan` splits results into `targets` and `skipped`, where each `SkippedSeed` carries a `SkipReason` of `DISABLED` or `UNSUPPORTED`.\n- Adapter table: `url` and `devpost` seeds pass through unchanged; `reddit` seeds map to the public JSON listing `https://www.reddit.com/r/<sub>/new.json?limit=50`, accepting either a bare subreddit name or a full URL.\n- Re-exported from `scholarship_factory/__init__.py`; 10 new tests in `tests/test_adapters.py`.\n\n**Tradeoffs and design notes**\n- Auth-walled `instagram`/`x` seeds are skipped as a visible `UNSUPPORTED` outcome rather than silently dropped or raising, keeping them observable for the future session that handles them.\n- No `wordpress` SeedType was added — WordPress listings are ordinary `url` seeds, per the ticket.\n- The enabled/auth-walled guard is intentionally duplicated across `targets_for` and `targets_for_seeds` so the single-seed entry point is correct when called directly.\n\n**Risks for a merger**\n- `_subreddit_name` is string-slicing, not URL parsing. It handles the tested shapes (`scholarships`, `r/sub`, `/r/sub`, full URL with and without trailing slash) but would need revisiting for exotic inputs like query strings on a subreddit URL.\n- Devpost targets are static-HTML URLs; if those listings become JS shells, that surfaces in the fetch/extract stage, not here."
}
```