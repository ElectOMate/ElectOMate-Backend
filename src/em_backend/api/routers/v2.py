from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

import logging
from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from em_backend.agent.agent import Agent
from em_backend.core.config import settings
from em_backend.database.utils import create_database_sessionmaker
from em_backend.llm.perplexity import PerplexityClient
from em_backend.vector.db import VectorDatabase
from em_backend.vector.parser import DocumentParser


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: APIRouter) -> AsyncGenerator[dict[str, Any]]:
    perplexity_client: PerplexityClient | None = None
    if settings.perplexity_api_key:
        logger.info(
            "Initializing Perplexity client with model='%s'",
            settings.perplexity_model,
        )
        perplexity_client = PerplexityClient(
            settings.perplexity_api_key,
            model=settings.perplexity_model,
        )
    else:
        logger.warning(
            "PERPLEXITY_API_KEY is not configured; web search features will be disabled"
        )
    async with (
        VectorDatabase.create() as vector_database,
        create_database_sessionmaker() as session_maker,
    ):
        agent = Agent(vector_database, perplexity_client=perplexity_client)
        document_parser = DocumentParser()
        try:
            yield {
                "vector_database": vector_database,
                "session_maker": session_maker,
                "agent": agent,
                "document_parser": document_parser,
            }
        finally:
            if perplexity_client is not None:
                await perplexity_client.close()


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
        raise RuntimeError("Vector database is not initialized.")
    return vector_database


def get_sessionmaker(req: Request) -> async_sessionmaker:
    """Dependency to get the singleton sessionmaker instance for the application."""
    session_maker = req.state.session_maker
    if session_maker is None:
        raise RuntimeError("Database is not initialized.")
    return session_maker


async def get_database_session(req: Request) -> AsyncGenerator[AsyncSession]:
    """Dependency to get a database session for the application."""
    sessionmaker = cast("async_sessionmaker[AsyncSession]", req.state.session_maker)
    if sessionmaker is None:
        raise RuntimeError("Database is not initialized.")
    async with sessionmaker() as session, session.begin():
        yield session


async def get_document_parser(req: Request) -> DocumentParser:
    """Dependency to get the singleton document parser."""
    document_parser = req.state.document_parser
    if document_parser is None:
        raise RuntimeError("Document Parser is not initialized.")
    return document_parser


v2_router = APIRouter(prefix="/v2", lifespan=lifespan)

from em_backend.api.routers import (  # noqa: E402
    agent,
    candidates,
    countries,
    documents,
    elections,
    parties,
    proposed_questions,
    quiz,
)

v2_router.include_router(agent.agent_router)
v2_router.include_router(countries.router)
v2_router.include_router(elections.router)
v2_router.include_router(parties.router)
v2_router.include_router(candidates.router)
v2_router.include_router(documents.router)
v2_router.include_router(proposed_questions.router)
v2_router.include_router(quiz.router)
