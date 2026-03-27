"""API endpoints for the Hungarian Political Argument Knowledge Graph."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from em_backend.graph.db import get_graph_db
from em_backend.graph.query_service import (
    ArgumentSummary,
    GraphStats,
    KnowledgeGraphService,
    PartyInfo,
    TopicInfo,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/graph", tags=["knowledge-graph"])


# ============================================================================
# Request/Response models
# ============================================================================


class FollowUpRequest(BaseModel):
    statement: str = Field(description="The Pol.is statement the user voted on")
    vote: str = Field(description="User's vote: agree, disagree, or pass")


class FollowUpResponse(BaseModel):
    original_statement: str
    user_vote: str
    follow_ups: list[dict[str, Any]]


class SeedRequest(BaseModel):
    topic: str = Field(description="Topic name (Hungarian)")
    count: int = Field(default=10, ge=1, le=30)


class SeedResponse(BaseModel):
    topic: str
    statements: list[dict[str, Any]]


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/arguments", response_model=list[ArgumentSummary])
async def get_arguments(
    topic: str | None = Query(default=None, description="Filter by topic name"),
    party: str | None = Query(default=None, description="Filter by party shortname"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ArgumentSummary]:
    """Query arguments from the knowledge graph."""
    try:
        graph = get_graph_db()
        service = KnowledgeGraphService(graph)

        if topic and party:
            return service.get_arguments_by_topic_and_party(topic, party, limit)
        elif topic:
            return service.get_arguments_by_topic(topic, limit)
        elif party:
            return service.get_arguments_by_party(party, limit)
        else:
            # Return recent arguments across all topics
            return service.get_arguments_by_topic("Gazdaság", limit)
    except Exception as e:
        logger.error("Failed to query arguments", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics", response_model=list[TopicInfo])
async def get_topics() -> list[TopicInfo]:
    """List all topics with argument counts."""
    try:
        graph = get_graph_db()
        service = KnowledgeGraphService(graph)
        return service.get_all_topics()
    except Exception as e:
        logger.error("Failed to get topics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parties", response_model=list[PartyInfo])
async def get_parties() -> list[PartyInfo]:
    """List all parties with argument counts."""
    try:
        graph = get_graph_db()
        service = KnowledgeGraphService(graph)
        return service.get_all_parties()
    except Exception as e:
        logger.error("Failed to get parties", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare/{topic}", response_model=dict[str, list[str]])
async def compare_parties(topic: str) -> dict[str, list[str]]:
    """Compare all parties' arguments on a topic."""
    try:
        graph = get_graph_db()
        service = KnowledgeGraphService(graph)
        return service.compare_parties_on_topic(topic)
    except Exception as e:
        logger.error("Failed to compare parties", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rebuttals", response_model=list[ArgumentSummary])
async def get_rebuttals(
    argument: str = Query(description="Argument text to find rebuttals for"),
) -> list[ArgumentSummary]:
    """Find arguments that rebut a given argument."""
    try:
        graph = get_graph_db()
        service = KnowledgeGraphService(graph)
        return service.get_rebuttals(argument)
    except Exception as e:
        logger.error("Failed to get rebuttals", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/polis/followups", response_model=FollowUpResponse)
async def generate_polis_followups(request: FollowUpRequest) -> FollowUpResponse:
    """Generate Pol.is follow-up questions based on user's vote."""
    from em_backend.graph.polis.question_generator import generate_followups

    try:
        result = await generate_followups(
            statement=request.statement,
            user_vote=request.vote,
        )
        return FollowUpResponse(
            original_statement=result.original_statement,
            user_vote=result.user_vote,
            follow_ups=[fu.model_dump() for fu in result.follow_ups],
        )
    except Exception as e:
        logger.error("Failed to generate follow-ups", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/polis/seed", response_model=SeedResponse)
async def generate_polis_seeds(request: SeedRequest) -> SeedResponse:
    """Generate seed statements for a Pol.is conversation topic."""
    from em_backend.graph.polis.seed_generator import generate_seed_statements

    try:
        result = await generate_seed_statements(
            topic=request.topic,
            count=request.count,
        )
        return SeedResponse(
            topic=result.topic,
            statements=[s.model_dump() for s in result.statements],
        )
    except Exception as e:
        logger.error("Failed to generate seeds", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neighborhood")
async def get_neighborhood(
    node_type: str = Query(..., description="Node type: Topic, Party, or Argument"),
    node_name: str = Query(..., description="Node identifier (topic name, party shortname, or argument text)"),
    depth: int = Query(default=1, ge=1, le=2),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """Get graph neighborhood around a node for visualization. Returns {nodes, edges}."""
    try:
        graph = get_graph_db()
        service = KnowledgeGraphService(graph)
        return service.get_neighborhood(node_type, node_name, depth, limit)
    except Exception as e:
        logger.error("Failed to get neighborhood", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_graph_overview() -> dict:
    """Get all topics and parties with connections for the initial graph view."""
    try:
        graph = get_graph_db()
        service = KnowledgeGraphService(graph)
        return service.get_graph_overview()
    except Exception as e:
        logger.error("Failed to get overview", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=GraphStats)
async def get_graph_stats() -> GraphStats:
    """Get overall knowledge graph statistics."""
    try:
        graph = get_graph_db()
        service = KnowledgeGraphService(graph)
        return service.get_stats()
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
