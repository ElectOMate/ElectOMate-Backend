import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import aiostream
import httpx
import weaviate
from em_backend.query.db_search import database_search
from em_backend.query.web_search import web_search
from em_backend.statics.tools import database_search_tools, web_search_tools

from ..langchain_citation_client import (
    AIMessage,
    CitationOptions,
    DocumentToolContent,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from ..old_models import (
    Answer,
    AnswerChunk,
    SinglePartyAnswer,
    StandardAnswer,
    SupportedLanguages,
    SupportedParties,
)
from ..statics.prompts import (
    multiparty_detection_instructions,
    multiparty_detection_response_format,
    query_rag_system_instructions,
    query_rag_system_multi_instructions,
)


async def single_pary_stream(
    question: str,
    party: SupportedParties,
    use_web_search: bool,
    use_database_search: bool,
    multiparty: bool,
    langchain_async_clients: dict[str, Any],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
) -> AsyncGenerator[dict[str, Any] | dict[str, dict[str, Any]], Any]:
    messages = list()
    if party is None:
        messages.append(
            SystemMessage(
                content=query_rag_system_instructions(
                    use_web_search, use_database_search
                )[language]
            )
        )
    else:
        messages.append(
            SystemMessage(
                content=query_rag_system_multi_instructions(
                    use_web_search, use_database_search
                )[language].format(party)
            )
        )
    messages.append(HumanMessage(content=question))

    tools = list()
    if use_web_search is True:
        tools.append(web_search_tools[language])
    if use_database_search is True:
        tools.append(database_search_tools[language])

    res = langchain_async_clients["langchain_chat_client"].chat_stream(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        citation_options=CitationOptions(mode="ACCURATE"),
    )

    func_name = None
    tool_plan = ""
    tool_calls_arguments = dict()
    tool_calls_ids = dict()
    citations: dict[str, list[DocumentToolContent]] = {"database": [], "web": []}

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
                    # This assumes that 'tool-call-start'was received but doesn't check for performance optimization
                    tool_calls_arguments[func_name] += (
                        event.delta.message.tool_calls.function.arguments
                    )
                if event.type == "tool-call-end":
                    # This assumes that 'tool-call-start'was received but doesn't check for performance optimization
                    func_name = None
                if (
                    event.type == "message-end"
                    and event.delta.finish_reason == "TOOL_CALL"
                ):
                    messages.append(
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": tool_calls_ids[func],
                                    "type": "function",
                                    "function": {
                                        "name": func,
                                        "arguments": tool_calls_arguments[func],
                                    },
                                }
                                for func in tool_calls_ids
                            ],
                        )
                    )
                    for func in tool_calls_arguments:
                        if func == "database_search":
                            tool_results = await database_search(
                                **json.loads(tool_calls_arguments[func]),
                                party=party,
                                question=question,
                                langchain_async_clients=langchain_async_clients,
                                weaviate_async_client=weaviate_async_client,
                            )
                            citations["database"].extend(tool_results)
                        if func == "web_search":
                            tool_results = await web_search(
                                **json.loads(tool_calls_arguments[func]),
                                langchain_async_clients=langchain_async_clients,
                            )
                            citations["web"].extend(tool_results)
                        messages.append(
                            ToolMessage(
                                tool_call_id=tool_calls_ids[func],
                                content=json.dumps(
                                    [doc.document.data for doc in tool_results]
                                ),
                            )
                        )
                    tool_calls_arguments = dict()
                    tool_calls_ids = dict()
                    res = langchain_async_clients["langchain_chat_client"].chat_stream(
                        model="gpt-4o",
                        messages=messages,
                        tools=tools,
                        citation_options=CitationOptions(mode="ACCURATE"),
                    )
                if event.type == "content-delta":
                    if multiparty is True:
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
                    for citation in citations["database"]:
                        yield {
                            "citation": {
                                "type": "manifesto-citation",
                                "title": citation.document.data["title"],
                                "content": citation.document.data["content"],
                                "manifesto": citation.document.data["filename"][:-4],
                            }
                        }
                    for citation in citations["web"]:
                        yield {
                            "citation": {
                                "type": "web-citation",
                                "title": citation.document.data["title"],
                                "content": citation.document.data["content"],
                                "url": citation.document.data["url"],
                            }
                        }
                if event.type == "message-end":
                    break
            else:
                break
        except httpx.ReadError:
            pass


async def stream_rag(
    question: str,
    parties: list[SupportedParties],
    use_web_search: bool,
    use_database_search: bool,
    langchain_async_clients: dict[str, Any],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
) -> AsyncGenerator[AnswerChunk]:
    # Model to decide if a single party is refered to in multiparty scenario
    res = await langchain_async_clients["langchain_chat_client"].chat(
        model="gpt-4o",
        messages=[
            SystemMessage(content=multiparty_detection_instructions[language]),
            HumanMessage(content=question),
        ],
        response_format=multiparty_detection_response_format,
    )
    new_parties = json.loads(res.message.content[0].text)["parties"]

    if "all" in new_parties:
        new_parties = list(SupportedParties)

    if len(parties) == 0:
        yield json.dumps(
            {"type": "answer-type-chunk", "answer_type": "standard-answer"}
        )
        result = single_pary_stream(
            question,
            party=None,
            use_web_search=use_web_search,
            use_database_search=use_database_search,
            multiparty=False,
            langchain_async_clients=langchain_async_clients,
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
            multiparty=False,
            langchain_async_clients=langchain_async_clients,
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
                multiparty=True,
                langchain_async_clients=langchain_async_clients,
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
    multiparty: bool,
    langchain_async_clients: dict[str, Any],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
) -> StandardAnswer | SinglePartyAnswer:
    messages = list()
    if party is None:
        messages.append(
            SystemMessage(
                content=query_rag_system_instructions(
                    use_web_search, use_database_search
                )[language]
            )
        )
    else:
        messages.append(
            SystemMessage(
                content=query_rag_system_multi_instructions(
                    use_web_search, use_database_search
                )[language].format(party)
            )
        )
    messages.append(HumanMessage(content=question))

    tools = list()
    if use_web_search is True:
        tools.append(web_search_tools[language])
    if use_database_search is True:
        tools.append(database_search_tools[language])

    res = await langchain_async_clients["langchain_chat_client"].chat(
        model="gpt-4o",
        messages=messages,
        tools=tools,
    )

    citations: dict[str, list[DocumentToolContent]] = {"database": [], "web": []}
    while res.message.tool_calls:
        messages.append(AIMessage(content="", tool_calls=res.message.tool_calls))

        for tc in res.message.tool_calls:
            if tc.function.name == "database_search":
                tool_results = await database_search(
                    **json.loads(tc.function.arguments),
                    party=party,
                    question=question,
                    langchain_async_clients=langchain_async_clients,
                    weaviate_async_client=weaviate_async_client,
                )
                citations["database"].extend(tool_results)
            elif tc.function.name == "web_search":
                tool_results = await web_search(
                    **json.loads(tc.function.arguments),
                    langchain_async_clients=langchain_async_clients,
                )
                citations["web"].extend(tool_results)

            messages.append(
                ToolMessage(
                    tool_call_id=tc.id,
                    content=json.dumps([doc.document.data for doc in tool_results]),
                )
            )

            res = await langchain_async_clients["langchain_chat_client"].chat(
                model="gpt-4o", messages=messages, tools=tools
            )

    citations_res = list()
    for citation in citations["database"]:
        citations_res.append(
            {
                "citation": {
                    "type": "manifesto-citation",
                    "title": citation.document.data["title"],
                    "content": citation.document.data["content"],
                    "manifesto": citation.document.data["filename"][:-4],
                }
            }
        )
    for citation in citations["web"]:
        citations_res.append(
            {
                "citation": {
                    "type": "web-citation",
                    "title": citation.document.data["title"],
                    "content": citation.document.data["content"],
                    "url": citation.document.data["url"],
                }
            }
        )

    if multiparty is True:
        return {
            "answer": res.message.content[0].text,
            "citations": citations_res,
            "party": party,
        }
    else:
        return {
            "type": "standard-answer",
            "answer": res.message.content[0].text,
            "citations": citations_res,
        }


async def query_rag(
    question: str,
    parties: list[SupportedParties],
    use_web_search: bool,
    use_database_search: bool,
    langchain_async_clients: dict[str, Any],
    weaviate_async_client: weaviate.WeaviateAsyncClient,
    language: SupportedLanguages,
) -> Answer:
    # Model to decide if a single party is refered to in multiparty scenario
    res = await langchain_async_clients["langchain_chat_client"].chat(
        model="gpt-4o",
        messages=[
            SystemMessage(content=multiparty_detection_instructions[language]),
            HumanMessage(content=question),
        ],
        response_format=multiparty_detection_response_format,
    )
    new_parties = json.loads(res.message.content[0].text)["parties"]

    if "all" in new_parties:
        new_parties = list(SupportedParties)

    parties = list(set(new_parties) & set(parties))

    if len(parties) == 0:
        result = await single_party_search(
            question,
            party=None,
            use_web_search=use_web_search,
            use_database_search=use_database_search,
            multiparty=False,
            langchain_async_clients=langchain_async_clients,
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
            multiparty=False,
            langchain_async_clients=langchain_async_clients,
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
                multiparty=True,
                langchain_async_clients=langchain_async_clients,
                weaviate_async_client=weaviate_async_client,
                language=language,
            )
            for party in parties
        ]
        results = await asyncio.gather(*tasks)
        return {"answer": {"type": '"multi-party-answer', "answers": results}}
