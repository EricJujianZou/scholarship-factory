from scholarship_factory.models import Opportunity, Provenance
from scholarship_factory.parse_money import (
    MoneyBound,
    parse_money,
    typed_cost,
    typed_reward,
)


def test_upper_bound_with_currency():
    v = parse_money("Up to EUR 7,500")
    assert v is not None
    assert v.amount == 7500
    assert v.currency == "EUR"
    assert v.bound == MoneyBound.UPPER


def test_free_and_zero_are_zero():
    free = parse_money("Free")
    assert free is not None and free.amount == 0 and free.bound == MoneyBound.EXACT

    zero = parse_money("$0")
    assert zero is not None and zero.amount == 0 and zero.currency == "USD"


def test_period_arithmetic_total():
    v = parse_money("$5,000/yr for 4 years")
    assert v is not None
    assert v.amount == 20000
    assert v.per_period == 5000
    assert v.periods == 4
    assert v.currency == "USD"


def test_lower_bound():
    v = parse_money("from $1,000")
    assert v is not None and v.amount == 1000 and v.bound == MoneyBound.LOWER


def test_unparseable_or_absent_returns_none():
    assert parse_money("no numbers here at all") is None
    assert parse_money(None) is None
    assert parse_money("") is None


def test_typed_helpers_provenance():
    opp = Opportunity(
        title="t",
        apply_url="https://example.com",
        source_url="https://example.com",
        reward="Up to EUR 7,500",
        cost="Free",
    )
    reward, reward_prov = typed_reward(opp)
    cost, cost_prov = typed_cost(opp)

    assert reward is not None and reward.amount == 7500
    assert reward_prov == Provenance.DERIVED
    assert cost is not None and cost.amount == 0
    assert cost_prov == Provenance.DERIVED


def test_typed_none_when_absent():
    opp = Opportunity(
        title="t",
        apply_url="https://example.com",
        source_url="https://example.com",
    )
    value, prov = typed_reward(opp)
    assert value is None
    assert prov == Provenance.NONE
