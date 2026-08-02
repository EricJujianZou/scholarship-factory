"""One provider-agnostic structured LLM call, shared by every stage that needs one.

Anthropic gets a forced tool-use call; Gemini gets a JSON response schema. Both
return the same validated pydantic model, so callers never branch on provider.

Extracted from `extract.py` when the relevance ranker became a second caller --
provider selection is the kind of thing that must have exactly one definition.
"""
import os
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

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
    if provider is None:
        if client is not None or os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            provider = "gemini"
        else:
            raise RuntimeError(
                "cannot pick an LLM provider: set SF_LLM_PROVIDER to 'anthropic' or "
                "'gemini', or set ANTHROPIC_API_KEY, GEMINI_API_KEY, or GOOGLE_API_KEY."
            )
    if provider not in ("anthropic", "gemini"):
        raise ValueError(f"unknown LLM provider: {provider!r}")
    return provider


def provider_configured() -> bool:
    """Whether a provider can be picked from the environment as it stands.

    The dashboard asks before offering a button that would spend an LLM call:
    a missing key should read as "not set up yet", not as a traceback after
    the click.
    """
    try:
        resolve_provider(None, None)
    except RuntimeError:
        return False
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
