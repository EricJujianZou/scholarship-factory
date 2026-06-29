from scholarship_factory import Opportunity, OpportunityStore


def make_opp(apply_url="https://example.com/apply", **kwargs):
    kwargs.setdefault("title", "Test Scholarship")
    return Opportunity(
        apply_url=apply_url,
        source_url=apply_url,
        **kwargs,
    )


def test_crud_round_trip(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    opp = make_opp(title="Original")
    inserted = store.insert(opp)

    fetched = store.get(inserted.id)
    assert fetched is not None
    assert fetched.title == "Original"

    all_opps = store.list()
    assert len(all_opps) == 1

    fetched.title = "Updated"
    updated = store.update(fetched)
    assert updated.title == "Updated"
    assert store.get(inserted.id).title == "Updated"


def test_owner_defaults_and_timestamps_populated(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    inserted = store.insert(make_opp())
    assert inserted.owner == "me"
    assert inserted.first_seen is not None
    assert inserted.last_seen is not None


def test_dedup_tracking_param(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    store.insert(make_opp("https://example.com/apply?utm_source=x"))
    store.insert(make_opp("https://example.com/apply"))
    assert len(store.list()) == 1


def test_dedup_trailing_slash(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    store.insert(make_opp("https://example.com/apply/"))
    store.insert(make_opp("https://example.com/apply"))
    assert len(store.list()) == 1


def test_dedup_http_https(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    store.insert(make_opp("http://example.com/apply"))
    store.insert(make_opp("https://example.com/apply"))
    assert len(store.list()) == 1


def test_last_seen_refresh_on_reinsert(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    first = store.insert(make_opp("https://example.com/apply"))
    second = store.insert(make_opp("https://example.com/apply"))

    assert first.id == second.id
    assert first.first_seen == second.first_seen
    assert second.last_seen >= first.last_seen


def test_source_span_fields_round_trip(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    opp = make_opp(
        deadline="2026-07-01",
        deadline_provenance="quoted",
        deadline_source="Applications close July 1, 2026",
        cost="$50",
        cost_provenance="quoted",
        cost_source="A $50 application fee applies",
        source_observed_date="2026-06-01",
    )
    inserted = store.insert(opp)

    fetched = store.get(inserted.id)
    assert fetched.deadline_source == "Applications close July 1, 2026"
    assert fetched.cost_source == "A $50 application fee applies"
    assert fetched.source_observed_date == "2026-06-01"
    assert fetched.reward_source is None

    fetched.cost_source = "Updated cost source"
    updated = store.update(fetched)
    assert updated.cost_source == "Updated cost source"
    assert store.get(inserted.id).cost_source == "Updated cost source"
