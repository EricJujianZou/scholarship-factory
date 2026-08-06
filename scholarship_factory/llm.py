"""One provider-agnostic structured LLM call, shared by every stage that needs one.

Anthropic gets a forced tool-use call; Gemini gets a JSON response schema; the
claude-cli provider shells out to `claude -p` headlessly, spending the owner's
Claude subscription instead of a metered key (the parking-lot decision, resolved
2026-08-05). All return the same validated pydantic model, so callers never
branch on provider.

claude-cli caveats, learned in content-machine: the prompt goes in on STDIN,
never as an argv element -- on Windows `claude -p` truncates an argument at the
first newline. Calls are slower than an API call (a fresh session each time)
and draw from the same subscription usage window as interactive Claude Code.

Extracted from `extract.py` when the relevance ranker became a second caller --
provider selection is the kind of thing that must have exactly one definition.
"""
import json
import os
import shutil
import subprocess
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
CLAUDE_CLI_TIMEOUT = 600.0

T = TypeVar("T", bound=BaseModel)


class _MessagesClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class AnthropicClient(Protocol):
    messages: _MessagesClient


def _default_anthropic_client() -> AnthropicClient:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "the anthropic provider requires the 'anthropic' package; install the "
            "'llm' extra or pass an explicit client."
        ) from exc
    return anthropic.Anthropic()


def _default_gemini_client() -> Any:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "the gemini provider requires the 'google-genai' package; install the "
            "'gemini' extra or pass an explicit client."
        ) from exc
    return genai.Client()


def resolve_provider(provider: str | None, client: Any | None) -> str:
    if provider is None:
        provider = os.environ.get("SF_LLM_PROVIDER")
        # claude-cli cannot speak through an injected client, so an explicit
        # client falls back to the client path rather than shelling out --
        # without this, stub-client tests spend real subscription calls the
        # moment the owner's .env sets SF_LLM_PROVIDER=claude-cli.
        if provider == "claude-cli" and client is not None:
            provider = "anthropic"
    if provider is None:
        if client is not None or os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            provider = "gemini"
        else:
            raise RuntimeError(
                "cannot pick an LLM provider: set SF_LLM_PROVIDER to 'anthropic', "
                "'gemini' or 'claude-cli', or set ANTHROPIC_API_KEY, GEMINI_API_KEY, "
                "or GOOGLE_API_KEY."
            )
    if provider not in ("anthropic", "gemini", "claude-cli"):
        raise ValueError(f"unknown LLM provider: {provider!r}")
    return provider


def provider_configured() -> bool:
    """Whether a provider can be picked from the environment as it stands.

    The dashboard asks before offering a button that would spend an LLM call:
    a missing key should read as "not set up yet", not as a traceback after
    the click.
    """
    try:
        provider = resolve_provider(None, None)
    except RuntimeError:
        return False
    if provider == "claude-cli":
        return shutil.which("claude") is not None
    return True


def structured_call(
    system: str,
    user: str,
    schema: type[T],
    *,
    client: Any | None = None,
    model: str | None = None,
    provider: str | None = None,
    tool_name: str = "report",
    max_tokens: int = 4096,
) -> T:
    provider = resolve_provider(provider, client)
    if provider == "gemini":
        return _call_gemini(system, user, schema, client, model)
    if provider == "claude-cli":
        return _call_claude_cli(system, user, schema, model)
    return _call_anthropic(system, user, schema, client, model, tool_name, max_tokens)


def _call_anthropic(
    system: str,
    user: str,
    schema: type[T],
    client: AnthropicClient | None,
    model: str | None,
    tool_name: str,
    max_tokens: int,
) -> T:
    if client is None:
        client = _default_anthropic_client()

    message = client.messages.create(
        model=model or DEFAULT_ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        tools=[
            {
                "name": tool_name,
                "description": schema.__doc__ or "Report the structured result.",
                "input_schema": schema.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": user}],
    )

    tool_use = next(block for block in message.content if block.type == "tool_use")
    return schema.model_validate(tool_use.input)


def _run_claude_cli(prompt: str, model: str | None) -> str:
    """One headless `claude -p` invocation; returns the raw result text.

    Separate from the parsing so tests can stub the subprocess boundary. The
    .cmd shim from an npm install cannot be exec'd directly on Windows, hence
    the cmd.exe wrapper.
    """
    exe = shutil.which("claude")
    if exe is None:
        raise RuntimeError(
            "the claude-cli provider needs the `claude` CLI on PATH "
            "(it spends the owner's Claude subscription)."
        )
    cmd = [exe, "-p", "--output-format", "json"]
    if model:
        cmd += ["--model", model]
    if exe.lower().endswith((".cmd", ".bat")):
        cmd = ["cmd", "/c", *cmd]

    completed = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=CLAUDE_CLI_TIMEOUT,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"claude -p failed (exit {completed.returncode}): "
            f"{(completed.stderr or completed.stdout or '').strip()[:500]}"
        )
    envelope = json.loads(completed.stdout)
    result = envelope.get("result")
    if not isinstance(result, str):
        raise RuntimeError(f"claude -p returned no result text: {completed.stdout[:200]}")
    return result


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _call_claude_cli(
    system: str, user: str, schema: type[T], model: str | None
) -> T:
    prompt = (
        f"{system}\n\n{user}\n\n"
        "Respond with ONLY a JSON object that validates against this JSON schema. "
        "No prose, no code fences, no explanation:\n"
        f"{json.dumps(schema.model_json_schema())}"
    )
    result = _run_claude_cli(prompt, model)
    return schema.model_validate_json(_strip_fences(result))


def _call_gemini(
    system: str,
    user: str,
    schema: type[T],
    client: Any | None,
    model: str | None,
) -> T:
    if client is None:
        client = _default_gemini_client()

    config: Any = {
        "system_instruction": system,
        "response_mime_type": "application/json",
        "response_schema": schema,
    }
    try:
        from google.genai import types
    except ImportError:
        pass
    else:
        config = types.GenerateContentConfig(**config)

    response = client.models.generate_content(
        model=model or DEFAULT_GEMINI_MODEL,
        contents=user,
        config=config,
    )

    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, schema):
        return parsed
    return schema.model_validate_json(response.text)
