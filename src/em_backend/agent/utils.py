from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from typing import Any, cast
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages import AnyMessage as AnyLcMessage
from langchain_openai import ChatOpenAI

from em_backend.agent.prompts.improve_rag_query import IMPROVE_RAG_QUERY
from em_backend.agent.prompts.rerank_documents import (
    RERANK_DOCUMENTS,
    RerankDocumentsStructuredOutput,
)
from em_backend.agent.types import AgentState
from em_backend.database.models import Election, Party
from em_backend.models.chunks import (
    AnyChunk,
    ComparisonMessageChunk,
    ComparisonSourcesChunk,
    ComparisonTokenChunk,
    FollowUpQuestionsChunk,
    PartyMessageChunk,
    PartySourcesChunk,
    PartyTokenChunk,
    TitleChunk,
)
from em_backend.models.messages import AnyMessage, AssistantMessage, UserMessage
from em_backend.vector.db import DocumentChunk, VectorDatabase


def convert_to_lc_message(messages: list[AnyMessage]) -> list[AnyLcMessage]:
    lc_messages = []
    for msg in messages:
        match msg.type:
            case "assistant":
                lc_messages.append(AIMessage(id=msg.id, content=msg.content))
            case "user":
                lc_messages.append(HumanMessage(id=msg.id, content=msg.content))
    return lc_messages


def convert_from_lc_message(lc_messages: Sequence[AnyLcMessage]) -> list[AnyMessage]:
    messages = []
    for msg in lc_messages:
        match msg.type:
            case "ai":
                messages.append(
                    AssistantMessage(id=msg.id or str(uuid4()), content=msg.text())
                )
            case "human":
                messages.append(
                    UserMessage(id=msg.id or str(uuid4()), content=msg.text())
                )
    return messages


async def process_lc_stream(
    lc_stream: AsyncIterator[dict[str, Any] | Any],
) -> AsyncGenerator[AnyChunk]:
    async for response in lc_stream:
        # Drop incorrectly formatted stream responses
        if not isinstance(response, tuple):
            pass

        # Extract chunk from tuple
        mode: str  # Type of the chunk
        chunk: Any  # Chunk content
        mode, chunk = response

        match mode:
            case "updates":
                # Updates means we get all the state updates after a Pregel step
                update_chunk: dict[str, AgentState] = chunk

                if update := next(
                    (d for d in update_chunk.values() if "conversation_title" in d),
                    None,
                ):
                    yield TitleChunk(title=update["conversation_title"])

                if update := next(
                    (
                        d
                        for d in update_chunk.values()
                        if "conversation_follow_up_questions" in d
                    ),
                    None,
                ):
                    yield FollowUpQuestionsChunk(
                        follow_up_questions=update["conversation_follow_up_questions"]
                    )

                for node, update in update_chunk.items():
                    if node.startswith("generate_single_party_answer"):
                        msg = convert_from_lc_message(update["messages"])[-1]
                        yield PartyMessageChunk(
                            id=msg.id or str(uuid4()),
                            message=msg,
                            party=cast("Party", update.get("party")).shortname,
                        )

                    if node.startswith("generate_comparison_answer"):
                        msg = convert_from_lc_message(update["messages"])[-1]
                        yield ComparisonMessageChunk(
                            id=msg.id or str(uuid4()),
                            message=msg,
                        )

            case "messages":
                # Messages means a token from an LLM call in one of the nodes
                lc_msg: AnyLcMessage
                metadata: dict[str, Any]
                lc_msg, metadata = chunk
                # Only stream LLM chunks with content and streaming enabled.
                if (
                    "stream" in metadata.get("tags", [])
                    and lc_msg.content
                    and lc_msg.type
                    in (
                        "AIMessageChunk",
                        "HumanMessageChunk",
                        "ChatMessageChunk",
                        "FunctionMessageChunk",
                        "ToolMessageChunk",
                    )
                ):
                    if tag := next(
                        (
                            tag
                            for tag in cast("list[str]", metadata.get("tags", []))
                            if tag.startswith("party_")
                        ),
                        "",
                    ):
                        yield PartyTokenChunk(
                            id=lc_msg.id or str(uuid4()),
                            content=lc_msg.text(),
                            party=tag.removeprefix("party_"),
                        )
                    else:
                        yield ComparisonTokenChunk(
                            id=lc_msg.id or str(uuid4()),
                            content=lc_msg.text(),
                        )

            case "custom":
                if isinstance(chunk, PartySourcesChunk | ComparisonSourcesChunk):
                    yield chunk

            case _:
                pass


async def retrieve_documents_from_user_question(
    messages: Sequence[AnyLcMessage],
    election: Election,
    party: Party,
    chat_model: ChatOpenAI,
    vector_database: VectorDatabase,
) -> list[DocumentChunk]:
    model = IMPROVE_RAG_QUERY | chat_model
    response = await model.ainvoke(
        {
            "election_year": election.year,
            "election_name": election.name,
            "messages": messages,
        }
    )
    documents = await vector_database.retrieve_chunks(
        election.id, party.id, response.text()
    )
    model = RERANK_DOCUMENTS | chat_model.with_structured_output(
        RerankDocumentsStructuredOutput
    )
    response = cast(
        "RerankDocumentsStructuredOutput",
        await model.ainvoke(
            {
                "sources": "\n".join(
                    [
                        "<document>\n"
                        f"index: {i}\n"
                        f"# {doc['title']}\n"
                        f"{doc['text']}\n"
                        "</document>"
                        for i, doc in enumerate(documents)
                    ]
                ),
                "messages": messages,
            }
        ),
    )
    return [documents[i] for i in response.reranked_doc_indices][:5]
