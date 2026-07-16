from pathlib import Path

from scholarship_factory import (
    AdapterPlan,
    ExtractionResult,
    FetchResult,
    Opportunity,
    OpportunityStore,
    PageKind,
    Seed,
    SeedType,
    SkipReason,
    run_sourcing,
)
from scholarship_factory.jsonld import extract_jsonld

FIXTURES = Path(__file__).parent / "fixtures"


def make_opp(apply_url, **kwargs):
    kwargs.setdefault("title", "Test Opportunity")
    kwargs.setdefault("source_url", apply_url)
    return Opportunity(apply_url=apply_url, **kwargs)


class FakeFetch:
    def __init__(self, results: dict[str, FetchResult]):
        self._results = results
        self.calls: list[str] = []

    def __call__(self, url: str) -> FetchResult:
        self.calls.append(url)
        return self._results[url]


def ok_result(url: str, body: str = "<html></html>") -> FetchResult:
    return FetchResult(requested_url=url, final_url=url, status_code=200, body=body)


class RecordingJsonld:
    def __init__(self, opportunities_by_url: dict[str, list[Opportunity]]):
        self._by_url = opportunities_by_url
        self.calls: list[tuple[str, str]] = []

    def __call__(self, body: str, url: str) -> list[Opportunity]:
        self.calls.append((body, url))
        return self._by_url.get(url, [])


class RecordingExtract:
    def __init__(
        self,
        opportunities_by_url: dict[str, list[Opportunity]],
        kind_by_url: dict[str, PageKind] | None = None,
    ):
        self._by_url = opportunities_by_url
        self._kind_by_url = kind_by_url or {}
        self.calls: list[tuple[str, str]] = []

    def __call__(self, body: str, url: str) -> ExtractionResult:
        self.calls.append((body, url))
        return ExtractionResult(
            kind=self._kind_by_url.get(url, PageKind.DETAIL),
            opportunities=self._by_url.get(url, []),
        )


def test_url_and_skipped_seed_reports_one_target_and_stores_opportunities(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [
        Seed(type=SeedType.URL, value="https://example.com/a"),
        Seed(type=SeedType.INSTAGRAM, value="somepage"),
    ]
    fetch_fn = FakeFetch({"https://example.com/a": ok_result("https://example.com/a")})
    opp = make_opp("https://example.com/apply")
    jsonld_fn = RecordingJsonld({"https://example.com/a": [opp]})
    extract_fn = RecordingExtract({})

    report = run_sourcing(
        seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn, jsonld_fn=jsonld_fn
    )

    assert report.targets_attempted == 1
    assert len(report.skipped) == 1
    assert report.skipped[0].reason == SkipReason.UNSUPPORTED
    assert [o.apply_url for o in store.list()] == ["https://example.com/apply"]


def test_fetch_failure_recorded_other_targets_still_process(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [
        Seed(type=SeedType.URL, value="https://example.com/fails"),
        Seed(type=SeedType.URL, value="https://example.com/ok"),
    ]
    fetch_fn = FakeFetch(
        {
            "https://example.com/fails": FetchResult(
                requested_url="https://example.com/fails",
                final_url="https://example.com/fails",
                status_code=403,
                body=None,
                error="forbidden",
            ),
            "https://example.com/ok": ok_result("https://example.com/ok"),
        }
    )
    opp = make_opp("https://example.com/apply-ok")
    jsonld_fn = RecordingJsonld({"https://example.com/ok": [opp]})
    extract_fn = RecordingExtract({})

    report = run_sourcing(
        seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn, jsonld_fn=jsonld_fn
    )

    assert report.targets_attempted == 2
    failed = next(o for o in report.outcomes if o.url == "https://example.com/fails")
    assert failed.ok is False
    assert failed.status_code == 403
    assert failed.error == "forbidden"
    succeeded = next(o for o in report.outcomes if o.url == "https://example.com/ok")
    assert succeeded.ok is True
    assert [o.apply_url for o in store.list()] == ["https://example.com/apply-ok"]


def test_rerun_against_same_store_does_not_duplicate(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [Seed(type=SeedType.URL, value="https://example.com/a")]
    fetch_fn = FakeFetch({"https://example.com/a": ok_result("https://example.com/a")})
    opp = make_opp("https://example.com/apply")
    jsonld_fn = RecordingJsonld({"https://example.com/a": [opp]})
    extract_fn = RecordingExtract({})

    run_sourcing(seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn, jsonld_fn=jsonld_fn)
    first = store.list()
    run_sourcing(seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn, jsonld_fn=jsonld_fn)
    second = store.list()

    assert len(second) == 1
    assert first[0].id == second[0].id
    assert first[0].first_seen == second[0].first_seen
    assert second[0].last_seen >= first[0].last_seen


def test_both_extract_paths_run_on_lablab_fixture(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [Seed(type=SeedType.URL, value="https://example.com/lablab")]
    body = (FIXTURES / "lablab_executorch.html").read_text(encoding="utf-8")
    fetch_fn = FakeFetch({"https://example.com/lablab": ok_result("https://example.com/lablab", body)})

    real_jsonld_calls: list[tuple[str, str]] = []

    def jsonld_fn(html: str, url: str) -> list[Opportunity]:
        real_jsonld_calls.append((html, url))
        return extract_jsonld(html, url)

    prose_opp = make_opp("https://example.com/apply-prose", title="Prose Record")
    extract_fn = RecordingExtract({"https://example.com/lablab": [prose_opp]})

    report = run_sourcing(
        seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn, jsonld_fn=jsonld_fn
    )

    assert len(real_jsonld_calls) == 1
    assert len(extract_fn.calls) == 1
    apply_urls = {o.apply_url for o in store.list()}
    assert "https://example.com/apply-prose" in apply_urls
    assert report.opportunities_stored == 2


def test_listing_traversal_stores_detail_record_with_deadline(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [Seed(type=SeedType.URL, value="https://example.com/listing")]
    fetch_fn = FakeFetch(
        {
            "https://example.com/listing": ok_result("https://example.com/listing"),
            "https://example.com/detail": ok_result("https://example.com/detail"),
        }
    )
    thin_item = make_opp("https://example.com/detail", title="Thin")
    detail_opp = make_opp(
        "https://example.com/detail",
        title="Detail",
        deadline="2026-05-01",
        deadline_source="Deadline: 2026-05-01",
        deadline_provenance="quoted",
    )
    extract_fn = RecordingExtract(
        {
            "https://example.com/listing": [thin_item],
            "https://example.com/detail": [detail_opp],
        },
        kind_by_url={"https://example.com/listing": PageKind.LIST},
    )
    jsonld_fn = RecordingJsonld({})

    run_sourcing(
        seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn, jsonld_fn=jsonld_fn
    )

    stored = store.list()
    assert len(stored) == 1
    assert stored[0].deadline == "2026-05-01"
    assert stored[0].source_url == "https://example.com/detail"


def test_target_outcome_exposes_traversal_cap_reached(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [Seed(type=SeedType.URL, value="https://example.com/listing")]
    thin_items = [make_opp(f"https://example.com/{i}", title=str(i)) for i in range(3)]
    fetch_fn = FakeFetch(
        {
            "https://example.com/listing": ok_result("https://example.com/listing"),
            **{
                f"https://example.com/{i}": ok_result(f"https://example.com/{i}")
                for i in range(3)
            },
        }
    )
    extract_fn = RecordingExtract(
        {
            "https://example.com/listing": thin_items,
            **{
                f"https://example.com/{i}": [make_opp(f"https://example.com/{i}")]
                for i in range(3)
            },
        },
        kind_by_url={"https://example.com/listing": PageKind.LIST},
    )
    jsonld_fn = RecordingJsonld({})

    report = run_sourcing(
        seeds,
        store,
        fetch_fn=fetch_fn,
        extract_fn=extract_fn,
        jsonld_fn=jsonld_fn,
        page_cap=1,
    )

    outcome = next(o for o in report.outcomes if o.url == "https://example.com/listing")
    assert outcome.traversal is not None
    assert outcome.traversal.cap_reached is True
