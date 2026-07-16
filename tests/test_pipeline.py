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
    def __init__(self, opportunities_by_url: dict[str, list[Opportunity]]):
        self._by_url = opportunities_by_url
        self.calls: list[tuple[str, str]] = []

    def __call__(self, body: str, url: str) -> ExtractionResult:
        self.calls.append((body, url))
        return ExtractionResult(
            kind=PageKind.DETAIL, opportunities=self._by_url.get(url, [])
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
