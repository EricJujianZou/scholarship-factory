import json
from pathlib import Path

import pytest

from scholarship_factory import PageKind, extract
from scholarship_factory.clean import clean_html
from scholarship_factory.extract import _resolve_provider
from scholarship_factory.models import Provenance

FIXTURES = Path(__file__).parent / "fixtures"
RECORDED = FIXTURES / "recorded"

_PROVIDER_ENV_VARS = (
    "SF_LLM_PROVIDER",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)


class _Response:
    def __init__(self, text: str):
        self.parsed = None
        self.text = text


class GeminiStubClient:
    def __init__(self, recorded_name: str):
        self._text = (RECORDED / f"{recorded_name}.json").read_text(encoding="utf-8")
        self.models = self

    def generate_content(self, **kwargs):
        return _Response(self._text)


class AnthropicStubClient:
    def __init__(self):
        self.messages = self
        self.called = False

    def create(self, **kwargs):
        self.called = True
        raise AssertionError("anthropic path should not be reached")


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch):
    for var in _PROVIDER_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_uwaterloo_grants_facts_are_quoted_and_verbatim_via_gemini():
    raw = (FIXTURES / "uwaterloo_grants.html").read_text(encoding="utf-8")
    url = "https://grants.uwaterloo.ca/"
    result = extract(
        raw, url, client=GeminiStubClient("uwaterloo_grants"), provider="gemini"
    )

    cleaned = clean_html(raw)
    lite_seed = next(o for o in result.opportunities if o.title == "LITE Seed Grant")

    assert lite_seed.reward_provenance == Provenance.QUOTED
    assert lite_seed.reward_source in cleaned
    assert lite_seed.deadline_provenance == Provenance.QUOTED
    assert lite_seed.deadline_source in cleaned
    assert "June 1st" in lite_seed.deadline
    assert "October 1st" in lite_seed.deadline


def test_oppsforyouth_listing_yields_thin_items_via_gemini():
    raw = (FIXTURES / "oppsforyouth_grants_listing.html").read_text(encoding="utf-8")
    url = "https://opportunitiesforyouth.org/?s=grants"
    result = extract(
        raw,
        url,
        client=GeminiStubClient("oppsforyouth_grants_listing"),
        provider="gemini",
    )

    assert result.kind == PageKind.LIST
    assert len(result.opportunities) == 5
    for opp in result.opportunities:
        assert opp.title
        assert opp.apply_url
        assert opp.deadline is None
        assert opp.deadline_provenance == Provenance.NONE


def test_gemini_parsed_result_is_used_when_present():
    raw = (FIXTURES / "uwaterloo_grants.html").read_text(encoding="utf-8")
    url = "https://grants.uwaterloo.ca/"

    from scholarship_factory.extract import LLMResult

    class ParsedStub(GeminiStubClient):
        def generate_content(self, **kwargs):
            response = _Response("not json")
            response.parsed = LLMResult.model_validate(json.loads(self._text))
            return response

    result = extract(raw, url, client=ParsedStub("uwaterloo_grants"), provider="gemini")
    assert any(o.title == "LITE Seed Grant" for o in result.opportunities)


def test_sf_llm_provider_env_wins(monkeypatch):
    monkeypatch.setenv("SF_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    raw = (FIXTURES / "uwaterloo_grants.html").read_text(encoding="utf-8")
    result = extract(
        raw, "https://grants.uwaterloo.ca/", client=GeminiStubClient("uwaterloo_grants")
    )
    assert result.opportunities


def test_injected_client_defaults_to_anthropic():
    assert _resolve_provider(None, AnthropicStubClient()) == "anthropic"


def test_gemini_key_only_resolves_to_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "key")
    assert _resolve_provider(None, None) == "gemini"


def test_no_keys_raises_runtime_error():
    with pytest.raises(RuntimeError, match="SF_LLM_PROVIDER"):
        extract("<html></html>", "https://example.com/")


def test_bad_provider_raises_value_error():
    with pytest.raises(ValueError, match="unknown LLM provider"):
        extract(
            "<html></html>",
            "https://example.com/",
            client=GeminiStubClient("uwaterloo_grants"),
            provider="openai",
        )
