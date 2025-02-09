import cohere
from cohere import (
    AssistantChatMessageV2,
    UserChatMessageV2,
    SystemChatMessageV2,
    ToolMessageV2,
    CitationOptions,
)
import weaviate

from .db_search import database_search
from .web_search import web_search
from ..statics.prompts import (
    query_rag_system_instructions,
    multiparty_detection_instructions,
    multiparty_detection_response_format,
)
from ..statics.tools import database_search_tools, web_search_tools
from ..models import AnswerChunk, Answer, SupportedLanguages, SupportedParties

import json
import asyncio
import httpx

from typing import AsyncGenerator


async def single_party_search(
    question: str,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
    party: SupportedParties,
    use_web_search: bool,
):
    messages = [
        [
            SystemChatMessageV2(content=query_rag_system_instructions[language]),
            UserChatMessageV2(content=question),
        ],
    ]

    if use_web_search is True:
        tools = [database_search_tools[language], web_search_tools[language]]
    else:
        tools = [database_search_tools[language]]

    res = await cohere_async_clients["command_r_async_client"].chat(
        model="command-r-08-2024",
        messages=messages,
        tools=tools,
    )

    while res.message.tool_calls:
        messages.append(
            AssistantChatMessageV2(
                tool_calls=res.message.tool_calls, tool_plan=res.message.tool_plan
            )
        )

        for tc in res.message.tool_calls:

            if tc.function.name == "database_search":
                tool_results = await database_search(
                    **json.loads(tc.function.arguments),
                    party=party,
                    question=question,
                    cohere_async_clients=cohere_async_clients,
                    weaviate_async_client=weaviate_async_client,
                    language=language
                )
            elif tc.function.name == "web_search":
                tool_results = await web_search(
                    **json.loads(tc.function.arguments),
                    cohere_async_clients=cohere_async_clients,
                    language=language
                )

            messages.append(ToolMessageV2(tool_call_id=tc.id, content=tool_results))

            res = cohere_async_clients.chat(
                model="command-r-08-2024", messages=messages, tools=tools
            )

    # Ensure citations are not None
    citations = res.message.citations if res.message.citations else []

    return {
        "answer": res.message.content[0].text,
        "citations": [
            {
                "title": citation.sources[0].document["title"],
                "text": citation.sources[0].document["text"],
            }
            for citation in citations
        ],
    }


async def stream_rag(
    question: str,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
    party: SupportedParties,
) -> AsyncGenerator[AnswerChunk, None]:
    raise NotImplementedError("This function has not been implemented yet.")

    # response = cohere_async_clients["command_r_async_client"].chat_stream(
    #     model="command-r-08-2024",
    #     messages=[
    #         SystemChatMessageV2(content=query_rag_system_instructions[language]),
    #         UserChatMessageV2(content=question),
    #     ],
    #     documents=documents,
    #     citation_options=CitationOptions(mode="FAST"),
    # )

    # try:
    #     async for chunk in response:
    #         if chunk:
    #             if chunk.type == "content-delta":
    #                 content = json.dumps(
    #                     {
    #                         "type": "response-chunk",
    #                         "text": chunk.delta.message.content.text,
    #                     }
    #                 )
    #                 yield "data: " + content + "\n\n"
    #             elif chunk.type == "citation-start":
    #                 content = json.dumps(
    #                     {
    #                         "type": "citation",
    #                         "title": chunk.delta.message.citations.sources[0].document[
    #                             "title"
    #                         ],
    #                         "text": chunk.delta.message.citations.sources[0].document[
    #                             "text"
    #                         ],
    #                     }
    #                 )
    #                 yield "data: " + content + "\n\n"
    # except httpx.RemoteProtocolError:
    #     pass
    # finally:
    #     yield "data: [DONE]\n\n"


async def query_rag(
    question: str,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
    parties: list[SupportedParties],
    use_web_search: bool,
) -> Answer:

    if len(parties) > 1:
        # Model to decide if a single party is refered to in multiparty scenario
        res = await cohere_async_clients["command_r_async_client"].chat(
            model="command-r-08-2024",
            messages=[
                SystemChatMessageV2(multiparty_detection_instructions[language]),
                UserChatMessageV2(content=question),
            ],
            response_format=multiparty_detection_response_format,
        )
        parties = json.loads(res.message.content[0].text)["parties"]

        if "all" in parties:
            parties = list(SupportedParties)

        if "unspecified" in parties:
            parties = []

    if len(parties) == 0:
        results = await single_party_search(
            question,
            cohere_async_clients,
            weaviate_async_client,
            language,
            None,
            use_web_search,
        )
    else:
        tasks = [
            single_party_search(
                question,
                cohere_async_clients,
                weaviate_async_client,
                language,
                party,
                use_web_search,
            )
            for party in parties
        ]
        results = asyncio.gather(*tasks)

    return results