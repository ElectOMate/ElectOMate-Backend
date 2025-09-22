from asyncio import TaskGroup
from collections.abc import AsyncGenerator
from datetime import date
from typing import Any, Literal, cast
from uuid import uuid4

from langchain_core.messages import (
    HumanMessage,
    RemoveMessage,
)
from langgraph.graph import StateGraph
from langgraph.pregel import Pregel
from langgraph.runtime import Runtime
from langgraph.types import Send
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.agent.prompts.comparison_party_answer import COMPARISON_PARTY_ANSWER
from em_backend.agent.prompts.generate_title_and_replies import (
    GENERATE_TITLE_AND_REPLIES,
    GenerateTitleAndRepliedStructuredOutput,
)
from em_backend.agent.prompts.rephrase_question import (
    REPHRASE_QUESTION,
    RephraseQuestionStructuredOutput,
)
from em_backend.agent.prompts.single_party_answer import SINGLE_PARTY_ANSWER
from em_backend.agent.prompts.update_question_targets import (
    DETERMINE_QUESTION_TARGET,
    DetermineQuestionTargetStructuredOutput,
)
from em_backend.agent.types import AgentContext, AgentState, NonComparisonQuestionState
from em_backend.agent.utils import (
    convert_to_lc_message,
    process_lc_stream,
    retrieve_documents_from_user_question,
)
from em_backend.database.models import Election, Party
from em_backend.database.utils import get_missing_party_shortnames
from em_backend.llm.openai import get_openai_model
from em_backend.models.chunks import (
    AnyChunk,
    ComparisonSourcesChunk,
    PartySourcesChunk,
)
from em_backend.models.messages import AnyMessage
from em_backend.vector.db import DocumentChunk, VectorDatabase


class Agent:
    def __init__(self, vector_database: VectorDatabase) -> None:
        self.graph = Agent.get_compiled_agent_graph()
        self.vector_database = vector_database

    def invoke(
        self,
        messages: list[AnyMessage],
        *,
        election: Election,
        selected_parties: list[Party],
        session: AsyncSession,
    ) -> AsyncGenerator[AnyChunk]:
        lc_messages = convert_to_lc_message(messages)

        chunk_stream = self.graph.astream(
            {
                "messages": lc_messages,
                "country": election.country,
                "election": election,
                "selected_parties": selected_parties,
                "is_comparison_question": False,
                "conversation_title": "",
                "conversation_follow_up_questions": [],
            },
            context={
                "session": session,
                "chat_model": get_openai_model(with_proxy=True),
                "vector_database": self.vector_database,
            },
            stream_mode=["updates", "messages", "custom"],
        )

        return process_lc_stream(chunk_stream)

    @staticmethod
    def get_compiled_agent_graph() -> Pregel[AgentState, AgentContext]:
        async def update_qestion_targets(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            available_parties = await get_missing_party_shortnames(
                runtime.context["session"],
                state["election"],
                state["selected_parties"],
            )
            model = DETERMINE_QUESTION_TARGET | runtime.context[
                "chat_model"
            ].with_structured_output(DetermineQuestionTargetStructuredOutput)
            selected_parties_response = cast(
                "DetermineQuestionTargetStructuredOutput",
                await model.ainvoke(
                    {
                        "current_party_list": ", ".join(
                            [party.fullname for party in state["selected_parties"]]
                        ),
                        "additional_party_list": ", ".join(available_parties),
                        "messages": state["messages"],
                    }
                ),
            )
            return {"selected_parties": selected_parties_response.selected_parties}

        async def rephrase_question(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            model = REPHRASE_QUESTION | runtime.context[
                "chat_model"
            ].with_structured_output(RephraseQuestionStructuredOutput)
            response = cast(
                "RephraseQuestionStructuredOutput",
                await model.ainvoke({"messages": state["messages"]}),
            )

            return {
                "messages": [
                    RemoveMessage(id=state["messages"][-1].id),  # pyright: ignore[reportArgumentType]
                    HumanMessage(
                        id=uuid4(),
                        content=response.rephrased_question,
                    ),
                ],
                "is_comparison_question": response.is_comparison_question,
            }

        def route_answer_generation(
            state: AgentState,
        ) -> list[Send] | Literal["generate_comparison_answer"]:
            if state["is_comparison_question"] and len(state["selected_parties"]) > 1:
                return "generate_comparison_answer"
            else:
                return [
                    Send(
                        "generate_single_party_answer",
                        {
                            "messages": state["messages"],
                            "country": state["country"],
                            "election": state["election"],
                            "party": party,
                        },
                    )
                    for party in state["selected_parties"]
                ]

        async def generate_comparison_answer(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            documents: dict[str, list[DocumentChunk]] = {}

            async def add_documents(party: Party) -> None:
                documents[
                    party.shortname
                ] = await retrieve_documents_from_user_question(
                    state["messages"],
                    state["election"],
                    party,
                    runtime.context["chat_model"],
                    runtime.context["vector_database"],
                )

            async with TaskGroup() as tg:
                for party in state["selected_parties"]:
                    tg.create_task(add_documents(party))

            runtime.stream_writer(ComparisonSourcesChunk(documents=documents))

            model = COMPARISON_PARTY_ANSWER | runtime.context["chat_model"].bind(
                tags=(runtime.context["chat_model"].tags or []) + ["stream"]
            )
            parties_data = "\n".join(
                [
                    "<party>"
                    f"Abbreviation: {party.shortname}\n"
                    f"Full name: {party.fullname}\n"
                    f"Description: {party.description}\n"
                    f"Top Candidate: {party.candidate.given_name} "
                    "{party.candidate.family_name}\n"
                    f"Website: {party.url}\n"
                    f"### Party Documents\n"
                    + "\n".join(
                        [
                            "<document>\n"
                            f"Title: {doc['title']}\n"
                            f"Text: {doc['text']}\n"
                            "</document>"
                            for doc in documents[party.shortname]
                        ]
                    )
                    + "</party>"
                    for party in state["selected_parties"]
                ]
            )
            response = await model.ainvoke(
                {
                    "election_name": state["election"].name,
                    "election_year": state["election"].year,
                    "election_date": state["election"].date.strftime("%B %d, %Y"),
                    "date": date.today().strftime("%B %d, %Y"),
                    "selected_parties": ", ".join(
                        f"{party.shortname} ({party.fullname})"
                        for party in state["selected_parties"]
                    ),
                    "parties_data": parties_data,
                    "messages": state["messages"],
                }
            )
            return {"messages": [response]}

        async def generate_single_party_answer(
            state: NonComparisonQuestionState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            documents = await retrieve_documents_from_user_question(
                state["messages"],
                state["election"],
                state["party"],
                runtime.context["chat_model"],
                runtime.context["vector_database"],
            )
            runtime.stream_writer(
                PartySourcesChunk(party=state["party"].shortname, documents=documents)
            )
            model = SINGLE_PARTY_ANSWER | runtime.context["chat_model"].bind(
                tags=(runtime.context["chat_model"].tags or [])
                + ["stream", f"party_f{state['party'].shortname}"]
            )
            response = await model.ainvoke(
                {
                    "election_name": state["election"].name,
                    "election_year": state["election"].year,
                    "election_date": state["election"].date.strftime("%B %d, %Y"),
                    "date": date.today().strftime("%B %d, %Y"),
                    "party_name": state["party"].shortname,
                    "party_fullname": state["party"].fullname,
                    "party_description": state["party"].description,
                    "party_url": state["party"].url,
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
                    "messages": state["messages"],
                }
            )
            return {"messages": [response], "party": state["party"]}

        async def generate_title_and_replies(
            state: AgentState, runtime: Runtime[AgentContext]
        ) -> dict[str, Any]:
            model = GENERATE_TITLE_AND_REPLIES | runtime.context[
                "chat_model"
            ].with_structured_output(GenerateTitleAndRepliedStructuredOutput)
            response = cast(
                "GenerateTitleAndRepliedStructuredOutput",
                await model.ainvoke(
                    {
                        "party_list": ", ".join(
                            f"{party.shortname} ({party.fullname})"
                            for party in state["selected_parties"]
                        ),
                        "messages": state["messages"],
                    }
                ),
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
        workflow.add_conditional_edges(
            "rephrase_question",
            route_answer_generation,
            ["generate_comparison_answer", "generate_comparison_answer"],
        )
        workflow.add_node("generate_comparison_answer", generate_comparison_answer)
        workflow.add_node("generate_single_party_answer", generate_single_party_answer)
        workflow.add_edge("generate_comparison_answer", "generate_title_and_replies")
        workflow.add_edge("generate_single_party_answer", "generate_title_and_replies")
        workflow.add_node("generate_title_and_replies", generate_title_and_replies)
        workflow.set_finish_point("generate_title_and_replies")

        return workflow.compile()
