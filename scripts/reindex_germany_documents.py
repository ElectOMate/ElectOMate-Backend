#!/usr/bin/env python3
"""
Re-index Germany Bundestagswahl 2025 manifesto documents.

Deletes the existing (bbox-less) documents from Postgres + Weaviate, then
re-uploads the local PDF copies so the new pipeline extracts PyMuPDF bbox_data
for PDF citation highlighting.

Usage (backend must be running locally OR set BASE_URL to the deployed URL):
    # Local
    make local          # in another terminal
    python scripts/reindex_germany_documents.py

    # Deployed
    BASE_URL=https://your-backend.onrender.com python scripts/reindex_germany_documents.py

Requirements: httpx  (already in project deps)
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

# Assets directory — relative to repo root (ElectOMate-Backend/)
REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFESTO_DIR = REPO_ROOT / "assets" / "manifestos"

# Hardcoded from DB dump (em_dev_data.sql).
# doc_id  = existing Postgres document to delete
# party_id = Postgres party UUID to re-attach the upload to
# pdf_file = local filename in assets/manifestos/
# shortname = human-readable label for logging
GERMANY_DOCS = [
    {
        "shortname": "CDU",
        "doc_id": "00ebd589-78c9-4880-9393-8fd9f49ed6c2",  # uploaded run 3
        "party_id": "0db83901-3c7b-4018-ac5b-33a593378c96",
        "pdf_file": "CDU.pdf",
    },
    {
        "shortname": "SPD",
        "doc_id": "6d651bae-0626-47be-bfe0-c0520ea46e49",  # uploaded run 3
        "party_id": "cdad554d-0df5-4b03-b4b3-c886c3340072",
        "pdf_file": "SPD.pdf",
    },
    {
        "shortname": "Grüne",
        "doc_id": "489faad3-614a-4c6b-9f2d-eabd90f5d48a",  # uploaded run 3 (delete timed out, old chunks may linger)
        "party_id": "5e0e42a5-c71f-434d-bbcd-6f52c0f91f3b",
        "pdf_file": "GRUNE.pdf",
    },
    {
        "shortname": "FDP",
        "doc_id": "11b8b16b-4661-4892-998f-4e2aa30a99f5",  # delete timed out, upload timed out — retry
        "party_id": "c17a7e9a-b257-41a1-9888-6665e7e3fc03",
        "pdf_file": "FDP.pdf",
    },
    {
        "shortname": "AfD",
        "doc_id": "64e35c60-25c4-4f08-9e7d-1fc6b60ec9b3",
        "party_id": "8ef6fe41-e1b4-4fc1-a74e-f8abef1f4f89",
        "pdf_file": "AFD.pdf",
    },
    {
        "shortname": "Linke",
        "doc_id": "eec5a27c-c551-4426-b722-676e7591b2aa",
        "party_id": "9d00acf3-92a8-4d6f-aa19-b71456ba1ecb",
        "pdf_file": "LINKE.pdf",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_backend(client: httpx.Client) -> None:
    try:
        r = client.get(f"{BASE_URL}/health", timeout=5)
        r.raise_for_status()
        print(f"✅ Backend reachable at {BASE_URL}")
    except Exception:
        # Some backends don't have /health — try /v2/documents/ instead
        try:
            r = client.get(f"{BASE_URL}/v2/documents/", timeout=5)
            print(f"✅ Backend reachable at {BASE_URL} (via /v2/documents/)")
        except Exception as e:
            print(f"❌ Cannot reach backend at {BASE_URL}: {e}")
            print("   Start the backend first: make local")
            sys.exit(1)


def delete_document(client: httpx.Client, doc_id: str, shortname: str) -> bool:
    # Weaviate delete_many for large documents (thousands of chunks) can be slow.
    # Use a long timeout (5 min) to avoid premature failures.
    try:
        r = client.delete(f"{BASE_URL}/v2/documents/{doc_id}", timeout=300)
    except httpx.ReadTimeout:
        print(f"  ⚠️  Delete timed out for {shortname} ({doc_id}) — Weaviate may still be processing.")
        print(f"     Proceeding with upload anyway (old chunks may linger briefly).")
        return True  # Upload can still proceed; Weaviate will overwrite on re-query
    if r.status_code == 200:
        print(f"  ✅ Deleted existing document for {shortname} ({doc_id})")
        return True
    elif r.status_code == 404:
        print(f"  ⚠️  Document {doc_id} ({shortname}) not found — skipping delete")
        return True  # Not a fatal error — maybe already deleted
    else:
        print(f"  ❌ Delete failed for {shortname}: {r.status_code} {r.text[:200]}")
        return False


def upload_document(client: httpx.Client, entry: dict) -> str | None:
    """Upload PDF. Returns new document_id on success, None on failure."""
    pdf_path = MANIFESTO_DIR / entry["pdf_file"]
    if not pdf_path.exists():
        print(f"  ❌ PDF not found: {pdf_path}")
        return None

    shortname = entry["shortname"]
    try:
        with open(pdf_path, "rb") as f:
            r = client.post(
                f"{BASE_URL}/v2/documents/",
                files={"file": (entry["pdf_file"], f, "application/pdf")},
                data={
                    "party_id": entry["party_id"],
                    "country_code": "DE",
                    "party_name": shortname,
                },
                timeout=300,  # Backend may be slow when background tasks are running
            )
    except httpx.ReadTimeout:
        print(f"  ⚠️  Upload timed out for {shortname} — backend may be overloaded.")
        print(f"     The document may have been created. Check /v2/documents/ manually.")
        return None

    if r.status_code in (200, 201):
        doc = r.json()
        new_id = doc.get("id", "?")
        print(f"  ✅ Uploaded {shortname} → new doc_id={new_id}")
        print(f"     Parsing runs in background (~6-10 min per document)")
        return new_id
    else:
        print(f"  ❌ Upload failed for {shortname}: {r.status_code} {r.text[:300]}")
        return None


def poll_status(client: httpx.Client, doc_id: str, shortname: str, timeout_s: int = 900) -> None:
    """Poll /v2/documents/{id}/status until indexed or timed out."""
    print(f"  ⏳ Polling status for {shortname} ({doc_id}) — up to {timeout_s//60} min…")
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
                        print(f"  ✅ {shortname} indexed successfully!")
                    elif iq == "PARTIAL_SUCCESS":
                        print(f"  ⚠️  {shortname} indexed with partial success")
                    else:
                        print(f"  ❌ {shortname} indexing FAILED")
                    return
        except Exception as e:
            print(f"     status poll error: {e}")
        time.sleep(interval)
    print(f"  ⏰ Timed out waiting for {shortname} — check status manually")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(poll: bool = False) -> None:
    print()
    print("╔" + "═" * 62 + "╗")
    print("║" + " Re-index Germany Manifesto Documents ".center(62) + "║")
    print("╚" + "═" * 62 + "╝")
    print(f"Backend: {BASE_URL}")
    print(f"PDFs:    {MANIFESTO_DIR}")
    print()

    if not MANIFESTO_DIR.exists():
        print(f"❌ Manifesto directory not found: {MANIFESTO_DIR}")
        sys.exit(1)

    new_doc_ids: dict[str, str] = {}

    with httpx.Client() as client:
        check_backend(client)
        print()

        for entry in GERMANY_DOCS:
            shortname = entry["shortname"]
            print(f"── {shortname} ──────────────────────────────")

            # Step 1: delete old document
            ok = delete_document(client, entry["doc_id"], shortname)
            if not ok:
                print(f"  ⚠️  Skipping upload for {shortname} due to delete failure")
                print()
                continue

            # Small pause to let Weaviate delete propagate
            time.sleep(2)

            # Step 2: re-upload
            new_id = upload_document(client, entry)
            if new_id:
                new_doc_ids[shortname] = new_id
            print()

        if poll and new_doc_ids:
            print("=" * 64)
            print("Polling indexing status (Ctrl+C to abort)…")
            print("Each document takes ~6-10 min to parse and index.")
            print("=" * 64)
            print()
            for shortname, doc_id in new_doc_ids.items():
                poll_status(client, doc_id, shortname)
                print()

    print("=" * 64)
    print("Done. Uploads submitted. Documents index in the background.")
    if not poll:
        print("Run with --poll to wait and monitor indexing status.")
    print()
    if new_doc_ids:
        print("New document IDs:")
        for sn, did in new_doc_ids.items():
            print(f"  {sn:<10} {did}")
    print()


if __name__ == "__main__":
    poll_flag = "--poll" in sys.argv
    main(poll=poll_flag)
