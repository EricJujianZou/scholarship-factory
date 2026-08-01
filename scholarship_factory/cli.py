"""Dev CLI to run and inspect the sourcing pipeline.

The roadmap is pipeline-first (no dashboard until ~Session 7), so this is how the
owner sanity-checks what's in the store meanwhile. `list`/`show` are read-only over
the existing OpportunityStore (GH-1); `source` runs a sourcing pass and writes to it.

    sf list [--status new] [--db PATH]
    sf show <id> [--db PATH]
    sf source --seeds seeds.toml [--db PATH] [--page-cap N] [--min-interval S]
    sf refresh <id> [--db PATH]

db path: `--db`, else $SF_DB_PATH, else ./scholarship_factory.db
"""
import argparse
import os
import sys

from .cache import FetchCache, cached_fetch
from .extract import extract
from .fetch import fetch_url
from .pipeline import run_sourcing
from .polite import DEFAULT_MIN_INTERVAL, PoliteFetcher
from .refresh import refresh_opportunity
from .seeds import load_seeds
from .store import OpportunityStore
from .traverse import TRAVERSE_PAGE_CAP


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


def _sourcing_fetch_fn(db_path: str, min_interval: float):
    """robots.txt + per-host spacing + response cache around the plain fetcher.

    Only sourcing gets this: `refresh` must see live bytes, so it stays on the
    uncached `fetch_url`.
    """
    polite = PoliteFetcher(min_interval=min_interval, fetch_fn=fetch_url)
    cache = FetchCache(db_path)
    return lambda url: cached_fetch(url, cache=cache, fetch_fn=polite.fetch)


def _cmd_source(
    store: OpportunityStore, seeds_path: str, page_cap: int, min_interval: float
) -> int:
    report = run_sourcing(
        load_seeds(seeds_path),
        store,
        fetch_fn=_sourcing_fetch_fn(store.db_path, min_interval),
        extract_fn=extract,
        page_cap=page_cap,
    )
    print(f"targets attempted: {report.targets_attempted}")
    print(f"opportunities stored: {report.opportunities_stored}")
    traversals = [o.traversal for o in report.outcomes if o.traversal]
    if traversals:
        links_traversed = sum(t.links_traversed for t in traversals)
        links_discovered = sum(t.links_discovered for t in traversals)
        print(f"traversed: {links_traversed} of {links_discovered} links")
        for outcome in report.outcomes:
            if outcome.traversal and outcome.traversal.cap_reached:
                not_followed = outcome.traversal.links_discovered - outcome.traversal.links_traversed
                print(f"  cap reached on {outcome.url} -> {not_followed} links not followed")
    unlinked = sum(o.unlinked_items_dropped for o in report.outcomes)
    if unlinked:
        print(f"dropped: {unlinked} listing items with no link of their own")
    print(f"skipped: {len(report.skipped)}")
    for skipped in report.skipped:
        print(f"  {skipped.seed.type.value}:{skipped.seed.value} -> {skipped.reason.value}")
    failures = [o for o in report.outcomes if not o.ok]
    print(f"failures: {len(failures)}")
    for outcome in failures:
        print(f"  {outcome.url} -> status={outcome.status_code} error={outcome.error}")
    return 0


def _cmd_refresh(store: OpportunityStore, opp_id: str) -> int:
    try:
        outcome = refresh_opportunity(
            store, opp_id, fetch_fn=fetch_url, extract_fn=extract
        )
    except KeyError:
        print(f"not found: {opp_id}", file=sys.stderr)
        return 1

    print(f"status: {outcome.status}")
    for change in outcome.changed_fields:
        print(f"  {change.field}: {change.old_value!r} -> {change.new_value!r}")
    for field in outcome.no_longer_found:
        print(f"  {field}: no longer found on the page")
    return 0


def _cmd_serve(db_path: str, host: str, port: int) -> int:
    import uvicorn

    from .api import create_app

    uvicorn.run(create_app(db_path), host=host, port=port)
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
    p_source = sub.add_parser("source", parents=[common], help="run a sourcing pass")
    p_source.add_argument("--seeds", required=True, help="seeds TOML path")
    p_source.add_argument(
        "--page-cap", type=int, default=TRAVERSE_PAGE_CAP,
        help=f"max pages traversed per listing (default: {TRAVERSE_PAGE_CAP})",
    )
    p_source.add_argument(
        "--min-interval", type=float, default=DEFAULT_MIN_INTERVAL,
        help=f"min seconds between requests to one host (default: {DEFAULT_MIN_INTERVAL})",
    )
    p_refresh = sub.add_parser("refresh", parents=[common], help="re-check one opportunity's facts")
    p_refresh.add_argument("id")
    p_serve = sub.add_parser("serve", parents=[common], help="run the dashboard API")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)
    if args.command == "serve":
        return _cmd_serve(args.db or _default_db_path(), args.host, args.port)

    store = OpportunityStore(args.db or _default_db_path())
    if args.command == "list":
        return _cmd_list(store, args.status)
    if args.command == "source":
        return _cmd_source(store, args.seeds, args.page_cap, args.min_interval)
    if args.command == "refresh":
        return _cmd_refresh(store, args.id)
    return _cmd_show(store, args.id)


if __name__ == "__main__":
    raise SystemExit(main())
