import sqlite3

from scholarship_factory import OpportunityStore
from scholarship_factory.identity import merge_into, normalize_text, title_org_key
from tests.test_store import make_opp


def test_normalize_text():
    assert normalize_text("The  Smith-Jones Fund!") == "the smith jones fund"
    assert normalize_text("  --  ") is None
    assert normalize_text(None) is None


def test_title_org_key_requires_both_halves():
    assert title_org_key("The  Smith-Jones Fund!", "Smith Jones Foundation") == (
        "the smith jones fund\x1fsmith jones foundation"
    )
    assert title_org_key("A Title", None) is None
    assert title_org_key(None, "An Org") is None


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
    assert merged.id == first.id
    assert merged.first_seen == first.first_seen
    assert merged.last_seen > first.last_seen


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


def test_url_match_wins_over_earlier_title_org_match(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    store.insert(
        make_opp("https://host-a.example.com/apply", title="Shared", organization="Org")
    )
    by_url = store.insert(
        make_opp("https://host-b.example.com/apply", title="Other", organization="Else")
    )
    merged = store.insert(
        make_opp("https://host-b.example.com/apply", title="Shared", organization="Org")
    )
    assert merged.id == by_url.id
    assert len(store.list()) == 2


def test_dedup_across_sources(tmp_path):
    store = OpportunityStore(str(tmp_path / "test.db"))
    store.insert(
        make_opp(
            "https://jobs.example.com/swe-intern",
            title="SWE Intern",
            organization="Acme",
        )
    )
    store.insert(
        make_opp(
            "https://careers.example.com/other-link",
            title="SWE  Intern!",
            organization="ACME",
        )
    )
    assert len(store.list()) == 1


_PRE_MIGRATION_SCHEMA = """
CREATE TABLE opportunities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    apply_url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    deadline TEXT, reward TEXT, cost TEXT,
    organization TEXT, requirements TEXT, type TEXT, description TEXT,
    deadline_provenance TEXT NOT NULL,
    reward_provenance TEXT NOT NULL,
    cost_provenance TEXT NOT NULL,
    deadline_source TEXT, reward_source TEXT, cost_source TEXT,
    source_observed_date TEXT,
    owner TEXT NOT NULL, status TEXT NOT NULL,
    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
    normalized_apply_url TEXT NOT NULL
)
"""


def test_migration_backfills_title_org_key(tmp_path):
    db = str(tmp_path / "old.db")
    conn = sqlite3.connect(db)
    conn.execute(_PRE_MIGRATION_SCHEMA)
    conn.execute(
        "INSERT INTO opportunities (id, title, apply_url, source_url, organization,"
        " deadline_provenance, reward_provenance, cost_provenance, owner, status,"
        " first_seen, last_seen, normalized_apply_url) VALUES"
        " ('old1', 'The Smith-Jones Fund!', 'https://host-a.example.com/apply',"
        " 'https://host-a.example.com', 'Smith Jones Foundation', 'none', 'none',"
        " 'none', 'me', 'new', '2026-01-01', '2026-01-01',"
        " 'https://host-a.example.com/apply')"
    )
    conn.commit()
    conn.close()

    store = OpportunityStore(db)
    store.insert(
        make_opp(
            "https://host-b.example.com/apply",
            title="the smith jones fund",
            organization="smith jones foundation",
        )
    )
    all_opps = store.list()
    assert len(all_opps) == 1
    assert all_opps[0].id == "old1"


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
