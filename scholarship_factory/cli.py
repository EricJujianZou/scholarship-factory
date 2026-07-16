"""Dev CLI to run and inspect the sourcing pipeline.

The roadmap is pipeline-first (no dashboard until ~Session 7), so this is how the
owner sanity-checks what's in the store meanwhile. `list`/`show` are read-only over
the existing OpportunityStore (GH-1); `source` runs a sourcing pass and writes to it.

    sf list [--status new] [--db PATH]
    sf show <id> [--db PATH]
    sf source --seeds seeds.toml [--db PATH]

db path: `--db`, else $SF_DB_PATH, else ./scholarship_factory.db
"""
import argparse
import os
import sys

from .extract import extract
from .fetch import fetch_url
from .pipeline import run_sourcing
from .seeds import load_seeds
from .store import OpportunityStore


def _default_db_path() -> str:
    return os.environ.get("SF_DB_PATH", "scholarship_factory.db")


def _cmd_list(store: OpportunityStore, status: str | None) -> int:
    for opp in store.list():
        if status is not None and opp.status != status:
            continue
        print(
            f"{opp.id}\t{opp.title}\t"
            f"deadline={opp.deadline}\tstatus={opp.status}\towner={opp.owner}"
        )
    return 0


def _cmd_show(store: OpportunityStore, opp_id: str) -> int:
    opp = store.get(opp_id)
    if opp is None:
        print(f"not found: {opp_id}", file=sys.stderr)
        return 1
    for field, value in opp.model_dump().items():
        print(f"{field}: {value}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sf", description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--db", default=None,
        help="SQLite db path (default: $SF_DB_PATH or ./scholarship_factory.db)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list", parents=[common], help="list stored opportunities")
    p_list.add_argument("--status", default=None, help="only this status")
    p_show = sub.add_parser("show", parents=[common], help="show one opportunity by id")
    p_show.add_argument("id")

    args = parser.parse_args(argv)
    store = OpportunityStore(args.db or _default_db_path())
    if args.command == "list":
        return _cmd_list(store, args.status)
    return _cmd_show(store, args.id)


if __name__ == "__main__":
    raise SystemExit(main())
