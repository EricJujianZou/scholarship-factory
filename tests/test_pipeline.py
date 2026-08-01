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


def test_listing_facts_survive_an_unreachable_detail_page(tmp_path):
    """Facts stated on the listing itself must not be lost when the link fails."""
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [Seed(type=SeedType.URL, value="https://example.com/listing")]
    fetch_fn = FakeFetch(
        {
            "https://example.com/listing": ok_result("https://example.com/listing"),
            "https://example.com/detail": FetchResult(
                requested_url="https://example.com/detail",
                final_url="https://example.com/detail",
                status_code=404,
                body=None,
            ),
        }
    )
    thin_item = make_opp(
        "https://example.com/detail",
        title="LITE Seed Grant",
        reward="Up to $7,500",
        reward_source="Amount: Up to $7,500",
        reward_provenance="quoted",
    )
    extract_fn = RecordingExtract(
        {"https://example.com/listing": [thin_item]},
        kind_by_url={"https://example.com/listing": PageKind.LIST},
    )

    run_sourcing(
        seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn,
        jsonld_fn=RecordingJsonld({}),
    )

    stored = store.list()
    assert len(stored) == 1
    assert stored[0].title == "LITE Seed Grant"
    assert stored[0].reward == "Up to $7,500"


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


def test_listing_item_without_link_does_not_store_thin_record(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [Seed(type=SeedType.URL, value="https://example.com/listing")]
    fetch_fn = FakeFetch(
        {
            "https://example.com/listing": ok_result("https://example.com/listing"),
            "https://example.com/detail": ok_result("https://example.com/detail"),
        }
    )
    linkless_item = make_opp("https://example.com/listing", title="Linkless")
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
            "https://example.com/listing": [linkless_item, thin_item],
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


def test_extract_failure_is_recorded_not_raised(tmp_path):
    """An LLM outage on one target must not abort the whole sourcing run."""
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [
        Seed(type=SeedType.URL, value="https://example.com/boom"),
        Seed(type=SeedType.URL, value="https://example.com/fine"),
    ]
    fetch_fn = FakeFetch(
        {
            "https://example.com/boom": ok_result("https://example.com/boom"),
            "https://example.com/fine": ok_result("https://example.com/fine"),
        }
    )

    def extract_fn(body: str, url: str) -> ExtractionResult:
        if url.endswith("/boom"):
            raise RuntimeError("503 UNAVAILABLE")
        return ExtractionResult(
            kind=PageKind.DETAIL, opportunities=[make_opp(url, title="Fine")]
        )

    report = run_sourcing(
        seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn,
        jsonld_fn=RecordingJsonld({}),
    )

    boom = next(o for o in report.outcomes if o.url.endswith("/boom"))
    assert boom.ok is False
    assert "503 UNAVAILABLE" in boom.error
    assert [o.title for o in store.list()] == ["Fine"]  # the good target still stored


def test_listing_item_folds_into_the_detail_record_it_linked_to(tmp_path):
    """A detail page that states a different apply link is still the same
    opportunity as the listing item that pointed at it - one row, not two."""
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [Seed(type=SeedType.URL, value="https://example.com/listing")]
    fetch_fn = FakeFetch(
        {
            "https://example.com/listing": ok_result("https://example.com/listing"),
            "https://example.com/article": ok_result("https://example.com/article"),
        }
    )
    thin_item = make_opp(
        "https://example.com/article",
        title="Solidarity Fund",
        reward="grants from GBP 2,000 to GBP 50,000",
        reward_source="grants from GBP 2,000 to GBP 50,000",
        reward_provenance="quoted",
    )
    detail_opp = make_opp(
        "https://apply.example.org/form",  # external apply link, not the article URL
        title="Solidarity Fund",
        deadline="10 August 2026",
        deadline_source="Deadline: 10 August 2026",
        deadline_provenance="quoted",
    )
    extract_fn = RecordingExtract(
        {
            "https://example.com/listing": [thin_item],
            "https://example.com/article": [detail_opp],
        },
        kind_by_url={"https://example.com/listing": PageKind.LIST},
    )

    run_sourcing(
        seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn,
        jsonld_fn=RecordingJsonld({}),
    )

    stored = store.list()
    assert len(stored) == 1
    assert stored[0].apply_url == "https://apply.example.org/form"  # detail wins
    assert stored[0].deadline == "10 August 2026"                   # from the detail
    assert stored[0].reward == "grants from GBP 2,000 to GBP 50,000"  # from the listing


def test_max_pages_follows_rel_next_across_listing_pages(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [Seed(type=SeedType.URL, value="https://example.com/page/1")]
    page1 = ok_result(
        "https://example.com/page/1", '<a rel="next" href="/page/2">older</a>'
    )
    page2 = ok_result("https://example.com/page/2", "<html></html>")  # no next
    fetch_fn = FakeFetch(
        {
            "https://example.com/page/1": page1,
            "https://example.com/page/2": page2,
            "https://example.com/a": ok_result("https://example.com/a"),
            "https://example.com/b": ok_result("https://example.com/b"),
        }
    )
    extract_fn = RecordingExtract(
        {
            "https://example.com/page/1": [make_opp("https://example.com/a", title="A")],
            "https://example.com/page/2": [make_opp("https://example.com/b", title="B")],
            "https://example.com/a": [make_opp("https://example.com/a", title="A")],
            "https://example.com/b": [make_opp("https://example.com/b", title="B")],
        },
        kind_by_url={
            "https://example.com/page/1": PageKind.LIST,
            "https://example.com/page/2": PageKind.LIST,
        },
    )

    report = run_sourcing(
        seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn,
        jsonld_fn=RecordingJsonld({}), max_pages=3,
    )

    assert report.targets_attempted == 2  # stopped when page 2 declared no next
    assert sorted(o.title for o in store.list()) == ["A", "B"]


def test_max_pages_default_visits_only_the_seed_page(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    seeds = [Seed(type=SeedType.URL, value="https://example.com/page/1")]
    fetch_fn = FakeFetch(
        {
            "https://example.com/page/1": ok_result(
                "https://example.com/page/1", '<a rel="next" href="/page/2">older</a>'
            )
        }
    )
    extract_fn = RecordingExtract(
        {}, kind_by_url={"https://example.com/page/1": PageKind.LIST}
    )

    report = run_sourcing(
        seeds, store, fetch_fn=fetch_fn, extract_fn=extract_fn,
        jsonld_fn=RecordingJsonld({}),
    )

    assert report.targets_attempted == 1
    assert fetch_fn.calls == ["https://example.com/page/1"]
