import json
from pathlib import Path

from scholarship_factory import ExtractionResult, PageKind, extract
from scholarship_factory.clean import clean_html
from scholarship_factory.extract import LLMItem, _to_opportunity
from scholarship_factory.models import Provenance

FIXTURES = Path(__file__).parent / "fixtures"
RECORDED = FIXTURES / "recorded"


class _ToolUseBlock:
    type = "tool_use"

    def __init__(self, input: dict):
        self.input = input


class _Message:
    def __init__(self, input: dict):
        self.content = [_ToolUseBlock(input)]


class StubClient:
    def __init__(self, recorded_name: str):
        self._input = json.loads(
            (RECORDED / f"{recorded_name}.json").read_text(encoding="utf-8")
        )
        self.messages = self

    def create(self, **kwargs):
        return _Message(self._input)


def test_clean_html_preserves_inline_facts():
    raw = (FIXTURES / "uwaterloo_grants.html").read_text(encoding="utf-8")
    cleaned = clean_html(raw)
    assert "Up to $7,500" in cleaned
    assert "June 1st, and October 1st" in cleaned


def test_uwaterloo_grants_facts_are_quoted_and_verbatim():
    raw = (FIXTURES / "uwaterloo_grants.html").read_text(encoding="utf-8")
    url = "https://grants.uwaterloo.ca/"
    result = extract(raw, url, client=StubClient("uwaterloo_grants"))

    cleaned = clean_html(raw)
    lite_seed = next(o for o in result.opportunities if o.title == "LITE Seed Grant")

    assert lite_seed.reward_provenance == Provenance.QUOTED
    assert lite_seed.reward_source in cleaned
    assert lite_seed.deadline_provenance == Provenance.QUOTED
    assert lite_seed.deadline_source in cleaned
    assert "June 1st" in lite_seed.deadline
    assert "October 1st" in lite_seed.deadline


def test_oppsforyouth_listing_yields_thin_items_with_no_fabricated_deadlines():
    raw = (FIXTURES / "oppsforyouth_grants_listing.html").read_text(encoding="utf-8")
    url = "https://opportunitiesforyouth.org/?s=grants"
    result = extract(raw, url, client=StubClient("oppsforyouth_grants_listing"))

    assert result.kind == PageKind.LIST
    assert len(result.opportunities) == 5
    for opp in result.opportunities:
        assert opp.title
        assert opp.apply_url
        assert opp.deadline is None
        assert opp.deadline_provenance == Provenance.NONE


def test_oppsforyouth_detail_yields_one_record():
    raw = (FIXTURES / "oppsforyouth_detail.html").read_text(encoding="utf-8")
    url = (
        "https://opportunitiesforyouth.org/2026/06/27/"
        "we-empower-ii-grant-2026-up-to-e7500-funding-for-projects-advancing-"
        "migrant-womens-democratic-participation-across-the-european-union/"
    )
    result = extract(raw, url, client=StubClient("oppsforyouth_detail"))

    assert result.kind == PageKind.DETAIL
    assert len(result.opportunities) == 1
    opp = result.opportunities[0]
    assert "WE-EMPOWER II Grant" in opp.title
    assert opp.reward == "Up to €7,500"
    assert opp.reward_provenance == Provenance.QUOTED


def test_fact_with_source_not_on_page_is_nulled():
    item = LLMItem(
        title="Some Grant",
        deadline="2026-12-31",
        deadline_source="this text is not on the page",
    )
    opp = _to_opportunity(item, "https://example.com/grant", "the actual page text")

    assert opp.deadline is None
    assert opp.deadline_source is None
    assert opp.deadline_provenance == Provenance.NONE
