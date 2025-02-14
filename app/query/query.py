import cohere
from cohere import (
    AssistantChatMessageV2,
    UserChatMessageV2,
    SystemChatMessageV2,
    ToolChatMessageV2,
    ToolCallV2,
    ToolCallV2Function,
    CitationOptions,
)
import weaviate
import httpx
import aiostream

from .db_search import database_search
from .web_search import web_search
from ..statics.prompts import (
    query_rag_system_instructions,
    query_rag_system_multi_instructions,
    multiparty_detection_instructions,
    multiparty_detection_response_format,
)
from ..statics.tools import database_search_tools, web_search_tools
from ..models import (
    AnswerChunk,
    Answer,
    SupportedLanguages,
    SupportedParties,
    SinglePartyAnswer,
    StandardAnswer,
)

import json
import asyncio
import warnings
from typing import AsyncGenerator, Union


async def single_pary_stream(
    question: str,
    party: SupportedParties,
    use_web_search: bool,
    use_database_search: bool,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
):
    messages = list()
    if party is None:
        messages.append(
            SystemChatMessageV2(
                content=query_rag_system_instructions(
                    use_web_search, use_database_search
                )[language]
            )
        )
    else:
        messages.append(
            SystemChatMessageV2(
                content=query_rag_system_multi_instructions(
                    use_web_search, use_database_search
                )[language].format(party)
            )
        )
    messages.append(UserChatMessageV2(content=question))

    tools = list()
    if use_web_search is True:
        tools.append(web_search_tools[language])
    if use_database_search is True:
        tools.append(database_search_tools[language])

    res = cohere_async_clients["command_r_async_client"].chat_stream(
        model="command-r-08-2024",
        messages=messages,
        tools=tools,
        citation_options=CitationOptions(mode="ACCURATE"),
    )

    func_name = None
    tool_plan = ""
    tool_calls_arguments = dict()
    tool_calls_ids = dict()

    while True:
        try:
            async for event in res:
                if event.type == "tool-plan-delta":
                    tool_plan += event.delta.message.tool_plan
                if event.type == "tool-call-start":
                    func_name = event.delta.message.tool_calls.function.name
                    tool_calls_arguments[func_name] = (
                        event.delta.message.tool_calls.function.arguments
                    )
                    tool_calls_ids[func_name] = event.delta.message.tool_calls.id
                if event.type == "tool-call-delta":
                    # This assumes that 'tool-call-start' was received but doesn't check for performance optimization
                    tool_calls_arguments[func_name] += event.delta.message.tool_calls.function.arguments
                if event.type == "tool-call-end":
                    # This assumes that 'tool-call-start' was received but doesn't check for performance optimization
                    func_name = None
                if event.type == "message-end":
                    if event.delta.finish_reason == "TOOL_CALL":
                        messages.append(
                            AssistantChatMessageV2(
                                tool_calls=[
                                    ToolCallV2(
                                        id=tool_calls_ids[func],
                                        type="function",
                                        function=ToolCallV2Function(
                                            name=func,
                                            arguments=tool_calls_arguments[func],
                                        ),
                                    )
                                    for func in tool_calls_ids.keys()
                                ],
                                tool_plan=tool_plan,
                            )
                        )
                        for func in tool_calls_arguments.keys():
                            if func == "database_search":
                                tool_results = await database_search(
                                    **json.loads(tool_calls_arguments[func]),
                                    party=party,
                                    question=question,
                                    cohere_async_clients=cohere_async_clients,
                                    weaviate_async_client=weaviate_async_client,
                                )
                            if func == "web_search":
                                tool_results = await web_search(
                                    **json.loads(tool_calls_arguments[func]),
                                    cohere_async_clients=cohere_async_clients,
                                    language=language,
                                )
                            messages.append(
                                ToolChatMessageV2(
                                    tool_call_id=tool_calls_ids[func],
                                    content=tool_results,
                                )
                            )
                        tool_calls_arguments = dict()
                        tool_calls_ids = dict()
                        res = cohere_async_clients[
                            "command_r_async_client"
                        ].chat_stream(
                            model="command-r-08-2024",
                            messages=messages,
                            tools=tools,
                            citation_options=CitationOptions(mode="ACCURATE"),
                        )
                if event.type == "content-delta":
                    if party is not None:
                        yield {
                            "type": "multi-party-answer-chunk",
                            "answer_delta": event.delta.message.content.text,
                            "party": party,
                        }
                    else:
                        yield {
                            "type": "standard-answer-chunk",
                            "answer-delta": event.delta.message.content.text,
                        }
                if event.type == "citation-start":
                    citation = event.delta.message.citations
                    if citation.sources[0].tool_output["type"] == "manifesto-citation":
                        yield {
                            "citation": {
                                "type": "manifesto-citation",
                                "title": citation.sources[0].tool_output["title"],
                                "content": citation.sources[0].tool_output["content"],
                                "manifesto": citation.sources[0].tool_output["filename"][:-4],
                                "citation_start": citation.start,
                                "citation_end": citation.end,
                            }
                        }
                    elif citation.sources[0].tool_output["type"] == "web-citation":
                        yield {
                            "citation": {
                                "type": "web-citation",
                                "title": citation.sources[0].tool_output["title"],
                                "content": citation.sources[0].tool_output["content"],
                                "url": citation.sources[0].tool_output["url"],
                                "citation_start": citation.start,
                                "citation_end": citation.end,
                            }
                        }
                    else:
                        warnings.warn("Unrecognized citation type.")
                if event.type == "message-end":
                    break
            else:
                break
        except httpx.ReadError:
            break  # End the loop gracefully when a ReadError occurs


async def stream_rag(
    question: str,
    parties: list[SupportedParties],
    use_web_search: bool,
    use_database_search: bool,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
) -> AsyncGenerator[AnswerChunk, None]:
    if len(parties) > 1:
        # Model to decide if a single party is refered to in multiparty scenario
        res = await cohere_async_clients["command_r_async_client"].chat(
            model="command-r-08-2024",
            messages=[
                SystemChatMessageV2(
                    content=multiparty_detection_instructions[language]
                ),
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
        yield json.dumps(
            {"type": "answer-type-chunk", "answer_type": "standard-answer"}
        )
        result = single_pary_stream(
            question,
            party=None,
            use_web_search=use_web_search,
            use_database_search=use_database_search,
            cohere_async_clients=cohere_async_clients,
            weaviate_async_client=weaviate_async_client,
            language=language,
        )
        async for chunk in result:
            yield json.dumps(chunk)
    elif len(parties) == 1:
        yield json.dumps(
            {"type": "answer-type-chunk", "answer_type": "standard-answer"}
        )
        result = single_pary_stream(
            question,
            party=parties[0],
            use_web_search=use_web_search,
            use_database_search=use_database_search,
            cohere_async_clients=cohere_async_clients,
            weaviate_async_client=weaviate_async_client,
            language=language,
        )
        async for chunk in result:
            yield json.dumps(chunk)
    else:
        yield json.dumps(
            {"type": "answer-type-chunk", "answer_type": "multi-party-answer"}
        )
        tasks = [
            single_pary_stream(
                question,
                party,
                use_web_search=False,
                use_database_search=use_database_search,
                cohere_async_clients=cohere_async_clients,
                weaviate_async_client=weaviate_async_client,
                language=language,
            )
            for party in parties
        ]
        task_stream = aiostream.stream.merge(*tasks)
        async with task_stream.stream() as stream:
            async for chunk in stream:
                yield json.dumps(chunk)


async def single_party_search(
    question: str,
    party: SupportedParties,
    use_web_search: bool,
    use_database_search: bool,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
) -> Union[StandardAnswer, SinglePartyAnswer]:
    messages = list()
    if party is None:
        messages.append(
            SystemChatMessageV2(
                content=query_rag_system_instructions(
                    use_web_search, use_database_search
                )[language]
            )
        )
    else:
        messages.append(
            SystemChatMessageV2(
                content=query_rag_system_multi_instructions(
                    use_web_search, use_database_search
                )[language].format(party)
            )
        )
    messages.append(UserChatMessageV2(content=question))

    tools = list()
    if use_web_search is True:
        tools.append(web_search_tools[language])
    if use_database_search is True:
        tools.append(database_search_tools[language])

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
        print(res.message.tool_plan)

        for tc in res.message.tool_calls:

            if tc.function.name == "database_search":
                tool_results = await database_search(
                    **json.loads(tc.function.arguments),
                    party=party,
                    question=question,
                    cohere_async_clients=cohere_async_clients,
                    weaviate_async_client=weaviate_async_client,
                )
                messages.append(
                    ToolChatMessageV2(tool_call_id=tc.id, content=tool_results)
                )
            elif tc.function.name == "web_search":
                tool_results = await web_search(
                    **json.loads(tc.function.arguments),
                    cohere_async_clients=cohere_async_clients,
                    language=language,
                )
                messages.append(
                    ToolChatMessageV2(tool_call_id=tc.id, content=tool_results)
                )

            res = await cohere_async_clients["command_r_async_client"].chat(
                model="command-r-08-2024", messages=messages, tools=tools
            )

    citations = list()
    for citation in res.message.citations:
        if citation.sources[0].tool_output["type"] == "manifesto-citation":
            citations.append(
                {
                    "citation": {
                        "type": "manifesto-citation",
                        "title": citation.sources[0].tool_output["title"],
                        "content": citation.sources[0].tool_output["content"],
                        "manifesto": citation.sources[0].tool_output["filename"][:-4],
                        "citation_start": citation.start,
                        "citation_end": citation.end,
                    }
                }
            )
        elif citation.sources[0].tool_output["type"] == "web-citation":
            citations.append(
                {
                    "citation": {
                        "type": "web-citation",
                        "title": citation.sources[0].tool_output["title"],
                        "content": citation.sources[0].tool_output["content"],
                        "url": citation.sources[0].tool_output["url"],
                        "citation_start": citation.start,
                        "citation_end": citation.end,
                    }
                }
            )
        else:
            warnings.warn("Unrecognized citation type.")

    if party is not None:
        return {
            "answer": res.message.content[0].text,
            "citations": citations,
            "party": party,
        }
    else:
        return {
            "type": "standard-answer",
            "answer": res.message.content[0].text,
            "citations": citations,
        }


async def query_rag(
    question: str,
    parties: list[SupportedParties],
    use_web_search: bool,
    use_database_search: bool,
    cohere_async_clients: dict[str, cohere.AsyncClientV2],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
) -> Answer:

    if len(parties) > 1:
        # Model to decide if a single party is refered to in multiparty scenario
        res = await cohere_async_clients["command_r_async_client"].chat(
            model="command-r-08-2024",
            messages=[
                SystemChatMessageV2(
                    content=multiparty_detection_instructions[language]
                ),
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
        result = await single_party_search(
            question,
            party=None,
            use_web_search=use_web_search,
            use_database_search=use_database_search,
            cohere_async_clients=cohere_async_clients,
            weaviate_async_client=weaviate_async_client,
            language=language,
        )
        return {"answer": result}
    elif len(parties) == 1:
        result = await single_party_search(
            question,
            party=parties[0],
            use_web_search=use_web_search,
            use_database_search=use_database_search,
            cohere_async_clients=cohere_async_clients,
            weaviate_async_client=weaviate_async_client,
            language=language,
        )
        return {"answer": result}
    else:
        tasks = [
            single_party_search(
                question,
                party,
                use_web_search=False,
                use_database_search=use_database_search,
                cohere_async_clients=cohere_async_clients,
                weaviate_async_client=weaviate_async_client,
                language=language,
            )
            for party in parties
        ]
        results = await asyncio.gather(*tasks)
        return {"answer": {"type": '"multi-party-answer', "answers": results}}
