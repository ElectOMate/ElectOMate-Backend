"""Knowledge graph builder pipeline.

Orchestrates the full ingestion flow:
Source → Connector → Argument Miner → Entity Resolution → Graph Insert
"""

from __future__ import annotations

from datetime import date
from typing import Any

import structlog

from em_backend.graph.connectors.base import IngestedDocument
from em_backend.graph.db import GraphDB, get_graph_db
from em_backend.graph.extraction.argument_miner import (
    ExtractedArgument,
    ExtractionResult,
    extract_arguments_from_document,
)
from em_backend.graph.extraction.entity_resolver import (
    resolve_party,
    resolve_politician,
)
from em_backend.graph.extraction.relationship_detector import (
    ArgumentRelation,
    detect_relationships_batch,
)
from em_backend.graph.extraction.topic_builder import classify_arguments_batch

logger = structlog.get_logger(__name__)


async def ingest_document(
    doc: IngestedDocument,
    graph: GraphDB | None = None,
    detect_relations: bool = True,
) -> dict[str, Any]:
    """Ingest a single document into the knowledge graph.

    Full pipeline: extract arguments → resolve entities → classify topics
    → insert into graph → detect relationships.

    Args:
        doc: The document to ingest.
        graph: GraphDB instance (uses singleton if None).
        detect_relations: Whether to detect inter-argument relationships.

    Returns:
        Summary dict with counts of inserted nodes/edges.
    """
    if graph is None:
        graph = get_graph_db()

    logger.info("Starting document ingestion", title=doc.title, source_type=doc.source_type)
    stats = {
        "source": doc.title,
        "arguments_extracted": 0,
        "arguments_inserted": 0,
        "relationships_found": 0,
        "topics_linked": 0,
        "politicians_linked": 0,
        "parties_linked": 0,
    }

    # Step 1: Extract arguments
    extraction = await extract_arguments_from_document(doc)
    stats["arguments_extracted"] = len(extraction.arguments)

    if not extraction.arguments:
        logger.warning("No arguments extracted", title=doc.title)
        return stats

    # Step 2: Create source node
    source_url = doc.source_url or doc.source_path or f"local://{doc.title}"
    _escape = lambda s: s.replace("'", "\\'") if s else ""

    graph.write(f"""
        MERGE (s:Source {{url: '{_escape(source_url)}'}})
        SET s.type = '{doc.source_type}',
            s.title = '{_escape(doc.title)}',
            s.date = '{doc.date or ""}',
            s.modality = '{doc.modality}'
        RETURN s
    """)

    # Step 3: Classify topics for all arguments
    topic_map = await classify_arguments_batch(extraction.arguments, use_llm=True)

    # Step 4: Insert each argument
    for i, arg in enumerate(extraction.arguments):
        try:
            # Resolve entities
            resolved_speaker = None
            if arg.speaker:
                resolved_speaker = resolve_politician(arg.speaker)

            resolved_party = resolve_party(arg.party) if arg.party else None
            if not resolved_party and resolved_speaker:
                resolved_party = resolved_speaker.party_shortname

            # Create argument node
            claim_escaped = _escape(arg.claim)
            summary_escaped = _escape(arg.conclusion or arg.claim[:200])

            graph.write(f"""
                MERGE (a:Argument {{text: '{claim_escaped}'}})
                SET a.type = 'claim',
                    a.summary = '{summary_escaped}',
                    a.argument_type = '{arg.argument_type}',
                    a.confidence = {extraction.confidence},
                    a.sentiment = '{arg.sentiment}',
                    a.strength = {arg.strength},
                    a.extraction_date = '{date.today()}'
                RETURN a
            """)
            stats["arguments_inserted"] += 1

            # Link to source
            graph.write(f"""
                MATCH (a:Argument {{text: '{claim_escaped}'}})
                MATCH (s:Source {{url: '{_escape(source_url)}'}})
                MERGE (a)-[:SOURCED_FROM]->(s)
            """)

            # Link to topics
            topics = topic_map.get(i, [])
            for topic_name in topics:
                try:
                    graph.write(f"""
                        MATCH (a:Argument {{text: '{claim_escaped}'}})
                        MATCH (t:Topic {{name: '{_escape(topic_name)}'}})
                        MERGE (a)-[:ABOUT]->(t)
                    """)
                    stats["topics_linked"] += 1
                except Exception:
                    logger.debug("Failed to link topic", topic=topic_name)

            # Link to party
            if resolved_party:
                try:
                    graph.write(f"""
                        MATCH (a:Argument {{text: '{claim_escaped}'}})
                        MATCH (p:Party {{shortname: '{resolved_party}'}})
                        MERGE (a)-[:MADE_BY]->(p)
                    """)
                    stats["parties_linked"] += 1
                except Exception:
                    logger.debug("Failed to link party", party=resolved_party)

            # Link to politician
            if resolved_speaker and resolved_speaker.confidence >= 0.5:
                speaker_name = _escape(resolved_speaker.canonical_name)
                try:
                    graph.write(f"""
                        MERGE (pol:Politician {{name: '{speaker_name}'}})
                        SET pol.role = '{_escape(resolved_speaker.role or "")}',
                            pol.active = true
                        RETURN pol
                    """)
                    graph.write(f"""
                        MATCH (a:Argument {{text: '{claim_escaped}'}})
                        MATCH (pol:Politician {{name: '{speaker_name}'}})
                        MERGE (a)-[:MADE_BY]->(pol)
                    """)
                    stats["politicians_linked"] += 1

                    # Link politician to party
                    if resolved_party:
                        graph.write(f"""
                            MATCH (pol:Politician {{name: '{speaker_name}'}})
                            MATCH (p:Party {{shortname: '{resolved_party}'}})
                            MERGE (pol)-[:MEMBER_OF]->(p)
                        """)
                except Exception:
                    logger.debug("Failed to link politician", name=speaker_name)

        except Exception as e:
            logger.error(
                "Failed to insert argument",
                arg_index=i,
                error=str(e),
            )

    # Step 5: Detect relationships between arguments
    if detect_relations and len(extraction.arguments) > 1:
        try:
            relations = await detect_relationships_batch(
                extraction.arguments,
                same_topic_only=True,
                min_confidence=0.6,
            )
            for idx_a, idx_b, rel_result in relations:
                arg_a = extraction.arguments[idx_a]
                arg_b = extraction.arguments[idx_b]
                claim_a = _escape(arg_a.claim)
                claim_b = _escape(arg_b.claim)

                rel_type = rel_result.relation.value
                try:
                    graph.write(f"""
                        MATCH (a1:Argument {{text: '{claim_a}'}})
                        MATCH (a2:Argument {{text: '{claim_b}'}})
                        MERGE (a1)-[:{rel_type}]->(a2)
                    """)
                    stats["relationships_found"] += 1
                except Exception:
                    logger.debug(
                        "Failed to create relationship",
                        type=rel_type,
                    )
        except Exception as e:
            logger.error("Relationship detection failed", error=str(e))

    logger.info("Document ingestion complete", **stats)
    return stats


async def ingest_documents(
    documents: list[IngestedDocument],
    graph: GraphDB | None = None,
    detect_relations: bool = True,
) -> list[dict[str, Any]]:
    """Ingest multiple documents into the knowledge graph.

    Args:
        documents: List of documents to ingest.
        graph: GraphDB instance.
        detect_relations: Whether to detect inter-argument relationships.

    Returns:
        List of summary dicts for each document.
    """
    if graph is None:
        graph = get_graph_db()

    results = []
    for i, doc in enumerate(documents):
        logger.info(
            "Ingesting document",
            progress=f"{i + 1}/{len(documents)}",
            title=doc.title,
        )
        result = await ingest_document(doc, graph, detect_relations)
        results.append(result)

    # Summary
    total_args = sum(r["arguments_inserted"] for r in results)
    total_rels = sum(r["relationships_found"] for r in results)
    logger.info(
        "Batch ingestion complete",
        documents=len(documents),
        total_arguments=total_args,
        total_relationships=total_rels,
    )

    return results
