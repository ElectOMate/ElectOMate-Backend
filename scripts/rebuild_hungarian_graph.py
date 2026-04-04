#!/usr/bin/env python3
"""Rebuild the Hungarian political knowledge graph from scratch.

Full pipeline:
1. Ensure AGE graph exists & initialize schema (topics, parties)
2. Ingest all 7 Hungarian party manifestos via argument extraction (GPT-4o)
3. Enrich graph metadata (politicians, platforms, locations, orgs)
4. Compute BGE-M3 embeddings and store in pgvector
5. Detect inter-argument relationships (SUPPORTS/REBUTS/CONTRADICTS)

Prerequisites:
- AGE PostgreSQL running on port 5433 (docker compose up age-postgres -d)
- OPENAI_API_KEY set in environment or .env
- Python venv with all deps installed

Usage:
    # Full rebuild (default)
    python scripts/rebuild_hungarian_graph.py

    # Skip expensive steps
    python scripts/rebuild_hungarian_graph.py --skip-relationships
    python scripts/rebuild_hungarian_graph.py --skip-embeddings
    python scripts/rebuild_hungarian_graph.py --schema-only
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Load .env if present
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    for line in open(env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

AGE_URL = os.environ.get(
    "AGE_POSTGRES_URL",
    "host=localhost port=5433 dbname=age_graph user=postgres password=postgres",
)


def check_prerequisites():
    """Verify AGE is reachable and OPENAI_API_KEY is set."""
    import psycopg2

    print("Checking prerequisites...")

    # Check DB connection
    try:
        conn = psycopg2.connect(AGE_URL)
        conn.close()
        print("  [OK] AGE PostgreSQL reachable")
    except Exception as e:
        print(f"  [FAIL] Cannot connect to AGE: {e}")
        print("  → Run: docker compose -f docker-compose.graph.yml up age-postgres -d")
        sys.exit(1)

    # Check OpenAI key
    if not os.environ.get("OPENAI_API_KEY"):
        print("  [FAIL] OPENAI_API_KEY not set")
        print("  → Set it in .env or export OPENAI_API_KEY=...")
        sys.exit(1)
    print("  [OK] OPENAI_API_KEY set")

    # Ensure pgvector extension and argument_embeddings table exist
    try:
        conn = psycopg2.connect(AGE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS argument_embeddings (
                id SERIAL PRIMARY KEY,
                argument_id TEXT UNIQUE NOT NULL,
                argument_text TEXT NOT NULL,
                embedding vector(1024) NOT NULL,
                party TEXT,
                topics TEXT[],
                speaker TEXT,
                arg_type TEXT,
                sentiment TEXT,
                source_date TEXT,
                platform TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_argument_embeddings_hnsw
                ON argument_embeddings USING hnsw (embedding vector_cosine_ops);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_argument_embeddings_party
                ON argument_embeddings (party);
        """)
        conn.close()
        print("  [OK] pgvector table argument_embeddings ready")
    except Exception as e:
        print(f"  [WARN] Could not create pgvector table: {e}")


def step_1_schema():
    """Initialize graph schema with topics and parties."""
    print("\n" + "=" * 60)
    print("STEP 1: Initialize schema (topics + parties)")
    print("=" * 60)

    from em_backend.graph.schema import initialize_schema, get_graph_stats

    initialize_schema()

    stats = get_graph_stats()
    for label, count in stats.items():
        print(f"  {label}: {count}")


async def step_2_ingest_manifestos():
    """Extract arguments from all 7 Hungarian manifestos."""
    print("\n" + "=" * 60)
    print("STEP 2: Ingest Hungarian manifestos (GPT-4o argument extraction)")
    print("=" * 60)

    from em_backend.graph.connectors.manifesto import extract_all_hungarian_manifestos
    from em_backend.graph.builder import ingest_documents
    from em_backend.graph.schema import get_graph_stats

    docs = extract_all_hungarian_manifestos()
    print(f"  Extracted text from {len(docs)} manifestos:")
    for doc in docs:
        party = doc.metadata.get("party_shortname", "?")
        pages = doc.metadata.get("total_pages", 0)
        chars = len(doc.raw_text)
        print(f"    {party}: {pages} pages, {chars:,} chars")

    if not docs:
        print("  [WARN] No manifesto PDFs found. Skipping ingestion.")
        return

    t0 = time.time()
    results = await ingest_documents(docs, detect_relations=False)
    elapsed = time.time() - t0

    total_args = sum(r["arguments_inserted"] for r in results)
    total_topics = sum(r["topics_linked"] for r in results)
    total_parties = sum(r["parties_linked"] for r in results)

    print(f"\n  Ingestion complete in {elapsed:.0f}s:")
    print(f"    Arguments inserted: {total_args}")
    print(f"    Topic links: {total_topics}")
    print(f"    Party links: {total_parties}")

    stats = get_graph_stats()
    print(f"\n  Graph stats after ingestion:")
    for label, count in stats.items():
        print(f"    {label}: {count}")


def step_3_enrich():
    """Run metadata enrichment (politicians, platforms, etc.)."""
    print("\n" + "=" * 60)
    print("STEP 3: Enrich graph metadata")
    print("=" * 60)

    # Import and run the enrichment script's main logic
    import importlib.util
    script_path = os.path.join(os.path.dirname(__file__), "enrich_graph_metadata.py")
    if os.path.exists(script_path):
        spec = importlib.util.spec_from_file_location("enrich", script_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
        else:
            print("  [SKIP] enrich_graph_metadata.py has no main()")
    else:
        print("  [SKIP] enrich_graph_metadata.py not found")


def step_4_embeddings():
    """Compute BGE-M3 embeddings and store in pgvector."""
    print("\n" + "=" * 60)
    print("STEP 4: Compute BGE-M3 embeddings")
    print("=" * 60)

    import importlib.util
    script_path = os.path.join(os.path.dirname(__file__), "embed_all_arguments.py")
    if os.path.exists(script_path):
        spec = importlib.util.spec_from_file_location("embed", script_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
        else:
            print("  [SKIP] embed_all_arguments.py has no main()")
    else:
        print("  [SKIP] embed_all_arguments.py not found")


def step_5_relationships():
    """Detect inter-argument relationships using GPT-4o."""
    print("\n" + "=" * 60)
    print("STEP 5: Detect argument relationships (GPT-4o)")
    print("=" * 60)

    import importlib.util
    script_path = os.path.join(os.path.dirname(__file__), "detect_global_relationships.py")
    if os.path.exists(script_path):
        spec = importlib.util.spec_from_file_location("rels", script_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
        else:
            print("  [SKIP] detect_global_relationships.py has no main()")
    else:
        print("  [SKIP] detect_global_relationships.py not found")


def print_final_stats():
    """Print final graph statistics."""
    print("\n" + "=" * 60)
    print("REBUILD COMPLETE")
    print("=" * 60)

    from em_backend.graph.schema import get_graph_stats
    stats = get_graph_stats()
    for label, count in stats.items():
        print(f"  {label}: {count}")

    try:
        from em_backend.graph.embeddings import get_embedding_count
        print(f"  Embeddings: {get_embedding_count()}")
    except Exception:
        pass


async def main():
    parser = argparse.ArgumentParser(description="Rebuild Hungarian political knowledge graph")
    parser.add_argument("--skip-relationships", action="store_true", help="Skip relationship detection (saves GPT-4o tokens)")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip BGE-M3 embedding computation")
    parser.add_argument("--skip-enrichment", action="store_true", help="Skip metadata enrichment")
    parser.add_argument("--schema-only", action="store_true", help="Only create schema and seed data")
    args = parser.parse_args()

    t_start = time.time()

    check_prerequisites()

    # Step 1: Always run schema
    step_1_schema()

    if args.schema_only:
        print_final_stats()
        return

    # Step 2: Ingest manifestos
    await step_2_ingest_manifestos()

    # Step 3: Enrich
    if not args.skip_enrichment:
        step_3_enrich()

    # Step 4: Embeddings
    if not args.skip_embeddings:
        step_4_embeddings()

    # Step 5: Relationships
    if not args.skip_relationships:
        step_5_relationships()

    print_final_stats()
    elapsed = time.time() - t_start
    print(f"\n  Total time: {elapsed / 60:.1f} minutes")


if __name__ == "__main__":
    asyncio.run(main())
