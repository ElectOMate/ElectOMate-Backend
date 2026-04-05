"""
Diagnostic script: extract bboxes from a Hungarian PDF and render them visually.
Creates annotated PDF pages showing bbox rectangles overlaid on the original.
"""
import sys
import json
sys.path.insert(0, "src")

import fitz  # PyMuPDF
from em_backend.services.pdf_bbox_extractor import PDFBboxExtractor

PDF_PATH = "assets/manifestos/FIDESZ.pdf"
OUTPUT_PATH = "scripts/bbox_diagnostic_output.pdf"


def get_sample_chunks(doc: fitz.Document) -> list[dict]:
    """Create realistic sample chunks from actual PDF text to test bbox matching."""
    chunks = []

    # Chunk 1: First page title/header area
    page0_text = doc[0].get_text()
    chunks.append({
        "chunk_id": "chunk-page1-title",
        "text": page0_text[:300],
        "page_number": 1,
    })

    # Chunk 2: Page 2 content
    page1_text = doc[1].get_text()
    chunks.append({
        "chunk_id": "chunk-page2-content",
        "text": page1_text[:400],
        "page_number": 2,
    })

    # Chunk 3: Page 3 content
    page2_text = doc[2].get_text()
    chunks.append({
        "chunk_id": "chunk-page3-content",
        "text": page2_text[:400],
        "page_number": 3,
    })

    # Chunk 4: Simulate a markdown-formatted chunk (like Docling would produce)
    # This is the KEY test - the extractor should still find this in the PDF
    chunks.append({
        "chunk_id": "chunk-markdown-formatted",
        "text": "## Fidesz-KDNP — Politikai Pozíciók\n\nPárt: Fidesz-KDNP (Fidesz – Magyar Polgári Szövetség / Kereszténydemokrata Néppárt)\n\n[...]\n\nA Fidesz-KDNP",
        "page_number": 1,
    })

    # Chunk 5: Middle of a page (page 5 if exists)
    if len(doc) >= 5:
        page4_text = doc[4].get_text()
        chunks.append({
            "chunk_id": "chunk-page5-mid",
            "text": page4_text[100:500],
            "page_number": 5,
        })

    return chunks


def render_bbox_diagnostic(doc: fitz.Document, bbox_map: dict[str, list[dict]], chunks: list[dict]) -> fitz.Document:
    """Create a new PDF with bbox rectangles drawn on pages."""
    # We'll annotate a copy of the original
    output_doc = fitz.open(PDF_PATH)

    colors = [
        (1, 0, 0),      # Red
        (0, 0, 1),      # Blue
        (0, 0.7, 0),    # Green
        (1, 0.5, 0),    # Orange
        (0.5, 0, 0.5),  # Purple
    ]

    for i, chunk in enumerate(chunks):
        chunk_id = chunk["chunk_id"]
        bboxes = bbox_map.get(chunk_id, [])
        color = colors[i % len(colors)]

        print(f"\n{'='*60}")
        print(f"Chunk: {chunk_id}")
        print(f"  Page hint: {chunk.get('page_number')}")
        print(f"  Text preview: {chunk['text'][:100]!r}")
        print(f"  Bboxes found: {len(bboxes)}")

        if not bboxes:
            print("  ⚠️  NO BBOXES FOUND - this is a problem!")
            continue

        for j, bbox in enumerate(bboxes):
            page_num = bbox["page"]  # 1-indexed
            page_idx = page_num - 1
            if page_idx < 0 or page_idx >= len(output_doc):
                print(f"  ⚠️  Invalid page {page_num}")
                continue

            page = output_doc[page_idx]
            rect = fitz.Rect(bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"])

            # Draw rectangle
            annot = page.add_rect_annot(rect)
            annot.set_colors(stroke=color)
            annot.set_border(width=1.5)
            annot.set_opacity(0.3)
            annot.update()

            # Also draw a filled highlight
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(color=color, fill=color, fill_opacity=0.15, width=0.5)
            shape.commit()

            if j < 3:  # Print first 3
                print(f"  bbox[{j}]: page={page_num}, ({bbox['x0']:.1f}, {bbox['y0']:.1f}) -> ({bbox['x1']:.1f}, {bbox['y1']:.1f})")

        if len(bboxes) > 3:
            print(f"  ... and {len(bboxes)-3} more bboxes")

        # Add label annotation on first bbox's page
        if bboxes:
            first_bbox = bboxes[0]
            page = output_doc[first_bbox["page"] - 1]
            label_point = fitz.Point(first_bbox["x0"], first_bbox["y0"] - 5)
            page.insert_text(label_point, chunk_id, fontsize=8, color=color)

    return output_doc


def analyze_bbox_quality(doc: fitz.Document, bbox_map: dict[str, list[dict]], chunks: list[dict]):
    """Analyze and report on bbox extraction quality."""
    print("\n" + "="*60)
    print("BBOX QUALITY ANALYSIS")
    print("="*60)

    total_chunks = len(chunks)
    chunks_with_bboxes = sum(1 for c in chunks if bbox_map.get(c["chunk_id"]))
    chunks_without = total_chunks - chunks_with_bboxes

    print(f"Total chunks: {total_chunks}")
    print(f"Chunks with bboxes: {chunks_with_bboxes}")
    print(f"Chunks without bboxes: {chunks_without}")

    # Check if bboxes are on the right page
    page_mismatch = 0
    for chunk in chunks:
        hint = chunk.get("page_number")
        bboxes = bbox_map.get(chunk["chunk_id"], [])
        if hint and bboxes:
            bbox_pages = {b["page"] for b in bboxes}
            if hint not in bbox_pages:
                page_mismatch += 1
                print(f"  ⚠️  Page mismatch: {chunk['chunk_id']} hint={hint}, bbox pages={bbox_pages}")

    print(f"Page mismatches: {page_mismatch}")

    # Check bbox dimensions
    for chunk in chunks:
        bboxes = bbox_map.get(chunk["chunk_id"], [])
        for bbox in bboxes:
            w = bbox["x1"] - bbox["x0"]
            h = bbox["y1"] - bbox["y0"]
            if w <= 0 or h <= 0:
                print(f"  ⚠️  Invalid bbox dimensions for {chunk['chunk_id']}: w={w:.1f}, h={h:.1f}")
            if w > 700 or h > 900:
                print(f"  ⚠️  Suspiciously large bbox for {chunk['chunk_id']}: w={w:.1f}, h={h:.1f}")

    # Check the search phrase extraction
    extractor = PDFBboxExtractor()
    print("\nSearch phrases extracted:")
    for chunk in chunks:
        phrase = extractor._extract_search_phrase(chunk["text"])
        print(f"  {chunk['chunk_id']}: {phrase!r}")
        # Check if this phrase actually exists in the PDF
        hint = chunk.get("page_number", 1)
        page = doc[hint - 1]
        hits = page.search_for(phrase)
        print(f"    → search_for() hits on page {hint}: {len(hits)}")
        if not hits and len(doc) > 1:
            # Try other pages
            for pi in range(len(doc)):
                if pi != hint - 1:
                    alt_hits = doc[pi].search_for(phrase)
                    if alt_hits:
                        print(f"    → Found on page {pi+1} instead!")
                        break


if __name__ == "__main__":
    extractor = PDFBboxExtractor()
    doc = extractor.extract_from_path(PDF_PATH)
    print(f"Loaded {PDF_PATH}: {len(doc)} pages")

    # Get sample chunks
    chunks = get_sample_chunks(doc)
    print(f"Created {len(chunks)} sample chunks")

    # Extract bboxes
    chunk_inputs = [
        {"chunk_id": c["chunk_id"], "text": c["text"], "page_number": c.get("page_number")}
        for c in chunks
    ]
    bbox_map = extractor.extract_bboxes_for_chunks(doc, chunk_inputs)

    # Analyze quality
    analyze_bbox_quality(doc, bbox_map, chunks)

    # Render diagnostic PDF
    output_doc = render_bbox_diagnostic(doc, bbox_map, chunks)
    output_doc.save(OUTPUT_PATH)
    output_doc.close()
    doc.close()

    print(f"\n✅ Diagnostic PDF saved to: {OUTPUT_PATH}")
    print("Open this PDF to visually verify bbox positions.")
