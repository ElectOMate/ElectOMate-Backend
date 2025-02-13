from azure.cognitiveservices.search.websearch.models import AnswerType
import cohere
from cohere import Document, DocumentToolContent
from uuid import uuid4

from ..config import bing_client
from ..models import SupportedLanguages


async def web_search(
    search_query: str,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    language: SupportedLanguages,
) -> list[dict]:
    """
    Perform a Bing web search via Azure.
    Returns a list of dicts, each containing 'title', 'url', and 'snippet'.
    """
    response = bing_client.web.search(
        query=search_query,
        market="de-DE",
        set_lang=language.upper(),
        response_filter=[AnswerType.news, AnswerType.web_pages],
        count=20,
    )

    chunks = []
    if hasattr(response.web_pages, "value"):
        for web_page in response.web_pages.value:
            chunks.append(
                {
                    "title": web_page.name,
                    "url": web_page.url,
                    "chunk_content": web_page.text,
                }
            )

    if hasattr(response.news, "values"):
        for news_page in response.news.value:
            chunks.append(
                {
                    "title": news_page.name,
                    "url": news_page.url,
                    "chunk_content": news_page.text,
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
