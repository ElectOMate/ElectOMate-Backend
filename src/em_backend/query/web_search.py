from typing import Any
from uuid import uuid4

from em_backend.config import tavily_client
from em_backend.langchain_citation_client import Document, DocumentToolContent


async def web_search(
    search_query: str,
    langchain_async_clients: dict[str, Any],
) -> list[DocumentToolContent]:
    """
    Perform a Bing web search via Azure.
    Returns a list of dicts, each containing 'title', 'url', and 'snippet'.
    """
    response = await tavily_client.search(query=search_query)

    chunks = []
    for result in response["results"]:
        chunks.append(
            {
                "title": result["title"],
                "url": result["url"],
                "chunk_content": result["content"],
            }
        )

    # TO REMOVE: outdated calls -- migrating to third-party service
    rerank_response = await langchain_async_clients["rerank_client"].rerank(
        model="rerank-v3.5",
        query=search_query,
        documents=map(lambda x: x["chunk_content"], chunks),
        top_n=5,
    )

    documents = [
        DocumentToolContent(
            document=Document(
                id=str(uuid4),
                data={
                    "content": chunks[result.index]["chunk_content"],
                    "title": chunks[result.index]["title"],
                    "url": chunks[result.index]["url"],
                    "type": "web-citation",
                },
            )
        )
        for result in rerank_response.results
    ]
    return documents
