I have everything I need. The seam ("adapters yield target URLs; one generic fetcher pulls them") is confirmed in `docs/s3-fetch-design.md:63-67`, the `Seed` model is merged, and `fetch_url` from GH-26 is the consumer. Here's the plan.

## Context

- `scholarship_factory/seeds.py:18-31` defines `SeedType` (`url`, `reddit`, `devpost`, `instagram`, `x`) and `Seed(type, value, enabled, label)` — merged in GH-15, and the input to this ticket. `SeedType` gains no new members.
- `scholarship_factory/fetch.py:64` is the merged generic fetcher (`fetch_url(url, ...) -> FetchResult`). This ticket produces the URLs it will be handed; it does not call it. No network anywhere.
- `docs/s3-fetch-design.md:63-67` locks the seam this ticket implements: adapters map seed → target URL(s), the fetcher stays source-agnostic. `docs/s3-fetch-design.md:9-11` locks the open-web-only split (Instagram/X deferred).
- Repo conventions: one small module per concern under `scholarship_factory/`, pydantic `BaseModel` for data (`fetch.py:31`), a matching `tests/test_<module>.py` of plain pytest functions, and every public name re-exported from `scholarship_factory/__init__.py:1-35`.
- Deliberately *not* used: `normalize_apply_url` (`scholarship_factory/urls.py:6`). It force-upgrades scheme to https and strips trailing slashes; it exists for dedup identity of `apply_url`, and applying it here would violate the "same URL" acceptance criterion for `url` seeds.

## Approach

Add a single boring lookup module, `scholarship_factory/adapters.py`, holding `FetchTarget` (a pydantic model: `url` + `seed_type` + optional `label`), a per-seed mapper `targets_for(seed) -> list[FetchTarget]`, and a list-level `targets_for_seeds(seeds) -> AdapterPlan`. `targets_for` is a pure function with a small `if/elif` over `SeedType` returning `[]` for disabled and auth-walled seeds; `AdapterPlan` carries both `targets` and `skipped: list[SkippedSeed]` (each a seed plus a `SkipReason` enum of `disabled | unsupported`), which is how the skip becomes an explicit, assertable outcome rather than a silent drop. `url` and `devpost` pass their value through verbatim as one target; `reddit` is the only one with real logic — derive the subreddit name from any of the accepted forms and build the public JSON listing URL.

The rejected alternative was making `targets_for` itself return the plan/skip-reason for a single seed. That forces every caller — including the trivial `url` case — to unwrap a wrapper object to get at a list, and it puts the same skip information in two places. Keeping the per-seed function a plain list and surfacing skips only at the list level (where a caller actually wants a report of what it didn't fetch) is smaller and matches how the fetcher will consume it: iterate `plan.targets`, log `plan.skipped`.

Decisions made now so the implementer doesn't have to re-interpret:

- **`FetchTarget` fields:** `url: str`, `seed_type: SeedType`, `label: str | None = None` (carried from `Seed.label` for observability). No `Seed` object embedded — `seed_type` is what Extract needs to know "what shape of content to expect", per the ticket.
- **Reddit accepted input forms:** `scholarships`, `r/scholarships`, `/r/scholarships` (the merged `tests/test_seeds.py:18` fixture uses the `r/` form), and any URL containing `/r/<sub>`. Derivation: if the value contains `r/`, take the segment after the last `r/`; otherwise take the whole value; then strip surrounding `/` and take the first path segment. Output: `https://www.reddit.com/r/<sub>/new.json?limit=50`.
- **No validation of malformed/empty seed values.** Seed values are trusted input already validated by pydantic at load; per CLAUDE.md §2 we do not add handling for scenarios the criteria don't name.
- **Reddit `limit=50` is a module constant** (`REDDIT_LISTING_LIMIT`), matching the `DEFAULT_TIMEOUT` / `RETRY_ATTEMPTS` constant style in `fetch.py:22-27`.

## Steps

1. Create `scholarship_factory/adapters.py` with a module docstring (stating the seam and the no-network/no-I/O boundary, in the style of `fetch.py:1-8`) and the `REDDIT_LISTING_LIMIT = 50` constant — done when the file imports cleanly with `uv run python -c "import scholarship_factory.adapters"`.
2. Add `FetchTarget(BaseModel)` with `url: str`, `seed_type: SeedType`, `label: str | None = None` in `scholarship_factory/adapters.py` — done when `FetchTarget(url="https://x", seed_type=SeedType.URL)` constructs and rejects a missing `url` with `ValidationError`.
3. Add `SkipReason(str, Enum)` with members `DISABLED = "disabled"` and `UNSUPPORTED = "unsupported"`, plus `SkippedSeed(BaseModel)` with `seed: Seed` and `reason: SkipReason`, in `scholarship_factory/adapters.py` — done when both construct.
4. Add the private helper `_subreddit_name(value: str) -> str` in `scholarship_factory/adapters.py` implementing the derivation rule above — done when it returns `"scholarships"` for all four accepted forms.
5. Add `targets_for(seed: Seed) -> list[FetchTarget]` in `scholarship_factory/adapters.py`: return `[]` if `not seed.enabled` or `seed.type` is `INSTAGRAM`/`X`; `URL` and `DEVPOST` → one `FetchTarget(url=seed.value, ...)`; `REDDIT` → one `FetchTarget` with the `/r/<sub>/new.json?limit=<REDDIT_LISTING_LIMIT>` URL — done when each branch returns the expected list and no branch raises.
6. Add `AdapterPlan(BaseModel)` with `targets: list[FetchTarget]` and `skipped: list[SkippedSeed]`, and `targets_for_seeds(seeds: Iterable[Seed]) -> AdapterPlan` in `scholarship_factory/adapters.py`, which classifies each seed (disabled → `SkipReason.DISABLED`; instagram/x → `SkipReason.UNSUPPORTED`; disabled wins if both) and otherwise extends `targets` from `targets_for` — done when a mixed seed list yields the right split.
7. Re-export `FetchTarget`, `AdapterPlan`, `SkipReason`, `SkippedSeed`, `targets_for`, `targets_for_seeds` from `scholarship_factory/__init__.py` (import line after `.extract`, names appended to `__all__`, matching the existing pattern at `scholarship_factory/__init__.py:1-35`) — done when `from scholarship_factory import targets_for_seeds` works.
8. Create `tests/test_adapters.py` covering every acceptance criterion (see mapping below), importing from the package root like `tests/test_fetch.py:7` — done when `uv run pytest -q` is green with no network access.

## Acceptance criteria mapping

- `"url seed -> exactly one FetchTarget with the same URL."` -> steps 2, 5; verified by `test_url_seed_passes_through` in `tests/test_adapters.py` asserting `len(targets) == 1` and `targets[0].url == seed.value` verbatim (including a value with a query string like `https://opportunitiesforyouth.org/?s=grants`, to pin that no normalization is applied).
- `"reddit seed given as bare subreddit name (scholarships) and as full URL both -> the /r/<sub>/new.json public-JSON target."` -> steps 4, 5; verified by a `@pytest.mark.parametrize` `test_reddit_seed_maps_to_public_json` over `scholarships`, `r/scholarships`, `/r/scholarships`, `https://www.reddit.com/r/scholarships`, `https://www.reddit.com/r/scholarships/`, each asserting the single target URL equals `https://www.reddit.com/r/scholarships/new.json?limit=50`.
- `"devpost seed -> its listing URL as a target."` -> step 5; verified by `test_devpost_seed_passes_through` asserting one target whose `url` is the seed value and whose `seed_type` is `SeedType.DEVPOST`.
- `"instagram / x seeds -> zero targets, surfaced as an explicit skipped/unsupported outcome (asserted in tests), no exception."` -> steps 3, 5, 6; verified by `test_auth_walled_seeds_are_skipped` (parametrized over `instagram`/`x`) asserting `targets_for(seed) == []` **and** that `targets_for_seeds([seed])` returns `targets == []` with one `skipped` entry whose `reason is SkipReason.UNSUPPORTED` and whose `seed` is the input — the call itself raising nothing.
- `"enabled=False seeds -> zero targets."` -> steps 5, 6; verified by `test_disabled_seed_yields_no_targets` asserting `targets_for(seed) == []` for a disabled `url` seed, and `targets_for_seeds` reports it under `skipped` with `reason is SkipReason.DISABLED`.
- `"No network anywhere; uv run pytest -q green."` -> steps 1-8; verified by `uv run pytest -q` passing, and by `adapters.py` importing neither `httpx` nor `scholarship_factory.fetch` — asserted structurally in `test_adapters_module_does_no_io` via `"httpx" not in dir(adapters_module)`, plus a mixed-list test `test_targets_for_seeds_splits_mixed_list` over one seed of each type.

## Risks

1. **The reddit derivation over-matching a URL that contains `r/` outside the subreddit segment** (e.g. a host like `reader.example.com/r/x`, or the literal `.../user/r/`). Taking the segment after the *last* `r/` is what makes the five parametrized forms pass; if the implementer finds a listed form failing, fix the derivation to split the URL path on `/` and take the element following the first exact `r` component — do not add a regex zoo, and do not add forms beyond the five listed.
2. **`SkippedSeed` embedding `Seed` may trip pydantic's model-rebuild ordering** if `SkippedSeed` is declared before `Seed` is imported. `Seed` is imported at module top from `.seeds`, so this should not fire; if it does, keep the field typed as `Seed` and confirm the import is top-level rather than deferring it into a `TYPE_CHECKING` block.
3. **Re-export churn in `__init__.py` is the one shared file this ticket touches**, so it's the likeliest merge conflict with any concurrently-built Session 3 ticket. If the import block has moved, re-apply the addition to whatever the current shape is rather than reverting to the shape quoted here.

```json
{
  "stage": "plan",
  "ticket_id": "GH-27",
  "outcome": "success",
  "exit_signal": false,
  "summary": "Plan for GH-27 source adapters: new scholarship_factory/adapters.py with FetchTarget, targets_for (pure per-seed mapping, [] for disabled/auth-walled), and targets_for_seeds returning an AdapterPlan carrying targets + explicit SkippedSeed reasons; re-exported from __init__ and covered by a new tests/test_adapters.py. No network, no fetcher coupling.",
  "failure_reason": null,
  "files_changed": 0,
  "suggested_tools": [],
  "system_repair_suggested": false,
  "file_manifest": {
    "edit": [
      "scholarship_factory/adapters.py",
      "scholarship_factory/__init__.py:1",
      "tests/test_adapters.py"
    ],
    "read": [
      "scholarship_factory/seeds.py:18",
      "scholarship_factory/fetch.py:22",
      "scholarship_factory/urls.py:6",
      "tests/test_seeds.py:17",
      "tests/test_fetch.py:1",
      "docs/s3-fetch-design.md:63",
      "REPO_CONTENT.md:126",
      "pyproject.toml"
    ]
  }
}
```