import os
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel

from .clean import clean_html
from .models import Opportunity, Provenance

DEFAULT_MODEL = "claude-sonnet-5"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
_TOOL_NAME = "report_opportunities"

_SYSTEM_PROMPT = """You extract funding/scholarship opportunities from a cleaned web page.

Rules (follow exactly):
- Whole-record honesty: never invent an opportunity that is not on the page; never \
merge two distinct opportunities into one record.
- Quoted-only provenance: every fact you report (deadline, reward, cost) must be \
copied verbatim from the page as `*_source`. Do not paraphrase or compute values \
(no "derived" facts here). If a fact is not stated on the page, leave its value and \
source null.
- Source spans must be exact, literal substrings of the page text you were given.
- Emit `source_observed_date` only when the page itself states an observation/posted \
date.
- Classify the page as a `detail` (one record worth of facts) or a `list` (a listing \
of multiple thin items, typically title + url only)."""


class PageKind(str, Enum):
    DETAIL = "detail"
    LIST = "list"


class ExtractionResult(BaseModel):
    kind: PageKind
    opportunities: list[Opportunity]


class LLMItem(BaseModel):
    title: str
    apply_url: str | None = None
    deadline: str | None = None
    deadline_source: str | None = None
    reward: str | None = None
    reward_source: str | None = None
    cost: str | None = None
    cost_source: str | None = None
    source_observed_date: str | None = None
    organization: str | None = None
    requirements: str | None = None
    type: str | None = None
    description: str | None = None


class LLMResult(BaseModel):
    kind: PageKind
    items: list[LLMItem]


CONTRACT_TOOL = {
    "name": _TOOL_NAME,
    "description": "Report the opportunities found on the page, or none.",
    "input_schema": LLMResult.model_json_schema(),
}


class _MessagesClient(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class _AnthropicClient(Protocol):
    messages: _MessagesClient


def _default_client() -> _AnthropicClient:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "extract() requires the 'anthropic' package; install the 'llm' extra "
            "or pass an explicit client."
        ) from exc
    return anthropic.Anthropic()


def _default_gemini_client() -> Any:
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "extract() with provider='gemini' requires the 'google-genai' package; "
            "install the 'gemini' extra or pass an explicit client."
        ) from exc
    return genai.Client()


def _resolve_provider(provider: str | None, client: Any | None) -> str:
    if provider is None:
        provider = os.environ.get("SF_LLM_PROVIDER")
    if provider is None:
        if client is not None or os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            provider = "gemini"
        else:
            raise RuntimeError(
                "extract() cannot pick an LLM provider: set SF_LLM_PROVIDER to "
                "'anthropic' or 'gemini', or set ANTHROPIC_API_KEY, GEMINI_API_KEY, "
                "or GOOGLE_API_KEY."
            )
    if provider not in ("anthropic", "gemini"):
        raise ValueError(f"unknown LLM provider: {provider!r}")
    return provider


def _quoted_fact(
    value: str | None, source: str | None, page_text: str
) -> tuple[str | None, str | None, Provenance]:
    if value is not None and source and source in page_text:
        return value, source, Provenance.QUOTED
    return None, None, Provenance.NONE


def _to_opportunity(item: LLMItem, source_url: str, page_text: str) -> Opportunity:
    deadline, deadline_source, deadline_provenance = _quoted_fact(
        item.deadline, item.deadline_source, page_text
    )
    reward, reward_source, reward_provenance = _quoted_fact(
        item.reward, item.reward_source, page_text
    )
    cost, cost_source, cost_provenance = _quoted_fact(
        item.cost, item.cost_source, page_text
    )

    return Opportunity(
        title=item.title,
        apply_url=item.apply_url or source_url,
        source_url=source_url,
        deadline=deadline,
        reward=reward,
        cost=cost,
        organization=item.organization,
        requirements=item.requirements,
        type=item.type,
        description=item.description,
        deadline_provenance=deadline_provenance,
        reward_provenance=reward_provenance,
        cost_provenance=cost_provenance,
        deadline_source=deadline_source,
        reward_source=reward_source,
        cost_source=cost_source,
        source_observed_date=item.source_observed_date,
    )


def extract(
    raw_html: str,
    source_url: str,
    *,
    client: Any | None = None,
    model: str | None = None,
    provider: str | None = None,
) -> ExtractionResult:
    provider = _resolve_provider(provider, client)
    page_text = clean_html(raw_html)
    user_content = f"source_url: {source_url}\n\npage text:\n{page_text}"

    if provider == "gemini":
        llm_result = _call_gemini(client, model, user_content)
    else:
        llm_result = _call_anthropic(client, model, user_content)

    opportunities = [
        _to_opportunity(item, source_url, page_text) for item in llm_result.items
    ]
    return ExtractionResult(kind=llm_result.kind, opportunities=opportunities)


def _call_anthropic(
    client: _AnthropicClient | None, model: str | None, user_content: str
) -> LLMResult:
    if client is None:
        client = _default_client()

    message = client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        tools=[CONTRACT_TOOL],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
        messages=[{"role": "user", "content": user_content}],
    )

    tool_use = next(block for block in message.content if block.type == "tool_use")
    return LLMResult.model_validate(tool_use.input)


def _call_gemini(client: Any | None, model: str | None, user_content: str) -> LLMResult:
    if client is None:
        client = _default_gemini_client()

    config: Any = {
        "system_instruction": _SYSTEM_PROMPT,
        "response_mime_type": "application/json",
        "response_schema": LLMResult,
    }
    try:
        from google.genai import types
    except ImportError:
        pass
    else:
        config = types.GenerateContentConfig(**config)

    response = client.models.generate_content(
        model=model or DEFAULT_GEMINI_MODEL,
        contents=user_content,
        config=config,
    )

    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, LLMResult):
        return parsed
    return LLMResult.model_validate_json(response.text)
