#!/usr/bin/env python3
"""CLI for Knowledge Graph operations.

Usage:
    python scripts/kg_cli.py search "adócsökkentés"
    python scripts/kg_cli.py add "Az adók csökkentése szükséges." --party FIDESZ --topic Gazdaság
    python scripts/kg_cli.py query --topic Egészségügy --party MSZP
    python scripts/kg_cli.py stats
    python scripts/kg_cli.py continuations "argument text..."
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

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


def cmd_search(args):
    from em_backend.graph.embeddings import find_similar_to_text
    results = find_similar_to_text(args.query, limit=args.limit, min_similarity=0.3)
    if not results:
        print("No results found.")
        return
    for r in results:
        party = r.get("party") or "?"
        sim = r.get("similarity", 0)
        text = r.get("text", "")[:120]
        print(f"  [{party}] sim={sim:.3f} | {text}")
        quote = r.get("source_quote")
        if quote:
            print(f"    Quote: {quote[:100]}")


def cmd_add(args):
    from em_backend.graph.deduplication import check_duplicate
    from em_backend.graph.continuation import generate_and_insert_continuations
    from em_backend.graph.db import get_graph_db
    from em_backend.graph.embeddings import embed_text, store_embedding

    async def _add():
        dedup = await check_duplicate(args.text, party=args.party)
        print(f"Dedup: action={dedup.action}, sim={dedup.similarity_score:.3f}")

        if dedup.action == "skip":
            print(f"Skipped: duplicate of existing argument")
            print(f"  Existing: {dedup.existing_text[:100]}")
            return

        # Insert
        g = get_graph_db()
        _escape = lambda s: s.replace("'", "\\'") if s else ""
        claim_esc = _escape(args.text)

        g.write(f"""
            CREATE (a:Argument {{
                text: '{claim_esc}',
                generated: false,
                argument_type: 'user_submitted'
            }}) RETURN a
        """)
        print(f"Inserted argument.")

        # Link to party
        if args.party:
            try:
                g.write(f"""
                    MATCH (a:Argument {{text: '{claim_esc}'}})
                    MATCH (p:Party {{shortname: '{args.party}'}})
                    MERGE (a)-[:MADE_BY]->(p)
                """)
            except Exception:
                pass

        # Link to topic
        if args.topic:
            try:
                g.write(f"""
                    MATCH (a:Argument {{text: '{claim_esc}'}})
                    MATCH (t:Topic {{name: '{_escape(args.topic)}'}})
                    MERGE (a)-[:ABOUT]->(t)
                """)
            except Exception:
                pass

        # Embed
        try:
            embedding = embed_text(args.text)
            store_embedding(
                argument_id=f"user::{args.text[:80]}",
                text=args.text,
                embedding=embedding,
                party=args.party,
            )
        except Exception as e:
            print(f"Embed warning: {e}")

        # Generate continuations
        result = await generate_and_insert_continuations(
            args.text, parent_party=args.party, parent_topic=args.topic, graph=g
        )
        print(f"Continuations: {result.inserted_count} inserted, {result.skipped_duplicate_count} skipped")
        for c in result.continuations:
            print(f"  [{c.continuation_type}] {c.claim[:100]}")

    asyncio.run(_add())


def cmd_query(args):
    from em_backend.graph.query_service import KnowledgeGraphService
    svc = KnowledgeGraphService()

    if args.topic and args.party:
        results = svc.get_arguments_by_topic_and_party(args.topic, args.party, limit=args.limit)
    elif args.topic:
        results = svc.get_arguments_by_topic(args.topic, limit=args.limit)
    elif args.party:
        results = svc.get_arguments_by_party(args.party, limit=args.limit)
    else:
        print("Specify --topic and/or --party")
        return

    if not results:
        print("No results.")
        return
    for a in results:
        print(f"  [{a.party or '?'}] {a.text[:120]}")


def cmd_stats(args):
    from em_backend.graph.schema import get_graph_stats
    from em_backend.graph.embeddings import get_embedding_count

    stats = get_graph_stats()
    print("Graph stats:")
    for label, count in stats.items():
        print(f"  {label}: {count}")

    try:
        print(f"  Embeddings: {get_embedding_count()}")
    except Exception:
        print("  Embeddings: (table not ready)")


def main():
    parser = argparse.ArgumentParser(description="Knowledge Graph CLI")
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search", help="Semantic search")
    p_search.add_argument("query", type=str)
    p_search.add_argument("--limit", type=int, default=10)
    p_search.set_defaults(func=cmd_search)

    p_add = sub.add_parser("add", help="Add a new argument")
    p_add.add_argument("text", type=str)
    p_add.add_argument("--party", type=str, default=None)
    p_add.add_argument("--topic", type=str, default=None)
    p_add.set_defaults(func=cmd_add)

    p_query = sub.add_parser("query", help="Query by topic/party")
    p_query.add_argument("--topic", type=str, default=None)
    p_query.add_argument("--party", type=str, default=None)
    p_query.add_argument("--limit", type=int, default=20)
    p_query.set_defaults(func=cmd_query)

    p_stats = sub.add_parser("stats", help="Show graph stats")
    p_stats.set_defaults(func=cmd_stats)

    parsed = parser.parse_args()
    if not parsed.command:
        parser.print_help()
        return

    parsed.func(parsed)


if __name__ == "__main__":
    main()
