"""Iterative enrichment loop for the knowledge graph.

Scheduled re-crawl of sources, re-extraction as models improve,
gap analysis, and confidence-weighted deduplication.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import structlog

from em_backend.graph.builder import ingest_document
from em_backend.graph.connectors.base import IngestedDocument
from em_backend.graph.db import GraphDB, get_graph_db
from em_backend.graph.query_service import KnowledgeGraphService

logger = structlog.get_logger(__name__)


async def run_enrichment_cycle(
    graph: GraphDB | None = None,
    new_documents: list[IngestedDocument] | None = None,
) -> dict[str, Any]:
    """Run a single enrichment cycle.

    1. Ingest any new documents
    2. Analyze gaps (topics/parties with few arguments)
    3. Report stats

    Args:
        graph: GraphDB instance.
        new_documents: New documents to ingest.

    Returns:
        Summary of the enrichment cycle.
    """
    if graph is None:
        graph = get_graph_db()

    service = KnowledgeGraphService(graph)
    summary: dict[str, Any] = {"date": str(date.today())}

    # Step 1: Ingest new documents
    if new_documents:
        logger.info("Ingesting new documents", count=len(new_documents))
        for doc in new_documents:
            try:
                await ingest_document(doc, graph)
            except Exception as e:
                logger.error("Failed to ingest document", title=doc.title, error=str(e))
        summary["documents_ingested"] = len(new_documents)

    # Step 2: Gap analysis
    gaps = analyze_gaps(graph)
    summary["gaps"] = gaps

    # Step 3: Current stats
    stats = service.get_stats()
    summary["stats"] = stats.model_dump()

    logger.info("Enrichment cycle complete", **summary)
    return summary


def analyze_gaps(graph: GraphDB | None = None) -> dict[str, Any]:
    """Identify gaps in the knowledge graph coverage.

    Finds:
    - Topics with few arguments
    - Parties with few arguments
    - Topics where specific parties have no representation
    """
    if graph is None:
        graph = get_graph_db()

    service = KnowledgeGraphService(graph)
    topics = service.get_all_topics()
    parties = service.get_all_parties()

    gaps: dict[str, Any] = {
        "underrepresented_topics": [],
        "underrepresented_parties": [],
        "missing_party_topic_combinations": [],
    }

    # Topics with fewer than 3 arguments
    for topic in topics:
        if topic.argument_count < 3:
            gaps["underrepresented_topics"].append({
                "topic": topic.name,
                "argument_count": topic.argument_count,
            })

    # Parties with fewer than 5 arguments total
    for party in parties:
        if party.argument_count < 5:
            gaps["underrepresented_parties"].append({
                "party": party.shortname,
                "argument_count": party.argument_count,
            })

    # Check for party-topic combinations with zero arguments
    for topic in topics:
        for party in parties:
            args = service.get_arguments_by_topic_and_party(
                topic.name, party.shortname, limit=1
            )
            if not args:
                gaps["missing_party_topic_combinations"].append({
                    "topic": topic.name,
                    "party": party.shortname,
                })

    return gaps


async def enrichment_loop(
    interval_minutes: int = 60,
    graph: GraphDB | None = None,
) -> None:
    """Run the enrichment loop continuously.

    Args:
        interval_minutes: Minutes between cycles.
        graph: GraphDB instance.
    """
    logger.info("Starting enrichment loop", interval_minutes=interval_minutes)

    while True:
        try:
            await run_enrichment_cycle(graph=graph)
        except Exception as e:
            logger.error("Enrichment cycle failed", error=str(e))

        await asyncio.sleep(interval_minutes * 60)
