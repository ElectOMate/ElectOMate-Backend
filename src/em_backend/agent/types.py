from collections.abc import Sequence
from operator import add
from typing import Annotated, TypedDict, TYPE_CHECKING

from langchain_core.messages import AnyMessage as AnyLcMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.database.models import Country, Election, Party
from em_backend.vector.db import VectorDatabase

if TYPE_CHECKING:  # pragma: no cover - type checking hook
    from em_backend.llm.perplexity import PerplexityClient


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
    perplexity_party_sources: dict[str, list["WebSource"]]
    perplexity_party_summaries: dict[str, str]

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
    party: Party


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
