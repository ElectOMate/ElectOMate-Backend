from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast

from fastapi import APIRouter, Request

from em_backend.agent.agent import Agent
from em_backend.database.utils import create_database_sessionmaker
from em_backend.vector.db import VectorDatabase

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@asynccontextmanager
async def lifespan(_: APIRouter) -> AsyncGenerator[dict[str, Any]]:
    async with (
        VectorDatabase.create() as vector_database,
        create_database_sessionmaker() as session_maker,
    ):
        agent = Agent(vector_database)
        yield {
            "vector_database": vector_database,
            "session_maker": session_maker,
            "agent": agent,
        }


def get_agent(req: Request) -> Agent:
    """Dependency to get the singleton agent instance for the application."""
    agent = req.state.agent
    if agent is None:
        raise RuntimeError("Agent handler is not initialized.")
    return agent


def get_vector_database(req: Request) -> VectorDatabase:
    """Dependency to get the singleton vector database instance for the application."""
    vector_database = req.state.vector_database
    if vector_database is None:
        raise RuntimeError("Agent handler is not initialized.")
    return vector_database


async def get_database_session(req: Request) -> AsyncGenerator[AsyncSession]:
    """Dependency to get a database session for the application."""
    sessionmaker = cast("async_sessionmaker[AsyncSession]", req.state.session_maker)
    if sessionmaker is None:
        raise RuntimeError("Agent handler is not initialized.")
    async with sessionmaker() as session, session.begin():
        yield session


v2_router = APIRouter(prefix="/v2", tags=["v2"], lifespan=lifespan)

from em_backend.routers import (  # noqa: E402
    agent,
    candidates,
    countries,
    documents,
    elections,
    parties,
    proposed_questions,
)

v2_router.include_router(agent.agent_router)
v2_router.include_router(countries.router)
v2_router.include_router(elections.router)
v2_router.include_router(parties.router)
v2_router.include_router(candidates.router)
v2_router.include_router(documents.router)
v2_router.include_router(proposed_questions.router)
