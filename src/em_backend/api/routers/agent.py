from collections.abc import AsyncGenerator
import logging
from typing import Annotated
from uuid import UUID

from aiostream import streamcontext
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import AfterValidator, BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from em_backend.agent.agent import Agent
from em_backend.api.routers.v2 import get_agent, get_database_session, get_sessionmaker
from em_backend.database.utils import (
    get_election_from_election_id,
    get_missing_party_shortnames,
    get_party_from_name_list,
)
from em_backend.models.messages import AnyMessage


logger = logging.getLogger(__name__)

agent_router = APIRouter(tags=["agent"])


def last_message_is_user(value: list[AnyMessage]) -> list[AnyMessage]:
    if value[-1].type != "user":
        raise ValueError("Last message should be user message")
    return value


class AgentChatRequest(BaseModel):
    messages: Annotated[
        list[AnyMessage], AfterValidator(last_message_is_user), Field(min_length=1)
    ]

    election_id: UUID
    selected_parties: list[str]

    use_vector_database: bool
    use_web_search: bool


@agent_router.post("/chat")
async def agent_chat(
    chat_request: AgentChatRequest,
    agent: Annotated[Agent, Depends(get_agent)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    # We need the sessionmaker as we need to open a new db session for execution
    # As the dependency injection one gets closed when we return the StreamingResponse
    session_maker: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_sessionmaker)
    ],
) -> StreamingResponse:
    logger.info(
        "Received agent chat request: election_id=%s, message_count=%s, selected_parties=%s, "
        "use_vector_database=%s, use_web_search=%s",
        chat_request.election_id,
        len(chat_request.messages),
        chat_request.selected_parties,
        chat_request.use_vector_database,
        chat_request.use_web_search,
    )
    election = await get_election_from_election_id(session, chat_request.election_id)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Election not registered."
        )
    selected_parties = await get_party_from_name_list(
        session, chat_request.selected_parties
    )

    if chat_request.selected_parties:
        missing_parties = set(chat_request.selected_parties) - {
            party.shortname for party in selected_parties
        }
        if missing_parties:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parties {', '.join(missing_parties)} not registered.",
            )
        logger.info(
            "Validated %s requested parties: %s",
            len(selected_parties),
            [party.shortname for party in selected_parties],
        )
    else:
        available_shortnames = await get_missing_party_shortnames(
            session, election, []
        )
        if not available_shortnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No parties available for this election.",
            )
        logger.info(
            "No parties provided; %s available for auto-selection",
            len(available_shortnames),
        )

    async def sse_stream() -> AsyncGenerator[str]:
        async with session_maker() as session, session.begin():
            bound_election = await session.merge(election)
            bound_selected_parties = [
                await session.merge(party) for party in selected_parties
            ]
            logger.info(
                "Invoking agent for election=%s with parties=%s",
                bound_election.id,
                [party.shortname for party in bound_selected_parties],
            )
            try:
                stream = await agent.invoke(
                    chat_request.messages,
                    election=bound_election,
                    selected_parties=bound_selected_parties,
                    session=session,
                )
            except Exception:
                logger.exception("Agent invocation failed")
                yield "event: ERROR\ndata: ERROR\n\n"
                raise
            async with streamcontext(stream) as streamer:
                try:
                    async for chunk in streamer:
                        logger.debug(
                            "Streaming chunk type=%s payload=%s",
                            chunk.type,
                            chunk.model_dump_json(),
                        )
                        yield f"event: {chunk.type}\ndata: {chunk.model_dump_json()}\n\n"
                except Exception:
                    logger.exception("Error while streaming agent chunks")
                    yield "event: ERROR\ndata: ERROR\n\n"
                    raise
        logger.info("Finished agent stream for election=%s", election.id)
        yield "event: DONE\ndata: DONE\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")
