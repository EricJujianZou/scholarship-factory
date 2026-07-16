"""Source adapters (Session 3 / Fetch, second link).

Adapters map a `Seed` to the URL(s) the generic fetcher should pull. This
module does no network I/O and does not call `fetch_url` — it only decides
*what* to fetch, per the locked seam: adapters yield target URLs, one
generic fetcher pulls them.
"""
from collections.abc import Iterable
from enum import Enum

from pydantic import BaseModel

from .seeds import Seed, SeedType

REDDIT_LISTING_LIMIT = 50


class FetchTarget(BaseModel):
    url: str
    seed_type: SeedType
    label: str | None = None


class SkipReason(str, Enum):
    DISABLED = "disabled"
    UNSUPPORTED = "unsupported"


class SkippedSeed(BaseModel):
    seed: Seed
    reason: SkipReason


class AdapterPlan(BaseModel):
    targets: list[FetchTarget]
    skipped: list[SkippedSeed]


def _subreddit_name(value: str) -> str:
    if "r/" in value:
        value = value.rsplit("r/", 1)[1]
    return value.strip("/").split("/")[0]


def targets_for(seed: Seed) -> list[FetchTarget]:
    if not seed.enabled or seed.type in (SeedType.INSTAGRAM, SeedType.X):
        return []

    if seed.type in (SeedType.URL, SeedType.DEVPOST):
        return [FetchTarget(url=seed.value, seed_type=seed.type, label=seed.label)]

    if seed.type == SeedType.REDDIT:
        subreddit = _subreddit_name(seed.value)
        url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={REDDIT_LISTING_LIMIT}"
        return [FetchTarget(url=url, seed_type=seed.type, label=seed.label)]

    return []


def targets_for_seeds(seeds: Iterable[Seed]) -> AdapterPlan:
    targets: list[FetchTarget] = []
    skipped: list[SkippedSeed] = []

    for seed in seeds:
        if not seed.enabled:
            skipped.append(SkippedSeed(seed=seed, reason=SkipReason.DISABLED))
        elif seed.type in (SeedType.INSTAGRAM, SeedType.X):
            skipped.append(SkippedSeed(seed=seed, reason=SkipReason.UNSUPPORTED))
        else:
            targets.extend(targets_for(seed))

    return AdapterPlan(targets=targets, skipped=skipped)
