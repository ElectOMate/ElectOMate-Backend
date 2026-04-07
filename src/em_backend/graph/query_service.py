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
    source_quote: str | None = None
    source_page: int | None = None
    source_section: str | None = None
    generated: bool = False


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

    def get_neighborhood(
        self,
        node_type: str,
        node_name: str,
        depth: int = 1,
        limit: int = 50,
    ) -> dict[str, list]:
        """Get nodes and edges around a given node for graph visualization.

        Args:
            node_type: "Topic", "Party", or "Argument"
            node_name: The node's identifying property
            depth: 1 = direct neighbors, 2 = neighbors of neighbors
            limit: Max neighbor nodes per expansion

        Returns:
            {"nodes": [...], "edges": [...]}
        """
        nodes: dict[str, dict] = {}
        edges: list[dict] = []

        escaped = node_name.replace("'", "\\'")

        # Identify the root node's key property
        if node_type == "Topic":
            prop = "name"
            root_id = f"topic::{node_name}"
        elif node_type == "Party":
            prop = "shortname"
            root_id = f"party::{node_name}"
        else:
            prop = "text"
            root_id = f"arg::{node_name[:80]}"

        # Add root node
        nodes[root_id] = {
            "id": root_id,
            "type": node_type,
            "label": node_name[:120],
            "properties": {},
        }

        # Depth 1: direct neighbors
        if node_type == "Topic":
            # Arguments about this topic
            results = self._graph.query(
                f"""
                MATCH (a:Argument)-[:ABOUT]->(t:Topic {{{prop}: '{escaped}'}})
                OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party)
                RETURN a.text, a.argument_type, a.sentiment, a.strength, p.shortname
                LIMIT {limit}
                """,
                columns=["text", "arg_type", "sentiment", "strength", "party"],
            )
            for r in results:
                text = str(r.get("text", "")).strip('"')
                aid = f"arg::{text[:80]}"
                nodes[aid] = {
                    "id": aid, "type": "Argument", "label": text[:120],
                    "properties": {
                        "argument_type": r.get("arg_type"),
                        "sentiment": r.get("sentiment"),
                        "strength": r.get("strength"),
                        "party": r.get("party"),
                    },
                }
                edges.append({"source": aid, "target": root_id, "type": "ABOUT"})
                # Also add party node + edge
                party = r.get("party")
                if party:
                    party = str(party).strip('"')
                    pid = f"party::{party}"
                    if pid not in nodes:
                        nodes[pid] = {"id": pid, "type": "Party", "label": party, "properties": {}}
                    edges.append({"source": aid, "target": pid, "type": "MADE_BY"})

        elif node_type == "Party":
            # Arguments by this party
            results = self._graph.query(
                f"""
                MATCH (a:Argument)-[:MADE_BY]->(p:Party {{{prop}: '{escaped}'}})
                OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic)
                RETURN a.text, a.argument_type, a.sentiment, a.strength, t.name
                LIMIT {limit}
                """,
                columns=["text", "arg_type", "sentiment", "strength", "topic"],
            )
            for r in results:
                text = str(r.get("text", "")).strip('"')
                aid = f"arg::{text[:80]}"
                nodes[aid] = {
                    "id": aid, "type": "Argument", "label": text[:120],
                    "properties": {
                        "argument_type": r.get("arg_type"),
                        "sentiment": r.get("sentiment"),
                        "strength": r.get("strength"),
                    },
                }
                edges.append({"source": aid, "target": root_id, "type": "MADE_BY"})
                topic = r.get("topic")
                if topic:
                    topic = str(topic).strip('"')
                    tid = f"topic::{topic}"
                    if tid not in nodes:
                        nodes[tid] = {"id": tid, "type": "Topic", "label": topic, "properties": {}}
                    edges.append({"source": aid, "target": tid, "type": "ABOUT"})

        else:  # Argument
            # Topics, parties, rebuttals, supports
            for rel, target_label, target_prop in [
                ("ABOUT", "Topic", "name"),
                ("MADE_BY", "Party", "shortname"),
            ]:
                try:
                    results = self._graph.query(
                        f"""
                        MATCH (a:Argument {{{prop}: '{escaped}'}})-[:{rel}]->(n:{target_label})
                        RETURN n.{target_prop}
                        """,
                        columns=["val"],
                    )
                    for r in results:
                        val = str(r.get("val", "")).strip('"')
                        nid = f"{target_label.lower()}::{val}"
                        nodes[nid] = {"id": nid, "type": target_label, "label": val, "properties": {}}
                        edges.append({"source": root_id, "target": nid, "type": rel})
                except Exception:
                    pass

            # Rebuttals and supports
            for rel in ["REBUTS", "SUPPORTS", "CONTRADICTS"]:
                try:
                    results = self._graph.query(
                        f"""
                        MATCH (a:Argument {{{prop}: '{escaped}'}})-[:{rel}]->(b:Argument)
                        RETURN b.text
                        LIMIT 10
                        """,
                        columns=["text"],
                    )
                    for r in results:
                        text = str(r.get("text", "")).strip('"')
                        bid = f"arg::{text[:80]}"
                        nodes[bid] = {"id": bid, "type": "Argument", "label": text[:120], "properties": {}}
                        edges.append({"source": root_id, "target": bid, "type": rel})
                except Exception:
                    pass

        # Depth 2: expand argument neighbors (only if requested)
        if depth >= 2 and node_type in ("Topic", "Party"):
            arg_ids = [nid for nid, n in nodes.items() if n["type"] == "Argument"]
            for aid in arg_ids[:20]:  # Limit depth-2 expansion
                arg_text = nodes[aid]["label"].replace("'", "\\'")
                for rel in ["REBUTS", "SUPPORTS", "CONTRADICTS"]:
                    try:
                        results = self._graph.query(
                            f"""
                            MATCH (a:Argument {{text: '{arg_text}'}})-[:{rel}]->(b:Argument)
                            RETURN b.text
                            LIMIT 3
                            """,
                            columns=["text"],
                        )
                        for r in results:
                            text = str(r.get("text", "")).strip('"')
                            bid = f"arg::{text[:80]}"
                            if bid not in nodes:
                                nodes[bid] = {"id": bid, "type": "Argument", "label": text[:120], "properties": {}}
                            edges.append({"source": aid, "target": bid, "type": rel})
                    except Exception:
                        pass

        return {"nodes": list(nodes.values()), "edges": edges}

    def get_graph_overview(self) -> dict[str, list]:
        """Get all topics and parties with connection counts for the initial view."""
        nodes: list[dict] = []
        edges: list[dict] = []

        # Get topics with argument counts
        topics = self.get_all_topics()
        for t in topics:
            nodes.append({
                "id": f"topic::{t.name}",
                "type": "Topic",
                "label": t.name,
                "properties": {
                    "name_en": t.name_en,
                    "category": t.category,
                    "argument_count": t.argument_count,
                },
            })

        # Get parties with argument counts
        parties = self.get_all_parties()
        for p in parties:
            nodes.append({
                "id": f"party::{p.shortname}",
                "type": "Party",
                "label": p.shortname,
                "properties": {
                    "name": p.name,
                    "ideology": p.ideology,
                    "argument_count": p.argument_count,
                },
            })

        # Get topic-party connections (how many arguments each party has per topic)
        for t in topics:
            for p in parties:
                try:
                    args = self.get_arguments_by_topic_and_party(t.name, p.shortname, limit=1)
                    if args:
                        edges.append({
                            "source": f"party::{p.shortname}",
                            "target": f"topic::{t.name}",
                            "type": "HAS_ARGUMENTS",
                        })
                except Exception:
                    pass

        return {"nodes": nodes, "edges": edges}

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
