"""Graph query service for accessing the argument knowledge graph.

Provides high-level query methods that return Pydantic models
suitable for API consumption.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, Field

from em_backend.graph.db import GraphDB, get_graph_db
from em_backend.graph import queries

logger = structlog.get_logger(__name__)


# ============================================================================
# Response models
# ============================================================================


class ArgumentSummary(BaseModel):
    text: str
    summary: str | None = None
    argument_type: str | None = None
    sentiment: str | None = None
    strength: int | None = None
    party: str | None = None
    politician: str | None = None
    topics: list[str] = Field(default_factory=list)


class TopicInfo(BaseModel):
    name: str
    name_en: str | None = None
    category: str | None = None
    argument_count: int = 0


class PartyInfo(BaseModel):
    shortname: str
    name: str | None = None
    ideology: str | None = None
    argument_count: int = 0


class GraphStats(BaseModel):
    total_arguments: int = 0
    total_topics: int = 0
    total_parties: int = 0
    total_politicians: int = 0
    total_sources: int = 0
    total_relationships: int = 0


# ============================================================================
# Query functions
# ============================================================================


class KnowledgeGraphService:
    """Service for querying the argument knowledge graph."""

    def __init__(self, graph: GraphDB | None = None) -> None:
        self._graph = graph or get_graph_db()

    def get_arguments_by_topic(
        self,
        topic_name: str,
        limit: int = 50,
    ) -> list[ArgumentSummary]:
        """Get all arguments about a specific topic."""
        results = self._graph.query(
            f"""
            MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{topic_name}'}})
            OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party)
            OPTIONAL MATCH (a)-[:MADE_BY]->(pol:Politician)
            RETURN a.text, a.summary, a.argument_type, a.sentiment,
                   a.strength, p.shortname, pol.name
            LIMIT {limit}
            """,
            columns=["text", "summary", "arg_type", "sentiment", "strength", "party", "politician"],
        )

        return [
            ArgumentSummary(
                text=r.get("text", ""),
                summary=r.get("summary"),
                argument_type=r.get("arg_type"),
                sentiment=r.get("sentiment"),
                strength=r.get("strength"),
                party=r.get("party"),
                politician=r.get("politician"),
                topics=[topic_name],
            )
            for r in results
        ]

    def get_arguments_by_party(
        self,
        party_shortname: str,
        limit: int = 50,
    ) -> list[ArgumentSummary]:
        """Get all arguments made by a specific party."""
        results = self._graph.query(
            f"""
            MATCH (a:Argument)-[:MADE_BY]->(p:Party {{shortname: '{party_shortname}'}})
            OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic)
            RETURN a.text, a.summary, a.argument_type, a.sentiment,
                   a.strength, t.name
            LIMIT {limit}
            """,
            columns=["text", "summary", "arg_type", "sentiment", "strength", "topic"],
        )

        return [
            ArgumentSummary(
                text=r.get("text", ""),
                summary=r.get("summary"),
                argument_type=r.get("arg_type"),
                sentiment=r.get("sentiment"),
                strength=r.get("strength"),
                party=party_shortname,
                topics=[r["topic"]] if r.get("topic") else [],
            )
            for r in results
        ]

    def get_arguments_by_topic_and_party(
        self,
        topic_name: str,
        party_shortname: str,
        limit: int = 50,
    ) -> list[ArgumentSummary]:
        """Get arguments about a topic from a specific party."""
        results = self._graph.query(
            f"""
            MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{topic_name}'}})
            MATCH (a)-[:MADE_BY]->(p:Party {{shortname: '{party_shortname}'}})
            RETURN a.text, a.summary, a.argument_type, a.sentiment, a.strength
            LIMIT {limit}
            """,
            columns=["text", "summary", "arg_type", "sentiment", "strength"],
        )

        return [
            ArgumentSummary(
                text=r.get("text", ""),
                summary=r.get("summary"),
                argument_type=r.get("arg_type"),
                sentiment=r.get("sentiment"),
                strength=r.get("strength"),
                party=party_shortname,
                topics=[topic_name],
            )
            for r in results
        ]

    def get_rebuttals(self, argument_text: str) -> list[ArgumentSummary]:
        """Get all arguments that rebut a specific argument."""
        escaped = argument_text.replace("'", "\\'")
        results = self._graph.query(
            f"""
            MATCH (r:Argument)-[:REBUTS]->(a:Argument {{text: '{escaped}'}})
            OPTIONAL MATCH (r)-[:MADE_BY]->(p:Party)
            RETURN r.text, r.summary, r.sentiment, p.shortname
            """,
            columns=["text", "summary", "sentiment", "party"],
        )

        return [
            ArgumentSummary(
                text=r.get("text", ""),
                summary=r.get("summary"),
                sentiment=r.get("sentiment"),
                party=r.get("party"),
            )
            for r in results
        ]

    def compare_parties_on_topic(
        self,
        topic_name: str,
    ) -> dict[str, list[str]]:
        """Compare all parties' arguments on a topic."""
        results = self._graph.query(
            f"""
            MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{topic_name}'}})
            MATCH (a)-[:MADE_BY]->(p:Party)
            RETURN p.shortname, collect(a.summary)
            """,
            columns=["party", "summaries"],
        )

        comparison: dict[str, list[str]] = {}
        for r in results:
            party = r.get("party", "Unknown")
            summaries = r.get("summaries", [])
            if isinstance(summaries, list):
                comparison[party] = summaries
            else:
                comparison[party] = [str(summaries)]

        return comparison

    def get_all_topics(self) -> list[TopicInfo]:
        """Get all topics with argument counts."""
        results = self._graph.query(
            queries.GET_ALL_TOPICS,
            columns=["name", "name_en", "category", "argument_count"],
        )

        return [
            TopicInfo(
                name=r.get("name", ""),
                name_en=r.get("name_en"),
                category=r.get("category"),
                argument_count=r.get("argument_count", 0),
            )
            for r in results
        ]

    def get_all_parties(self) -> list[PartyInfo]:
        """Get all parties with argument counts."""
        results = self._graph.query(
            queries.GET_ALL_PARTIES,
            columns=["shortname", "name", "ideology", "argument_count"],
        )

        return [
            PartyInfo(
                shortname=r.get("shortname", ""),
                name=r.get("name"),
                ideology=r.get("ideology"),
                argument_count=r.get("argument_count", 0),
            )
            for r in results
        ]

    def get_stats(self) -> GraphStats:
        """Get overall graph statistics."""
        from em_backend.graph.schema import get_graph_stats

        raw_stats = get_graph_stats(self._graph)

        # Count relationships
        try:
            rel_result = self._graph.query(
                """
                MATCH ()-[r]->()
                RETURN count(r)
                """,
                columns=["cnt"],
            )
            total_rels = rel_result[0]["cnt"] if rel_result else 0
        except Exception:
            total_rels = 0

        return GraphStats(
            total_arguments=raw_stats.get("Argument", 0),
            total_topics=raw_stats.get("Topic", 0),
            total_parties=raw_stats.get("Party", 0),
            total_politicians=raw_stats.get("Politician", 0),
            total_sources=raw_stats.get("Source", 0),
            total_relationships=total_rels,
        )
