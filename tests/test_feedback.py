from scholarship_factory.feedback import (
    DecisionStore,
    DecisionVerdict,
    PreferenceStore,
)


def test_decision_round_trip_and_change(tmp_path):
    store = DecisionStore(str(tmp_path / "t.db"))
    store.set("opp-1", DecisionVerdict.INTERESTED, note="close to home")

    stored = store.get("opp-1")
    assert stored.verdict == DecisionVerdict.INTERESTED
    assert stored.note == "close to home"
    assert stored.decided_at

    store.set("opp-1", DecisionVerdict.NOT_INTERESTED)
    assert store.get("opp-1").verdict == DecisionVerdict.NOT_INTERESTED
    assert len(store.list()) == 1  # changed, not duplicated


def test_decisions_are_listed_newest_first(tmp_path):
    store = DecisionStore(str(tmp_path / "t.db"))
    store.set("old", DecisionVerdict.INTERESTED)
    store.set("new", DecisionVerdict.NOT_INTERESTED)

    assert [d.opportunity_id for d in store.list()][0] == "new"


def test_clear_removes_a_decision(tmp_path):
    store = DecisionStore(str(tmp_path / "t.db"))
    store.set("opp-1", DecisionVerdict.INTERESTED)
    store.clear("opp-1")
    assert store.get("opp-1") is None


def test_decision_does_not_touch_opportunity_status(tmp_path):
    """The freshness lifecycle and the owner's call are separate dimensions."""
    from scholarship_factory.models import Opportunity
    from scholarship_factory.store import OpportunityStore

    db = str(tmp_path / "t.db")
    opps = OpportunityStore(db)
    opp = opps.insert(
        Opportunity(
            title="G", apply_url="https://e.com/a", source_url="https://e.com"
        )
    )
    DecisionStore(db).set(opp.id, DecisionVerdict.NOT_INTERESTED)

    assert opps.get(opp.id).status == "new"


def test_preference_summary_round_trip(tmp_path):
    store = PreferenceStore(str(tmp_path / "t.db"))
    assert store.get() is None
    assert store.decision_count() == 0

    store.set("You tend to accept Canadian awards.", 7)
    assert store.get() == "You tend to accept Canadian awards."
    assert store.decision_count() == 7

    store.set("Updated.", 12)
    assert store.get() == "Updated."
    assert store.decision_count() == 12
