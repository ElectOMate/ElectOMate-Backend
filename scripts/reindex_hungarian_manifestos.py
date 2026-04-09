#!/usr/bin/env python3
"""
Re-index Hungarian 2026 compiled manifesto documents.

Deletes the existing AI-compiled documents from Postgres + Weaviate, then
re-uploads the new source-compiled PDFs so the pipeline extracts fresh
bbox_data for PDF citation highlighting.

After this script completes, run generate_bbox_overrides.py to update
the frontend bbox-overrides.json.

Usage:
    # Against deployed backend
    BASE_URL=https://backend.electomate.com python scripts/reindex_hungarian_manifestos.py

    # Against local backend
    make local          # in another terminal
    python scripts/reindex_hungarian_manifestos.py

    # With status polling (waits for indexing to complete)
    python scripts/reindex_hungarian_manifestos.py --poll
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFESTO_DIR = REPO_ROOT / "assets" / "manifestos"

# From deployed backend API (backend.electomate.com) on 2026-04-08:
HUNGARIAN_DOCS = [
    {
        "shortname": "Fidesz",
        "doc_id": "2a82ee5f-9392-4910-90c8-6b8d93aa0512",
        "party_id": "fc45c5a2-93f6-4764-8997-fbbc75fd0ff1",
        "pdf_file": "FIDESZ.pdf",
    },
    {
        "shortname": "Jobbik",
        "doc_id": "db636bef-4449-4635-8499-b712e150e4e1",
        "party_id": "201dd925-a24e-4f4c-aa54-bfbbd15709fb",
        "pdf_file": "JOBBIK.pdf",
    },
    {
        "shortname": "MSZP",
        "doc_id": "2f6baf83-9d0a-4f0d-874b-b231f0687125",
        "party_id": "52131029-8b5b-4ed7-b22d-e266240ccd0b",
        "pdf_file": "MSZP.pdf",
    },
    {
        "shortname": "MKKP",
        "doc_id": "cce25ad6-c131-4a1f-b907-08e909b6daa6",
        "party_id": "5dc71bea-a6fa-45ec-bd0a-144d7fbe86b5",
        "pdf_file": "MKKP.pdf",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_backend(client: httpx.Client) -> None:
    try:
        r = client.get(f"{BASE_URL}/health", timeout=5)
        r.raise_for_status()
        print(f"  Backend reachable at {BASE_URL}")
    except Exception:
        try:
            r = client.get(f"{BASE_URL}/v2/documents/", timeout=5)
            print(f"  Backend reachable at {BASE_URL} (via /v2/documents/)")
        except Exception as e:
            print(f"  Cannot reach backend at {BASE_URL}: {e}")
            print("   Start the backend first: make local")
            sys.exit(1)


def delete_document(client: httpx.Client, doc_id: str, shortname: str) -> bool:
    try:
        r = client.delete(f"{BASE_URL}/v2/documents/{doc_id}", timeout=300)
    except httpx.ReadTimeout:
        print(f"  Delete timed out for {shortname} ({doc_id}) — Weaviate may still be processing.")
        print(f"     Proceeding with upload anyway.")
        return True
    if r.status_code == 200:
        print(f"  Deleted existing document for {shortname} ({doc_id})")
        return True
    elif r.status_code == 404:
        print(f"  Document {doc_id} ({shortname}) not found — skipping delete")
        return True
    else:
        print(f"  Delete failed for {shortname}: {r.status_code} {r.text[:200]}")
        return False


def upload_document(client: httpx.Client, entry: dict) -> str | None:
    """Upload PDF. Returns new document_id on success, None on failure."""
    pdf_path = MANIFESTO_DIR / entry["pdf_file"]
    if not pdf_path.exists():
        print(f"  PDF not found: {pdf_path}")
        return None

    shortname = entry["shortname"]
    try:
        with open(pdf_path, "rb") as f:
            r = client.post(
                f"{BASE_URL}/v2/documents/",
                files={"file": (entry["pdf_file"], f, "application/pdf")},
                data={
                    "party_id": entry["party_id"],
                    "country_code": "HU",
                    "party_name": shortname,
                },
                timeout=300,
            )
    except httpx.ReadTimeout:
        print(f"  Upload timed out for {shortname} — backend may be overloaded.")
        return None

    if r.status_code in (200, 201):
        doc = r.json()
        new_id = doc.get("id", "?")
        print(f"  Uploaded {shortname} -> new doc_id={new_id}")
        print(f"     Parsing runs in background (~6-10 min per document)")
        return new_id
    else:
        print(f"  Upload failed for {shortname}: {r.status_code} {r.text[:300]}")
        return None


def poll_status(client: httpx.Client, doc_id: str, shortname: str, timeout_s: int = 900) -> None:
    """Poll /v2/documents/{id}/status until indexed or timed out."""
    print(f"  Polling status for {shortname} ({doc_id}) — up to {timeout_s // 60} min...")
    deadline = time.time() + timeout_s
    interval = 30
    while time.time() < deadline:
        try:
            r = client.get(f"{BASE_URL}/v2/documents/{doc_id}/status", timeout=10)
            if r.status_code == 200:
                status = r.json()
                iq = status.get("indexing_success", "?")
                pq = status.get("parsing_quality", "?")
                print(f"     parsing={pq}  indexing={iq}")
                if iq in ("SUCCESS", "PARTIAL_SUCCESS", "FAILED"):
                    if iq == "SUCCESS":
                        print(f"  {shortname} indexed successfully!")
                    elif iq == "PARTIAL_SUCCESS":
                        print(f"  {shortname} indexed with partial success")
                    else:
                        print(f"  {shortname} indexing FAILED")
                    return
        except Exception as e:
            print(f"     status poll error: {e}")
        time.sleep(interval)
    print(f"  Timed out waiting for {shortname} — check status manually")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(poll: bool = False) -> None:
    print()
    print("=" * 64)
    print(" Re-index Hungarian Manifesto Documents (Source-Compiled) ")
    print("=" * 64)
    print(f"Backend: {BASE_URL}")
    print(f"PDFs:    {MANIFESTO_DIR}")
    print()

    client = httpx.Client()
    check_backend(client)

    new_doc_ids: dict[str, str] = {}

    for entry in HUNGARIAN_DOCS:
        shortname = entry["shortname"]
        print(f"\n--- {shortname} ---")

        # Step 1: Delete old
        if not delete_document(client, entry["doc_id"], shortname):
            print(f"  Skipping {shortname} due to delete failure")
            continue

        # Step 2: Upload new
        new_id = upload_document(client, entry)
        if new_id:
            new_doc_ids[shortname] = new_id

    # Summary
    print(f"\n{'=' * 64}")
    print("SUMMARY")
    print(f"{'=' * 64}")
    print(f"Deleted: {len(HUNGARIAN_DOCS)} old documents")
    print(f"Uploaded: {len(new_doc_ids)} new documents")
    for name, doc_id in new_doc_ids.items():
        print(f"  {name}: {doc_id}")

    if not new_doc_ids:
        print("\nNo documents uploaded — nothing to poll.")
        client.close()
        return

    # Step 3: Poll if requested
    if poll:
        print(f"\nPolling indexing status...")
        for name, doc_id in new_doc_ids.items():
            poll_status(client, doc_id, name)
    else:
        print(f"\nDocuments are parsing in the background (~6-10 min each).")
        print(f"To poll status manually:")
        for name, doc_id in new_doc_ids.items():
            print(f"  curl {BASE_URL}/v2/documents/{doc_id}/status")

    print(f"\nAfter all documents are indexed, run:")
    print(f"  python scripts/generate_bbox_overrides.py")
    print(f"to regenerate bbox-overrides.json for the frontend.")

    client.close()


if __name__ == "__main__":
    poll = "--poll" in sys.argv
    main(poll=poll)
