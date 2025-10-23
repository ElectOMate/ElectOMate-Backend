from collections.abc import Sequence
from operator import add
from typing import TYPE_CHECKING, Annotated, TypedDict

from langchain_core.messages import AnyMessage as AnyLcMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.database.models import Country, Election, Party
from em_backend.vector.db import VectorDatabase

if TYPE_CHECKING:  # pragma: no cover - type checking hook
    from em_backend.llm.perplexity import PerplexityClient


def use_latest_party(existing: "Party | None", update: "Party | None") -> "Party | None":
    """LangGraph aggregator that keeps the most recent party value."""

    return update or existing


def merge_party_sources(
    existing: "dict[str, list[WebSource]] | None",
    update: "dict[str, list[WebSource]] | None",
) -> "dict[str, list[WebSource]]":
    """Merge party-scoped web sources, concatenating lists per party."""

    merged: dict[str, list[WebSource]] = {}

    if existing:
        for key, documents in existing.items():
            merged[key] = list(documents)

    if update:
        for key, documents in update.items():
            current = merged.setdefault(key, [])
            current.extend(documents)

    return merged


def merge_party_summaries(
    existing: "dict[str, str] | None",
    update: "dict[str, str] | None",
) -> "dict[str, str]":
    """Merge party summaries preferring most recent values per party."""

    merged: dict[str, str] = {}

    if existing:
        merged.update(existing)

    if update:
        merged.update(update)

    return merged


class AgentState(TypedDict):
    messages: Annotated[Sequence[AnyLcMessage], add_messages]
    country: Country
    election: Election
    selected_parties: list[Party]
    lock_selected_parties: bool
    is_comparison_question: bool
    conversation_title: str
    conversation_follow_up_questions: list[str]

    use_web_search: bool
    use_vector_database: bool
    should_use_generic_web_search: bool
    perplexity_generic_sources: list["WebSource"]
    perplexity_generic_summary: str
    perplexity_comparison_sources: list["WebSource"]
    perplexity_comparison_summary: str
    perplexity_party_sources: Annotated[
        dict[str, list["WebSource"]],
        merge_party_sources,
    ]
    perplexity_party_summaries: Annotated[
        dict[str, str],
        merge_party_summaries,
    ]

    # Language preferences passed from frontend
    # Name of the language in which to write final answers (human-readable, e.g., "Spanish")
    response_language_name: str | None
    # Name of the manifesto/source language for query generation (e.g., "Spanish")
    manifesto_language_name: str | None
    # Whether it's okay to match the user's message language when appropriate
    respond_in_user_language: bool | None

    # Keep this, even though the key is never used
    party_tag: Annotated[list[Party], add]


class NonComparisonQuestionState(AgentState):
    party: Annotated[Party, use_latest_party]


class AgentContext(TypedDict):
    session: AsyncSession
    chat_model: ChatOpenAI
    vector_database: VectorDatabase
    perplexity_client: "PerplexityClient | None"


class WebSource(TypedDict, total=False):
    title: str
    url: str
    snippet: str
    published_at: str
