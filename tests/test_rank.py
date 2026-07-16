from datetime import date

import pytest

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


def test_benign_us_prose_does_not_exclude():
    profile = ApplicantProfile(region="Canada")
    opp = _opp(
        description="For students using renewable energy research, usually joining us in the lab"
    )

    results = rank([opp], profile, today=TODAY)

    assert results.excluded == []
    assert results.eligible[0].verdict == Verdict.ELIGIBLE


@pytest.mark.parametrize(
    "requirements,profile_region,expected_label",
    [
        ("Open to EU residents only", "Canada", "EU residents"),
        ("US citizens only", "Canada", "US residents"),
        ("Canada only", "Germany", "Canadian residents"),
        ("Open to UK residents", "Canada", "UK residents"),
    ],
)
def test_region_rule_fires_on_explicit_constraint(requirements, profile_region, expected_label):
    profile = ApplicantProfile(region=profile_region)
    opp = _opp(requirements=requirements)

    results = rank([opp], profile, today=TODAY)

    assert results.eligible == []
    assert len(results.excluded) == 1
    ranked = results.excluded[0]
    assert ranked.verdict == Verdict.INELIGIBLE
    assert expected_label in ranked.reasons[0]
    assert profile_region in ranked.reasons[0]


@pytest.mark.parametrize(
    "description,profile_region",
    [
        ("a European Union grant program", "Canada"),
        ("we ship to United States addresses", "Canada"),
        ("the Canadian Space Agency sponsors this", "Germany"),
        ("UK based mentors will advise", "Canada"),
    ],
)
def test_region_rule_does_not_fire_on_benign_text(description, profile_region):
    profile = ApplicantProfile(region=profile_region)
    opp = _opp(description=description)

    results = rank([opp], profile, today=TODAY)

    assert results.excluded == []
    assert results.eligible[0].verdict == Verdict.ELIGIBLE


@pytest.mark.parametrize(
    "requirements,profile_education,expected_label",
    [
        ("High school students only", "undergraduate", "high school students only"),
        ("Undergraduates only", "phd", "undergraduate students only"),
        ("Graduate students only", "high school", "graduate students only"),
    ],
)
def test_education_rule_fires_on_explicit_constraint(requirements, profile_education, expected_label):
    profile = ApplicantProfile(education_level=profile_education)
    opp = _opp(requirements=requirements)

    results = rank([opp], profile, today=TODAY)

    assert results.eligible == []
    assert len(results.excluded) == 1
    ranked = results.excluded[0]
    assert ranked.verdict == Verdict.INELIGIBLE
    assert expected_label in ranked.reasons[0]
    assert profile_education in ranked.reasons[0]


@pytest.mark.parametrize(
    "description",
    [
        "open to high school students and undergraduates",
        "undergraduate research experience preferred",
        "graduate students are encouraged to apply",
    ],
)
def test_education_rule_does_not_fire_on_benign_text(description):
    profile = ApplicantProfile(education_level="undergraduate")
    opp = _opp(description=description)

    results = rank([opp], profile, today=TODAY)

    assert results.excluded == []
    assert results.eligible[0].verdict == Verdict.ELIGIBLE
