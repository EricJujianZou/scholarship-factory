"""Seed-list model + TOML loader (Session 3 / Fetch groundwork).

The owner provides a seed list of sources; Session 3 turns it into fetch targets.
This module is the typed representation of a seed plus a loader — no fetching, no
adapters, no network (source adapters, a later ticket, consume `Seed`s).

The `SeedType` enum represents all source types including the auth-walled ones
(instagram / x), even though the open-web fetch split defers actually fetching
them — the *model* represents all; the *adapters* fetch a subset.
"""
import tomllib
from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class SeedType(str, Enum):
    URL = "url"
    REDDIT = "reddit"
    DEVPOST = "devpost"
    INSTAGRAM = "instagram"  # auth-walled — deferred to its own session
    X = "x"  # auth-walled — deferred to its own session


class Seed(BaseModel):
    type: SeedType
    value: str
    enabled: bool = True
    label: str | None = None


def load_seeds(path: str | Path) -> list[Seed]:
    """Load a seed list from a TOML file: an array of `[[seeds]]` tables.

    Empty / seedless file -> empty list. A malformed entry (unknown `type`,
    missing `value`, …) raises a pydantic `ValidationError` with the offending
    field named.
    """
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    return [Seed(**item) for item in data.get("seeds", [])]
