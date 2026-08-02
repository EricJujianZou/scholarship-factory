import os
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from scholarship_factory.api import create_app
from scholarship_factory.application import (
    ApplicationRequirements,
    EssayPrompt,
    RequirementsStore,
)
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


def _finished_job(client: TestClient, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get("/api/jobs/current").json()["job"]
        if job and job["state"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


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


def test_refresh_endpoint_updates_changed_field():
    path = _temp_db()
    store = OpportunityStore(path)
    opp = store.insert(
        Opportunity(
            title="Test Grant",
            apply_url="https://example.com/apply",
            source_url="https://example.com/apply",
            deadline="July 1, 2026",
        )
    )
    ProfileStore(path).insert(ApplicantProfile(region="Canada"))

    def stub_fetch(url: str) -> FetchResult:
        return FetchResult(requested_url=url, final_url=url, status_code=200, body="<html></html>")

    def stub_extract(body: str, url: str) -> ExtractionResult:
        return ExtractionResult(
            kind=PageKind.DETAIL,
            opportunities=[
                Opportunity(
                    title=opp.title,
                    apply_url=opp.apply_url,
                    source_url=opp.source_url,
                    deadline="August 1, 2026",
                )
            ],
        )

    client = TestClient(create_app(path, fetch_fn=stub_fetch, extract_fn=stub_extract))

    res = client.post(f"/api/opportunities/{opp.id}/refresh")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "changed"
    assert data["changed_fields"][0]["new_value"] == "August 1, 2026"


def test_refresh_endpoint_unknown_id_404():
    path = _seeded_db()
    client = TestClient(create_app(path))

    res = client.post("/api/opportunities/does-not-exist/refresh")
    assert res.status_code == 404


def test_dashboard_has_refresh_control():
    html = _index_html()
    assert "data-refresh-id" in html
    assert "/refresh" in html


def test_root_serves_dashboard():
    path = _seeded_db()
    client = TestClient(create_app(path))

    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "/api/opportunities" in res.text
    assert "/api/profile" in res.text


def test_actions_are_described_for_the_buttons():
    client = TestClient(create_app(_temp_db()))

    body = client.get("/api/actions").json()
    by_id = {a["id"]: a for a in body["actions"]}
    assert {"poll", "rank", "context"} <= set(by_id)
    assert by_id["poll"]["description"]
    assert by_id["poll"]["cost"]
    assert by_id["context"]["needs_llm"] is False


def test_actions_report_whether_a_provider_is_configured(monkeypatch):
    for name in ("SF_LLM_PROVIDER", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    client = TestClient(create_app(_temp_db()))

    llm = client.get("/api/actions").json()["llm"]
    assert llm["ready"] is False
    assert "GEMINI_API_KEY" in llm["hint"]

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    assert client.get("/api/actions").json()["llm"]["ready"] is True


def test_an_llm_action_is_refused_when_no_key_is_set(monkeypatch):
    """Refuse before the click rather than fail with a traceback after it."""
    for name in ("SF_LLM_PROVIDER", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    path = _seeded_db()
    client = TestClient(create_app(path))

    res = client.post("/api/actions/poll")
    assert res.status_code == 409
    assert "GEMINI_API_KEY" in res.json()["detail"]

    opp_id = OpportunityStore(path).list()[0].id
    assert client.post(f"/api/opportunities/{opp_id}/requirements").status_code == 409

    # The one action that spends nothing stays available.
    assert client.get("/api/jobs/current").json()["job"] is None


def test_unknown_action_is_404():
    client = TestClient(create_app(_temp_db()))
    assert client.post("/api/actions/rm-rf").status_code == 404


def test_running_an_action_reports_a_job(monkeypatch):
    """`rank` on an empty store returns without calling an LLM."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = TestClient(create_app(_temp_db()))

    res = client.post("/api/actions/rank")
    assert res.status_code == 200
    assert res.json()["state"] in {"running", "succeeded"}

    job = _finished_job(client)
    assert job["state"] == "succeeded"
    assert any("nothing stored yet" in line for line in job["lines"])


def test_no_job_running_reports_nothing():
    client = TestClient(create_app(_temp_db()))
    assert client.get("/api/jobs/current").json()["job"] is None


def test_requirements_for_an_unknown_opportunity_is_404():
    client = TestClient(create_app(_seeded_db()))
    assert client.post("/api/opportunities/nope/requirements").status_code == 404


def test_stored_requirements_ride_along_with_the_opportunity():
    """The row can show what an application asks for without a second request."""
    path = _seeded_db()
    opp = OpportunityStore(path).list()[0]
    RequirementsStore(path).set(
        opp.id,
        ApplicationRequirements(
            essay_prompts=[EssayPrompt(prompt="Why you?", word_limit=500)],
            documents=["Transcript"],
            referees=2,
        ),
    )

    data = TestClient(create_app(path)).get("/api/opportunities").json()
    item = next(
        i for i in data["eligible"] + data["excluded"]
        if i["opportunity"]["id"] == opp.id
    )
    assert item["requirements"]["essay_prompts"][0]["word_limit"] == 500
    assert item["requirements"]["referees"] == 2

    other = next(
        i for i in data["eligible"] + data["excluded"]
        if i["opportunity"]["id"] != opp.id
    )
    assert other["requirements"] is None


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


def test_decision_endpoint_records_and_annotates(tmp_path):
    from scholarship_factory.models import Opportunity
    from scholarship_factory.store import OpportunityStore

    db = str(tmp_path / "t.db")
    opp = OpportunityStore(db).insert(
        Opportunity(title="G", apply_url="https://e.com/a", source_url="https://e.com")
    )
    client = TestClient(create_app(db))

    posted = client.post(
        f"/api/opportunities/{opp.id}/decision",
        json={"verdict": "not_interested", "note": "wrong country"},
    )
    assert posted.status_code == 200
    assert posted.json()["verdict"] == "not_interested"

    listed = client.get("/api/opportunities").json()
    assert listed["eligible"][0]["decision"] == "not_interested"
    assert listed["eligible"][0]["fit"] is None  # sf rank has not run


def test_decision_on_unknown_opportunity_is_404(tmp_path):
    client = TestClient(create_app(str(tmp_path / "t.db")))
    res = client.post("/api/opportunities/nope/decision", json={"verdict": "interested"})
    assert res.status_code == 404


def test_stored_fit_is_surfaced_and_orders_the_list(tmp_path):
    from scholarship_factory.models import Opportunity
    from scholarship_factory.relevance import RelevanceStore, ScoredOpportunity
    from scholarship_factory.store import OpportunityStore

    db = str(tmp_path / "t.db")
    store = OpportunityStore(db)
    low = store.insert(
        Opportunity(title="Low", apply_url="https://e.com/l", source_url="https://e.com")
    )
    high = store.insert(
        Opportunity(title="High", apply_url="https://e.com/h", source_url="https://e.com")
    )
    RelevanceStore(db).replace(
        [
            ScoredOpportunity(opportunity=low, fit="low", reason="far away"),
            ScoredOpportunity(opportunity=high, fit="high", reason="right fit"),
        ]
    )

    listed = TestClient(create_app(db)).get("/api/opportunities").json()

    assert [e["opportunity"]["title"] for e in listed["eligible"]] == ["High", "Low"]
    assert listed["eligible"][0]["fit_reason"] == "right fit"
