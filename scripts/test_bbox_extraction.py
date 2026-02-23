#!/usr/bin/env python3
"""
Local unit test for PDFBboxExtractor — no Weaviate, no Docling, no uploads.

Tests that the bbox extraction pipeline can find bounding boxes for text
extracted directly from a PDF using PyMuPDF.

Usage:
    uv run python scripts/test_bbox_extraction.py [PDF_PATH]

    # Defaults to AFD.pdf if no path given
    uv run python scripts/test_bbox_extraction.py assets/manifestos/AFD.pdf
    uv run python scripts/test_bbox_extraction.py assets/manifestos/CDU.pdf
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import fitz  # PyMuPDF

# --- path setup so we can import from src/ without installing the package ---
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from em_backend.services.pdf_bbox_extractor import PDFBboxExtractor  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_sample_chunks(pdf_path: Path, pages_to_sample: int = 10) -> list[dict]:
    """
    Open the PDF with fitz and extract one "chunk" per sampled page.
    We take blocks of real text (≥ 50 chars) from the page, mimicking
    what the Docling chunker would produce.
    """
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    sample_step = max(1, total_pages // pages_to_sample)

    chunks = []
    for page_idx in range(0, total_pages, sample_step):
        page = doc[page_idx]
        text = page.get_text("text").strip()
        if len(text) < 50:
            continue  # Skip near-empty pages (covers, TOC images, etc.)

        # Take up to 500 chars to simulate a realistic chunk excerpt
        chunk_text = text[:500]

        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "text": chunk_text,
            "page_number": page_idx + 1,  # 1-indexed
        })

    doc.close()
    return chunks


def run_bbox_test(pdf_path: Path) -> None:
    print()
    print("╔" + "═" * 60 + "╗")
    print("║" + " PDFBboxExtractor — Local Unit Test ".center(60) + "║")
    print("╚" + "═" * 60 + "╝")
    print(f"PDF:   {pdf_path}")

    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)

    # Step 1: Extract sample chunks using fitz text (no Docling needed)
    print("\n[1/3] Extracting sample text chunks from PDF…")
    chunks = extract_sample_chunks(pdf_path, pages_to_sample=15)
    print(f"      → {len(chunks)} sample chunks from {len(fitz.open(str(pdf_path)))} pages")

    if not chunks:
        print("❌ No usable text found in PDF — is it image-only?")
        sys.exit(1)

    # Step 2: Run PDFBboxExtractor (the actual production code)
    print("\n[2/3] Running PDFBboxExtractor on chunks…")
    extractor = PDFBboxExtractor()
    fitz_doc = extractor.extract_from_path(pdf_path)
    try:
        bbox_map = extractor.extract_bboxes_for_chunks(fitz_doc, chunks)
    finally:
        fitz_doc.close()

    # Step 3: Assert and report
    print("\n[3/3] Results:")
    print()

    hits = 0
    misses = 0
    total_bboxes = 0

    for chunk in chunks:
        cid = chunk["chunk_id"]
        bboxes = bbox_map.get(cid, [])
        page = chunk["page_number"]
        preview = chunk["text"][:60].replace("\n", " ")

        if bboxes:
            hits += 1
            total_bboxes += len(bboxes)
            sample_bbox = bboxes[0]
            print(
                f"  ✅ p{page:>3}  {len(bboxes):>2} bbox(es)  "
                f"first=[x0={sample_bbox['x0']:.1f} y0={sample_bbox['y0']:.1f} "
                f"x1={sample_bbox['x1']:.1f} y1={sample_bbox['y1']:.1f}]"
            )
            print(f"         text: \"{preview}\"")
        else:
            misses += 1
            print(f"  ❌ p{page:>3}  0 bboxes  text: \"{preview}\"")

    print()
    print("─" * 60)
    coverage = hits / len(chunks) * 100 if chunks else 0
    print(f"Coverage: {hits}/{len(chunks)} chunks have bboxes ({coverage:.0f}%)")
    print(f"Total bboxes extracted: {total_bboxes}")

    # --- Assertions ---
    assert hits > 0, "FAIL: No chunks got any bboxes at all!"
    assert coverage >= 50, f"FAIL: Coverage {coverage:.0f}% is below 50% threshold"

    print()
    if coverage >= 80:
        print("✅ PASS — bbox extraction is working correctly")
    elif coverage >= 50:
        print("⚠️  PARTIAL — bbox extraction works but coverage is low")
        print("   (Low coverage is expected for pages with complex layouts,")
        print("    tables, or hyphenated text that fitz can't match)")
    print()


# ---------------------------------------------------------------------------
# Also test the specific AfD chunk from the bug report (page 61)
# ---------------------------------------------------------------------------

def run_afd_known_chunk_test(pdf_path: Path) -> None:
    """Test the specific AfD chunk that was showing empty bbox_data in Weaviate."""
    print("─" * 60)
    print("Bonus: Testing known AfD chunk (page 61) from bug report…")
    print()

    # Exact text from the Weaviate chunk shown by the user
    afd_text = (
        "## Vermögen- und Erbschaftsteuer abschaffen "
        "Die AfD will die derzeit zur Erhebung ausgesetzte Vermögensteuer sowie die "
        "Erbschaftssteuer abschaffen. Beide sind Substanzsteuern, d. h. sie werden "
        "unabhängig von der wirtschaftlichen Leistungsfä -higkeit des Steuerbürgers "
        "erhoben."
    )

    fake_chunk = {
        "chunk_id": "5d60ff8f-bbb3-49a6-8162-88d4e548e2e1",  # Real chunk_id from Weaviate
        "text": afd_text,
        "page_number": 61,
    }

    extractor = PDFBboxExtractor()
    fitz_doc = extractor.extract_from_path(pdf_path)
    try:
        bbox_map = extractor.extract_bboxes_for_chunks(fitz_doc, [fake_chunk])
    finally:
        fitz_doc.close()

    bboxes = bbox_map.get(fake_chunk["chunk_id"], [])
    print(f"AfD chunk (page 61) → {len(bboxes)} bbox(es)")

    if bboxes:
        for i, b in enumerate(bboxes[:5]):
            print(f"  bbox[{i}]: page={b['page']} x0={b['x0']:.1f} y0={b['y0']:.1f} x1={b['x1']:.1f} y1={b['y1']:.1f}")
        if len(bboxes) > 5:
            print(f"  … and {len(bboxes) - 5} more")
        print(f"\n  Raw JSON (first 2): {json.dumps(bboxes[:2], indent=2)}")
        print("\n✅ Known chunk has bboxes — extractor is working")
    else:
        print("❌ Known chunk has NO bboxes — likely a text encoding mismatch")
        # Debug: show what the extractor's search phrase is
        search_phrase = extractor._extract_search_phrase(afd_text)
        print(f"   Search phrase used: \"{search_phrase}\"")
        print("   Possible cause: PDF uses hyphenation/ligatures fitz can't match")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    default_pdf = REPO_ROOT / "assets" / "manifestos" / "AFD.pdf"
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_pdf

    run_bbox_test(pdf_path)

    # Run the specific known chunk test only for the AfD PDF
    afd_pdf = REPO_ROOT / "assets" / "manifestos" / "AFD.pdf"
    if pdf_path.resolve() == afd_pdf.resolve() and afd_pdf.exists():
        run_afd_known_chunk_test(afd_pdf)
