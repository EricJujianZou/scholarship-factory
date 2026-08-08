import json

import pytest

from scholarship_factory import Provenance, parse_zshah

SOURCE_URL = (
    "https://raw.githubusercontent.com/zshah101/"
    "Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/main/docs/api/jobs.json"
)


def job(**overrides):
    # Real item from the live docs/api/jobs.json (2026-08-08).
    base = {
        "id": "workday:gdit:/job/USA-VA-Falls-Church/RQ225912",
        "company": "General Dynamics Information Technology",
        "title": "Summer 2027 AI/Machine Learning Internship -DC Metro Area",
        "season": "Summer 2027",
        "seasons": None,
        "season_inferred": False,
        "category": "Data & ML/AI",
        "location": "USA VA Falls Church",
        "url": "https://gdit.wd5.myworkdayjobs.com/external_career_site/job/RQ225912",
        "posted_at": "2026-08-07T00:00:00Z",
        "posted_at_source": "date_only",
        "first_seen_at": "2026-08-07T20:39:05Z",
        "sponsorship": "citizens-only",
        "salary": None,
        "skills": ["Python"],
        "source": "workday",
        "h1b_approvals": 28,
        "program": "Internship",
        "remote": False,
    }
    base.update(overrides)
    return base


def parse(*jobs):
    return parse_zshah(json.dumps({"count": len(jobs), "jobs": list(jobs)}), SOURCE_URL)


def test_maps_facts_and_fabricates_nothing():
    [opp] = parse(job())

    assert opp.title == "Summer 2027 AI/Machine Learning Internship -DC Metro Area"
    assert opp.apply_url == (
        "https://gdit.wd5.myworkdayjobs.com/external_career_site/job/RQ225912"
    )
    assert opp.source_url == SOURCE_URL
    assert opp.organization == "General Dynamics Information Technology"
    assert opp.type == "internship"
    assert opp.description == (
        "Data & ML/AI internship. Term: Summer 2027. Location: USA VA Falls Church"
    )
    assert opp.requirements == (
        "Sponsorship: U.S. Citizenship is Required. Skills: Python"
    )
    assert opp.source_observed_date == "2026-08-07"
    # the board publishes no deadline or cost — none may be invented
    assert opp.deadline is None
    assert opp.deadline_provenance is Provenance.NONE
    assert opp.cost is None


def test_stated_salary_is_quoted_with_its_span():
    [opp] = parse(job(salary="$55 - $65 per hour"))

    assert opp.reward == "$55 - $65 per hour"
    assert opp.reward_provenance is Provenance.QUOTED
    assert json.loads(opp.reward_source) == {"salary": "$55 - $65 per hour"}


def test_absent_salary_stays_absent():
    [opp] = parse(job(salary=None))
    assert opp.reward is None
    assert opp.reward_provenance is Provenance.NONE
    assert opp.reward_source is None


def test_blank_salary_is_not_a_fact():
    [opp] = parse(job(salary="   "))
    assert opp.reward is None
    assert opp.reward_provenance is Provenance.NONE


def test_rows_missing_url_or_title_are_dropped():
    assert parse(job(url=None), job(title="")) == []


def test_unknown_sponsorship_leaves_it_out():
    [opp] = parse(job(sponsorship="unknown", skills=[]))
    assert opp.requirements is None


def test_not_stated_season_is_not_written_as_a_term():
    [opp] = parse(job(season="Not stated"))
    assert "Term:" not in opp.description


def test_multi_season_rows_use_the_seasons_list():
    [opp] = parse(job(season="Summer 2027", seasons=["Summer 2027", "Fall 2026"]))
    assert "Term: Summer 2027, Fall 2026" in opp.description


def test_remote_is_noted_only_when_true():
    [remote] = parse(job(remote=True))
    [onsite] = parse(job(remote=False))
    assert remote.description.endswith("Remote")
    assert "Remote" not in onsite.description


def test_observed_date_falls_back_to_first_seen():
    [opp] = parse(job(posted_at=None))
    assert opp.source_observed_date == "2026-08-07"


def test_unparseable_timestamp_leaves_the_date_absent():
    [opp] = parse(job(posted_at="a while ago", first_seen_at=None))
    assert opp.source_observed_date is None


def test_bare_list_payload_is_accepted():
    [opp] = parse_zshah(json.dumps([job()]), SOURCE_URL)
    assert opp.title.startswith("Summer 2027")


def test_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_zshah("not json", SOURCE_URL)
