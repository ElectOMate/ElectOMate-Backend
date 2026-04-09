"""
Generate pre-calculated bounding box overrides for Hungarian election chunks.

Connects to Weaviate, retrieves all chunks for each Hungarian party,
recalculates bboxes using the fixed PDFBboxExtractor, and saves them
to a JSON file that the frontend can use as an override.

Usage:
    cd ElectOMate-Backend
    python scripts/generate_bbox_overrides.py
"""
import json
import os
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, "src")

from dotenv import load_dotenv

load_dotenv()

import fitz
import weaviate
from weaviate.classes.init import Auth, AdditionalConfig, Timeout
from weaviate.classes.query import Filter

from em_backend.services.pdf_bbox_extractor import PDFBboxExtractor

# Weaviate collection for Hungarian 2026 election
WV_COLLECTION = "D2026_orszggylsivlaszts_f1299647"

# Frontend PDFs (relative to repo root)
FRONTEND_PDF_DIR = Path(__file__).resolve().parents[2] / "ElectOMate-Frontend" / "public" / "country-storage" / "HU" / "manifestos"
BACKEND_PDF_DIR = Path(__file__).resolve().parent.parent / "assets" / "manifestos"

# The chunks in Weaviate store the original PDF filename in the "title" field.
# We use that to find the right PDF — the bboxes must match the PDF that was indexed.
# Some PDFs differ from what PartyRegistry.json references (compiled vs original).
#
# Known mapping from chunk titles:
#   Fidesz  → Fidesz_KDNP_compiled_manifesto.pdf (13 pages, matches)
#   TISZA   → tisza_manifesto.pdf (238 pages, NOT the compiled version)
#   DK      → dk_program.pdf (41 pages, NOT the compiled version)
#   Mi Hazánk → virradat2.pdf (112 pages, NOT the compiled version)
#   MKKP    → Magyar_Ketfarku_Kutya_Part_MKKP_program.pdf (matches)
#   Jobbik  → Jobbik_compiled_positions.pdf (matches)
#   MSZP    → MSZP_compiled_positions.pdf (matches)

# Output path
OUTPUT_PATH = Path(__file__).resolve().parents[2] / "ElectOMate-Frontend" / "public" / "country-storage" / "HU" / "bbox-overrides.json"


def fetch_all_chunks(client: weaviate.WeaviateClient) -> dict[str, list[dict]]:
    """Fetch all chunks from Weaviate, grouped by party UUID."""
    collection = client.collections.use(WV_COLLECTION)

    party_chunks: dict[str, list[dict]] = {}
    offset = 0
    batch_size = 100
    total = 0

    while True:
        response = collection.query.fetch_objects(
            limit=batch_size,
            offset=offset,
        )

        if not response.objects:
            break

        for obj in response.objects:
            props = obj.properties
            party_id = str(props.get("party", ""))
            chunk = {
                "chunk_id": props.get("chunk_id", ""),
                "text": props.get("text", ""),
                "page_number": props.get("page_number"),
                "title": props.get("title", ""),
            }
            if party_id not in party_chunks:
                party_chunks[party_id] = []
            party_chunks[party_id].append(chunk)
            total += 1

        offset += batch_size
        print(f"  Fetched {total} chunks so far...")

    print(f"Total chunks retrieved: {total}")
    print(f"Parties found: {len(party_chunks)}")
    for pid, chunks in party_chunks.items():
        print(f"  {pid}: {len(chunks)} chunks")

    return party_chunks


def find_pdf_by_title(title: str) -> Path | None:
    """Find the PDF file using the chunk's title field (original indexed filename).

    The bboxes must match the PDF that was actually indexed, not necessarily
    the 'compiled' version referenced in PartyRegistry.json.
    """
    # Title is the original filename (e.g., "tisza_manifesto.pdf")
    # Try frontend dir first
    frontend_path = FRONTEND_PDF_DIR / title
    if frontend_path.exists():
        return frontend_path

    # Try backend assets dir
    backend_path = BACKEND_PDF_DIR / title
    if backend_path.exists():
        return backend_path

    # Try case-insensitive search in frontend dir
    if FRONTEND_PDF_DIR.exists():
        for f in FRONTEND_PDF_DIR.iterdir():
            if f.name.lower() == title.lower():
                return f

    return None


def main():
    print("=" * 60)
    print("BBOX OVERRIDE GENERATOR")
    print("=" * 60)

    # Connect to Weaviate
    print("\nConnecting to Weaviate...")
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=os.getenv("WV_URL"),
        auth_credentials=Auth.api_key(os.getenv("WV_API_KEY")),
        additional_config=AdditionalConfig(
            timeout=Timeout(query=60, insert=120, init=30),
        ),
    )
    client.connect()
    print("Connected.")

    # Fetch all chunks
    print(f"\nFetching chunks from collection: {WV_COLLECTION}")
    party_chunks = fetch_all_chunks(client)
    client.close()

    # Group chunks by their title (= source PDF filename) instead of party
    # This ensures we use the correct PDF for bbox extraction
    from collections import defaultdict
    title_chunks: dict[str, list[dict]] = defaultdict(list)
    for chunks in party_chunks.values():
        for chunk in chunks:
            title = chunk.get("title", "unknown")
            title_chunks[title].append(chunk)

    print(f"\nGrouped into {len(title_chunks)} PDF titles:")
    for title, chunks in title_chunks.items():
        print(f"  {title}: {len(chunks)} chunks")

    # Process each PDF title group
    extractor = PDFBboxExtractor()
    all_bboxes: dict[str, list[dict]] = {}
    stats = {"total_chunks": 0, "chunks_with_bboxes": 0, "chunks_without": 0, "pdfs_processed": 0}

    for title, chunks in title_chunks.items():
        pdf_path = find_pdf_by_title(title)

        if not pdf_path:
            print(f"\n  WARNING: No PDF found for title '{title}'")
            print(f"    Searched: {FRONTEND_PDF_DIR}")
            print(f"    Searched: {BACKEND_PDF_DIR}")
            for chunk in chunks:
                all_bboxes[chunk["chunk_id"]] = []
                stats["total_chunks"] += 1
                stats["chunks_without"] += 1
            continue

        print(f"\nProcessing '{title}' ({len(chunks)} chunks)")
        print(f"  PDF: {pdf_path}")

        doc = fitz.open(str(pdf_path))
        print(f"  PDF pages: {len(doc)}")

        chunk_inputs = [
            {
                "chunk_id": c["chunk_id"],
                "text": c["text"],
                "page_number": c.get("page_number"),
            }
            for c in chunks
        ]

        bbox_map = extractor.extract_bboxes_for_chunks(doc, chunk_inputs)
        doc.close()

        matched = 0
        for chunk in chunks:
            cid = chunk["chunk_id"]
            bboxes = bbox_map.get(cid, [])
            all_bboxes[cid] = bboxes
            stats["total_chunks"] += 1
            if bboxes:
                stats["chunks_with_bboxes"] += 1
                matched += 1
            else:
                stats["chunks_without"] += 1

        stats["pdfs_processed"] += 1
        print(f"  Matched: {matched}/{len(chunks)} chunks")

    # Save JSON
    print(f"\nSaving to {OUTPUT_PATH}")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_bboxes, f, separators=(",", ":"))

    file_size = OUTPUT_PATH.stat().st_size
    print(f"  Size: {file_size / 1024:.1f} KB")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"PDFs processed: {stats['pdfs_processed']}")
    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Chunks with bboxes: {stats['chunks_with_bboxes']}")
    print(f"Chunks without bboxes: {stats['chunks_without']}")
    print(f"Match rate: {stats['chunks_with_bboxes']/max(1,stats['total_chunks'])*100:.1f}%")
    print(f"\nOutput: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
