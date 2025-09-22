from collections.abc import Sequence
from typing import cast

from langchain_core.messages import AnyMessage
from langchain_openai import ChatOpenAI

from em_backend.agent.prompts.improve_rag_query import IMPROVE_RAG_QUERY
from em_backend.agent.prompts.rerank_documents import (
    RERANK_DOCUMENTS,
    RerankDocumentsStructuredOutput,
)
from em_backend.database.models import Election, Party
from em_backend.vector.db import DocumentChunk, VectorDatabase


async def retrieve_documents_from_user_question(
    messages: Sequence[AnyMessage],
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
