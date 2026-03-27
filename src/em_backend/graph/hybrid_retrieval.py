"""Hybrid retrieval: vector similarity + graph traversal + RRF fusion.

Combines pgvector semantic search with AGE Cypher graph traversal,
merging results via Reciprocal Rank Fusion (HybridRAG pattern).
"""

from __future__ import annotations

import os
import re
from typing import Any

import psycopg2
import structlog

from em_backend.graph.embeddings import embed_text, find_similar
from em_backend.graph.schema import SEED_TOPICS, SEED_PARTIES

logger = structlog.get_logger(__name__)

AGE_URL = os.environ.get(
    "AGE_POSTGRES_URL",
    "host=localhost port=5433 dbname=age_graph user=postgres password=postgres",
)
GRAPH = "hungarian_politics"

# Topic keywords for entity extraction
TOPIC_KEYWORDS: dict[str, list[str]] = {
    t["name"]: t["keywords"] for t in SEED_TOPICS
}
PARTY_NAMES: dict[str, str] = {
    p["shortname"]: p["name"] for p in SEED_PARTIES
}


def _cypher_read(query: str, columns: list[str]) -> list[dict]:
    """Execute a read Cypher query."""
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = False
    try:
        cur = conn.cursor()
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path = ag_catalog, '$user', public;")
        col_defs = ", ".join(f"{c} agtype" for c in columns)
        cur.execute(f"SELECT * FROM cypher('{GRAPH}', $$ {query} $$) as ({col_defs});")
        rows = cur.fetchall()
        conn.commit()
        results = []
        for row in rows:
            d = {}
            for i, c in enumerate(columns):
                v = row[i]
                if isinstance(v, str):
                    v = v.strip('"')
                d[c] = v
            results.append(d)
        return results
    except Exception as e:
        conn.rollback()
        logger.warning("Cypher query failed", error=str(e))
        return []
    finally:
        conn.close()


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    weights: list[float] | None = None,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Merge multiple ranked lists using Reciprocal Rank Fusion.

    RRF score = sum(weight_i / (k + rank_i)) for each list.

    Args:
        ranked_lists: List of ranked ID lists (best first).
        weights: Optional weight per list (default equal).
        k: RRF constant (standard = 60).

    Returns:
        List of (id, score) tuples sorted by fused score descending.
    """
    if weights is None:
        weights = [1.0] * len(ranked_lists)

    scores: dict[str, float] = {}
    for ranked, weight in zip(ranked_lists, weights):
        for rank, item_id in enumerate(ranked):
            scores[item_id] = scores.get(item_id, 0.0) + weight / (k + rank + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def extract_entities(query: str) -> tuple[list[str], list[str]]:
    """Extract topic and party mentions from a query string.

    Simple rule-based extraction — no LLM needed.

    Returns:
        (matched_topics, matched_parties)
    """
    query_lower = query.lower()
    topics = []
    parties = []

    # Match topics by keywords
    for topic_name, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in query_lower:
                topics.append(topic_name)
                break

    # Match parties by name/shortname
    party_aliases = {
        "fidesz": "FIDESZ", "orbán": "FIDESZ", "orban": "FIDESZ",
        "tisza": "TISZA", "magyar péter": "TISZA",
        "dk": "DK", "gyurcsány": "DK", "dobrev": "DK",
        "mi hazánk": "MI_HAZANK", "toroczkai": "MI_HAZANK",
        "mkkp": "MKKP", "kétfarkú": "MKKP",
        "jobbik": "JOBBIK",
        "mszp": "MSZP", "szocialista": "MSZP",
    }
    for alias, shortname in party_aliases.items():
        if alias in query_lower:
            if shortname not in parties:
                parties.append(shortname)

    return topics, parties


def graph_retrieval(
    topics: list[str],
    parties: list[str],
    limit: int = 30,
) -> list[str]:
    """Retrieve argument IDs via graph traversal (Cypher)."""
    results: list[dict] = []

    if topics and parties:
        for topic in topics[:2]:
            for party in parties[:2]:
                t = topic.replace("'", "\\'")
                found = _cypher_read(
                    f"MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{t}'}}) "
                    f"MATCH (a)-[:MADE_BY]->(p:Party {{shortname: '{party}'}}) "
                    f"RETURN a.text LIMIT {limit}",
                    ["text"],
                )
                results.extend(found)
    elif topics:
        for topic in topics[:3]:
            t = topic.replace("'", "\\'")
            found = _cypher_read(
                f"MATCH (a:Argument)-[:ABOUT]->(t:Topic {{name: '{t}'}}) "
                f"RETURN a.text LIMIT {limit}",
                ["text"],
            )
            results.extend(found)
    elif parties:
        for party in parties[:2]:
            found = _cypher_read(
                f"MATCH (a:Argument)-[:MADE_BY]->(p:Party {{shortname: '{party}'}}) "
                f"RETURN a.text LIMIT {limit}",
                ["text"],
            )
            results.extend(found)

    # Deduplicate preserving order
    seen = set()
    ids = []
    for r in results:
        text = str(r.get("text", ""))
        aid = f"arg::{text[:80]}"
        if aid not in seen:
            seen.add(aid)
            ids.append(aid)

    return ids[:limit]


def hybrid_search(
    query: str,
    limit: int = 20,
    vector_weight: float = 0.6,
    graph_weight: float = 0.4,
    min_similarity: float = 0.3,
    party_filter: str | None = None,
    topic_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Hybrid retrieval combining vector similarity and graph traversal.

    1. Vector path: embed query → pgvector cosine search → ranked argument IDs
    2. Graph path: extract entities → Cypher traversal → ranked argument IDs
    3. RRF fusion: merge both ranked lists

    Args:
        query: Free-text search query (Hungarian or English).
        limit: Max results to return.
        vector_weight: Weight for vector results in RRF (default 0.6).
        graph_weight: Weight for graph results in RRF (default 0.4).
        min_similarity: Minimum cosine similarity for vector results.
        party_filter: Optional party shortname filter.
        topic_filter: Optional topic name filter.

    Returns:
        List of argument dicts with text, party, similarity, and fused score.
    """
    # Path 1: Vector similarity
    query_embedding = embed_text(query)
    vector_results = find_similar(
        query_embedding,
        limit=limit * 2,
        min_similarity=min_similarity,
        party_filter=party_filter,
        topic_filter=topic_filter,
    )
    vector_ids = [r["id"] for r in vector_results]
    vector_lookup = {r["id"]: r for r in vector_results}

    # Path 2: Graph traversal
    topics, parties = extract_entities(query)
    if party_filter:
        parties = [party_filter]
    if topic_filter:
        topics = [topic_filter]

    graph_ids = graph_retrieval(topics, parties, limit=limit * 2)

    # RRF fusion
    fused = reciprocal_rank_fusion(
        [vector_ids, graph_ids],
        weights=[vector_weight, graph_weight],
    )

    # Build result list with metadata
    results = []
    for item_id, score in fused[:limit]:
        if item_id in vector_lookup:
            r = vector_lookup[item_id]
            r["fused_score"] = score
            results.append(r)
        else:
            # Graph-only result — look up text from ID
            text = item_id.replace("arg::", "")
            results.append({
                "id": item_id,
                "text": text,
                "party": None,
                "topics": None,
                "similarity": 0.0,
                "fused_score": score,
                "source": "graph_only",
            })

    logger.info(
        "Hybrid search complete",
        query=query[:50],
        vector_results=len(vector_ids),
        graph_results=len(graph_ids),
        fused_results=len(results),
        topics_found=topics,
        parties_found=parties,
    )

    return results
