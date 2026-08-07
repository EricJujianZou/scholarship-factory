import json

import pytest

from scholarship_factory import Provenance, parse_vansh

SOURCE_URL = "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/dev/.github/scripts/listings.json"


def listing(**overrides):
    # Real item from the live listings.json (2026-08-07), trimmed only in id.
    base = {
        "date_updated": 1749260792,
        "url": "https://ats.rippling.com/en-GB/rippling/jobs/3fd9615a-d0c7-458c-a0fc-5d9d7f0ce77c",
        "locations": ["New York, NY", "San Francisco, CA"],
        "sponsorship": "Other",
        "active": True,
        "company_name": "Rippling",
        "title": "Frontend Software Engineer Intern",
        "season": "Winter",
        "source": "vanshb03",
        "id": "df70fa57",
        "date_posted": 1749260792,
        "company_url": "",
        "is_visible": True,
    }
    base.update(overrides)
    return base


def parse(*listings):
    return parse_vansh(json.dumps(list(listings)), SOURCE_URL)


def test_maps_facts_and_fabricates_nothing():
    [opp] = parse(listing())

    assert opp.title == "Frontend Software Engineer Intern"
    assert opp.apply_url == (
        "https://ats.rippling.com/en-GB/rippling/jobs/"
        "3fd9615a-d0c7-458c-a0fc-5d9d7f0ce77c"
    )
    assert opp.source_url == SOURCE_URL
    assert opp.organization == "Rippling"
    assert opp.type == "internship"
    assert opp.description == "Term: Winter. Location: New York, NY, San Francisco, CA"
    # the board publishes no deadline, reward or cost — none may be invented
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


def test_other_sponsorship_leaves_requirements_empty():
    [opp] = parse(listing(sponsorship="Other"))
    assert opp.requirements is None


def test_missing_season_and_locations_leave_description_empty():
    [opp] = parse(listing(season="", locations=[]))
    assert opp.description is None


def test_observed_date_prefers_date_updated():
    [opp] = parse(listing(date_updated=1765241556))
    assert opp.source_observed_date == "2025-12-09"


def test_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_vansh("not json", SOURCE_URL)
