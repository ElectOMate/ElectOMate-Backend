#!/usr/bin/env python3
"""Generate continuation arguments for all non-generated arguments in the graph.

Usage:
    .venv/bin/python scripts/generate_all_continuations.py
    .venv/bin/python scripts/generate_all_continuations.py --limit 50  # first 50 only
    .venv/bin/python scripts/generate_all_continuations.py --party FIDESZ
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Load .env
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

import structlog

logger = structlog.get_logger(__name__)


def load_arguments(party_filter=None, limit=None):
    """Load non-generated arguments from the graph."""
    import psycopg2

    age_url = os.environ["AGE_POSTGRES_URL"]
    conn = psycopg2.connect(age_url)
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute("LOAD 'age';")
    cur.execute("SET search_path = ag_catalog, '$user', public;")

    if party_filter:
        cur.execute(f"""
            SELECT * FROM cypher('hungarian_politics', $$
                MATCH (a:Argument)-[:MADE_BY]->(p:Party {{shortname: '{party_filter}'}})
                WHERE a.generated IS NULL OR a.generated = false
                RETURN a.text, p.shortname
            $$) as (text agtype, party agtype);
        """)
    else:
        cur.execute("""
            SELECT * FROM cypher('hungarian_politics', $$
                MATCH (a:Argument)
                WHERE a.generated IS NULL OR a.generated = false
                OPTIONAL MATCH (a)-[:MADE_BY]->(p:Party)
                RETURN a.text, p.shortname
            $$) as (text agtype, party agtype);
        """)

    args = []
    for row in cur.fetchall():
        text = str(row[0]).strip('"') if row[0] else ""
        party = str(row[1]).strip('"') if row[1] and str(row[1]) != "null" else None
        if text:
            args.append({"text": text, "party": party})

    conn.close()

    if limit:
        args = args[:limit]

    return args


async def main():
    parser = argparse.ArgumentParser(description="Generate continuations for all arguments")
    parser.add_argument("--limit", type=int, default=None, help="Max arguments to process")
    parser.add_argument("--party", type=str, default=None, help="Filter by party")
    args = parser.parse_args()

    from em_backend.graph.continuation import generate_and_insert_continuations

    arguments = load_arguments(party_filter=args.party, limit=args.limit)
    print(f"Loaded {len(arguments)} non-generated arguments")

    t0 = time.time()
    total_generated = 0
    total_skipped = 0
    errors = 0

    for i, arg in enumerate(arguments):
        try:
            result = await generate_and_insert_continuations(
                parent_claim=arg["text"],
                parent_party=arg["party"],
            )
            total_generated += result.inserted_count
            total_skipped += result.skipped_duplicate_count
            if (i + 1) % 10 == 0:
                elapsed = time.time() - t0
                print(f"  [{i+1}/{len(arguments)}] {total_generated} generated, {total_skipped} skipped ({elapsed:.0f}s)")
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.warning("continuation_failed", arg=arg["text"][:60], error=str(e))

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"CONTINUATIONS COMPLETE")
    print(f"  Arguments processed: {len(arguments)}")
    print(f"  Continuations generated: {total_generated}")
    print(f"  Duplicates skipped: {total_skipped}")
    print(f"  Errors: {errors}")
    print(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
