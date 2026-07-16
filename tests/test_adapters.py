import pytest

import scholarship_factory.adapters as adapters_module
from scholarship_factory import (
    AdapterPlan,
    FetchTarget,
    Seed,
    SeedType,
    SkipReason,
    targets_for,
    targets_for_seeds,
)


def test_url_seed_passes_through():
    seed = Seed(type="url", value="https://opportunitiesforyouth.org/?s=grants")
    targets = targets_for(seed)
    assert len(targets) == 1
    assert targets[0].url == seed.value
    assert targets[0].seed_type == SeedType.URL


@pytest.mark.parametrize(
    "value",
    [
        "scholarships",
        "r/scholarships",
        "/r/scholarships",
        "https://www.reddit.com/r/scholarships",
        "https://www.reddit.com/r/scholarships/",
    ],
)
def test_reddit_seed_maps_to_public_json(value):
    seed = Seed(type="reddit", value=value)
    targets = targets_for(seed)
    assert len(targets) == 1
    assert targets[0].url == "https://www.reddit.com/r/scholarships/new.json?limit=50"
    assert targets[0].seed_type == SeedType.REDDIT


def test_devpost_seed_passes_through():
    seed = Seed(type="devpost", value="https://hackathons.devpost.com/?search=scholarship")
    targets = targets_for(seed)
    assert len(targets) == 1
    assert targets[0].url == seed.value
    assert targets[0].seed_type == SeedType.DEVPOST


@pytest.mark.parametrize("seed_type", ["instagram", "x"])
def test_auth_walled_seeds_are_skipped(seed_type):
    seed = Seed(type=seed_type, value="somehandle")

    assert targets_for(seed) == []

    plan = targets_for_seeds([seed])
    assert plan.targets == []
    assert len(plan.skipped) == 1
    assert plan.skipped[0].seed == seed
    assert plan.skipped[0].reason is SkipReason.UNSUPPORTED


def test_disabled_seed_yields_no_targets():
    seed = Seed(type="url", value="https://example.com", enabled=False)

    assert targets_for(seed) == []

    plan = targets_for_seeds([seed])
    assert plan.targets == []
    assert len(plan.skipped) == 1
    assert plan.skipped[0].reason is SkipReason.DISABLED


def test_targets_for_seeds_splits_mixed_list():
    seeds = [
        Seed(type="url", value="https://example.com"),
        Seed(type="reddit", value="scholarships"),
        Seed(type="devpost", value="https://hackathons.devpost.com"),
        Seed(type="instagram", value="handle"),
        Seed(type="x", value="handle"),
        Seed(type="url", value="https://disabled.example.com", enabled=False),
    ]

    plan = targets_for_seeds(seeds)

    assert isinstance(plan, AdapterPlan)
    assert len(plan.targets) == 3
    assert len(plan.skipped) == 3
    reasons = {s.reason for s in plan.skipped}
    assert reasons == {SkipReason.UNSUPPORTED, SkipReason.DISABLED}


def test_fetch_target_requires_url():
    with pytest.raises(Exception):
        FetchTarget(seed_type=SeedType.URL)


def test_adapters_module_does_no_io():
    assert "httpx" not in dir(adapters_module)
