import pytest
from pydantic import BaseModel

import scholarship_factory.llm as llm
from scholarship_factory.llm import (
    _call_claude_cli,
    _strip_fences,
    provider_configured,
    resolve_provider,
)


class Toy(BaseModel):
    answer: str


def test_strip_fences_handles_fenced_and_bare():
    assert _strip_fences('{"a": 1}') == '{"a": 1}'
    assert _strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _strip_fences('```\n{"a": 1}\n```') == '{"a": 1}'


def test_call_claude_cli_validates_result(monkeypatch):
    seen = {}

    def fake_run(prompt, model):
        seen["prompt"] = prompt
        return '```json\n{"answer": "yes"}\n```'

    monkeypatch.setattr(llm, "_run_claude_cli", fake_run)

    result = _call_claude_cli("system text", "user text", Toy, None)

    assert result == Toy(answer="yes")
    assert "system text" in seen["prompt"]
    assert "user text" in seen["prompt"]
    assert "JSON schema" in seen["prompt"]


def test_resolve_provider_accepts_claude_cli(monkeypatch):
    monkeypatch.setenv("SF_LLM_PROVIDER", "claude-cli")
    assert resolve_provider(None, None) == "claude-cli"


def test_provider_configured_needs_the_cli_on_path(monkeypatch):
    monkeypatch.setenv("SF_LLM_PROVIDER", "claude-cli")
    monkeypatch.setattr(llm.shutil, "which", lambda _: None)
    assert provider_configured() is False
    monkeypatch.setattr(llm.shutil, "which", lambda _: r"C:\bin\claude.exe")
    assert provider_configured() is True


def test_unknown_provider_rejected():
    with pytest.raises(ValueError):
        resolve_provider("openai", None)


def test_env_claude_cli_yields_to_an_explicit_client(monkeypatch):
    """A stub/injected client must never be bypassed into a real CLI call."""
    monkeypatch.setenv("SF_LLM_PROVIDER", "claude-cli")
    assert resolve_provider(None, object()) == "anthropic"
    assert resolve_provider(None, None) == "claude-cli"
