import cohere
from cohere import Document
import weaviate
import weaviate.classes as wvc

from ..models import SupportedParties

import asyncio
from typing import Optional


async def database_search(
    search_queries: list[str],
    party: Optional[SupportedParties],
    question: str,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
) -> list[Document]:
    search_queries_embeddings_response = await cohere_async_clients[
        "embed_multilingual_async_client"
    ].embed(
        texts=search_queries,
        model="embed-multilingual-v3.0",
        input_type="search_query",
        embedding_types=["float"],
    )

    collection = weaviate_async_client.collections.get(name="Documents")

    if party is not None:
        party_filter = wvc.query.Filter.by_property("filename").like(f"{party}.pdf")

        tasks = [
            collection.query.hybrid(
                search_queries[i],
                vector=embedding,
                limit=30,
                filters=party_filter,
            )
            for i, embedding in enumerate(
                search_queries_embeddings_response.embeddings.float
            )
        ]
    else:
        tasks = [
            collection.query.hybrid(
                search_queries[i],
                vector=embedding,
                limit=30,
            )
            for i, embedding in enumerate(
                search_queries_embeddings_response.embeddings.float
            )
        ]
    chunks_responses = await asyncio.gather(*tasks)

    chunks = [
        {
            "title": object.properties["title"],
            "filename": object.properties["filename"],
            "chunk_content": object.properties["chunk_content"],
        }
        for chunks_response in chunks_responses
        for object in chunks_response.objects
    ]

    rerank_response = await cohere_async_clients[
        "rerank_multilingual_async_client"
    ].rerank(
        model="rerank-v3.5",
        query=question,
        documents=map(lambda x: x["chunk_content"], chunks),
        top_n=5,
    )

    documents = [
        Document(
            id=str(i),
            data={
                "text": chunks[result.index]["chunk_content"],
                "title": chunks[result.index]["title"],
                "filename": chunks[result.index]["filename"],
            },
        )
        for i, result in enumerate(rerank_response.results)
    ]
    return documents
