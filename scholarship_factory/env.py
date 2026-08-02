"""Load `.env` from the repo root so a key can be set by editing a file.

`setx` works but is invisible and needs a fresh shell; a file in the repo folder
is the thing you can actually see and change. A real environment variable always
wins - this only fills in what is not already set.
"""
import os
from pathlib import Path

ENV_PATH = Path(__file__).parent.parent / ".env"


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    """Apply `.env` to os.environ, returning what it set. Missing file is fine."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    applied = {k: v for k, v in parse_env(text).items() if k not in os.environ and v}
    os.environ.update(applied)
    return applied
