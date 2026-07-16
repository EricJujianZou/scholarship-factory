from scholarship_factory import (
    ExtractionResult,
    FetchResult,
    Opportunity,
    PageKind,
    Provenance,
    traverse,
)


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


class RecordingExtract:
    def __init__(self, opportunities_by_url: dict[str, list[Opportunity]]):
        self._by_url = opportunities_by_url
        self.calls: list[tuple[str, str]] = []

    def __call__(self, body: str, url: str) -> ExtractionResult:
        self.calls.append((body, url))
        return ExtractionResult(
            kind=PageKind.DETAIL, opportunities=self._by_url.get(url, [])
        )


def no_jsonld(body: str, url: str) -> list[Opportunity]:
    return []


def test_traverse_fetches_each_thin_item_and_returns_detail_records():
    thin_items = [
        make_opp("https://example.com/a", title="A"),
        make_opp("https://example.com/b", title="B"),
    ]
    listing = ExtractionResult(kind=PageKind.LIST, opportunities=thin_items)

    fetch_fn = FakeFetch(
        {
            "https://example.com/a": ok_result("https://example.com/a"),
            "https://example.com/b": ok_result("https://example.com/b"),
        }
    )
    detail_a = make_opp(
        "https://example.com/a",
        title="A",
        deadline="2026-01-01",
        deadline_source="Applications due 2026-01-01",
        deadline_provenance=Provenance.QUOTED,
    )
    detail_b = make_opp("https://example.com/b", title="B")
    extract_fn = RecordingExtract(
        {
            "https://example.com/a": [detail_a],
            "https://example.com/b": [detail_b],
        }
    )

    result = traverse(
        listing,
        "https://example.com/listing",
        fetch_fn=fetch_fn,
        extract_fn=extract_fn,
        jsonld_fn=no_jsonld,
    )

    assert sorted(fetch_fn.calls) == ["https://example.com/a", "https://example.com/b"]
    assert len(result.opportunities) == 2
    stored_a = next(o for o in result.opportunities if o.apply_url == "https://example.com/a")
    assert stored_a.deadline == "2026-01-01"
    assert stored_a.deadline_provenance == Provenance.QUOTED
    assert stored_a.source_url == "https://example.com/a"
    assert result.report.links_traversed == 2
    assert result.report.cap_reached is False


def test_page_cap_stops_early_and_flags_report():
    thin_items = [make_opp(f"https://example.com/{i}", title=str(i)) for i in range(5)]
    listing = ExtractionResult(kind=PageKind.LIST, opportunities=thin_items)

    fetch_fn = FakeFetch(
        {f"https://example.com/{i}": ok_result(f"https://example.com/{i}") for i in range(5)}
    )
    extract_fn = RecordingExtract(
        {f"https://example.com/{i}": [make_opp(f"https://example.com/{i}")] for i in range(5)}
    )

    result = traverse(
        listing,
        "https://example.com/listing",
        fetch_fn=fetch_fn,
        extract_fn=extract_fn,
        jsonld_fn=no_jsonld,
        page_cap=2,
    )

    assert len(fetch_fn.calls) == 2
    assert result.report.cap_reached is True
    assert result.report.links_discovered == 5
    assert result.report.links_traversed == 2


def test_fetch_failure_and_empty_extraction_reported_others_still_process():
    thin_items = [
        make_opp("https://example.com/fails", title="fails"),
        make_opp("https://example.com/empty", title="empty"),
        make_opp("https://example.com/ok", title="ok"),
    ]
    listing = ExtractionResult(kind=PageKind.LIST, opportunities=thin_items)

    fetch_fn = FakeFetch(
        {
            "https://example.com/fails": FetchResult(
                requested_url="https://example.com/fails",
                final_url="https://example.com/fails",
                status_code=404,
                body=None,
                error="not found",
            ),
            "https://example.com/empty": ok_result("https://example.com/empty"),
            "https://example.com/ok": ok_result("https://example.com/ok"),
        }
    )
    extract_fn = RecordingExtract(
        {"https://example.com/ok": [make_opp("https://example.com/ok")]}
    )

    result = traverse(
        listing,
        "https://example.com/listing",
        fetch_fn=fetch_fn,
        extract_fn=extract_fn,
        jsonld_fn=no_jsonld,
    )

    assert len(result.opportunities) == 1
    fails_outcome = next(o for o in result.report.outcomes if o.url == "https://example.com/fails")
    empty_outcome = next(o for o in result.report.outcomes if o.url == "https://example.com/empty")
    assert fails_outcome.ok is False
    assert fails_outcome.error == "not found"
    assert empty_outcome.ok is False
    assert empty_outcome.error != fails_outcome.error
    ok_outcome = next(o for o in result.report.outcomes if o.url == "https://example.com/ok")
    assert ok_outcome.ok is True


def test_duplicate_urls_after_normalization_fetched_once():
    thin_items = [
        make_opp("https://example.com/a/", title="a-slash"),
        make_opp("https://example.com/a?utm_source=x", title="a-utm"),
    ]
    listing = ExtractionResult(kind=PageKind.LIST, opportunities=thin_items)

    fetch_fn = FakeFetch(
        {
            "https://example.com/a/": ok_result("https://example.com/a/"),
        }
    )
    extract_fn = RecordingExtract(
        {"https://example.com/a/": [make_opp("https://example.com/a/")]}
    )

    result = traverse(
        listing,
        "https://example.com/listing",
        fetch_fn=fetch_fn,
        extract_fn=extract_fn,
        jsonld_fn=no_jsonld,
    )

    assert len(fetch_fn.calls) == 1
    assert result.report.links_discovered == 1


def test_relative_apply_url_resolves_against_listing_url():
    thin_items = [make_opp("/details/a", title="A")]
    listing = ExtractionResult(kind=PageKind.LIST, opportunities=thin_items)

    fetch_fn = FakeFetch(
        {"https://example.com/details/a": ok_result("https://example.com/details/a")}
    )
    extract_fn = RecordingExtract(
        {"https://example.com/details/a": [make_opp("https://example.com/details/a")]}
    )

    result = traverse(
        listing,
        "https://example.com/listing",
        fetch_fn=fetch_fn,
        extract_fn=extract_fn,
        jsonld_fn=no_jsonld,
    )

    assert fetch_fn.calls == ["https://example.com/details/a"]
    assert len(result.opportunities) == 1


def test_thin_item_linking_to_listing_itself_is_not_traversed():
    thin_items = [
        make_opp("https://example.com/listing", title="Linkless"),
        make_opp("https://example.com/detail", title="Detail"),
    ]
    listing = ExtractionResult(kind=PageKind.LIST, opportunities=thin_items)

    fetch_fn = FakeFetch(
        {"https://example.com/detail": ok_result("https://example.com/detail")}
    )
    extract_fn = RecordingExtract(
        {"https://example.com/detail": [make_opp("https://example.com/detail")]}
    )

    result = traverse(
        listing,
        "https://example.com/listing",
        fetch_fn=fetch_fn,
        extract_fn=extract_fn,
        jsonld_fn=no_jsonld,
    )

    assert fetch_fn.calls == ["https://example.com/detail"]
    assert all(o.title != "Linkless" for o in result.opportunities)
    assert result.report.links_discovered == 1
