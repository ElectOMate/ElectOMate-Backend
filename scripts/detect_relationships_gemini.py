#!/usr/bin/env python3
"""Detect SUPPORTS/REBUTS/CONTRADICTS relationships using Gemini + embedding pre-filter.

Pre-filters argument pairs by cosine similarity (> 0.5), then classifies via Gemini.

Usage:
    .venv/bin/python scripts/detect_relationships_gemini.py
    .venv/bin/python scripts/detect_relationships_gemini.py --limit 200  # top 200 pairs
    .venv/bin/python scripts/detect_relationships_gemini.py --min-sim 0.6  # stricter filter
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

os.environ.setdefault(
    "AGE_POSTGRES_URL",
    "host=localhost port=5433 dbname=age_graph user=postgres password=postgres",
)

import psycopg2
import structlog
from google import genai
from google.genai import types

logger = structlog.get_logger(__name__)

AGE_URL = os.environ["AGE_POSTGRES_URL"]
GRAPH = "hungarian_politics"


def find_similar_pairs_sql(min_similarity=0.5, max_pairs=300):
    """Find similar cross-party argument pairs using pgvector SQL."""
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Use pgvector's built-in cosine distance operator for efficiency
    cur.execute(f"""
        SELECT
            a.argument_id, a.argument_text, a.party,
            b.argument_id, b.argument_text, b.party,
            1 - (a.embedding <=> b.embedding) as similarity
        FROM argument_embeddings a
        CROSS JOIN LATERAL (
            SELECT argument_id, argument_text, party, embedding
            FROM argument_embeddings
            WHERE argument_id > a.argument_id
              AND party IS DISTINCT FROM a.party
            ORDER BY embedding <=> a.embedding
            LIMIT 3
        ) b
        WHERE 1 - (a.embedding <=> b.embedding) > %s
        ORDER BY similarity DESC
        LIMIT %s
    """, (min_similarity, max_pairs))

    pairs = []
    for row in cur.fetchall():
        pairs.append({
            "id_a": row[0], "text_a": row[1], "party_a": row[2],
            "id_b": row[3], "text_b": row[4], "party_b": row[5],
            "similarity": float(row[6]),
        })

    conn.close()
    logger.info("pairs_found", count=len(pairs))
    return pairs


def classify_relationship(client, model, text_a, party_a, text_b, party_b):
    """Classify relationship between two arguments using Gemini."""
    prompt = f"""You are analyzing two Hungarian political arguments. Determine their logical relationship.

ARGUMENT A by {party_a or 'Unknown'}: {text_a[:300]}

ARGUMENT B by {party_b or 'Unknown'}: {text_b[:300]}

Choose exactly one relationship type:
SUPPORTS - A provides evidence or reasoning that strengthens B
REBUTS - A directly counters or argues against B
CONTRADICTS - A and B make incompatible claims on the same topic
UNRELATED - No meaningful logical connection

Respond with a JSON object containing relation, confidence (0-1), and a brief explanation."""

    import re
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=500,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        text = response.text or ""
        # Extract JSON from markdown-wrapped response
        match = re.search(r'\{[^}]+\}', text)
        if match:
            return json.loads(match.group())
        return {"relation": "UNRELATED", "confidence": 0.0}
    except Exception as e:
        logger.warning("classify_failed", error=str(e)[:80])
        return {"relation": "UNRELATED", "confidence": 0.0}


def insert_relationship(conn, text_a, text_b, rel_type):
    """Insert a relationship edge into the graph."""
    cur = conn.cursor()
    cur.execute("LOAD 'age';")
    cur.execute("SET search_path = ag_catalog, '$user', public;")

    esc = lambda s: s.replace("'", "\\'") if s else ""
    try:
        cur.execute(f"""
            SELECT * FROM cypher('{GRAPH}', $$
                MATCH (a1:Argument {{text: '{esc(text_a[:300])}'}})
                MATCH (a2:Argument {{text: '{esc(text_b[:300])}'}})
                MERGE (a1)-[:{rel_type}]->(a2)
                RETURN a1.text
            $$) as (v agtype);
        """)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.debug("insert_rel_failed", error=str(e))
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-sim", type=float, default=0.5)
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--min-confidence", type=float, default=0.6)
    args = parser.parse_args()

    print(f"Finding cross-party pairs with similarity > {args.min_sim} (SQL)...")
    pairs = find_similar_pairs_sql(min_similarity=args.min_sim, max_pairs=args.limit)
    print(f"  Found {len(pairs)} candidate pairs")

    if not pairs:
        print("No pairs to classify.")
        return

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = False

    t0 = time.time()
    counts = {"SUPPORTS": 0, "REBUTS": 0, "CONTRADICTS": 0, "UNRELATED": 0, "errors": 0}

    for idx, pair in enumerate(pairs):
        result = classify_relationship(
            client, model,
            pair["text_a"], pair["party_a"],
            pair["text_b"], pair["party_b"],
        )
        rel = result.get("relation", "UNRELATED")
        conf = result.get("confidence", 0.0)

        if rel != "UNRELATED" and conf >= args.min_confidence:
            ok = insert_relationship(conn, pair["text_a"], pair["text_b"], rel)
            if ok:
                counts[rel] = counts.get(rel, 0) + 1
                total_rels = sum(v for k, v in counts.items() if k not in ("UNRELATED", "errors"))
                if total_rels <= 10:
                    print(f"  [{rel}] {pair['party_a'] or '?'}: {pair['text_a'][:50]} --> {pair['party_b'] or '?'}: {pair['text_b'][:50]}")
            else:
                counts["errors"] += 1
        else:
            counts["UNRELATED"] += 1

        if (idx + 1) % 50 == 0:
            print(f"  [{idx+1}/{len(pairs)}] {counts}")

    conn.close()
    elapsed = time.time() - t0

    print(f"\n{'='*60}")
    print(f"RELATIONSHIP DETECTION COMPLETE")
    print(f"  Pairs evaluated: {len(pairs)}")
    print(f"  SUPPORTS: {counts['SUPPORTS']}")
    print(f"  REBUTS: {counts['REBUTS']}")
    print(f"  CONTRADICTS: {counts['CONTRADICTS']}")
    print(f"  UNRELATED: {counts['UNRELATED']}")
    print(f"  Errors: {counts['errors']}")
    print(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
