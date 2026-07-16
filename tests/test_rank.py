from datetime import date

from scholarship_factory.models import Opportunity
from scholarship_factory.profile import ApplicantProfile
from scholarship_factory.rank import Verdict, rank

TODAY = date(2026, 7, 15)


def _opp(**kwargs) -> Opportunity:
    defaults = dict(
        title="t",
        apply_url="https://example.com",
        source_url="https://example.com",
        source_observed_date="2026-01-01",
    )
    defaults.update(kwargs)
    return Opportunity(**defaults)


def test_region_mismatch_is_ineligible_with_reason():
    profile = ApplicantProfile(region="Canada")
    opp = _opp(requirements="Open to EU residents only")

    results = rank([opp], profile, today=TODAY)

    assert results.eligible == []
    assert len(results.excluded) == 1
    ranked = results.excluded[0]
    assert ranked.verdict == Verdict.INELIGIBLE
    assert "EU residents" in ranked.reasons[0]
    assert "Canada" in ranked.reasons[0]


def test_missing_fields_eligible_and_sorts_last():
    profile = ApplicantProfile(region="Canada")
    dated = _opp(title="dated", deadline="September 15, 2026")
    undated = _opp(title="undated")

    results = rank([dated, undated], profile, today=TODAY)

    titles = [r.opportunity.title for r in results.eligible]
    assert titles == ["dated", "undated"]
    undated_ranked = results.eligible[-1]
    assert undated_ranked.verdict == Verdict.ELIGIBLE
    assert undated_ranked.deadline is None


def test_past_deadline_is_expired_and_excluded():
    profile = ApplicantProfile()
    opp = _opp(deadline="June 1, 2026")

    results = rank([opp], profile, today=TODAY)

    assert results.eligible == []
    assert len(results.excluded) == 1
    ranked = results.excluded[0]
    assert ranked.verdict == Verdict.EXPIRED
    assert "2026-06-01" in ranked.reasons[0]


def test_sort_deadline_then_reward():
    soonest = _opp(title="soonest", deadline="August 1, 2026", reward="$1,000")
    tied_low = _opp(title="tied_low", deadline="October 1, 2026", reward="$1,000")
    tied_high = _opp(title="tied_high", deadline="October 1, 2026", reward="$5,000")

    results = rank([tied_low, soonest, tied_high], ApplicantProfile(), today=TODAY)

    titles = [r.opportunity.title for r in results.eligible]
    assert titles == ["soonest", "tied_high", "tied_low"]


def test_null_profile_excludes_nothing():
    profile = ApplicantProfile()
    opp = _opp(requirements="Open to EU residents only")

    results = rank([opp], profile, today=TODAY)

    assert all(r.verdict != Verdict.INELIGIBLE for r in results.eligible + results.excluded)


def test_unrecognized_region_never_excludes():
    profile = ApplicantProfile(region="Mars")
    opp = _opp(requirements="Open to EU residents only")

    results = rank([opp], profile, today=TODAY)

    assert results.excluded == []
    assert results.eligible[0].verdict == Verdict.ELIGIBLE
