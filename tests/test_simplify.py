import json

import pytest

from scholarship_factory import Provenance, parse_simplify

SOURCE_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json"


def listing(**overrides):
    base = {
        "source": "Simplify",
        "category": "Software",
        "company_name": "Example Corp",
        "id": "abc123",
        "title": "Software Engineering Intern",
        "active": True,
        "terms": ["Summer 2026"],
        "date_updated": 1765241556,
        "date_posted": 1765236742,
        "url": "https://example.com/jobs/1",
        "locations": ["Toronto, ON"],
        "company_url": "https://simplify.jobs/c/Example-Corp",
        "is_visible": True,
        "sponsorship": "Other",
        "degrees": [],
    }
    base.update(overrides)
    return base


def parse(*listings):
    return parse_simplify(json.dumps(list(listings)), SOURCE_URL)


def test_maps_facts_and_fabricates_nothing():
    [opp] = parse(listing())

    assert opp.title == "Software Engineering Intern"
    assert opp.apply_url == "https://example.com/jobs/1"
    assert opp.source_url == SOURCE_URL
    assert opp.organization == "Example Corp"
    assert opp.type == "internship"
    assert "Software internship" in opp.description
    assert "Summer 2026" in opp.description
    assert "Toronto, ON" in opp.description
    # Simplify publishes no deadline, reward or cost — none may be invented
    assert opp.deadline is None
    assert opp.deadline_provenance is Provenance.NONE
    assert opp.reward is None
    assert opp.cost is None


def test_inactive_and_hidden_rows_are_dropped():
    assert parse(listing(active=False), listing(is_visible=False)) == []


def test_rows_missing_url_or_title_are_dropped():
    assert parse(listing(url=None), listing(title="")) == []


def test_informative_sponsorship_lands_in_requirements():
    [opp] = parse(listing(sponsorship="Does Not Offer Sponsorship"))
    assert opp.requirements == "Sponsorship: Does Not Offer Sponsorship"


def test_other_sponsorship_and_empty_degrees_leave_requirements_empty():
    [opp] = parse(listing(sponsorship="Other", degrees=[]))
    assert opp.requirements is None


def test_na_terms_are_not_described():
    [opp] = parse(listing(terms=["N/A"]))
    assert "N/A" not in (opp.description or "")


def test_observed_date_prefers_date_updated():
    [opp] = parse(listing(date_updated=1765241556))
    assert opp.source_observed_date == "2025-12-09"


def test_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_simplify("not json", SOURCE_URL)
