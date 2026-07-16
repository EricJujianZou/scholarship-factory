from scholarship_factory import OpportunityStore
from scholarship_factory.identity import merge_into, normalize_text
from tests.test_store import make_opp


def test_normalize_text():
    assert normalize_text("The  Smith-Jones Fund!") == "the smith jones fund"
    assert normalize_text("  --  ") is None
    assert normalize_text(None) is None


def test_url_dedup_still_merges_one_row(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    store.insert(make_opp("https://example.com/apply?utm_source=x&fbclid=123"))
    store.insert(make_opp("https://example.com/apply"))
    assert len(store.list()) == 1


def test_secondary_match_merges_union_of_facts(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    first = store.insert(
        make_opp(
            "https://host-a.example.com/apply",
            title="The  Smith-Jones Fund!",
            organization="Smith Jones Foundation",
            reward="$1000",
            reward_provenance="quoted",
            reward_source="Award is $1000",
        )
    )
    store.insert(
        make_opp(
            "https://host-b.example.com/apply",
            title="the smith jones fund",
            organization="smith jones foundation",
            reward="$2000",
            reward_provenance="quoted",
            reward_source="Award is $2000",
            deadline="2026-07-01",
            deadline_provenance="quoted",
            deadline_source="Applications close July 1, 2026",
        )
    )

    all_opps = store.list()
    assert len(all_opps) == 1
    merged = all_opps[0]
    assert merged.reward == "$1000"
    assert merged.deadline == "2026-07-01"
    assert merged.deadline_source == "Applications close July 1, 2026"
    assert merged.last_seen >= merged.first_seen


def test_same_title_different_org_does_not_merge(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    store.insert(
        make_opp("https://host-a.example.com/apply", title="Shared Title", organization="Org A")
    )
    store.insert(
        make_opp("https://host-b.example.com/apply", title="Shared Title", organization="Org B")
    )
    assert len(store.list()) == 2


def test_same_org_different_title_does_not_merge(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    store.insert(
        make_opp("https://host-a.example.com/apply", title="Title A", organization="Shared Org")
    )
    store.insert(
        make_opp("https://host-b.example.com/apply", title="Title B", organization="Shared Org")
    )
    assert len(store.list()) == 2


def test_thin_then_detail_same_url_carries_detail_facts(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    store.insert(make_opp("https://example.com/apply", title="Thin Listing"))
    store.insert(
        make_opp(
            "https://example.com/apply",
            title="Rich Detail Title",
            deadline="2026-07-01",
            deadline_provenance="quoted",
            deadline_source="Applications close July 1, 2026",
        )
    )

    all_opps = store.list()
    assert len(all_opps) == 1
    merged = all_opps[0]
    assert merged.title == "Thin Listing"
    assert merged.deadline == "2026-07-01"
    assert merged.deadline_source == "Applications close July 1, 2026"


def test_merge_into_keeps_existing_non_null_fact():
    existing = make_opp(
        "https://example.com/apply",
        deadline="2026-01-01",
        deadline_provenance="quoted",
        deadline_source="Existing source",
    )
    incoming = make_opp(
        "https://example.com/apply",
        deadline="2026-02-02",
        deadline_provenance="quoted",
        deadline_source="Incoming source",
    )
    merged = merge_into(existing, incoming)
    assert merged.deadline == "2026-01-01"
    assert merged.deadline_source == "Existing source"
