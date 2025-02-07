import cohere
from cohere import UserChatMessageV2, SystemChatMessageV2, Document, CitationOptions
import weaviate

from ..statics.prompts import query_generation_instructions
from ..statics.tools import query_generation_tools
from ..models import AnswerChunk, Answer, SupportedLanguages

import json
import asyncio
import httpx

from typing import AsyncGenerator


# Advanced document retrieval
async def get_documents_rerank(
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
    tasks = [
        collection.query.hybrid(search_queries[i], vector=embedding, limit=5)
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


# Basic document retrieval
async def get_documents(
    question: str,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages
) -> list[Document]:

    question_embedding_response = await cohere_async_clients[
        "embed_multilingual_async_client"
    ].embed(
        texts=[question],
        model="embed-multilingual-v3.0",
        input_type="search_query",
        embedding_types=["float"],
    )

    collection = weaviate_async_client.collections.get(name="Documents")
    query_response = await collection.query.hybrid(
        question,
        vector=question_embedding_response.embeddings.float[0],
        limit=5,
    )

    documents = [
        Document(
            id=str(i),
            data={
                "text": object.properties["chunk_content"],
                "title": object.properties["title"],
            },
        )
        for i, object in enumerate(query_response.objects)
    ]

    return documents


async def stream_rag(
    question: str,
    rerank: bool,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages
) -> AsyncGenerator[AnswerChunk, None]:
    if rerank is True:
        documents = await get_documents_rerank(
            question, cohere_async_clients, weaviate_async_client, language
        )
    else:
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
                    print(f"Content: {content}")
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
                    print(f"Citation: {content}")
    except httpx.RemoteProtocolError:
        pass
    finally:
        yield "data: [DONE]\n\n" 
        print("DONE")

async def query_rag(
    question: str,
    rerank: bool,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages
) -> Answer:

    if rerank is True:
        documents = await get_documents_rerank(
            question, cohere_async_clients, weaviate_async_client, language
        )
    else:
        documents = await get_documents(
            question, cohere_async_clients, weaviate_async_client, language
        )
        print(f"Weaviate retrieved these documents: {documents}")

    response = await cohere_async_clients["command_r_async_client"].chat(
        model="command-r-08-2024",
        messages=[UserChatMessageV2(content=question)],
        documents=documents,
    )
    print(f"Cohere response: {response}")
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
