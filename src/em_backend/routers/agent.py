from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from aiostream import streamcontext
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import AfterValidator, BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.agent.agent import Agent
from em_backend.database.utils import (
    get_country_from_shortcode,
    get_election_from_election_id,
    get_party_from_name_list,
)
from em_backend.models.messages import AnyMessage
from em_backend.routers.v2 import get_agent, get_database_session

agent_router = APIRouter()


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


@agent_router.post("/{country_code}/chat")
async def agent_chat(
    chat_request: AgentChatRequest,
    country_code: str,
    agent: Annotated[Agent, Depends(get_agent)],
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> StreamingResponse:
    country = await get_country_from_shortcode(session, country_code=country_code)
    if country is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Country not registered."
        )
    election = await get_election_from_election_id(session, chat_request.election_id)
    if election is None or election.country != country:
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

    chunk_stream = agent.invoke(
        chat_request.messages,
        election=election,
        selected_parties=selected_parties,
        session=session,
    )

    async def sse_stream() -> AsyncGenerator[str]:
        async with streamcontext(chunk_stream) as streamer:
            async for chunk in streamer:
                yield f"event: {chunk.type}\ndata: {chunk.model_dump_json()}\n\n"
        yield "event: DONE\ndata: DONE\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")
