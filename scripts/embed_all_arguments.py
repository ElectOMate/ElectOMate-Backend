"""Embed all arguments in the knowledge graph using BGE-M3.

Reads arguments from Apache AGE, computes embeddings with BGE-M3,
stores in pgvector table for semantic similarity search.

Usage: python scripts/embed_all_arguments.py
"""

import os
import sys
import time

import psycopg2

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

AGE_URL = os.environ.get(
    "AGE_POSTGRES_URL",
    "host=localhost port=5433 dbname=age_graph user=postgres password=postgres",
)


def load_arguments() -> list[dict]:
    """Load all arguments from AGE graph with metadata."""
    conn = psycopg2.connect(AGE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("LOAD 'age';")
    cur.execute("SET search_path = ag_catalog, '$user', public;")

    # Get arguments with party
    cur.execute("""
        SELECT * FROM cypher('hungarian_politics', $$
            MATCH (a:Argument)
            OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party)
            RETURN a.text, p.shortname, a.speaker, a.argument_type, a.sentiment
        $$) as (text agtype, party agtype, speaker agtype, arg_type agtype, sentiment agtype);
    """)

    arguments = []
    seen = set()
    for row in cur.fetchall():
        text = str(row[0]).strip('"') if row[0] else ""
        if not text or text in seen:
            continue
        seen.add(text)

        party = str(row[1]).strip('"') if row[1] else None
        speaker = str(row[2]).strip('"') if row[2] else None
        arg_type = str(row[3]).strip('"') if row[3] else None
        sentiment = str(row[4]).strip('"') if row[4] else None

        arguments.append({
            "id": f"arg::{text[:80]}",
            "text": text,
            "party": party if party and party != "null" else None,
            "speaker": speaker if speaker and speaker != "null" else None,
            "topics": [],  # will be filled below
            "arg_type": arg_type,
            "sentiment": sentiment,
        })

    # Get topics for each argument
    for arg in arguments:
        escaped = arg["text"][:200].replace("'", "\\'")
        try:
            cur.execute(f"""
                SELECT * FROM cypher('hungarian_politics', $$
                    MATCH (a:Argument {{text: '{escaped}'}})-[:ABOUT]->(t:Topic)
                    RETURN t.name
                $$) as (topic agtype);
            """)
            arg["topics"] = [str(r[0]).strip('"') for r in cur.fetchall()]
            conn.commit()
        except Exception:
            conn.rollback()
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path = ag_catalog, '$user', public;")

    conn.close()
    return arguments


def main():
    print("=" * 60)
    print("BGE-M3 Argument Embedding Pipeline")
    print("=" * 60)

    # Step 1: Load arguments
    print("\n1. Loading arguments from AGE graph...")
    arguments = load_arguments()
    print(f"   Loaded {len(arguments)} unique arguments")

    if not arguments:
        print("   No arguments found. Exiting.")
        return

    # Show sample
    for a in arguments[:3]:
        print(f"   [{a['party'] or '?'}] {a['text'][:80]}...")

    # Step 2: Compute embeddings
    print(f"\n2. Computing BGE-M3 embeddings ({len(arguments)} texts)...")
    from em_backend.graph.embeddings import embed_batch, store_embeddings_batch

    texts = [a["text"] for a in arguments]
    t0 = time.time()
    embeddings = embed_batch(texts, batch_size=32)
    elapsed = time.time() - t0
    print(f"   Embedded {len(embeddings)} arguments in {elapsed:.1f}s ({len(arguments)/elapsed:.0f} args/sec)")

    # Step 3: Store in pgvector
    print(f"\n3. Storing embeddings in pgvector...")
    stored = store_embeddings_batch(arguments, embeddings)
    print(f"   Stored {stored}/{len(arguments)} embeddings")

    # Step 4: Test similarity
    print(f"\n4. Testing semantic similarity...")
    from em_backend.graph.embeddings import find_similar_to_text, cosine_similarity, embed_text

    # Test: should find similar arguments
    test_queries = [
        ("adócsökkentés és gazdasági növekedés", "Economy/tax query"),
        ("korrupció elleni harc Magyarországon", "Corruption query"),
        ("EU-tagság és szuverenitás", "EU relations query"),
    ]

    for query, desc in test_queries:
        results = find_similar_to_text(query, limit=3, min_similarity=0.3)
        print(f"\n   Query: '{query}' ({desc})")
        for r in results:
            print(f"     [{r['party'] or '?'}] sim={r['similarity']:.3f} | {r['text'][:80]}")

    # Test: paraphrase detection
    print(f"\n5. Paraphrase detection test...")
    e1 = embed_text("Az adók csökkentése szükséges.")
    e2 = embed_text("Adócsökkentést kell végrehajtani.")
    e3 = embed_text("A migráció elleni harc fontos.")
    print(f"   'adók csökkentése' vs 'adócsökkentés': {cosine_similarity(e1, e2):.3f} (should be > 0.8)")
    print(f"   'adók csökkentése' vs 'migráció elleni': {cosine_similarity(e1, e3):.3f} (should be < 0.5)")

    # Final stats
    from em_backend.graph.embeddings import get_embedding_count
    print(f"\n{'=' * 60}")
    print(f"EMBEDDING COMPLETE")
    print(f"  Total embeddings stored: {get_embedding_count()}")
    print(f"  Embedding dimension: 1024 (BGE-M3)")
    print(f"  Index type: HNSW (cosine)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
