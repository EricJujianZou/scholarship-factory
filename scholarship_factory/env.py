"""Load `.env` from the repo root so a key can be set by editing a file.

`setx` works but is invisible and needs a fresh shell; a file in the repo folder
is the thing you can actually see and change. A real environment variable always
wins - this only fills in what is not already set.

The dashboard can re-read the file without restarting. That needs care: a plain
re-read cannot override, or a corrected key would never take effect, but
overriding everything would clobber a variable set in the shell. So we remember
which keys came from the file, and only those are ours to replace.
"""
import os
from pathlib import Path

ENV_PATH = Path(__file__).parent.parent / ".env"

#: keys this module put into os.environ, so a reload knows what it may replace
_APPLIED: set[str] = set()


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


def load_env(path: Path = ENV_PATH, *, reload: bool = False) -> dict[str, str]:
    """Apply `.env` to os.environ, returning what it set. Missing file is fine.

    With `reload`, a key the file previously supplied may be replaced by its new
    value; one that came from the real environment is still left alone.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    applied = {
        key: value
        for key, value in parse_env(text).items()
        if value and (key not in os.environ or (reload and key in _APPLIED))
    }
    os.environ.update(applied)
    _APPLIED.update(applied)
    return applied
