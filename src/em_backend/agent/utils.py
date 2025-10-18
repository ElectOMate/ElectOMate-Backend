from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from typing import Any, cast
from uuid import uuid4

import logging
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.messages import AnyMessage as AnyLcMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRefusalError

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


logger = logging.getLogger(__name__)


def _format_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            item.get("text", str(item)) if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def _log_prompt(label: str, prompt_messages: Sequence[BaseMessage]) -> None:
    prompt_text = "\n\n".join(
        f"{msg.type.upper() if hasattr(msg, 'type') else type(msg).__name__}: "
        f"{_format_message_content(msg.content)}"
        for msg in prompt_messages
    )
    logger.info("🧾 Prompt [%s]\n%s", label, prompt_text)


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
                    (
                        d
                        for d in update_chunk.values()
                        if d is not None and "conversation_title" in d
                    ),
                    None,
                ):
                    yield TitleChunk(title=update["conversation_title"])

                if update := next(
                    (
                        d
                        for d in update_chunk.values()
                        if d is not None and "conversation_follow_up_questions" in d
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
                            party=cast("list[Party]", update.get("party_tag"))[
                                -1
                            ].shortname,
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
    prompt_input = {
        "election_year": election.year,
        "election_name": election.name,
        "messages": messages,
    }
    _log_prompt("ImproveRAGQuery", IMPROVE_RAG_QUERY.format_messages(**prompt_input))
    response = await model.ainvoke(prompt_input)
    improved_query = response.text()
    logger.info(
        "🛠️  Refined RAG query for %s-%s ➜ %s",
        election.id,
        party.shortname,
        improved_query,
    )
    documents = await vector_database.retrieve_chunks(
        election, party, improved_query
    )
    if documents:
        logger.info(
            "✅ Retrieved %s doc(s) from Weaviate for %s-%s: %s",
            len(documents),
            election.id,
            party.shortname,
            [doc["title"] for doc in documents],
        )
        for idx, doc in enumerate(documents):
            text_preview = doc["text"]
            if len(text_preview) > 800:
                text_preview = f"{text_preview[:800]}…"
            logger.info(
                "📄 RAG chunk %s for %s-%s:\nTitle: %s\nScore: %.4f\nText:\n%s\n",
                idx,
                election.id,
                party.shortname,
                doc["title"],
                doc["score"],
                text_preview,
            )
            logger.info("")
    else:
        logger.warning(
            "⚠️ No documents returned from Weaviate for %s-%s (query=%s)",
            election.id,
            party.shortname,
            improved_query,
        )
    model = RERANK_DOCUMENTS | chat_model.with_structured_output(
        RerankDocumentsStructuredOutput
    )
    try:
        rerank_input = {
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
        _log_prompt("RerankDocuments", RERANK_DOCUMENTS.format_messages(**rerank_input))
        response = cast(
            "RerankDocumentsStructuredOutput",
            await model.ainvoke(rerank_input),
        )
        logger.info(
            "✅ Reranker indices for %s-%s: %s",
            election.id,
            party.shortname,
            response.reranked_doc_indices,
        )
    except OpenAIRefusalError as exc:
        logger.warning(
            "Rerank model refused to respond for party %s: %s; using top documents fallback",
            party.shortname,
            exc,
        )
        return documents[:5]
    valid_indices: list[int] = [
        idx
        for idx in response.reranked_doc_indices or []
        if isinstance(idx, int) and 0 <= idx < len(documents)
    ]
    if not valid_indices:
        if documents:
            logger.warning(
                "Reranker returned no valid indices; falling back to top documents for party %s",
                party.shortname,
            )
        return documents[:5]
    return [documents[i] for i in valid_indices][:5]
