import asyncio
from asyncio import TaskGroup
from collections.abc import AsyncGenerator
from datetime import date
from typing import Any, Literal, cast
from uuid import uuid4

import logging
import textwrap
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from langgraph.graph import StateGraph
from langgraph.pregel import Pregel
from langgraph.runtime import Runtime
from langgraph.types import Send
from sqlalchemy.ext.asyncio import AsyncSession


from em_backend.agent.prompts.comparison_party_answer import COMPARISON_PARTY_ANSWER
from em_backend.agent.prompts.decide_generic_web_search import (
    DECIDE_GENERIC_WEB_SEARCH,
    GenericWebSearchDecision,
)
from em_backend.agent.prompts.generate_title_and_replies import (
    GENERATE_TITLE_AND_REPLIES,
    GenerateTitleAndRepliedStructuredOutput,
)
from em_backend.agent.prompts.perplexity_comparison_query import (
    PERPLEXITY_COMPARISON_QUERY,
)
from em_backend.agent.prompts.perplexity_generic_query import (
    PERPLEXITY_GENERIC_QUERY,
)
from em_backend.agent.prompts.perplexity_single_party_query import (
    PERPLEXITY_SINGLE_PARTY_QUERY,
)
from em_backend.agent.prompts.rephrase_question import (
    REPHRASE_QUESTION,
    RephraseQuestionStructuredOutput,
)
from em_backend.agent.prompts.single_party_answer import SINGLE_PARTY_ANSWER
from em_backend.agent.prompts.update_question_targets import (
    DETERMINE_QUESTION_TARGET,
    DetermineQuestionTargetStructuredOutput,
    get_full_DetermineQuestionTargetStructuredOutput,
)
from em_backend.agent.prompts.generic_answer import GENERIC_ANSWER
from em_backend.agent.types import (
    AgentContext,
    AgentState,
    NonComparisonQuestionState,
    WebSource,
)
from em_backend.agent.utils import (
    convert_documents_to_web_sources,
    convert_to_lc_message,
    format_party_web_sources_for_prompt,
    format_web_sources_for_prompt,
    generate_perplexity_query,
    normalize_perplexity_sources,
    process_lc_stream,
    retrieve_documents_from_user_question,
)
from em_backend.database.models import Election, Party
from em_backend.database.utils import (
    get_missing_party_shortnames,
    get_parties_enum,
    get_party_from_name_list,
    get_party_fullname_from_name_list,
)
from em_backend.llm.openai import get_openai_model
from em_backend.llm.perplexity import PerplexityClient
from em_backend.llm.wikipedia import WikipediaClient
from em_backend.models.chunks import (
    AnyChunk,
    ComparisonSourcesChunk,
    PartySourcesChunk,
    PerplexitySourcesChunk,
)
from em_backend.models.messages import AnyMessage
from em_backend.vector.db import DocumentChunk, VectorDatabase
from langchain_openai.chat_models.base import OpenAIRefusalError


logger = logging.getLogger(__name__)

COUNTRY_LANGUAGE_MAP: dict[str, dict[str, str]] = {
    "DE": {"name": "Deutsch", "code": "de"},
    "CL": {"name": "Español", "code": "es"},
    "IE": {"name": "English", "code": "en"},
    "HU": {"name": "Magyar", "code": "hu"},
    "PL": {"name": "Polski", "code": "pl"},
    "NL": {"name": "Nederlands", "code": "nl"},
    "NO": {"name": "Norsk", "code": "no"},
    "SI": {"name": "Slovenščina", "code": "sl"},
}

# Answer length definitions for prompt injection
ANSWER_LENGTH_DEFINITIONS: dict[str, str] = {
    "Short": (
        "STRICT LENGTH CONSTRAINT — **Short** mode: Respond in **maximum 2 sentences**. "
        "No lists, no bullet points unless explicitly requested. Be extremely concise. "
        "If you cannot fit the answer in 2 sentences, prioritize the single most important point."
    ),
    "Medium": (
        "**Medium** length: 2-4 sentences or 3-4 bullet points. "
        "This is the standard length — balanced between brevity and completeness."
    ),
    "Long": (
        "**Long** mode: Provide a **comprehensive, detailed answer** with 5-8 sentences "
        "or a structured list of 4-6 bullet points. Include context, nuance, and specific "
        "policy details. Go deeper than a surface-level summary. Use subheadings if helpful."
    ),
}

# Language style definitions for prompt injection
LANGUAGE_STYLE_DEFINITIONS: dict[str, str] = {
    "Simple": (
        "STRICT STYLE CONSTRAINT — **Simple** mode: Write for a 16-year-old who has never "
        "followed politics. Use short sentences. No technical jargon — replace terms like "
        "'kvóta', 'paktum', 'szubszidiaritás', 'migrationspakt' with everyday equivalents. "
        "Example: instead of 'migrációs paktum' say 'az EU szabálya arról, hogyan osszák el a menekülteket'."
    ),
    "Normal": (
        "**Normal** communication style: Standard, clear communication suitable for general audiences. "
        "Use common political terms but explain unusual ones briefly."
    ),
    "Expert": (
        "**Expert** mode: Write for a political science audience. Use precise terminology: "
        "'migrációs paktum', 'hatásköri szubszidiaritás', 'dublini rendszer', 'Schengen-övezet'. "
        "Reference specific EU directives, policy frameworks, or legal instruments when relevant. "
        "Assume the reader understands institutional structures and legislative processes."
    ),
    "Unhinged": (
        "**Unhinged** mode: Channel the energy of a late-night political comedy show. "
        "Use vivid metaphors, dramatic analogies, pop culture references, and sharp wit. "
        "Be entertaining and irreverent but NEVER fabricate facts — every claim must still be accurate. "
        "Example tone: 'A TISZA párt úgy kezeli az illegális bevándorlást, mint egy bouncer a beléptetést — "
        "zéró tolerancia, ha nincs a listán, nem jössz be.' Make the reader laugh while they learn."
    ),
}


def get_answer_length_definition(answer_length: str | None) -> str:
    """Get the definition for the selected answer length option."""
    length = answer_length or "Medium"
    return ANSWER_LENGTH_DEFINITIONS.get(length, ANSWER_LENGTH_DEFINITIONS["Medium"])


def get_language_style_definition(language_style: str | None) -> str:
    """Get the definition for the selected language style option."""
    style = language_style or "Normal"
    return LANGUAGE_STYLE_DEFINITIONS.get(style, LANGUAGE_STYLE_DEFINITIONS["Normal"])


def _format_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            item.get("text", str(item)) if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def _format_content_preview(message: AIMessage) -> str:
    text = _format_message_content(getattr(message, "content", ""))
    return text.replace("\n", " ")[:200]


def _language_name_from_state(state: AgentState) -> str:
    """Get language name for queries (prioritizes manifesto language)."""
    if name := state.get("manifesto_language_name"):
        return cast(str, name)
    if name := state.get("response_language_name"):
        return cast(str, name)
    country = state.get("country")
    if country is not None:
        if code := getattr(country, "code", None):
            if match := COUNTRY_LANGUAGE_MAP.get(str(code).upper()):
                return match["name"]
    return "English"


# Maps language *names* to Wikipedia language codes
_LANGUAGE_NAME_TO_WIKI_CODE: dict[str, str] = {
    "deutsch": "de",
    "english": "en",
    "español": "es",
    "magyar": "hu",
    "polski": "pl",
    "nederlands": "nl",
    "norsk": "no",
    "slovenščina": "sl",
    # Also accept English language names
    "german": "de",
    "spanish": "es",
    "hungarian": "hu",
    "polish": "pl",
    "dutch": "nl",
    "norwegian": "no",
    "slovenian": "sl",
}


def _wiki_language_code_from_state(state: AgentState) -> str:
    """Derive a two-letter Wikipedia language code from the agent state."""
    lang_name = _language_name_from_state(state)
    code = _LANGUAGE_NAME_TO_WIKI_CODE.get(lang_name.lower())
    if code:
        return code
    # Fallback: try country code from COUNTRY_LANGUAGE_MAP
    country = state.get("country")
    if country is not None:
        country_code = getattr(country, "code", None)
        if country_code:
            match = COUNTRY_LANGUAGE_MAP.get(str(country_code).upper())
            if match:
                return match["code"]
    return "en"


async def _get_candidate_name_or_fallback(party: "Party") -> str:
    """Get candidate name or fallback if no candidate exists for the party."""
    try:
        candidate = await party.awaitable_attrs.candidate
        if candidate is not None:
            given_name = getattr(candidate, "given_name", "").strip()
            family_name = getattr(candidate, "family_name", "").strip()
            if given_name or family_name:
                return f"{given_name} {family_name}".strip()
    except Exception:
        # Handle any async/database errors gracefully
        pass

    # Fallback: use party name or indicate no candidate
    return f"Representative from {party.shortname}"


class Agent:
    def __init__(
        self,
        vector_database: VectorDatabase,
        *,
        perplexity_client: PerplexityClient | None = None,
    ) -> None:
        self.graph = Agent.get_compiled_agent_graph()
        self.vector_database = vector_database
        self.perplexity_client = perplexity_client

    async def invoke(
        self,
        messages: list[AnyMessage],
        *,
        election: Election,
        selected_parties: list[Party],
        session: AsyncSession,
        use_web_search: bool = False,
        use_vector_database: bool = True,
        use_wikipedia: bool = False,
        language_context: dict[str, Any] | None = None,
        answer_length: str | None = None,
        language_style: str | None = None,
    ) -> AsyncGenerator[AnyChunk]:
        lc_messages = convert_to_lc_message(messages)
        logger.info(
            "Agent invoke start: election=%s, initial_parties=%s, message_count=%s, "
            "answer_length='%s', language_style='%s'",
            election.id,
            [party.shortname for party in selected_parties],
            len(messages),
            answer_length or "None",
            language_style or "None",
        )

        effective_web_search = use_web_search and self.perplexity_client is not None
        if use_web_search and not effective_web_search:
            client_state = "missing" if self.perplexity_client is None else "disabled"
            logger.warning(
                "Web search requested but Perplexity client unavailable (%s); proceeding without web search",
                client_state,
            )

        country = await election.awaitable_attrs.country
        language_ctx = language_context or {}
        fallback_language = COUNTRY_LANGUAGE_MAP.get(
            getattr(country, "code", "").upper(), {"name": "English", "code": "en"}
        )
        response_language_name = (language_ctx.get("selected_language") or {}).get(
            "name"
        ) or fallback_language["name"]
        manifesto_language_name = (language_ctx.get("manifesto_language") or {}).get(
            "name"
        ) or fallback_language["name"]

        chunk_stream = self.graph.astream(
            {
                "messages": lc_messages,
                "country": country,
                "election": election,
                "selected_parties": selected_parties,
                "lock_selected_parties": False,
                "is_comparison_question": False,
                "conversation_title": "",
                "conversation_follow_up_questions": [],
                "party_tag": [],
                "use_web_search": effective_web_search,
                "use_vector_database": use_vector_database,
                "should_use_generic_web_search": False,
                "perplexity_generic_sources": [],
                "perplexity_generic_summary": "",
                "perplexity_comparison_sources": [],
                "perplexity_comparison_summary": "",
                "perplexity_party_sources": {},
                "perplexity_party_summaries": {},
                # Wikipedia search
                "use_wikipedia": use_wikipedia,
                "wikipedia_sources": [],
                "wikipedia_summary": "",
                # Language preferences (names preferred, no backend mapping needed)
                "response_language_name": response_language_name,
                "manifesto_language_name": manifesto_language_name,
                "respond_in_user_language": (
                    language_ctx.get("respond_in_user_language")
                    if language_context
                    else None
                ),
                # Answer formatting preferences
                "answer_length": answer_length,
                "language_style": language_style,
            },
            context={
                "session": session,
                "chat_model": get_openai_model(),
                "vector_database": self.vector_database,
                "perplexity_client": self.perplexity_client,
            },
            stream_mode=["updates", "messages", "custom"],
        )

        return process_lc_stream(chunk_stream)

    @staticmethod
    def get_compiled_agent_graph() -> Pregel[AgentState, AgentContext]:
        """Build and compile the Langgraph agent."""

        async def update_qestion_targets(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            available_parties = await get_missing_party_shortnames(
                runtime.context["session"],
                state["election"],
                state["selected_parties"],
            )
            logger.info(
                "Running party auto-selection for election=%s; available options=%s",
                state["election"].id,
                available_parties,
            )
            prompt_input = {
                "current_party_list": ", ".join(
                    [party.fullname for party in state["selected_parties"]]
                ),
                "additional_party_list": ", ".join(available_parties),
                "messages": state["messages"],
            }
            model = DETERMINE_QUESTION_TARGET | runtime.context[
                "chat_model"
            ].with_structured_output(
                get_full_DetermineQuestionTargetStructuredOutput(
                    await get_parties_enum(
                        runtime.context["session"], state["election"]
                    )
                )
            )

            try:
                selected_parties_response = cast(
                    "DetermineQuestionTargetStructuredOutput",
                    await model.ainvoke(prompt_input),
                )
                logger.info(
                    "Party selection prompt result: %s",
                    selected_parties_response.selected_parties,
                )
            except OpenAIRefusalError as exc:
                logger.warning(
                    "Party selection LLM refused to answer: %s; defaulting to empty party list for generic answer",
                    str(exc),
                )
                # Return empty party list, which will trigger a generic answer instead
                return {"selected_parties": []}

            unique_party_names: list[str] = []
            seen_party_names: set[str] = set()
            for party_name in selected_parties_response.selected_parties:
                if party_name not in seen_party_names:
                    unique_party_names.append(party_name)
                    seen_party_names.add(party_name)

            selected_parties = await get_party_fullname_from_name_list(
                runtime.context["session"], unique_party_names
            )
            logger.info(
                "Auto-selection completed with parties=%s",
                [party.shortname for party in selected_parties],
            )
            return {"selected_parties": selected_parties}

        async def rephrase_question(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            prompt_input = {
                "messages": state["messages"],
                "target_language_name": _language_name_from_state(state),
            }
            model = REPHRASE_QUESTION | runtime.context[
                "chat_model"
            ].with_structured_output(RephraseQuestionStructuredOutput)
            response = cast(
                "RephraseQuestionStructuredOutput",
                await model.ainvoke(prompt_input),
            )

            return {
                "messages": [
                    RemoveMessage(id=state["messages"][-1].id),  # pyright: ignore[reportArgumentType]
                    HumanMessage(
                        id=str(uuid4()),
                        content=response.rephrased_question,
                    ),
                ],
                "is_comparison_question": response.is_comparison_question,
            }

        async def decide_generic_web_search(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            if not state["use_web_search"]:
                return {}

            if runtime.context.get("perplexity_client") is None:
                logger.info(
                    "Perplexity client unavailable; skipping web search decision"
                )
                return {}

            prompt_input = {
                "election_name": state["election"].name,
                "election_year": state["election"].year,
                "response_language_name": state.get("response_language_name")
                or "English",
                "date": date.today().strftime("%B %d, %Y"),
                "messages": state["messages"],
            }
            model = DECIDE_GENERIC_WEB_SEARCH | runtime.context[
                "chat_model"
            ].with_structured_output(GenericWebSearchDecision)
            decision = cast(
                "GenericWebSearchDecision",
                await model.ainvoke(prompt_input),
            )
            logger.info(
                "Generic web search decision: use_web_search=%s reason=%s",
                decision.use_web_search,
                decision.reason,
            )
            return {"should_use_generic_web_search": decision.use_web_search}

        async def perplexity_generic_search(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            if not state["use_web_search"]:
                return {
                    "perplexity_generic_sources": [],
                    "perplexity_generic_summary": "",
                }

            client = runtime.context.get("perplexity_client")
            if client is None:
                logger.info(
                    "Perplexity client unavailable; skipping generic web search"
                )
                return {
                    "perplexity_generic_sources": [],
                    "perplexity_generic_summary": "",
                }

            query_language = _language_name_from_state(state)
            prompt_input = {
                "election_name": state["election"].name,
                "election_year": state["election"].year,
                "query_language": query_language,
                "messages": state["messages"],
                "date": date.today().strftime("%B %d, %Y"),
            }
            try:
                query = await generate_perplexity_query(
                    "PerplexityGenericQuery",
                    PERPLEXITY_GENERIC_QUERY,
                    prompt_input,
                    runtime.context["chat_model"],
                )
            except Exception:  # pragma: no cover - network/LLM errors
                logger.exception("Failed to build Perplexity query for generic flow")
                return {
                    "perplexity_generic_sources": [],
                    "perplexity_generic_summary": "",
                }

            if not query:
                logger.warning(
                    "Empty Perplexity query for generic flow; skipping web search"
                )
                return {
                    "perplexity_generic_sources": [],
                    "perplexity_generic_summary": "",
                }

            latest_user = state["messages"][-1]
            user_question = _format_message_content(getattr(latest_user, "content", ""))
            history_snippets = [
                f"{msg.type.capitalize()}: {_format_message_content(msg.content)}"
                for msg in state["messages"][-4:-1]
            ]
            history_block = "\n".join(history_snippets).strip()
            user_prompt_parts = [
                f"User question:\n{user_question}",
                f"Search query:\n{query}",
            ]
            if history_block:
                user_prompt_parts.append(f"Conversation context:\n{history_block}")
            user_prompt_parts.append(
                "Provide at most four bullet points with the freshest factual findings. "
                "Quote or paraphrase carefully and cite the source URL in parentheses at the end of each bullet."
            )
            system_prompt = (
                "You are a neutral political information assistant with live web search access. "
                "Use authoritative sources, focus on elections and party programmes, and avoid speculation."
            )
            # Run Perplexity and Wikipedia searches in parallel
            wiki_sources: list[WebSource] = []
            wiki_summary = ""
            perplexity_answer = ""
            perplexity_sources: list[WebSource] = []

            async def _do_perplexity() -> None:
                nonlocal perplexity_answer, perplexity_sources
                try:
                    raw_response = await client.create_completion(
                        [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": "\n\n".join(user_prompt_parts)},
                        ],
                        temperature=0.0,
                    )
                except Exception:  # pragma: no cover - network/LLM errors
                    logger.exception("Perplexity generic search request failed")
                    return
                perplexity_answer, perplexity_sources = normalize_perplexity_sources(raw_response)
                logger.info("Perplexity generic search returned %s sources", len(perplexity_sources))

            async def _do_wikipedia() -> None:
                nonlocal wiki_sources, wiki_summary
                wiki_sources, wiki_summary = await _run_wikipedia_search_inline(state, runtime)

            async with TaskGroup() as tg:
                tg.create_task(_do_perplexity())
                tg.create_task(_do_wikipedia())

            if perplexity_sources:
                runtime.stream_writer(
                    PerplexitySourcesChunk(
                        scope="generic",
                        sources=perplexity_sources,
                        summary=perplexity_answer,
                    )
                )

            return {
                "perplexity_generic_sources": perplexity_sources,
                "perplexity_generic_summary": perplexity_answer,
                "wikipedia_sources": wiki_sources,
                "wikipedia_summary": wiki_summary,
            }

        # Hungarian/common stopwords for Wikipedia entity extraction
        _WIKI_STOPWORDS: set[str] = {
            "a", "az", "és", "is", "nem", "hogy", "meg", "van", "volt", "egy",
            "the", "and", "for", "are", "but", "not", "you", "all", "can",
            "mit", "ami", "aki", "ezt", "azt", "más", "csak", "mint", "még",
            "von", "der", "die", "das", "und", "den", "des",
        }

        def _build_follow_up_queries(
            original_query: str,
            results: list,  # list of WikipediaResult
            party_context: str,
            max_queries: int = 2,
        ) -> list[str]:
            """Extract entities from initial Wikipedia results and build targeted follow-up queries."""
            entity_words: set[str] = set()
            for r in results:
                for word in r.title.split():
                    cleaned = word.strip("(),.:;\"'–—-")
                    if len(cleaned) >= 3 and cleaned.lower() not in _WIKI_STOPWORDS:
                        entity_words.add(cleaned)

            # Remove words already in the original query
            original_words = {w.lower() for w in original_query.split()}
            new_entities = [w for w in entity_words if w.lower() not in original_words]

            queries: list[str] = []
            if new_entities:
                queries.append(f"{' '.join(new_entities[:3])} {party_context}".strip())
            if len(new_entities) > 3:
                queries.append(f"{' '.join(new_entities[3:6])} {party_context}".strip())
            return queries[:max_queries]

        async def _rerank_wikipedia_results(
            results: list,  # list of WikipediaResult
            messages: Any,
            chat_model: Any,
            max_results: int = 5,
        ) -> list:
            """Rerank Wikipedia results using LLM. Falls back to original order."""
            from em_backend.agent.prompts.rerank_wikipedia import RERANK_WIKIPEDIA
            from em_backend.agent.prompts.rerank_documents import RerankDocumentsStructuredOutput

            model = RERANK_WIKIPEDIA | chat_model.with_structured_output(
                RerankDocumentsStructuredOutput
            )
            sources_text = "\n".join(
                f"<source>\nIndex: {i}\nTitle: {r.title}\nExtract: {r.extract or r.snippet}\n</source>"
                for i, r in enumerate(results)
            )
            rerank_input = {"sources": sources_text, "messages": messages}

            for attempt in range(2):
                try:
                    response = await model.ainvoke(rerank_input)
                    valid = [
                        idx for idx in response.reranked_doc_indices
                        if isinstance(idx, int) and 0 <= idx < len(results)
                    ]
                    if valid:
                        logger.info(
                            "Wikipedia rerank succeeded: %d→%d results, order=%s",
                            len(results), min(len(valid), max_results), valid[:max_results],
                        )
                        return [results[i] for i in valid][:max_results]
                except Exception as exc:
                    logger.warning("Wikipedia rerank attempt %d failed: %s", attempt + 1, exc)

            logger.info("Wikipedia rerank failed, using original order (top %d)", max_results)
            return results[:max_results]

        async def _run_wikipedia_search_inline(
            state: AgentState,
            runtime: Runtime[AgentContext],
        ) -> tuple[list[WebSource], str]:
            """Iterative Wikipedia search with note-taking and reranking.

            Pipeline: broad search → extract entities → follow-up queries → deduplicate → rerank → return top 5.
            Safe to call from any node — returns empty results on failure or when ``use_wikipedia`` is False.
            """
            if not state.get("use_wikipedia", False):
                return [], ""

            # Build a Wikipedia-friendly search query
            import re
            raw_query = state.get("rephrased_question", "")
            if not raw_query:
                latest_user = state["messages"][-1]
                raw_query = _format_message_content(getattr(latest_user, "content", ""))
            if not raw_query:
                return [], ""

            query = raw_query
            query = re.sub(
                r"^(mi a |mit mondasz |mi a véleményed |mit gondolsz |what is your |what do you think about |"
                r"how do you |tell me about |what are your |milyen a |mi az |hogyan )",
                "", query, flags=re.IGNORECASE,
            )
            query = query.rstrip("?").strip()

            # Build party/election context string
            party_context = ""
            party_obj = state.get("party")
            if party_obj and hasattr(party_obj, "fullname"):
                party_context = party_obj.fullname
                query = f"{query} {party_context}"
            elif "election" in state:
                election = state["election"]
                party_context = f"{getattr(election, 'name', '')} {getattr(election, 'year', '')}"
                query = f"{query} {party_context}"

            wiki_lang = _wiki_language_code_from_state(state)
            client = WikipediaClient(language=wiki_lang)

            try:
                # === ITERATION 1: Broad search ===
                response = await client.search(query, language=wiki_lang, limit=8)
                all_results = list(response.results)
                seen_titles: set[str] = {r.title for r in all_results}

                logger.info(
                    "Wikipedia iter-1: %d results for query=%r lang=%s",
                    len(all_results), query, wiki_lang,
                )

                # === NOTE-TAKING & QUERY EXPANSION ===
                if all_results:
                    follow_up_queries = _build_follow_up_queries(
                        original_query=query,
                        results=all_results,
                        party_context=party_context,
                        max_queries=2,
                    )

                    # === ITERATION 2: Targeted follow-up searches (concurrent, 3s timeout) ===
                    if follow_up_queries:
                        logger.info("Wikipedia iter-2: follow-up queries=%s", follow_up_queries)
                        try:
                            follow_up_responses = await asyncio.wait_for(
                                client.search_multiple(follow_up_queries, language=wiki_lang, limit=5),
                                timeout=3.0,
                            )
                            for resp in follow_up_responses:
                                for result in resp.results:
                                    if result.title not in seen_titles:
                                        seen_titles.add(result.title)
                                        all_results.append(result)
                            logger.info(
                                "Wikipedia iter-2: %d new results (total %d)",
                                len(all_results) - len(response.results), len(all_results),
                            )
                        except asyncio.TimeoutError:
                            logger.warning("Wikipedia iter-2 timed out after 3s, using iter-1 results only")
                        except Exception:
                            logger.exception("Wikipedia iter-2 failed, using iter-1 results only")

                # === RERANK if we have enough candidates ===
                if len(all_results) > 5:
                    chat_model = runtime.context.get("chat_model")
                    if chat_model:
                        all_results = await _rerank_wikipedia_results(
                            all_results, state["messages"], chat_model, max_results=5,
                        )
                    else:
                        all_results = all_results[:5]

            except Exception:
                logger.exception("Wikipedia search failed for query=%r lang=%s", query, wiki_lang)
                return [], ""
            finally:
                try:
                    await client.close()
                except Exception:
                    pass

            if not all_results:
                return [], ""

            # === FORMAT RESULTS ===
            sources: list[WebSource] = []
            summary_parts: list[str] = []
            for result in all_results:
                snippet_text = result.extract or result.snippet
                sources.append({
                    "title": result.title,
                    "url": result.url,
                    "snippet": snippet_text,
                })
                if result.extract:
                    summary_parts.append(f"- {result.title}: {result.extract}")

            summary = "\n".join(summary_parts)

            logger.info(
                "Wikipedia final: %d sources for query=%r lang=%s",
                len(sources), query, wiki_lang,
            )

            if sources:
                runtime.stream_writer(
                    PerplexitySourcesChunk(
                        scope="wikipedia",
                        sources=sources,
                        summary=summary,
                    )
                )

            return sources, summary

        async def _run_party_perplexity_search(
            party: Party,
            state: AgentState,
            runtime: Runtime[AgentContext],
        ) -> tuple[str, list[WebSource]]:
            client = runtime.context.get("perplexity_client")
            if client is None:
                logger.info(
                    "Perplexity client unavailable; skipping comparison search for %s",
                    party.shortname,
                )
                return "", []

            query_language = _language_name_from_state(state)
            prompt_input = {
                "election_name": state["election"].name,
                "election_year": state["election"].year,
                "country_name": getattr(state["country"], "name", "Unknown Country"),
                "party_fullname": party.fullname,
                "party_shortname": party.shortname,
                "query_language": query_language,
                "messages": state["messages"],
                "date": date.today().strftime("%B %d, %Y"),
            }

            try:
                query = await generate_perplexity_query(
                    f"PerplexityComparisonPartyQuery[{party.shortname}]",
                    PERPLEXITY_SINGLE_PARTY_QUERY,
                    prompt_input,
                    runtime.context["chat_model"],
                )
            except Exception:  # pragma: no cover
                logger.exception(
                    "Failed to build Perplexity query for comparison party %s",
                    party.shortname,
                )
                return "", []

            if not query:
                logger.warning(
                    "Empty Perplexity query for comparison party %s; skipping web search",
                    party.shortname,
                )
                return "", []

            latest_user = state["messages"][-1]
            user_question = _format_message_content(getattr(latest_user, "content", ""))
            system_prompt = (
                "You are researching a political party using live web search. "
                "Report concrete commitments or statements from trustworthy media or official sources."
            )
            user_prompt = (
                f"User question:\n{user_question}\n\n"
                f"Party: {party.fullname} ({party.shortname})\n"
                f"Search query:\n{query}\n\n"
                "Provide up to three bullet points with the latest findings about this party. "
                "Cite each bullet with the source URL."
            )

            try:
                raw_response = await client.create_completion(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.0,
                )
            except Exception:  # pragma: no cover
                logger.exception(
                    "Perplexity comparison search request failed for %s",
                    party.shortname,
                )
                return "", []

            answer, sources = normalize_perplexity_sources(raw_response)
            logger.info(
                "Perplexity comparison search returned %s sources for %s",
                len(sources),
                party.shortname,
            )
            return answer, sources

        async def perplexity_comparison_search(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            if not state["use_web_search"]:
                return {
                    "perplexity_party_sources": {},
                    "perplexity_party_summaries": {},
                }

            if not state["selected_parties"]:
                return {
                    "perplexity_party_sources": {},
                    "perplexity_party_summaries": {},
                }

            party_summaries: dict[str, str] = {}
            party_sources: dict[str, list[WebSource]] = {}
            comparison_sources: list[WebSource] = []

            results: dict[str, tuple[str, list[WebSource]]] = {}
            wiki_sources: list[WebSource] = []
            wiki_summary = ""

            async def _do_wikipedia_comparison() -> None:
                nonlocal wiki_sources, wiki_summary
                wiki_sources, wiki_summary = await _run_wikipedia_search_inline(state, runtime)

            async with TaskGroup() as tg:

                async def run_for_party(p: Party) -> None:
                    summary, sources = await _run_party_perplexity_search(
                        p,
                        state,
                        runtime,
                    )
                    results[p.shortname] = (summary, sources)

                for party in state["selected_parties"]:
                    tg.create_task(run_for_party(party))

                # Run Wikipedia search in parallel with Perplexity party searches
                tg.create_task(_do_wikipedia_comparison())

            for party in state["selected_parties"]:
                summary, sources = results.get(party.shortname, ("", []))
                if summary:
                    party_summaries[party.shortname] = summary
                if sources:
                    party_sources[party.shortname] = sources
                    comparison_sources.extend(sources)

            return {
                "perplexity_party_sources": party_sources,
                "perplexity_party_summaries": party_summaries,
                "perplexity_comparison_sources": comparison_sources,
                "perplexity_comparison_summary": "",
                "wikipedia_sources": wiki_sources,
                "wikipedia_summary": wiki_summary,
            }

        async def perplexity_single_party_search(
            state: NonComparisonQuestionState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            if not state["use_web_search"]:
                # Run Wikipedia even if Perplexity web search is disabled
                wiki_sources, wiki_summary = await _run_wikipedia_search_inline(state, runtime)
                updated_state = {**state, "wikipedia_sources": wiki_sources, "wikipedia_summary": wiki_summary}
                answer_result = await generate_single_party_answer(updated_state, runtime)
                return {
                    "messages": answer_result.get("messages", []),
                    "party_tag": answer_result.get("party_tag", [state["party"]]),
                    "wikipedia_sources": wiki_sources,
                    "wikipedia_summary": wiki_summary,
                }

            client = runtime.context.get("perplexity_client")
            if client is None:
                logger.info(
                    "Perplexity client unavailable; skipping web search for party %s",
                    state["party"].shortname,
                )
                # Run Wikipedia even without Perplexity
                wiki_sources, wiki_summary = await _run_wikipedia_search_inline(state, runtime)
                updated_state = {**state, "wikipedia_sources": wiki_sources, "wikipedia_summary": wiki_summary}
                answer_result = await generate_single_party_answer(updated_state, runtime)
                return {
                    "messages": answer_result.get("messages", []),
                    "party_tag": answer_result.get("party_tag", [state["party"]]),
                    "wikipedia_sources": wiki_sources,
                    "wikipedia_summary": wiki_summary,
                }

            query_language = _language_name_from_state(state)
            prompt_input = {
                "election_name": state["election"].name,
                "election_year": state["election"].year,
                "country_name": getattr(state["country"], "name", "Unknown Country"),
                "party_fullname": state["party"].fullname,
                "party_shortname": state["party"].shortname,
                "query_language": query_language,
                "messages": state["messages"],
                "date": date.today().strftime("%B %d, %Y"),
            }
            try:
                query = await generate_perplexity_query(
                    f"PerplexitySinglePartyQuery[{state['party'].shortname}]",
                    PERPLEXITY_SINGLE_PARTY_QUERY,
                    prompt_input,
                    runtime.context["chat_model"],
                )
            except Exception:  # pragma: no cover
                logger.exception(
                    "Failed to build Perplexity query for party %s",
                    state["party"].shortname,
                )
                # Proceed to answer generation without web sources
                answer_result = await generate_single_party_answer(state, runtime)
                return {
                    "messages": answer_result.get("messages", []),
                    "party_tag": answer_result.get("party_tag", [state["party"]]),
                }

            if not query:
                logger.warning(
                    "Empty Perplexity query for party %s; skipping web search",
                    state["party"].shortname,
                )
                # Proceed to answer generation without web sources
                answer_result = await generate_single_party_answer(state, runtime)
                return {
                    "messages": answer_result.get("messages", []),
                    "party_tag": answer_result.get("party_tag", [state["party"]]),
                }

            latest_user = state["messages"][-1]
            user_question = _format_message_content(getattr(latest_user, "content", ""))
            system_prompt = (
                "You are researching a political party using live web search. "
                "Report concrete commitments or statements from trustworthy media or official sources."
            )
            user_prompt = (
                f"User question:\n{user_question}\n\n"
                f"Party: {state['party'].fullname} ({state['party'].shortname})\n"
                f"Search query:\n{query}\n\n"
                "Provide up to three bullet points with the latest findings about this party. "
                "Cite each bullet with the source URL."
            )

            # Run Perplexity and Wikipedia in parallel
            perplexity_answer = ""
            perplexity_sources: list[WebSource] = []
            wiki_sources: list[WebSource] = []
            wiki_summary = ""
            perplexity_failed = False

            async def _do_perplexity_single() -> None:
                nonlocal perplexity_answer, perplexity_sources, perplexity_failed
                try:
                    raw_response = await client.create_completion(
                        [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.0,
                    )
                except Exception:  # pragma: no cover
                    logger.exception(
                        "Perplexity single-party search failed for %s",
                        state["party"].shortname,
                    )
                    perplexity_failed = True
                    return
                perplexity_answer, perplexity_sources = normalize_perplexity_sources(raw_response)
                logger.info(
                    "Perplexity party search returned %s sources for %s",
                    len(perplexity_sources),
                    state["party"].shortname,
                )

            async def _do_wikipedia_single() -> None:
                nonlocal wiki_sources, wiki_summary
                wiki_sources, wiki_summary = await _run_wikipedia_search_inline(state, runtime)

            async with TaskGroup() as tg:
                tg.create_task(_do_perplexity_single())
                tg.create_task(_do_wikipedia_single())

            if perplexity_failed and not wiki_sources:
                # Both failed or Perplexity failed with no Wikipedia fallback
                answer_result = await generate_single_party_answer(state, runtime)
                return {
                    "messages": answer_result.get("messages", []),
                    "party_tag": answer_result.get("party_tag", [state["party"]]),
                }

            # Update the shared state with this party's sources
            updated_sources = dict(state["perplexity_party_sources"])
            updated_sources[state["party"].shortname] = perplexity_sources
            updated_summaries = dict(state["perplexity_party_summaries"])
            updated_summaries[state["party"].shortname] = perplexity_answer

            # Create updated state for this party's answer generation
            updated_state = {
                **state,
                "perplexity_party_sources": updated_sources,
                "perplexity_party_summaries": updated_summaries,
                "wikipedia_sources": wiki_sources,
                "wikipedia_summary": wiki_summary,
            }

            # Directly call generate_single_party_answer to avoid state merging issues
            answer_result = await generate_single_party_answer(updated_state, runtime)

            # Return the answer result along with the sources for LangGraph streaming
            return {
                "perplexity_party_sources": updated_sources,
                "perplexity_party_summaries": updated_summaries,
                "wikipedia_sources": wiki_sources,
                "wikipedia_summary": wiki_summary,
                "messages": answer_result.get("messages", []),
                "party_tag": answer_result.get("party_tag", [state["party"]]),
            }

        def route_after_rephrase(
            state: AgentState,
        ) -> (
            list[Send]
            | Literal[
                "decide_generic_web_search",
                "generate_generic_answer",
                "perplexity_comparison_search",
                "generate_comparison_answer",
                "perplexity_single_party_search",
                "generate_single_party_answer",
            ]
        ):
            def _single_party_payload(party: Party) -> dict[str, Any]:
                return {
                    "messages": state["messages"],
                    "country": state["country"],
                    "election": state["election"],
                    "party": party,
                    "use_web_search": state["use_web_search"],
                    "use_vector_database": state["use_vector_database"],
                    "response_language_name": state.get("response_language_name"),
                    "manifesto_language_name": state.get("manifesto_language_name"),
                    "respond_in_user_language": state.get("respond_in_user_language"),
                    "is_comparison_question": state["is_comparison_question"],
                    "lock_selected_parties": state["lock_selected_parties"],
                    "conversation_title": state["conversation_title"],
                    "conversation_follow_up_questions": state[
                        "conversation_follow_up_questions"
                    ],
                    "selected_parties": state["selected_parties"],
                    "should_use_generic_web_search": state[
                        "should_use_generic_web_search"
                    ],
                    "perplexity_generic_sources": state["perplexity_generic_sources"],
                    "perplexity_generic_summary": state["perplexity_generic_summary"],
                    "perplexity_comparison_sources": state[
                        "perplexity_comparison_sources"
                    ],
                    "perplexity_comparison_summary": state[
                        "perplexity_comparison_summary"
                    ],
                    "perplexity_party_sources": state["perplexity_party_sources"],
                    "perplexity_party_summaries": state["perplexity_party_summaries"],
                    "party_tag": state["party_tag"],
                    "use_wikipedia": state.get("use_wikipedia", False),
                    "wikipedia_sources": state.get("wikipedia_sources", []),
                    "wikipedia_summary": state.get("wikipedia_summary", ""),
                }

            if not state["selected_parties"]:
                if state["use_web_search"]:
                    logger.info(
                        "Routing to generic web search decision (no parties selected)"
                    )
                    return "decide_generic_web_search"
                logger.info("Routing directly to generic answer (web search disabled)")
                return "generate_generic_answer"

            if state["is_comparison_question"] and len(state["selected_parties"]) > 1:
                if state["use_web_search"]:
                    logger.info(
                        "Routing to comparison web search for parties=%s",
                        [party.shortname for party in state["selected_parties"]],
                    )
                    return "perplexity_comparison_search"
                logger.info(
                    "Routing to comparison answer for parties=%s",
                    [party.shortname for party in state["selected_parties"]],
                )
                return "generate_comparison_answer"

            target_node = (
                "perplexity_single_party_search"
                if state["use_web_search"]
                else "generate_single_party_answer"
            )
            logger.info(
                "Routing to single-party flow (%s) for parties=%s",
                target_node,
                [party.shortname for party in state["selected_parties"]],
            )
            payloads = []
            for party in state["selected_parties"]:
                payload = _single_party_payload(party)
                payload["party"] = party
                payloads.append(Send(target_node, payload))
            return payloads

        def route_after_generic_decision(
            state: AgentState,
        ) -> Literal["perplexity_generic_search", "generate_generic_answer"]:
            if state["use_web_search"] and state["should_use_generic_web_search"]:
                logger.info("Decision: run generic web search before answering")
                return "perplexity_generic_search"
            logger.info("Decision: skip web search and answer generically")
            return "generate_generic_answer"

        async def generate_generic_answer(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            logger.info("Generating generic answer with no party context")
            election = state["election"]
            # Build a lightweight parties overview for context
            try:
                parties = await election.awaitable_attrs.parties
            except Exception:  # pragma: no cover - defensive in case of lazy loading
                parties = []
            parties_overview = (
                "\n".join(
                    [
                        f"- {p.shortname} ({p.fullname})"
                        for p in parties
                        if getattr(p, "shortname", None)
                        and getattr(p, "fullname", None)
                    ]
                )
                or "(Keine Parteien geladen)"
            )

            project_about = (
                "Open Democracy is an open research project (Open Source, Non Profit) focused on political information and elections. "
                "Developed by Open Democracy, our aim is to provide citizens with clear, neutral content, in reserch collaboration with researchers from ETH Zurich. "
                "If you would like to contact a member of the team, please email info@opendemocracy.ai. "
                "To learn more about our pipeline and how the algorithms work, please visit the About Us page, where you will find a 'How it Works' button and detailed documentation about our algorithms. "
                "If a previous question has already been answered by the assistant, it will not be answered again unless the user specifically requests it."
            )

            latest_user_message = ""
            for msg in reversed(state["messages"]):
                if getattr(msg, "type", None) == "human":
                    latest_user_message = _format_message_content(
                        getattr(msg, "content", "")
                    )
                    break

            # Run Wikipedia if not already done (path that skips Perplexity)
            wiki_sources = state.get("wikipedia_sources", [])
            wiki_summary = state.get("wikipedia_summary", "")
            if not wiki_sources and state.get("use_wikipedia", False):
                wiki_sources, wiki_summary = await _run_wikipedia_search_inline(state, runtime)

            generic_sources = state.get("perplexity_generic_sources", [])
            # Combine Perplexity + Wikipedia sources
            combined_sources = [*generic_sources, *wiki_sources]
            web_summary = (
                state.get("perplexity_generic_summary", "") if generic_sources else ""
            )
            if wiki_summary:
                web_summary = f"{web_summary}\n\n{wiki_summary}".strip() if web_summary else wiki_summary
            web_sources_block = (
                format_web_sources_for_prompt(combined_sources)
                if combined_sources
                else ""
            )
            web_search_enabled = bool(combined_sources)

            model = GENERIC_ANSWER | runtime.context["chat_model"]
            prompt_input = {
                "election_name": election.name,
                "election_year": election.year,
                "election_date": election.date.strftime("%B %d, %Y"),
                "election_url": election.url,
                "parties_overview": parties_overview,
                "project_about": project_about,
                "date": date.today().strftime("%B %d, %Y"),
                "web_search_enabled": web_search_enabled,
                "web_summary": web_summary,
                "web_sources": web_sources_block,
                "latest_user_message": latest_user_message,
                "messages": state["messages"],
                "answer_length_definition": get_answer_length_definition(state.get("answer_length")),
                "language_style_definition": get_language_style_definition(state.get("language_style")),
            }
            # Use streaming for real-time token updates
            response_stream = model.astream(
                prompt_input,
                config={"tags": ["stream", "generic"]},
            )

            # Collect the complete response while streaming tokens
            complete_response = None
            async for token in response_stream:
                complete_response = token

            if complete_response is None:
                raise ValueError("No response received from model")

            logger.info(
                "✅ Chat response (generic) preview: %s",
                _format_content_preview(complete_response),
            )
            return {"messages": [complete_response]}

        async def generate_comparison_answer(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            logger.info(
                "Generating comparison answer for parties=%s",
                [party.shortname for party in state["selected_parties"]],
            )
            documents: dict[str, list[DocumentChunk]] = {
                party.shortname: [] for party in state["selected_parties"]
            }

            if state["use_vector_database"]:

                async def add_documents(party: Party) -> None:
                    documents[
                        party.shortname
                    ] = await retrieve_documents_from_user_question(
                        state["messages"],
                        state["election"],
                        party,
                        runtime.context["chat_model"],
                        runtime.context["vector_database"],
                        manifesto_language_name=state.get("manifesto_language_name"),
                    )

                async with TaskGroup() as tg:
                    for party in state["selected_parties"]:
                        tg.create_task(add_documents(party))

                runtime.stream_writer(ComparisonSourcesChunk(documents=documents))
            else:
                logger.info(
                    "Vector database disabled; skipping RAG retrieval for comparison answer"
                )

            vector_web_sources: list[WebSource] = []
            for party in state["selected_parties"]:
                vector_web_sources.extend(
                    convert_documents_to_web_sources(
                        documents.get(party.shortname, []),
                        party=party.shortname,
                        fallback_url=party.url or state["election"].url,
                    )
                )

            # Run Wikipedia if not already done (path that skips Perplexity)
            wiki_sources = state.get("wikipedia_sources", [])
            wiki_summary_text = state.get("wikipedia_summary", "")
            if not wiki_sources and state.get("use_wikipedia", False):
                wiki_sources, wiki_summary_text = await _run_wikipedia_search_inline(state, runtime)

            perplexity_sources = state.get("perplexity_comparison_sources", [])
            combined_web_sources = [*perplexity_sources, *vector_web_sources, *wiki_sources]
            web_summary = state.get("perplexity_comparison_summary", "")
            if wiki_summary_text:
                web_summary = f"{web_summary}\n\n{wiki_summary_text}".strip() if web_summary else wiki_summary_text
            if not web_summary and vector_web_sources:
                first_snippet = vector_web_sources[0].get("snippet", "") or ""
                if first_snippet:
                    web_summary = textwrap.shorten(
                        first_snippet, width=200, placeholder="…"
                    )

            if combined_web_sources:
                runtime.stream_writer(
                    PerplexitySourcesChunk(
                        scope="comparison",
                        sources=combined_web_sources,
                        summary=web_summary,
                    )
                )

            for party in state["selected_parties"]:
                party_sources = [
                    source
                    for source in combined_web_sources
                    if source.get("party") == party.shortname
                ]
                if party_sources:
                    runtime.stream_writer(
                        PerplexitySourcesChunk(
                            scope="party",
                            party=party.shortname,
                            sources=party_sources,
                            summary=state["perplexity_party_summaries"].get(
                                party.shortname, ""
                            ),
                        )
                    )

            web_sources_block = format_party_web_sources_for_prompt(
                state["selected_parties"],
                combined_web_sources,
                state["perplexity_party_summaries"],
            )
            web_search_enabled = bool(combined_web_sources)

            model = COMPARISON_PARTY_ANSWER | runtime.context["chat_model"]
            parties_data = "\n".join(
                [
                    "<party>"
                    f"Abbreviation: {party.shortname}\n"
                    f"Full name: {party.fullname}\n"
                    f"Description: {party.description}\n"
                    f"Top Candidate: "
                    f"{await _get_candidate_name_or_fallback(party)}\n"
                    f"Website: {party.url}\n"
                    f"### Party Documents\n"
                    + "\n".join(
                        [
                            "<document>\n"
                            f"Source ID: {doc.get('chunk_id', '')}\n"
                            f"Title: {doc['title']}\n"
                            f"Page number: {doc.get('page_number', 'unknown')}\n"
                            f"Text: {doc['text']}\n"
                            "</document>"
                            for doc in documents[party.shortname]
                        ]
                    )
                    + "</party>"
                    for party in state["selected_parties"]
                ]
            )

            latest_user_message = ""
            for msg in reversed(state["messages"]):
                if getattr(msg, "type", None) == "human":
                    latest_user_message = _format_message_content(
                        getattr(msg, "content", "")
                    )
                    break

            prompt_input = {
                "election_name": state["election"].name,
                "election_year": state["election"].year,
                "election_date": state["election"].date.strftime("%B %d, %Y"),
                "date": date.today().strftime("%B %d, %Y"),
                "selected_parties": ", ".join(
                    f"{party.shortname} ({party.fullname})"
                    for party in state["selected_parties"]
                ),
                "parties_being_compared": ", ".join(
                    f"{party.shortname}" for party in state["selected_parties"]
                ),
                "parties_data": parties_data,
                "web_search_enabled": web_search_enabled,
                "web_summary": web_summary,
                "web_sources": web_sources_block,
                "latest_user_message": latest_user_message,
                "messages": state["messages"],
                "election_url": state["election"].url,
                "answer_length_definition": get_answer_length_definition(state.get("answer_length")),
                "language_style_definition": get_language_style_definition(state.get("language_style")),
            }
            # Use streaming for real-time token updates
            response_stream = model.astream(
                prompt_input,
                config={"tags": ["stream", "comparison"]},
            )

            # Collect the complete response while streaming tokens
            complete_response = None
            async for token in response_stream:
                complete_response = token

            if complete_response is None:
                raise ValueError("No response received from model")

            logger.info(
                "✅ Chat response (comparison) preview: %s",
                _format_content_preview(complete_response),
            )
            return {"messages": [complete_response]}

        async def generate_single_party_answer(
            state: NonComparisonQuestionState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            logger.info(
                "Generating single-party answer for party=%s",
                state["party"].shortname,
            )
            documents: list[DocumentChunk] = []
            if state["use_vector_database"]:
                documents = await retrieve_documents_from_user_question(
                    state["messages"],
                    state["election"],
                    state["party"],
                    runtime.context["chat_model"],
                    runtime.context["vector_database"],
                    manifesto_language_name=state.get("manifesto_language_name"),
                )
                runtime.stream_writer(
                    PartySourcesChunk(
                        party=state["party"].shortname, documents=documents
                    )
                )
            else:
                logger.info(
                    "Vector database disabled; skipping RAG retrieval for party %s",
                    state["party"].shortname,
                )

            party_key = state["party"].shortname
            web_summary = state.get("perplexity_party_summaries", {}).get(party_key, "")
            party_web_sources = state.get("perplexity_party_sources", {}).get(
                party_key, []
            )
            vector_web_sources: list[WebSource] = convert_documents_to_web_sources(
                documents,
                party=party_key,
                fallback_url=state["party"].url or state["election"].url,
            )

            # Include Wikipedia sources
            wiki_sources = state.get("wikipedia_sources", [])
            wiki_summary_text = state.get("wikipedia_summary", "")

            combined_web_sources = [*party_web_sources, *vector_web_sources, *wiki_sources]
            if wiki_summary_text:
                web_summary = f"{web_summary}\n\n{wiki_summary_text}".strip() if web_summary else wiki_summary_text
            if not web_summary and vector_web_sources:
                first_snippet = vector_web_sources[0].get("snippet", "") or ""
                if first_snippet:
                    web_summary = textwrap.shorten(
                        first_snippet, width=180, placeholder="…"
                    )
                else:
                    web_summary = "Context extracted from party documents."

            if combined_web_sources:
                runtime.stream_writer(
                    PerplexitySourcesChunk(
                        scope="party",
                        party=party_key,
                        sources=combined_web_sources,
                        summary=web_summary,
                    )
                )

            web_sources_block = format_web_sources_for_prompt(combined_web_sources)
            web_search_enabled = bool(combined_web_sources)

            model = SINGLE_PARTY_ANSWER | runtime.context["chat_model"]
            party_candidate_name = await _get_candidate_name_or_fallback(state["party"])
            latest_user_message = ""
            for msg in reversed(state["messages"]):
                if getattr(msg, "type", None) == "human":
                    latest_user_message = _format_message_content(
                        getattr(msg, "content", "")
                    )
                    break

            prompt_input = {
                "election_name": state["election"].name,
                "election_year": state["election"].year,
                "election_date": state["election"].date.strftime("%B %d, %Y"),
                "election_url": state["election"].url,
                "date": date.today().strftime("%B %d, %Y"),
                "party_name": state["party"].shortname,
                "party_fullname": state["party"].fullname,
                "party_description": state["party"].description,
                "party_url": state["party"].url,
                "party_candidate": party_candidate_name,
                "sources": "\n".join(
                    [
                        "<document>\n"
                        f"index: {i}\n"
                        f"# {doc['title']}\n"
                        f"{doc['text']}\n"
                        "</document>"
                        for i, doc in enumerate(documents)
                    ]
                ),
                "web_search_enabled": web_search_enabled,
                "web_summary": web_summary,
                "web_sources": web_sources_block,
                "latest_user_message": latest_user_message,
                "messages": state["messages"],
                "answer_length_definition": get_answer_length_definition(state.get("answer_length")),
                "language_style_definition": get_language_style_definition(state.get("language_style")),
            }
            try:
                # Use streaming for real-time token updates
                response_stream = model.astream(
                    prompt_input,
                    config={"tags": ["stream", f"party_{state['party'].shortname}"]},
                )

                # Collect the complete response while streaming tokens
                complete_response = None
                async for token in response_stream:
                    complete_response = token

                if complete_response is None:
                    raise ValueError("No response received from model")

                logger.info(
                    "✅ Chat response (party=%s) preview: %s",
                    state["party"].shortname,
                    _format_content_preview(complete_response),
                )
            except OpenAIRefusalError as exc:
                logger.warning(
                    "LLM refused to answer for party %s: %s",
                    state["party"].shortname,
                    exc,
                )
                complete_response = AIMessage(
                    content=(
                        "I could not find enough context to answer this question right now. "
                        "Please try rephrasing or ask about another topic."
                    )
                )
            except Exception:  # pragma: no cover - defensive
                logger.exception(
                    "Unexpected error while generating single party answer for %s",
                    state["party"].shortname,
                )
                complete_response = AIMessage(
                    content=(
                        "Sorry, I ran into an internal issue while gathering the answer. "
                        "Please try again in a moment."
                    )
                )
            return {"messages": [complete_response], "party_tag": [state["party"]]}

        async def generate_title_and_replies(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            logger.info(
                "Generating title and follow-ups; final parties=%s",
                [party.shortname for party in state["selected_parties"]],
            )
            model = GENERATE_TITLE_AND_REPLIES | runtime.context[
                "chat_model"
            ].with_structured_output(GenerateTitleAndRepliedStructuredOutput)
            prompt_input = {
                "party_list": ", ".join(
                    f"{party.shortname} ({party.fullname})"
                    for party in state["selected_parties"]
                ),
                "messages": state["messages"],
            }
            response = cast(
                "GenerateTitleAndRepliedStructuredOutput",
                await model.ainvoke(prompt_input),
            )
            return {
                "conversation_title": response.conversation_title,
                "conversation_follow_up_questions": [
                    response.follow_up_one,
                    response.follow_up_two,
                    response.follow_up_three,
                ],
            }

        workflow = StateGraph(AgentState, AgentContext)

        workflow.set_entry_point("update_qestion_targets")
        workflow.add_node("update_qestion_targets", update_qestion_targets)
        workflow.add_edge("update_qestion_targets", "rephrase_question")
        workflow.add_node("rephrase_question", rephrase_question)
        workflow.add_node("decide_generic_web_search", decide_generic_web_search)
        workflow.add_node("perplexity_generic_search", perplexity_generic_search)
        workflow.add_node("perplexity_comparison_search", perplexity_comparison_search)
        workflow.add_node(
            "perplexity_single_party_search", perplexity_single_party_search
        )
        workflow.add_conditional_edges(
            "rephrase_question",
            route_after_rephrase,
            [
                "decide_generic_web_search",
                "generate_generic_answer",
                "perplexity_comparison_search",
                "generate_comparison_answer",
                "perplexity_single_party_search",
                "generate_single_party_answer",
            ],
        )
        workflow.add_conditional_edges(
            "decide_generic_web_search",
            route_after_generic_decision,
            ["perplexity_generic_search", "generate_generic_answer"],
        )
        workflow.add_node("generate_generic_answer", generate_generic_answer)
        workflow.add_node("generate_comparison_answer", generate_comparison_answer)
        workflow.add_node("generate_single_party_answer", generate_single_party_answer)
        workflow.add_edge("perplexity_generic_search", "generate_generic_answer")
        workflow.add_edge("perplexity_comparison_search", "generate_comparison_answer")
        # Note: perplexity_single_party_search directly calls generate_single_party_answer
        # to avoid LangGraph state merging issues with concurrent Send tasks
        workflow.add_edge(
            "perplexity_single_party_search", "generate_title_and_replies"
        )
        workflow.add_edge("generate_generic_answer", "generate_title_and_replies")
        workflow.add_edge("generate_comparison_answer", "generate_title_and_replies")
        workflow.add_edge("generate_single_party_answer", "generate_title_and_replies")
        workflow.add_node("generate_title_and_replies", generate_title_and_replies)
        workflow.set_finish_point("generate_title_and_replies")

        return workflow.compile()
