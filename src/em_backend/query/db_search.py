import asyncio
import itertools
from typing import Any

import weaviate
import weaviate.classes as wvc

from em_backend.langchain_citation_client import Document, DocumentToolContent
from em_backend.models import SupportedParties


async def get_documents(
    search_query: str,
    party: SupportedParties | None,
    question: str,
    langchain_async_clients: dict[str, Any],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
) -> list[DocumentToolContent]:
    # TO REMOVE: outdated calls -- migrating to third-party service
    search_query_embedding_response = await langchain_async_clients[
        "embed_client"
    ].embed(
        texts=[search_query],
        model="embed-multilingual-v3.0",
        input_type="search_query",
        embedding_types=["float"],
    )

    collection = weaviate_async_client.collections.get(name="Documents")

    if party is not None:
        party_filter = wvc.query.Filter.by_property("filename").like(
            f"{party.lower()}.pdf"
        )

        results = await collection.query.hybrid(
            search_query,
            vector=search_query_embedding_response.embeddings.float[0],
            limit=30,
            filters=party_filter,
        )
    else:
        results = await collection.query.hybrid(
            search_query,
            vector=search_query_embedding_response.embeddings.float[0],
            limit=30,
        )

    # TO REMOVE: outdated calls -- migrating to third-party service
    rerank_response = await langchain_async_clients["rerank_client"].rerank(
        model="rerank-v3.5",
        query=question,
        documents=map(lambda x: x.properties["chunk_content"], results.objects),
        top_n=10,
    )

    documents = [
        DocumentToolContent(
            document=Document(
                data={
                    "content": results.objects[rank.index].properties["chunk_content"],
                    "title": results.objects[rank.index].properties["title"],
                    "filename": results.objects[rank.index].properties["filename"],
                    "type": "manifesto-citation",
                },
            )
        )
        for rank in rerank_response.results
    ]
    return documents


async def database_search(
    search_queries: list[str],
    party: SupportedParties | None,
    question: str,
    langchain_async_clients: dict[str, Any],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
) -> list[DocumentToolContent]:
    tasks = [
        get_documents(
            search_queries[i],
            party,
            question,
            langchain_async_clients,
            weaviate_async_client,
        )
        for i in range(len(search_queries))
    ]
    results = await asyncio.gather(*tasks)
    return list(itertools.chain.from_iterable(results))
