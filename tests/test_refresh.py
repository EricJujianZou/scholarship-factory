from datetime import timedelta

from scholarship_factory import (
    ExtractionResult,
    FetchCache,
    FetchResult,
    Opportunity,
    OpportunityStore,
    PageKind,
    Provenance,
    refresh_opportunity,
)


class FakeFetch:
    def __init__(self, results: dict[str, FetchResult]):
        self._results = results
        self.calls: list[str] = []

    def __call__(self, url: str) -> FetchResult:
        self.calls.append(url)
        return self._results[url]


class RecordingExtract:
    def __init__(self, opportunities: list[Opportunity], kind: PageKind = PageKind.DETAIL):
        self._opportunities = opportunities
        self._kind = kind
        self.calls: list[tuple[str, str]] = []

    def __call__(self, body: str, url: str) -> ExtractionResult:
        self.calls.append((body, url))
        return ExtractionResult(kind=self._kind, opportunities=self._opportunities)


def ok_result(url: str, body: str = "<html></html>") -> FetchResult:
    return FetchResult(requested_url=url, final_url=url, status_code=200, body=body)


def seed_opp(store: OpportunityStore, **kwargs) -> Opportunity:
    kwargs.setdefault("title", "Test Grant")
    kwargs.setdefault("apply_url", "https://example.com/apply")
    kwargs.setdefault("source_url", "https://example.com/apply")
    return store.insert(Opportunity(**kwargs))


def test_unchanged_deadline_bumps_last_seen_and_status_refreshed(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    opp = seed_opp(
        store,
        deadline="July 1, 2026",
        deadline_provenance=Provenance.QUOTED,
        deadline_source="Applications close July 1, 2026",
    )
    candidate = Opportunity(
        title=opp.title,
        apply_url=opp.apply_url,
        source_url=opp.source_url,
        deadline="July 1, 2026",
        deadline_provenance=Provenance.QUOTED,
        deadline_source="Applications close July 1, 2026",
    )
    fetch_fn = FakeFetch({opp.source_url: ok_result(opp.source_url)})
    extract_fn = RecordingExtract([candidate])

    outcome = refresh_opportunity(store, opp.id, fetch_fn=fetch_fn, extract_fn=extract_fn)

    assert outcome.status == "refreshed"
    assert outcome.changed_fields == []
    assert outcome.no_longer_found == []
    row = store.get(opp.id)
    assert row.deadline == "July 1, 2026"
    assert row.deadline_source == "Applications close July 1, 2026"
    assert row.last_seen > opp.last_seen


def test_new_deadline_updates_fact_and_status_changed(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    opp = seed_opp(
        store,
        deadline="July 1, 2026",
        deadline_provenance=Provenance.QUOTED,
        deadline_source="Applications close July 1, 2026",
    )
    candidate = Opportunity(
        title=opp.title,
        apply_url=opp.apply_url,
        source_url=opp.source_url,
        deadline="August 1, 2026",
        deadline_provenance=Provenance.QUOTED,
        deadline_source="Applications close August 1, 2026",
    )
    fetch_fn = FakeFetch({opp.source_url: ok_result(opp.source_url)})
    extract_fn = RecordingExtract([candidate])

    outcome = refresh_opportunity(store, opp.id, fetch_fn=fetch_fn, extract_fn=extract_fn)

    assert outcome.status == "changed"
    assert len(outcome.changed_fields) == 1
    change = outcome.changed_fields[0]
    assert change.field == "deadline"
    assert change.old_value == "July 1, 2026"
    assert change.new_value == "August 1, 2026"

    row = store.get(opp.id)
    assert row.deadline == "August 1, 2026"
    assert row.deadline_source == "Applications close August 1, 2026"


def test_fact_absent_from_reextract_is_retained_and_recorded(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    opp = seed_opp(
        store,
        deadline="July 1, 2026",
        deadline_provenance=Provenance.QUOTED,
        deadline_source="Applications close July 1, 2026",
    )
    candidate = Opportunity(
        title=opp.title,
        apply_url=opp.apply_url,
        source_url=opp.source_url,
    )
    fetch_fn = FakeFetch({opp.source_url: ok_result(opp.source_url)})
    extract_fn = RecordingExtract([candidate])

    outcome = refresh_opportunity(store, opp.id, fetch_fn=fetch_fn, extract_fn=extract_fn)

    assert outcome.no_longer_found == ["deadline"]
    row = store.get(opp.id)
    assert row.deadline == "July 1, 2026"
    assert row.deadline_source == "Applications close July 1, 2026"


def test_fetch_failure_marks_unreachable_and_leaves_record_untouched(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    opp = seed_opp(
        store,
        deadline="July 1, 2026",
        deadline_provenance=Provenance.QUOTED,
        deadline_source="Applications close July 1, 2026",
    )
    before = store.get(opp.id)
    fetch_fn = FakeFetch(
        {
            opp.source_url: FetchResult(
                requested_url=opp.source_url,
                final_url=opp.source_url,
                status_code=503,
                body=None,
                error="server error",
            )
        }
    )
    extract_fn = RecordingExtract([])

    outcome = refresh_opportunity(store, opp.id, fetch_fn=fetch_fn, extract_fn=extract_fn)

    assert outcome.status == "unreachable"
    assert outcome.fetch_status_code == 503
    row = store.get(opp.id)
    assert row.last_seen == before.last_seen
    assert row.deadline == before.deadline
    assert row.deadline_source == before.deadline_source
    assert not extract_fn.calls


def test_cache_is_bypassed_even_with_fresh_entry(tmp_path):
    store = OpportunityStore(str(tmp_path / "t.db"))
    opp = seed_opp(store)
    cache = FetchCache(str(tmp_path / "cache.db"))
    cache.put(ok_result(opp.source_url, body="<html>stale-cached</html>"))

    fetch_fn = FakeFetch({opp.source_url: ok_result(opp.source_url, body="<html>fresh</html>")})
    candidate = Opportunity(
        title=opp.title,
        apply_url=opp.apply_url,
        source_url=opp.source_url,
    )
    extract_fn = RecordingExtract([candidate])

    refresh_opportunity(store, opp.id, fetch_fn=fetch_fn, extract_fn=extract_fn)

    assert fetch_fn.calls == [opp.source_url]
    assert extract_fn.calls[0][0] == "<html>fresh</html>"
    cache.get(opp.source_url, timedelta(days=1))
