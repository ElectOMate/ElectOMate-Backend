"""Embedding service for argument semantic similarity.

Uses BGE-M3 (BAAI/bge-m3) for multilingual embeddings — best
performer on Hungarian text per benchmarks (Harang 2024).
Stores embeddings in pgvector within the AGE PostgreSQL instance.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np
import psycopg2
import structlog

logger = structlog.get_logger(__name__)

# Connection to AGE PostgreSQL (same instance, pgvector extension)
AGE_URL = os.environ.get(
    "AGE_POSTGRES_URL",
    "host=localhost port=5433 dbname=age_graph user=postgres password=postgres",
)

# Model config
MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

# Singleton model
_model = None


def get_model():
    """Load BGE-M3 model (lazy singleton)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading BGE-M3 embedding model...", model=MODEL_NAME)
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("BGE-M3 model loaded", dim=EMBEDDING_DIM)
    return _model


def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    model = get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed multiple texts efficiently."""
    model = get_model()
    embeddings = model.encode(
        texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=True
    )
    return embeddings.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va, vb = np.array(a), np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


# ============================================================================
# pgvector storage
# ============================================================================


def _get_conn():
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = True
    return conn


def store_embedding(
    argument_id: str,
    text: str,
    embedding: list[float],
    party: str | None = None,
    topics: list[str] | None = None,
    speaker: str | None = None,
    source_date: str | None = None,
    platform: str | None = None,
) -> None:
    """Store an argument embedding in pgvector."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO argument_embeddings
               (argument_id, argument_text, embedding, party, topics, speaker, source_date, platform)
               VALUES (%s, %s, %s::vector, %s, %s, %s, %s, %s)
               ON CONFLICT (argument_id) DO UPDATE SET
                 embedding = EXCLUDED.embedding,
                 party = EXCLUDED.party,
                 topics = EXCLUDED.topics,
                 speaker = EXCLUDED.speaker,
                 source_date = EXCLUDED.source_date,
                 platform = EXCLUDED.platform
            """,
            (
                argument_id,
                text[:2000],
                str(embedding),
                party,
                topics,
                speaker,
                source_date,
                platform,
            ),
        )
    finally:
        conn.close()


def store_embeddings_batch(
    items: list[dict],
    embeddings: list[list[float]],
) -> int:
    """Store multiple embeddings efficiently."""
    conn = _get_conn()
    stored = 0
    try:
        cur = conn.cursor()
        for item, emb in zip(items, embeddings):
            try:
                cur.execute(
                    """INSERT INTO argument_embeddings
                       (argument_id, argument_text, embedding, party, topics, speaker, source_date, platform)
                       VALUES (%s, %s, %s::vector, %s, %s, %s, %s, %s)
                       ON CONFLICT (argument_id) DO UPDATE SET
                         embedding = EXCLUDED.embedding,
                         party = EXCLUDED.party,
                         topics = EXCLUDED.topics
                    """,
                    (
                        item["id"],
                        item["text"][:2000],
                        str(emb),
                        item.get("party"),
                        item.get("topics"),
                        item.get("speaker"),
                        item.get("source_date"),
                        item.get("platform"),
                    ),
                )
                stored += 1
            except Exception as e:
                logger.warning("Failed to store embedding", id=item["id"], error=str(e))
    finally:
        conn.close()
    return stored


def find_similar(
    query_embedding: list[float],
    limit: int = 20,
    min_similarity: float = 0.5,
    party_filter: str | None = None,
    topic_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Find semantically similar arguments using pgvector cosine distance."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        vec_str = str(query_embedding)

        filters = []
        params: list = []

        if party_filter:
            filters.append("party = %s")
            params.append(party_filter)

        if topic_filter:
            filters.append("%s = ANY(topics)")
            params.append(topic_filter)

        where = ""
        if filters:
            where = "WHERE " + " AND ".join(filters)

        cur.execute(
            f"""SELECT argument_id, argument_text, party, topics, speaker,
                       1 - (embedding <=> '{vec_str}'::vector) as similarity
                FROM argument_embeddings
                {where}
                ORDER BY embedding <=> '{vec_str}'::vector
                LIMIT %s""",
            params + [limit],
        )

        results = []
        for row in cur.fetchall():
            results.append({
                "id": row[0],
                "text": row[1],
                "party": row[2],
                "topics": row[3],
                "speaker": row[4],
                "similarity": float(row[5]),
            })
        return results
    finally:
        conn.close()


def find_similar_to_text(
    text: str,
    limit: int = 20,
    min_similarity: float = 0.5,
    **kwargs,
) -> list[dict[str, Any]]:
    """Embed text then find similar arguments."""
    embedding = embed_text(text)
    return find_similar(embedding, limit, min_similarity, **kwargs)


def get_embedding_count() -> int:
    """Get total number of stored embeddings."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM argument_embeddings")
        return cur.fetchone()[0]
    finally:
        conn.close()
