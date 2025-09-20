from uuid import uuid4

import cohere
from cohere import Document, DocumentToolContent

from ..config import tavily_client


async def web_search(
    search_query: str,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
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

    rerank_response = await cohere_async_clients[
        "rerank_multilingual_async_client"
    ].rerank(
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
