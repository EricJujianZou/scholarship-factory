from datetime import date

from scholarship_factory.models import Opportunity, Provenance
from scholarship_factory.parse_dates import parse_deadline_dates, typed_deadlines


def test_multi_deadline_not_collapsed():
    result = parse_deadline_dates("June 1st, and October 1st", date(2024, 1, 1))
    assert result == [date(2024, 6, 1), date(2024, 10, 1)]


def test_relative_expression_resolves_against_anchor_not_today():
    early_anchor = parse_deadline_dates("closes Friday", date(2024, 1, 1))
    later_anchor = parse_deadline_dates("closes Friday", date(2024, 6, 1))

    assert early_anchor == [date(2024, 1, 5)]
    assert later_anchor == [date(2024, 6, 7)]
    assert early_anchor != later_anchor


def test_absolute_date_string():
    result = parse_deadline_dates("September 15, 2024", date(2024, 1, 1))
    assert result == [date(2024, 9, 15)]


def test_unparseable_or_absent_returns_none():
    assert parse_deadline_dates("asdkjaslkdj not a date at all zzz", date(2024, 1, 1)) is None
    assert parse_deadline_dates(None, date(2024, 1, 1)) is None
    assert parse_deadline_dates("", date(2024, 1, 1)) is None


def test_typed_deadlines_derived_provenance():
    opp = Opportunity(
        title="t",
        apply_url="https://example.com",
        source_url="https://example.com",
        deadline="closes Friday",
        source_observed_date="2024-01-01",
    )
    dates, provenance = typed_deadlines(opp)

    assert dates == [date(2024, 1, 5)]
    assert provenance == Provenance.DERIVED


def test_typed_deadlines_none_provenance_when_unresolvable():
    opp = Opportunity(
        title="t",
        apply_url="https://example.com",
        source_url="https://example.com",
        deadline="gibberish zzz",
        first_seen="2024-01-01T00:00:00+00:00",
    )
    dates, provenance = typed_deadlines(opp)

    assert dates is None
    assert provenance == Provenance.NONE


def test_typed_deadlines_none_provenance_when_deadline_absent():
    opp = Opportunity(
        title="t",
        apply_url="https://example.com",
        source_url="https://example.com",
        deadline=None,
        source_observed_date="2024-01-01",
    )
    dates, provenance = typed_deadlines(opp)

    assert dates is None
    assert provenance == Provenance.NONE
