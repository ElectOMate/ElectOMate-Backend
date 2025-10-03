from collections.abc import Sequence
from operator import add
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage as AnyLcMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import add_messages
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.database.models import Country, Election, Party
from em_backend.vector.db import VectorDatabase


class AgentState(TypedDict):
    messages: Annotated[Sequence[AnyLcMessage], add_messages]
    country: Country
    election: Election
    selected_parties: list[Party]
    is_comparison_question: bool
    conversation_title: str
    conversation_follow_up_questions: list[str]

    # Keep this, even though the key is never used
    party_tag: Annotated[list[Party], add]


class NonComparisonQuestionState(AgentState):
    party: Party


class AgentContext(TypedDict):
    session: AsyncSession
    chat_model: ChatOpenAI
    vector_database: VectorDatabase
