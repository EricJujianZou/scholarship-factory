import os
import tempfile

import pytest
from pydantic import ValidationError

from scholarship_factory.seeds import Seed, SeedType, load_seeds


def _write_toml(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".toml")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def test_valid_seed_construction():
    s = Seed(type="reddit", value="r/scholarships")
    assert s.type == SeedType.REDDIT
    assert s.enabled is True
    assert s.label is None


def test_unknown_type_rejected():
    with pytest.raises(ValidationError):
        Seed(type="tiktok", value="whatever")


def test_loader_round_trip():
    path = _write_toml(
        """
[[seeds]]
type = "reddit"
value = "r/scholarships"

[[seeds]]
type = "url"
value = "https://grants.uwaterloo.ca"
label = "uwaterloo grants"
enabled = false
"""
    )
    seeds = load_seeds(path)
    assert len(seeds) == 2
    assert seeds[0].type == SeedType.REDDIT and seeds[0].value == "r/scholarships"
    assert seeds[1].type == SeedType.URL
    assert seeds[1].enabled is False
    assert seeds[1].label == "uwaterloo grants"


def test_empty_file_is_empty_list():
    assert load_seeds(_write_toml("")) == []


def test_malformed_entry_raises():
    path = _write_toml('[[seeds]]\ntype = "reddit"\n')  # missing `value`
    with pytest.raises(ValidationError):
        load_seeds(path)
