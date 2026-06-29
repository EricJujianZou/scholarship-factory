from pathlib import Path

from scholarship_factory import extract_jsonld
from scholarship_factory.models import Provenance

FIXTURES = Path(__file__).parent / "fixtures"


def test_lablab_event_yields_one_record_with_quoted_cost_and_no_deadline_or_reward():
    raw = (FIXTURES / "lablab_executorch.html").read_text(encoding="utf-8")
    url = "https://lablab.ai/ai-hackathons/qualcomm-x-meta-executorch-hackathon"
    opportunities = extract_jsonld(raw, url)

    assert len(opportunities) == 1
    opp = opportunities[0]
    assert opp.title == "ExecuTorch Hackathon"

    assert opp.cost_provenance == Provenance.QUOTED
    assert opp.cost_source is not None
    assert "0" in opp.cost_source

    assert opp.deadline is None
    assert opp.deadline_provenance == Provenance.NONE
    assert opp.deadline_source is None

    assert opp.reward is None
    assert opp.reward_provenance == Provenance.NONE
    assert opp.reward_source is None


def test_oppsforyouth_grants_listing_chrome_only_yields_zero():
    raw = (FIXTURES / "oppsforyouth_grants_listing.html").read_text(encoding="utf-8")
    url = "https://opportunitiesforyouth.org/?s=grants"

    assert extract_jsonld(raw, url) == []


def test_oppsforyouth_detail_chrome_only_yields_zero():
    raw = (FIXTURES / "oppsforyouth_detail.html").read_text(encoding="utf-8")
    url = (
        "https://opportunitiesforyouth.org/2026/06/27/"
        "we-empower-ii-grant-2026-up-to-e7500-funding-for-projects-advancing-"
        "migrant-womens-democratic-participation-across-the-european-union/"
    )

    assert extract_jsonld(raw, url) == []
