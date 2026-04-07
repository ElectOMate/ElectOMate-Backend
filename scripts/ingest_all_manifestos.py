#!/usr/bin/env python3
"""Deep-extract and ingest all Hungarian manifesto PDFs into the knowledge graph.

Processes each PDF page-by-page for precise source attribution.
Each argument gets source_quote, source_page, source_section.

Usage:
    .venv/bin/python scripts/ingest_all_manifestos.py
    .venv/bin/python scripts/ingest_all_manifestos.py --skip-large  # only small PDFs
    .venv/bin/python scripts/ingest_all_manifestos.py --party FIDESZ  # single party
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

# Ensure AGE connection points to the graph DB (port 5433), not the main DB
os.environ.setdefault(
    "AGE_POSTGRES_URL",
    "host=localhost port=5433 dbname=age_graph user=postgres password=postgres",
)

import structlog

logger = structlog.get_logger(__name__)

# All Hungarian manifesto PDFs to process
MANIFESTO_FILES = {
    # Small compiled manifestos
    "FIDESZ": "FIDESZ.pdf",
    "TISZA": "TISZA.pdf",
    "DK": "DK.pdf",
    "MI_HAZANK": "MI_HAZANK.pdf",
    "MKKP": "MKKP.pdf",
    "JOBBIK": "JOBBIK.pdf",
    "MSZP": "MSZP.pdf",
}

LARGE_MANIFESTO_FILES = {
    "TISZA": "TISZA_full.pdf",
    "MI_HAZANK": "MI_HAZANK_full.pdf",
    "DK": "DK_full.pdf",
    "DK_bg": "DK_background.pdf",
}


async def main():
    parser = argparse.ArgumentParser(description="Ingest Hungarian manifestos")
    parser.add_argument("--skip-large", action="store_true", help="Skip large PDFs")
    parser.add_argument("--party", type=str, help="Process single party only")
    parser.add_argument("--wipe", action="store_true", help="Wipe existing arguments first")
    args = parser.parse_args()

    from pathlib import Path
    from em_backend.graph.connectors.manifesto import extract_manifesto
    from em_backend.graph.extraction.argument_miner import extract_arguments_by_page
    from em_backend.graph.builder import ingest_document
    from em_backend.graph.schema import initialize_schema, get_graph_stats
    from em_backend.graph.db import get_graph_db

    manifesto_dir = Path(__file__).parent.parent / "assets" / "manifestos"
    graph = get_graph_db()

    # Optionally wipe existing arguments
    if args.wipe:
        logger.info("wiping_existing_arguments")
        try:
            graph.write("MATCH (a:Argument) DETACH DELETE a")
            logger.info("wiped_arguments")
        except Exception as e:
            logger.warning("wipe_failed", error=str(e))

    # Ensure schema exists
    initialize_schema(graph)

    # Build file list
    files_to_process = {}
    for party, filename in MANIFESTO_FILES.items():
        if args.party and party != args.party:
            continue
        files_to_process[f"{party}_small"] = (party, filename)

    if not args.skip_large:
        for party, filename in LARGE_MANIFESTO_FILES.items():
            if args.party and not party.startswith(args.party):
                continue
            files_to_process[f"{party}_large"] = (party.split("_")[0] if "_" in party else party, filename)

    logger.info("ingestion_start", files=len(files_to_process))
    t_start = time.time()

    total_args = 0
    args_by_party = {}
    results = []

    for key, (party, filename) in files_to_process.items():
        pdf_path = manifesto_dir / filename
        if not pdf_path.exists():
            logger.warning("pdf_not_found", party=party, file=filename)
            continue

        logger.info("processing_manifesto", party=party, file=filename, size_kb=pdf_path.stat().st_size // 1024)

        try:
            # Extract text from PDF
            doc = extract_manifesto(pdf_path, party)
            logger.info("pdf_extracted",
                party=party,
                pages=len(doc.segments),
                chars=len(doc.raw_text))

            # Extract arguments page-by-page
            extraction = await extract_arguments_by_page(doc, min_args_per_page=2, max_args_per_page=8)
            logger.info("arguments_extracted",
                party=party,
                file=filename,
                count=len(extraction.arguments))

            # Ingest into graph
            from em_backend.graph.connectors.base import IngestedDocument
            stats = await ingest_document(doc, graph=graph, detect_relations=False)
            # Also insert the page-level extracted arguments manually
            _escape = lambda s: s.replace("'", "\\'") if s else ""
            source_url = doc.source_path or f"local://{doc.title}"

            for arg in extraction.arguments:
                claim_escaped = _escape(arg.claim)
                source_quote_escaped = _escape(arg.source_quote[:280]) if arg.source_quote else ""
                source_section_escaped = _escape(arg.source_section) if arg.source_section else ""

                try:
                    graph.write(f"""
                        MERGE (a:Argument {{text: '{claim_escaped}'}})
                        SET a.type = 'claim',
                            a.summary = '{_escape(arg.conclusion or arg.claim[:200])}',
                            a.argument_type = '{arg.argument_type}',
                            a.sentiment = '{arg.sentiment}',
                            a.strength = {arg.strength},
                            a.source_quote = '{source_quote_escaped}',
                            a.source_page = {arg.source_page or 0},
                            a.source_section = '{source_section_escaped}',
                            a.generated = false
                        RETURN a
                    """)

                    # Link to source
                    graph.write(f"""
                        MATCH (a:Argument {{text: '{claim_escaped}'}})
                        MATCH (s:Source {{url: '{_escape(source_url)}'}})
                        MERGE (a)-[:SOURCED_FROM]->(s)
                    """)

                    # Link to party
                    if arg.party:
                        try:
                            from em_backend.graph.extraction.entity_resolver import resolve_party
                            resolved = resolve_party(arg.party)
                            if resolved:
                                graph.write(f"""
                                    MATCH (a:Argument {{text: '{claim_escaped}'}})
                                    MATCH (p:Party {{shortname: '{resolved}'}})
                                    MERGE (a)-[:MADE_BY]->(p)
                                """)
                        except Exception:
                            pass

                    # Link to topics
                    for tag in arg.topic_tags:
                        try:
                            graph.write(f"""
                                MATCH (a:Argument {{text: '{claim_escaped}'}})
                                MATCH (t:Topic {{name: '{_escape(tag)}'}})
                                MERGE (a)-[:ABOUT]->(t)
                            """)
                        except Exception:
                            pass

                except Exception as e:
                    logger.warning("argument_insert_failed", claim=arg.claim[:60], error=str(e))

            count = len(extraction.arguments)
            total_args += count
            args_by_party[party] = args_by_party.get(party, 0) + count
            results.append({"party": party, "file": filename, "arguments": count})

        except Exception as e:
            logger.error("manifesto_failed", party=party, file=filename, error=str(e))
            results.append({"party": party, "file": filename, "arguments": 0, "error": str(e)})

    elapsed = time.time() - t_start

    # Print summary
    print("\n" + "=" * 60)
    print("MANIFESTO INGESTION COMPLETE")
    print("=" * 60)
    print(f"\nTotal arguments: {total_args}")
    print(f"Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"\nPer party:")
    for party, count in sorted(args_by_party.items(), key=lambda x: -x[1]):
        print(f"  {party}: {count}")
    print(f"\nPer file:")
    for r in results:
        status = f"{r['arguments']} args" if not r.get('error') else f"ERROR: {r['error'][:60]}"
        print(f"  {r['file']}: {status}")

    # Graph stats
    stats = get_graph_stats()
    print(f"\nGraph stats:")
    for label, count in stats.items():
        print(f"  {label}: {count}")

    logger.info("ingestion_complete",
        total_arguments=total_args,
        arguments_per_party=args_by_party,
        elapsed_seconds=round(elapsed, 1))


if __name__ == "__main__":
    asyncio.run(main())
