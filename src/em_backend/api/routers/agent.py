from collections.abc import AsyncGenerator
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
    get_party_from_name_list,
)
from em_backend.models.messages import AnyMessage

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
    election = await get_election_from_election_id(session, chat_request.election_id)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Election not registered."
        )
    selected_parties = await get_party_from_name_list(
        session, chat_request.selected_parties
    )
    if missing_parties := set(chat_request.selected_parties) - set(
        party.shortname for party in selected_parties
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parties {', '.join(missing_parties)} not registered.",
        )

    async def sse_stream() -> AsyncGenerator[str]:
        async with session_maker() as session, session.begin():
            bound_election = await session.merge(election)
            bound_selected_parties = [
                await session.merge(party) for party in selected_parties
            ]
            async with streamcontext(
                await agent.invoke(
                    chat_request.messages,
                    election=bound_election,
                    selected_parties=bound_selected_parties,
                    session=session,
                )
            ) as streamer:
                try:
                    async for chunk in streamer:
                        yield f"event: {chunk.type}\n"
                        "data: {chunk.model_dump_json()}\n\n"
                except Exception:
                    yield "event: ERROR\ndata: ERROR\n\n"
                    raise
        yield "event: DONE\ndata: DONE\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")
