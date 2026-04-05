"""
Bbox Viewer: generates an HTML page with PDF pages + bbox overlays.
Serves on localhost so you can visually verify bbox accuracy in-browser.

Usage:
    python scripts/bbox_viewer.py [--port 8899]
"""
import sys
import json
import base64
import argparse
from pathlib import Path

sys.path.insert(0, "src")

import fitz
from em_backend.services.pdf_bbox_extractor import PDFBboxExtractor

HUNGARIAN_PDFS = [
    "assets/manifestos/FIDESZ.pdf",
    "assets/manifestos/TISZA.pdf",
    "assets/manifestos/DK.pdf",
    "assets/manifestos/MI_HAZANK.pdf",
    "assets/manifestos/MKKP.pdf",
    "assets/manifestos/JOBBIK.pdf",
    "assets/manifestos/MSZP.pdf",
]

# Colors for different chunks
COLORS = [
    "rgba(255, 0, 0, 0.25)",
    "rgba(0, 0, 255, 0.25)",
    "rgba(0, 180, 0, 0.25)",
    "rgba(255, 140, 0, 0.25)",
    "rgba(128, 0, 128, 0.25)",
    "rgba(0, 180, 180, 0.25)",
]

BORDER_COLORS = [
    "rgba(255, 0, 0, 0.7)",
    "rgba(0, 0, 255, 0.7)",
    "rgba(0, 180, 0, 0.7)",
    "rgba(255, 140, 0, 0.7)",
    "rgba(128, 0, 128, 0.7)",
    "rgba(0, 180, 180, 0.7)",
]


def create_sample_chunks(doc: fitz.Document, pdf_name: str) -> list[dict]:
    """Create realistic chunks: raw text + markdown-formatted versions."""
    chunks = []
    total_pages = len(doc)

    # Raw text chunks from first 3 pages
    for page_idx in range(min(3, total_pages)):
        page_text = doc[page_idx].get_text()
        if page_text.strip():
            chunks.append({
                "chunk_id": f"{pdf_name}-raw-p{page_idx+1}",
                "text": page_text[:400],
                "page_number": page_idx + 1,
                "label": f"Raw text page {page_idx+1}",
            })

    # Markdown-formatted chunks (simulating Docling output)
    for page_idx in range(min(2, total_pages)):
        page_text = doc[page_idx].get_text()
        lines = [l for l in page_text.splitlines() if l.strip()]
        if len(lines) >= 2:
            heading = lines[0].strip()
            body = "\n".join(lines[1:5])
            md_chunk = f"## {heading}\n\n{body}\n\n[...]"
            chunks.append({
                "chunk_id": f"{pdf_name}-md-p{page_idx+1}",
                "text": md_chunk,
                "page_number": page_idx + 1,
                "label": f"Markdown chunk page {page_idx+1}",
            })

    # Mid-page chunk
    if total_pages >= 4:
        mid_page = total_pages // 2
        page_text = doc[mid_page].get_text()
        if page_text.strip():
            chunks.append({
                "chunk_id": f"{pdf_name}-mid-p{mid_page+1}",
                "text": page_text[100:500],
                "page_number": mid_page + 1,
                "label": f"Mid-page text page {mid_page+1}",
            })

    return chunks


def render_page_as_image(doc: fitz.Document, page_idx: int, dpi: int = 150) -> str:
    """Render a PDF page to a base64 PNG."""
    page = doc[page_idx]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    return base64.b64encode(png_bytes).decode("utf-8")


def generate_html(results: list[dict]) -> str:
    """Generate an HTML page with PDF pages and bbox overlays."""
    html_parts = ["""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ElectOMate Bbox Diagnostic Viewer</title>
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    margin: 0;
    padding: 20px;
}
h1 { color: #00d4ff; text-align: center; }
h2 { color: #ff6b6b; border-bottom: 1px solid #333; padding-bottom: 8px; }
h3 { color: #ffd93d; }
.pdf-section { margin: 30px 0; padding: 20px; background: #16213e; border-radius: 12px; }
.chunk-info {
    background: #0f3460;
    padding: 10px 15px;
    margin: 8px 0;
    border-radius: 6px;
    font-size: 13px;
    border-left: 3px solid;
}
.chunk-info pre { margin: 4px 0; white-space: pre-wrap; font-size: 12px; color: #aaa; }
.page-container {
    position: relative;
    display: inline-block;
    margin: 15px 0;
    border: 2px solid #333;
    border-radius: 4px;
    overflow: hidden;
}
.page-container img { display: block; max-width: 100%; }
.bbox-overlay {
    position: absolute;
    border: 2px solid;
    pointer-events: none;
}
.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin: 20px 0;
}
.stat-card {
    background: #0f3460;
    padding: 15px;
    border-radius: 8px;
    text-align: center;
}
.stat-card .value { font-size: 32px; font-weight: bold; color: #00d4ff; }
.stat-card .label { font-size: 12px; color: #888; margin-top: 4px; }
.legend { display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0; }
.legend-item { display: flex; align-items: center; gap: 5px; font-size: 12px; }
.legend-swatch { width: 16px; height: 16px; border-radius: 3px; border: 1px solid #555; }
.success { color: #4caf50; }
.warning { color: #ff9800; }
.error { color: #f44336; }
</style>
</head>
<body>
<h1>ElectOMate Bounding Box Diagnostic Viewer</h1>
"""]

    # Summary stats
    total_chunks = sum(r["total_chunks"] for r in results)
    total_with_bbox = sum(r["chunks_with_bbox"] for r in results)
    total_pdfs = len(results)

    html_parts.append(f"""
<div class="stats">
    <div class="stat-card"><div class="value">{total_pdfs}</div><div class="label">PDFs Tested</div></div>
    <div class="stat-card"><div class="value">{total_chunks}</div><div class="label">Total Chunks</div></div>
    <div class="stat-card"><div class="value">{total_with_bbox}</div><div class="label">Chunks with Bboxes</div></div>
    <div class="stat-card"><div class="value">{total_with_bbox}/{total_chunks}</div><div class="label">Success Rate</div></div>
</div>
""")

    # Per-PDF sections
    for result in results:
        pdf_name = result["pdf_name"]
        status_class = "success" if result["chunks_with_bbox"] == result["total_chunks"] else "warning"

        html_parts.append(f"""
<div class="pdf-section">
    <h2>{pdf_name} <span class="{status_class}">({result['chunks_with_bbox']}/{result['total_chunks']} chunks matched)</span></h2>
""")

        # Chunk legend
        html_parts.append('<div class="legend">')
        for i, chunk in enumerate(result["chunks"]):
            color_idx = i % len(COLORS)
            bbox_count = len(chunk["bboxes"])
            status = f" ({bbox_count} bboxes)" if bbox_count else " (NO MATCH)"
            html_parts.append(f"""
            <div class="legend-item">
                <div class="legend-swatch" style="background: {COLORS[color_idx]}; border-color: {BORDER_COLORS[color_idx]};"></div>
                {chunk['label']}{status}
            </div>""")
        html_parts.append('</div>')

        # Chunk details
        for i, chunk in enumerate(result["chunks"]):
            color_idx = i % len(COLORS)
            html_parts.append(f"""
<div class="chunk-info" style="border-color: {BORDER_COLORS[color_idx]};">
    <strong>{chunk['label']}</strong> | {len(chunk['bboxes'])} bboxes | page hint: {chunk.get('page_number', '?')}
    <pre>{chunk['text_preview']}</pre>
    <pre>search_phrase: {chunk['search_phrase']!r}</pre>
</div>""")

        # Pages with overlays
        for page_data in result["pages"]:
            page_num = page_data["page_num"]
            img_b64 = page_data["image_b64"]
            page_width = page_data["width"]
            page_height = page_data["height"]

            html_parts.append(f"""
<h3>Page {page_num}</h3>
<div class="page-container" style="width: {page_width}px;">
    <img src="data:image/png;base64,{img_b64}" width="{page_width}" height="{page_height}" alt="Page {page_num}">
""")
            # Overlay bboxes
            for i, chunk in enumerate(result["chunks"]):
                color_idx = i % len(COLORS)
                for bbox in chunk["bboxes"]:
                    if bbox["page"] != page_num:
                        continue
                    # Convert PDF points to rendered pixels
                    scale = page_data["scale"]
                    left = bbox["x0"] * scale
                    top = bbox["y0"] * scale
                    width = (bbox["x1"] - bbox["x0"]) * scale
                    height = (bbox["y1"] - bbox["y0"]) * scale
                    html_parts.append(f"""
    <div class="bbox-overlay" style="left:{left:.1f}px; top:{top:.1f}px; width:{width:.1f}px; height:{height:.1f}px; background:{COLORS[color_idx]}; border-color:{BORDER_COLORS[color_idx]};"></div>""")

            html_parts.append("</div>")

        html_parts.append("</div>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8899)
    parser.add_argument("--output", default="scripts/bbox_viewer.html")
    parser.add_argument("--serve", action="store_true", help="Start HTTP server after generating")
    args = parser.parse_args()

    extractor = PDFBboxExtractor()
    results = []
    dpi = 150
    scale = dpi / 72.0

    for pdf_path in HUNGARIAN_PDFS:
        if not Path(pdf_path).exists():
            print(f"  Skipping {pdf_path} (not found)")
            continue

        print(f"\nProcessing {pdf_path}...")
        doc = fitz.open(pdf_path)
        pdf_name = Path(pdf_path).stem

        chunks = create_sample_chunks(doc, pdf_name)
        chunk_inputs = [
            {"chunk_id": c["chunk_id"], "text": c["text"], "page_number": c.get("page_number")}
            for c in chunks
        ]
        bbox_map = extractor.extract_bboxes_for_chunks(doc, chunk_inputs)

        # Enrich chunks with bbox data
        for chunk in chunks:
            chunk["bboxes"] = bbox_map.get(chunk["chunk_id"], [])
            chunk["text_preview"] = chunk["text"][:120].replace("\n", " ")
            chunk["search_phrase"] = extractor._extract_search_phrase(chunk["text"])

        # Determine which pages to render (pages with bboxes + hinted pages)
        pages_to_render = set()
        for chunk in chunks:
            if chunk.get("page_number"):
                pages_to_render.add(chunk["page_number"])
            for bbox in chunk["bboxes"]:
                pages_to_render.add(bbox["page"])

        # Render pages
        page_data = []
        for page_num in sorted(pages_to_render):
            page_idx = page_num - 1
            if page_idx < 0 or page_idx >= len(doc):
                continue
            img_b64 = render_page_as_image(doc, page_idx, dpi=dpi)
            page = doc[page_idx]
            rect = page.rect
            page_data.append({
                "page_num": page_num,
                "image_b64": img_b64,
                "width": int(rect.width * scale),
                "height": int(rect.height * scale),
                "scale": scale,
            })

        chunks_with_bbox = sum(1 for c in chunks if c["bboxes"])
        print(f"  {pdf_name}: {chunks_with_bbox}/{len(chunks)} chunks matched")

        results.append({
            "pdf_name": pdf_name,
            "total_chunks": len(chunks),
            "chunks_with_bbox": chunks_with_bbox,
            "chunks": chunks,
            "pages": page_data,
        })

        doc.close()

    # Generate HTML
    html = generate_html(results)
    output_path = Path(args.output)
    output_path.write_text(html, encoding="utf-8")
    print(f"\nHTML viewer saved to: {output_path}")
    print(f"  Size: {len(html) / 1024 / 1024:.1f} MB")

    if args.serve:
        import http.server
        import socketserver
        import os
        os.chdir(str(output_path.parent))
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", args.port), handler) as httpd:
            print(f"\nServing at http://localhost:{args.port}/{output_path.name}")
            httpd.serve_forever()
    else:
        print(f"\nTo view: open {output_path}")
        print(f"Or run: python scripts/bbox_viewer.py --serve --port {args.port}")


if __name__ == "__main__":
    main()
