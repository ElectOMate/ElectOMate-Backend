#!/usr/bin/env python3
"""
Local ingestion of Hungarian manifesto PDFs directly to Weaviate.

Bypasses the deployed backend entirely — parses, chunks, extracts bboxes,
and inserts to Weaviate from the local machine. Then creates Postgres
document records via the deployed API with is_document_already_parsed=true.

Usage:
    python scripts/local_ingest_hungarian.py
    python scripts/local_ingest_hungarian.py --party FIDESZ
    python scripts/local_ingest_hungarian.py --skip-existing
"""

from __future__ import annotations

import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import httpx
import weaviate
from weaviate.classes.init import Auth, AdditionalConfig, Timeout
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import Filter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEPLOYED_API = "https://backend.electomate.com"
WV_COLLECTION = "D2026_orszggylsivlaszts_93bf55de"

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFESTO_DIR = REPO_ROOT / "assets" / "manifestos"

# Party IDs on the deployed backend
HUNGARIAN_PARTIES = [
    {
        "shortname": "Fidesz",
        "party_id": "fc45c5a2-93f6-4764-8997-fbbc75fd0ff1",
        "pdf_file": "FIDESZ.pdf",
    },
    {
        "shortname": "TISZA",
        "party_id": "9c998041-aae3-45c1-a823-72cd643c51d4",
        "pdf_file": "TISZA.pdf",
    },
    {
        "shortname": "DK",
        "party_id": "5c043012-c153-4168-b843-c4464b456cee",
        "pdf_file": "DK.pdf",
    },
    {
        "shortname": "Mi Hazánk",
        "party_id": "2a0ee501-ef7f-4b83-9580-be8ad87534cc",
        "pdf_file": "MI_HAZANK.pdf",
    },
    {
        "shortname": "MKKP",
        "party_id": "5dc71bea-a6fa-45ec-bd0a-144d7fbe86b5",
        "pdf_file": "MKKP.pdf",
    },
    {
        "shortname": "Jobbik",
        "party_id": "201dd925-a24e-4f4c-aa54-bfbbd15709fb",
        "pdf_file": "JOBBIK.pdf",
    },
    {
        "shortname": "MSZP",
        "party_id": "52131029-8b5b-4ed7-b22d-e266240ccd0b",
        "pdf_file": "MSZP.pdf",
    },
]


# ---------------------------------------------------------------------------
# Step 1: Parse + Chunk locally
# ---------------------------------------------------------------------------

def parse_and_chunk(pdf_path: Path) -> tuple[list[dict], bytes]:
    """Parse PDF with Docling and chunk it. Returns (chunks, pdf_bytes)."""
    from em_backend.vector.parser import DocumentParser

    print(f"  Parsing {pdf_path.name}...")
    parser = DocumentParser()

    pdf_bytes = pdf_path.read_bytes()
    doc, confidence = parser.parse_document(pdf_path.name, BytesIO(pdf_bytes))
    print(f"  Parsed: confidence={confidence.mean_grade}")

    print(f"  Chunking...")
    chunks = list(parser.chunk_document(doc))
    print(f"  Chunks: {len(chunks)}")

    return chunks, pdf_bytes


# ---------------------------------------------------------------------------
# Step 2: Extract bboxes
# ---------------------------------------------------------------------------

def extract_bboxes(chunks: list[dict], pdf_bytes: bytes) -> list[dict]:
    """Extract PyMuPDF bboxes for each chunk."""
    from em_backend.services.pdf_bbox_extractor import PDFBboxExtractor

    print(f"  Extracting bboxes...")
    extractor = PDFBboxExtractor()
    fitz_doc = extractor.extract_from_bytes(pdf_bytes)

    chunk_inputs = [
        {"chunk_id": c["chunk_id"], "text": c.get("text", ""), "page_number": c.get("page_number")}
        for c in chunks
    ]

    try:
        bbox_map = extractor.extract_bboxes_for_chunks(fitz_doc, chunk_inputs)
    finally:
        fitz_doc.close()

    for chunk in chunks:
        chunk["bbox_data"] = json.dumps(bbox_map.get(chunk["chunk_id"], []))

    matched = sum(1 for c in chunks if c.get("bbox_data", "[]") != "[]")
    print(f"  Bboxes: {matched}/{len(chunks)} chunks matched")

    return chunks


# ---------------------------------------------------------------------------
# Step 3: Insert to Weaviate
# ---------------------------------------------------------------------------

def insert_to_weaviate(
    wv_client: weaviate.WeaviateClient,
    chunks: list[dict],
    party_id: str,
    document_id: str,
    pdf_filename: str,
) -> int:
    """Insert chunks to Weaviate in small batches with retry."""
    collection = wv_client.collections.use(WV_COLLECTION)

    BATCH_SIZE = 10
    MAX_RETRIES = 3
    total_inserted = 0

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

        for attempt in range(1, MAX_RETRIES + 1):
            errors = []
            with collection.batch.fixed_size(batch_size=BATCH_SIZE) as batch:
                for chunk in batch_chunks:
                    raw_bbox = chunk.get("bbox_data", "[]")
                    bbox_str = json.dumps(raw_bbox) if isinstance(raw_bbox, list) else raw_bbox

                    batch.add_object({
                        "text": chunk["text"],
                        "title": pdf_filename,
                        "party": party_id,
                        "document": document_id,
                        "chunk_id": chunk["chunk_id"],
                        "page_number": chunk.get("page_number"),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "token_count": chunk.get("token_count"),
                        "char_count": len(chunk.get("text", "")),
                        "word_count": len(chunk.get("text", "").split()),
                        "bbox_data": bbox_str,
                    })
                if batch.number_errors:
                    errors = list(collection.batch.failed_objects)

            if not errors:
                total_inserted += len(batch_chunks)
                print(f"    Batch {batch_num}/{total_batches}: {len(batch_chunks)} chunks OK")
                break
            else:
                if attempt < MAX_RETRIES:
                    wait = attempt * 10
                    print(f"    Batch {batch_num} failed (attempt {attempt}): {len(errors)} errors — retry in {wait}s")
                    print(f"      Error: {str(errors[0])[:200]}")
                    time.sleep(wait)
                else:
                    print(f"    Batch {batch_num} FAILED after {MAX_RETRIES} attempts: {len(errors)} errors")
                    print(f"      Error: {str(errors[0])[:200]}")
                    total_inserted += len(batch_chunks) - len(errors)

    return total_inserted


# ---------------------------------------------------------------------------
# Step 4: Create Postgres record via deployed API
# ---------------------------------------------------------------------------

def create_document_record(
    api: httpx.Client,
    party_id: str,
    pdf_path: Path,
) -> str | None:
    """Upload PDF to deployed API with is_document_already_parsed=true.
    This creates the Postgres record without re-parsing."""
    try:
        with open(pdf_path, "rb") as f:
            r = api.post(
                f"{DEPLOYED_API}/v2/documents/",
                files={"file": (pdf_path.name, f, "application/pdf")},
                data={
                    "party_id": party_id,
                    "is_document_already_parsed": "true",
                    "country_code": "HU",
                    "party_name": pdf_path.stem,
                },
                timeout=60,
            )
        if r.status_code in (200, 201):
            doc = r.json()
            return doc.get("id")
        else:
            print(f"    API error: {r.status_code} {r.text[:200]}")
            return None
    except Exception as e:
        print(f"    API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Step 5: Delete existing chunks for a document
# ---------------------------------------------------------------------------

def delete_existing_chunks(wv_client: weaviate.WeaviateClient, document_id: str) -> int:
    """Delete any existing chunks for a document from Weaviate."""
    collection = wv_client.collections.use(WV_COLLECTION)
    result = collection.data.delete_many(
        where=Filter.by_property("document").equal(document_id)
    )
    return result.successful


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--party", help="Process only this party (e.g. FIDESZ)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip parties that already have chunks")
    args = parser.parse_args()

    parties = HUNGARIAN_PARTIES
    if args.party:
        parties = [p for p in parties if p["shortname"].upper() == args.party.upper() or p["pdf_file"].upper() == args.party.upper() + ".PDF"]
        if not parties:
            print(f"Party {args.party} not found")
            sys.exit(1)

    print()
    print("=" * 60)
    print("  Local Hungarian Manifesto Ingestion → Weaviate")
    print("=" * 60)
    print(f"Collection: {WV_COLLECTION}")
    print(f"API: {DEPLOYED_API}")
    print(f"Parties: {len(parties)}")
    print()

    # Connect to Weaviate
    print("Connecting to Weaviate...")
    wv_client = weaviate.connect_to_weaviate_cloud(
        cluster_url=os.getenv("WV_URL"),
        auth_credentials=Auth.api_key(os.getenv("WV_API_KEY")),
        headers={"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")},
        additional_config=AdditionalConfig(timeout=Timeout(query=120, insert=300, init=60)),
    )
    wv_client.connect()
    print("Connected.")

    # Ensure collection exists
    if not wv_client.collections.exists(WV_COLLECTION):
        print(f"Creating collection {WV_COLLECTION}...")
        wv_client.collections.create(
            name=WV_COLLECTION,
            vector_config=Configure.Vectors.text2vec_openai(),
            generative_config=Configure.Generative.openai(),
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="title", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="party", data_type=DataType.UUID, skip_vectorization=True),
                Property(name="document", data_type=DataType.UUID, skip_vectorization=True),
                Property(name="chunk_id", data_type=DataType.TEXT, skip_vectorization=True),
                Property(name="page_number", data_type=DataType.INT, skip_vectorization=True),
                Property(name="chunk_index", data_type=DataType.INT, skip_vectorization=True),
                Property(name="token_count", data_type=DataType.INT, skip_vectorization=True),
                Property(name="char_count", data_type=DataType.INT, skip_vectorization=True),
                Property(name="word_count", data_type=DataType.INT, skip_vectorization=True),
                Property(name="bbox_data", data_type=DataType.TEXT, skip_vectorization=True,
                         index_filterable=False, index_searchable=False),
            ],
        )

    api = httpx.Client(timeout=300)
    results: dict[str, dict] = {}

    for entry in parties:
        name = entry["shortname"]
        party_id = entry["party_id"]
        pdf_path = MANIFESTO_DIR / entry["pdf_file"]

        print(f"\n{'─' * 60}")
        print(f"  {name} ({pdf_path.name})")
        print(f"{'─' * 60}")

        if not pdf_path.exists():
            print(f"  PDF not found: {pdf_path}")
            results[name] = {"status": "SKIP", "reason": "PDF not found"}
            continue

        # Check for existing documents for this party via API
        if args.skip_existing:
            r = api.get(f"{DEPLOYED_API}/v2/documents/", timeout=30)
            if r.status_code == 200:
                existing = [d for d in r.json() if d.get("party_id") == party_id]
                if existing:
                    print(f"  Already has {len(existing)} document(s) — skipping")
                    results[name] = {"status": "SKIP", "reason": "already exists"}
                    continue

        # Step 1: Create Postgres record via API (before chunking, so we have the doc ID)
        print(f"  Creating Postgres record via API...")
        doc_id = create_document_record(api, party_id, pdf_path)
        if not doc_id:
            print(f"  Failed to create document record — skipping")
            results[name] = {"status": "FAIL", "reason": "API record creation failed"}
            continue
        print(f"  Document ID: {doc_id}")

        # Step 2: Parse + chunk locally
        try:
            chunks, pdf_bytes = parse_and_chunk(pdf_path)
        except Exception as e:
            print(f"  Parse/chunk failed: {e}")
            results[name] = {"status": "FAIL", "reason": f"parse error: {e}", "doc_id": doc_id}
            continue

        # Step 3: Extract bboxes
        try:
            chunks = extract_bboxes(chunks, pdf_bytes)
        except Exception as e:
            print(f"  Bbox extraction failed (continuing without): {e}")

        # Step 4: Insert to Weaviate
        print(f"  Inserting {len(chunks)} chunks to Weaviate...")
        inserted = insert_to_weaviate(wv_client, chunks, party_id, doc_id, pdf_path.name)
        print(f"  Inserted: {inserted}/{len(chunks)}")

        results[name] = {
            "status": "OK" if inserted == len(chunks) else "PARTIAL",
            "doc_id": doc_id,
            "chunks": len(chunks),
            "inserted": inserted,
        }

    # Cleanup
    wv_client.close()
    api.close()

    # Summary
    print(f"\n{'=' * 60}")
    print("  SUMMARY")
    print(f"{'=' * 60}")
    for name, info in results.items():
        status = info.get("status", "?")
        doc_id = info.get("doc_id", "")
        chunks = info.get("chunks", "")
        inserted = info.get("inserted", "")
        reason = info.get("reason", "")

        if status in ("OK", "PARTIAL"):
            print(f"  {name}: {status} — doc={doc_id} chunks={inserted}/{chunks}")
        else:
            print(f"  {name}: {status} — {reason}")

    # Verify Weaviate
    print(f"\nVerifying Weaviate collection...")
    wv_client = weaviate.connect_to_weaviate_cloud(
        cluster_url=os.getenv("WV_URL"),
        auth_credentials=Auth.api_key(os.getenv("WV_API_KEY")),
        additional_config=AdditionalConfig(timeout=Timeout(query=60, insert=120, init=30)),
    )
    wv_client.connect()
    col = wv_client.collections.use(WV_COLLECTION)
    agg = col.aggregate.over_all(total_count=True)
    print(f"  Total chunks in {WV_COLLECTION}: {agg.total_count}")
    wv_client.close()

    print(f"\nDone! Next steps:")
    print(f"  1. Update PartyRegistry.json with new document IDs")
    print(f"  2. Run: python scripts/generate_bbox_overrides.py")
    print(f"  3. Deploy frontend with updated PDFs + bbox-overrides.json")


if __name__ == "__main__":
    main()
