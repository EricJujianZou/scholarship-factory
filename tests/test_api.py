import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from scholarship_factory.api import create_app
from scholarship_factory.extract import ExtractionResult, PageKind
from scholarship_factory.fetch import FetchResult
from scholarship_factory.models import Opportunity
from scholarship_factory.profile import ApplicantProfile, ProfileStore
from scholarship_factory.store import OpportunityStore


def _temp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def _seeded_db(profile_region: str = "Canada") -> str:
    path = _temp_db()
    store = OpportunityStore(path)
    store.insert(
        Opportunity(
            title="Eligible Future Grant",
            apply_url="https://example.com/eligible",
            source_url="https://example.com",
            deadline="September 15, 2099",
            reward="$5,000",
        )
    )
    store.insert(
        Opportunity(
            title="No Deadline Grant",
            apply_url="https://example.com/no-deadline",
            source_url="https://example.com",
        )
    )
    store.insert(
        Opportunity(
            title="Expired Grant",
            apply_url="https://example.com/expired",
            source_url="https://example.com",
            deadline="January 1, 2020",
        )
    )
    store.insert(
        Opportunity(
            title="EU Only Grant",
            apply_url="https://example.com/eu-only",
            source_url="https://example.com",
            requirements="Open to EU residents only.",
        )
    )
    ProfileStore(path).insert(ApplicantProfile(region=profile_region))
    return path


def test_opportunities_ranked_with_parsed_and_verbatim():
    path = _seeded_db()
    client = TestClient(create_app(path))

    res = client.get("/api/opportunities")
    assert res.status_code == 200
    data = res.json()

    eligible_titles = [item["opportunity"]["title"] for item in data["eligible"]]
    assert eligible_titles == ["Eligible Future Grant", "No Deadline Grant"]

    eligible_grant = data["eligible"][0]
    assert eligible_grant["opportunity"]["reward"] == "$5,000"
    assert eligible_grant["reward"]["amount"] == 5000.0

    excluded_by_title = {item["opportunity"]["title"]: item for item in data["excluded"]}
    assert excluded_by_title["Expired Grant"]["verdict"] == "expired"
    assert excluded_by_title["EU Only Grant"]["verdict"] == "ineligible"
    assert excluded_by_title["EU Only Grant"]["reasons"]


def _index_html() -> str:
    path = Path(__file__).parent.parent / "scholarship_factory" / "static" / "index.html"
    return path.read_text(encoding="utf-8")


def test_missing_deadline_serializes_null():
    path = _seeded_db()
    client = TestClient(create_app(path))

    data = client.get("/api/opportunities").json()
    no_deadline = next(
        item for item in data["eligible"]
        if item["opportunity"]["title"] == "No Deadline Grant"
    )
    assert no_deadline["deadline"] is None
    assert no_deadline["opportunity"]["deadline"] is None

    assert "no deadline found" in _index_html()


def test_profile_update_reranks():
    path = _seeded_db(profile_region="Canada")
    client = TestClient(create_app(path))

    before = client.get("/api/opportunities").json()
    before_excluded_titles = [item["opportunity"]["title"] for item in before["excluded"]]
    assert "EU Only Grant" in before_excluded_titles

    res = client.put(
        "/api/profile",
        json={
            "region": "Germany",
            "education_level": "undergraduate",
            "field_of_study": "computer science",
            "tags": ["first-gen"],
            "bio": "Studying CS.",
        },
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["region"] == "Germany"
    assert updated["education_level"] == "undergraduate"
    assert updated["field_of_study"] == "computer science"
    assert updated["tags"] == ["first-gen"]
    assert updated["bio"] == "Studying CS."

    after = client.get("/api/opportunities").json()
    after_eligible_titles = [item["opportunity"]["title"] for item in after["eligible"]]
    assert "EU Only Grant" in after_eligible_titles


def test_root_serves_dashboard():
    path = _seeded_db()
    client = TestClient(create_app(path))

    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "/api/opportunities" in res.text
    assert "/api/profile" in res.text


def test_markup_in_stored_fields_is_not_rendered_raw():
    path = _temp_db()
    store = OpportunityStore(path)
    store.insert(
        Opportunity(
            title='<img src=x onerror="alert(1)">',
            apply_url="javascript:alert(1)",
            source_url="https://example.com",
        )
    )
    ProfileStore(path).insert(ApplicantProfile(region="Canada"))
    client = TestClient(create_app(path))

    data = client.get("/api/opportunities").json()
    titles = [item["opportunity"]["title"] for item in data["eligible"] + data["excluded"]]
    assert '<img src=x onerror="alert(1)">' in titles

    html = _index_html()
    assert "function escapeHtml(" in html
    assert "${opp.title}" not in html
    assert "${opp.apply_url}" not in html
    assert "${escapeHtml(opp.title)}" in html
    assert "safeUrl(opp.apply_url)" in html
