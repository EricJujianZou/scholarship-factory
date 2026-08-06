import json

from scholarship_factory.feedback import Decision, DecisionVerdict
from scholarship_factory.models import Opportunity
from scholarship_factory.profile import ApplicantProfile
from scholarship_factory.relevance import (
    RelevanceStore,
    ScoredOpportunity,
    distil_preferences,
    score,
)


class StubClient:
    """Anthropic-shaped stub: records the prompt, returns a canned tool call."""

    def __init__(self, payload):
        self._payload = payload
        self.messages = self
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        block = type("Block", (), {"type": "tool_use", "input": self._payload})()
        return type("Message", (), {"content": [block]})()

    @property
    def user_text(self):
        return self.last_kwargs["messages"][0]["content"]


def _opp(title, **kwargs):
    kwargs.setdefault("apply_url", f"https://e.com/{title}")
    kwargs.setdefault("source_url", "https://e.com")
    return Opportunity(title=title, **kwargs)


def test_score_orders_high_fit_first_and_keeps_reasons():
    opps = [_opp("Africa Youth Grant"), _opp("Waterloo Award")]
    client = StubClient(
        {
            "fits": [
                {"index": 0, "fit": "low", "reason": "aimed at West Africa"},
                {"index": 1, "fit": "high", "reason": "open to Waterloo undergrads"},
            ]
        }
    )

    result = score(opps, ApplicantProfile(region="Canada"), client=client)

    assert [s.opportunity.title for s in result] == ["Waterloo Award", "Africa Youth Grant"]
    assert result[0].fit == "high"
    assert "Waterloo" in result[0].reason


def test_unjudged_opportunity_is_medium_not_low():
    """A model that skips an entry has said nothing, not something bad."""
    opps = [_opp("A"), _opp("B")]
    client = StubClient({"fits": [{"index": 0, "fit": "high", "reason": "yes"}]})

    result = score(opps, ApplicantProfile(), client=client)

    skipped = next(s for s in result if s.opportunity.title == "B")
    assert skipped.fit == "medium"
    assert "not judged" in skipped.reason


def test_decisions_and_summary_reach_the_prompt():
    opps = [_opp("Target")]
    decisions = [
        Decision(opportunity_id=opps[0].id, verdict=DecisionVerdict.NOT_INTERESTED)
    ]
    client = StubClient({"fits": [{"index": 0, "fit": "low", "reason": "r"}]})

    score(
        opps,
        ApplicantProfile(region="Canada"),
        decisions=decisions,
        preference_summary="You tend to skip travel-heavy programs.",
        client=client,
    )

    assert "REJECTED: Target" in client.user_text
    assert "travel-heavy" in client.user_text
    assert "region: Canada" in client.user_text


def test_decision_for_a_deleted_opportunity_is_not_quoted():
    client = StubClient({"fits": [{"index": 0, "fit": "high", "reason": "r"}]})
    decisions = [Decision(opportunity_id="gone", verdict=DecisionVerdict.INTERESTED)]

    score([_opp("Kept")], ApplicantProfile(), decisions=decisions, client=client)

    assert "THEIR PAST DECISIONS" not in client.user_text


def test_empty_input_makes_no_llm_call():
    client = StubClient({"fits": []})
    assert score([], ApplicantProfile(), client=client) == []
    assert client.last_kwargs is None


def test_distil_preferences_summarizes_decisions():
    client = StubClient({"summary": "You tend to accept Canadian awards."})
    decisions = [Decision(opportunity_id="a", verdict=DecisionVerdict.INTERESTED)]

    summary = distil_preferences(
        decisions, {"a": "Waterloo Award"}, ApplicantProfile(), client=client
    )

    assert summary == "You tend to accept Canadian awards."
    assert "ACCEPTED: Waterloo Award" in client.user_text


def test_relevance_store_round_trip_and_update(tmp_path):
    store = RelevanceStore(str(tmp_path / "t.db"))
    opp = _opp("A")
    store.replace([ScoredOpportunity(opportunity=opp, fit="low", reason="first")])
    assert store.all()[opp.id] == ("low", "first")

    store.replace([ScoredOpportunity(opportunity=opp, fit="high", reason="second")])
    assert store.all()[opp.id] == ("high", "second")
    assert len(store.all()) == 1


class BatchingStubClient:
    """Returns a fits payload sized to each request, recording every call."""

    def __init__(self):
        self.messages = self
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = kwargs["messages"][0]["content"]
        count = text.count("\n[")  # every "[i] Title" line, including the first
        fits = [{"index": i, "fit": "medium", "reason": "r"} for i in range(count)]
        block = type("Block", (), {"type": "tool_use", "input": {"fits": fits}})()
        return type("Message", (), {"content": [block]})()


def test_bulk_scoring_batches_instead_of_one_giant_call():
    from scholarship_factory.relevance import SCORE_BATCH_SIZE

    opps = [_opp(f"Opp {i:04d}") for i in range(SCORE_BATCH_SIZE * 2 + 5)]
    client = BatchingStubClient()

    result = score(opps, ApplicantProfile(), client=client)

    assert len(client.calls) == 3
    assert len(result) == len(opps)  # every opportunity judged exactly once
    assert {s.opportunity.title for s in result} == {o.title for o in opps}


def test_on_batch_persists_batches_as_they_land():
    """A quota death mid-run must keep the batches already judged."""
    from scholarship_factory.relevance import SCORE_BATCH_SIZE

    opps = [_opp(f"Opp {i:04d}") for i in range(SCORE_BATCH_SIZE + 3)]

    class DiesOnSecondCall(BatchingStubClient):
        def create(self, **kwargs):
            if len(self.calls) >= 1:
                raise RuntimeError("429 quota exhausted")
            return super().create(**kwargs)

    persisted = []
    try:
        score(opps, ApplicantProfile(), client=DiesOnSecondCall(), on_batch=persisted.extend)
    except RuntimeError:
        pass

    assert len(persisted) == SCORE_BATCH_SIZE  # first batch survived the crash
