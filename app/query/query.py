import cohere
from cohere import UserChatMessageV2, SystemChatMessageV2, Document, CitationOptions
import weaviate
from weaviate.collections.classes.filters import Filter

from ..statics.prompts import query_generation_instructions, query_rag_system_instructions
from ..statics.tools import query_generation_tools
from ..models import AnswerChunk, Answer, SupportedLanguages

import json
import asyncio
import httpx

from typing import AsyncGenerator


# Advanced document retrieval
async def get_documents(
    question: str,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages
) -> list[Document]:
    res = await cohere_async_clients["command_r_async_client"].chat(
        model="command-r-08-2024",
        messages=[
            SystemChatMessageV2(content=query_generation_instructions[language]),
            UserChatMessageV2(content=question),
        ],
        tools=[query_generation_tools[language]],
    )

    search_queries = list()
    if res.message.tool_calls:
        for tc in res.message.tool_calls:
            queries = json.loads(tc.function.arguments)["queries"]
            search_queries.extend(queries)

    search_queries_embeddings_response = await cohere_async_clients[
        "embed_multilingual_async_client"
    ].embed(
        texts=search_queries,
        model="embed-multilingual-v3.0",
        input_type="search_query",
        embedding_types=["float"],
    )

    collection = weaviate_async_client.collections.get(name="Documents")

    # Define the filter to check if the document name contains "CDU"
    cdu_filter = Filter.by_property("title").like("*linke*")

    tasks = [
        collection.query.hybrid(
            search_queries[i],
            vector=embedding,
            limit=30,
            # filters=cdu_filter  # Apply the filter here
        )
        for i, embedding in enumerate(
            search_queries_embeddings_response.embeddings.float
        )
    ]
    chunks_responses = await asyncio.gather(*tasks)

    chunks = [
        {
            "title": object.properties["title"],
            "chunk_content": object.properties["chunk_content"],
        }
        for chunks_response in chunks_responses
        for object in chunks_response.objects
    ]

    rerank_response = await cohere_async_clients["rerank_multilingual_async_client"].rerank(
        model="rerank-v3.5",
        query=question,
        documents=map(lambda x: x["chunk_content"], chunks),
        top_n=3,
    )

    documents = [
        Document(
            id=str(i),
            data={
                "text": chunks[result.index]["chunk_content"],
                "title": chunks[result.index]["title"],
            },
        )
        for i, result in enumerate(rerank_response.results)
    ]
    return documents


async def stream_rag(
    question: str,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages
) -> AsyncGenerator[AnswerChunk, None]:
    documents = await get_documents(
        question, cohere_async_clients, weaviate_async_client, language
    )

    response = cohere_async_clients["command_r_async_client"].chat_stream(
        model="command-r-08-2024",
        messages=[UserChatMessageV2(content=question)],
        documents=documents,
        citation_options=CitationOptions(mode="FAST"),
    )

    try:
        async for chunk in response:
            if chunk:
                if chunk.type == "content-delta":
                    content = json.dumps(
                        {
                            "type": "response-chunk",
                            "text": chunk.delta.message.content.text,
                        }
                    )
                    yield "data: " + content + "\n\n"
                elif chunk.type == "citation-start":
                    content = json.dumps(
                        {
                            "type": "citation",
                            "title": chunk.delta.message.citations.sources[0].document[
                                "title"
                            ],
                            "text": chunk.delta.message.citations.sources[0].document[
                                "text"
                            ],
                        }
                    )
                    yield "data: " + content + "\n\n"
    except httpx.RemoteProtocolError:
        pass
    finally:
        yield "data: [DONE]\n\n"
        
async def query_rag(
    question: str,
    rerank: bool,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages
) -> Answer:

    documents = await get_documents(
        question, cohere_async_clients, weaviate_async_client, language
    )

    response = await cohere_async_clients["command_r_async_client"].chat(
        model="command-r-08-2024",
        messages = [
            SystemChatMessageV2(content=query_rag_system_instructions[language]),
            UserChatMessageV2(content=question),
        ],
        documents=documents,
    )
    # Ensure citations are not None
    citations = response.message.citations if response.message.citations else []

    return {
        "answer": response.message.content[0].text,
        "citations": [
            {
                "title": citation.sources[0].document["title"],
                "text": citation.sources[0].document["text"],
            }
            for citation in citations
        ],
    }
