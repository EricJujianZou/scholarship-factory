from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel

from .clean import clean_html
from .models import Opportunity, Provenance

DEFAULT_MODEL = "claude-opus-4-8"
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
    client: _AnthropicClient | None = None,
    model: str = DEFAULT_MODEL,
) -> ExtractionResult:
    page_text = clean_html(raw_html)
    if client is None:
        client = _default_client()

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        tools=[CONTRACT_TOOL],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
        messages=[
            {
                "role": "user",
                "content": f"source_url: {source_url}\n\npage text:\n{page_text}",
            }
        ],
    )

    tool_use = next(block for block in message.content if block.type == "tool_use")
    llm_result = LLMResult.model_validate(tool_use.input)

    opportunities = [
        _to_opportunity(item, source_url, page_text) for item in llm_result.items
    ]
    return ExtractionResult(kind=llm_result.kind, opportunities=opportunities)
