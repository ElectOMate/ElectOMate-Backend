"""
Secondary bbox extraction pass using PyMuPDF.
Runs AFTER existing chunking — does NOT change chunk boundaries.
Matches chunk text to PDF page lines to extract {page, x0, y0, x1, y1} bboxes.
"""
import re
import logging
import httpx
import fitz  # PyMuPDF
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_BBOXES_PER_CHUNK = 20  # Keep first 10 + last 10 if more


@dataclass
class BboxEntry:
    page: int    # 1-indexed
    x0: float
    y0: float
    x1: float
    y1: float

    def to_dict(self) -> dict:
        return {"page": self.page, "x0": self.x0, "y0": self.y0,
                "x1": self.x1, "y1": self.y1}


class PDFBboxExtractor:
    """
    Given a PDF and a list of text chunks (with page_number hints),
    extracts PyMuPDF bounding boxes for each chunk's text.

    Strategy:
    1. Load PDF with PyMuPDF
    2. For each chunk, search the chunk's text using fitz.Page.search_for()
       on the hinted page(s), expanding outward if not found
    3. Also collect surrounding line bboxes for fuller coverage
    4. Store up to MAX_BBOXES_PER_CHUNK bboxes per chunk
    """

    async def extract_from_url(self, pdf_url: str) -> fitz.Document:
        """Download PDF from URL and open with PyMuPDF."""
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()
        return fitz.open(stream=response.content, filetype="pdf")

    def extract_from_path(self, pdf_path: str | Path) -> fitz.Document:
        """Open local PDF with PyMuPDF."""
        return fitz.open(str(pdf_path))

    def extract_from_bytes(self, pdf_bytes: bytes) -> fitz.Document:
        """Open PDF from bytes with PyMuPDF."""
        return fitz.open(stream=pdf_bytes, filetype="pdf")

    def extract_bboxes_for_chunks(
        self,
        doc: fitz.Document,
        chunks: list[dict],  # Each: {"chunk_id": str, "text": str, "page_number": int | None}
    ) -> dict[str, list[dict]]:
        """
        Returns: {chunk_id: [{"page": N, "x0": f, "y0": f, "x1": f, "y1": f}, ...]}
        """
        results: dict[str, list[dict]] = {}

        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            text = chunk.get("text", "")
            page_hint = chunk.get("page_number")  # 1-indexed, may be None

            bboxes = self._find_bboxes_for_text(doc, text, page_hint)
            results[chunk_id] = [b.to_dict() for b in bboxes]
            logger.debug(
                "Extracted bboxes for chunk",
                extra={"chunk_id": chunk_id, "bbox_count": len(bboxes)}
            )

        return results

    def _find_bboxes_for_text(
        self,
        doc: fitz.Document,
        text: str,
        page_hint: Optional[int],
    ) -> list[BboxEntry]:
        """Find bboxes for chunk text in the PDF."""
        if not text or not text.strip():
            return []

        excerpt = self._extract_search_phrase(text)
        if not excerpt:
            return []

        bboxes: list[BboxEntry] = []
        search_pages = self._build_page_order(doc, page_hint)

        for page_idx in search_pages:
            page = doc[page_idx]  # 0-indexed
            hits = page.search_for(excerpt)

            if hits:
                for rect in hits:
                    bboxes.append(BboxEntry(
                        page=page_idx + 1,  # 1-indexed
                        x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1
                    ))
                # Also get surrounding line bboxes for fuller coverage
                more = self._get_paragraph_bboxes(page, page_idx, text)
                bboxes.extend(more)
                break  # Found the page, stop searching

        # Dedup by (page, rounded x0, rounded y0)
        seen: set[tuple] = set()
        deduped: list[BboxEntry] = []
        for b in bboxes:
            key = (b.page, round(b.x0, 1), round(b.y0, 1))
            if key not in seen:
                seen.add(key)
                deduped.append(b)

        # Cap: keep first 10 + last 10
        if len(deduped) > MAX_BBOXES_PER_CHUNK:
            deduped = deduped[:10] + deduped[-10:]

        return deduped

    def _extract_search_phrase(self, text: str, length: int = 80) -> str:
        """Extract a clean phrase for PDF text search."""
        clean = re.sub(r'\s+', ' ', text.strip())
        if len(clean) < 20:
            return clean
        phrase = clean[:length]
        last_space = phrase.rfind(' ')
        if last_space > 20:
            phrase = phrase[:last_space]
        return phrase.strip()

    def _build_page_order(self, doc: fitz.Document, page_hint: Optional[int]) -> list[int]:
        """Build 0-indexed page search order, starting at hint and expanding."""
        total = len(doc)
        if page_hint is None:
            return list(range(total))
        hint_0 = max(0, min(page_hint - 1, total - 1))
        order = [hint_0]
        for offset in range(1, total):
            if hint_0 - offset >= 0:
                order.append(hint_0 - offset)
            if hint_0 + offset < total:
                order.append(hint_0 + offset)
        return order

    def _get_paragraph_bboxes(
        self, page: fitz.Page, page_idx: int, text: str
    ) -> list[BboxEntry]:
        """Get line-level bboxes for lines that appear in the chunk text."""
        bboxes = []
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        chunk_words = set(text[:500].lower().split())
        if len(chunk_words) < 3:
            return []

        for block in blocks:
            if block.get("type") != 0:  # Skip images
                continue
            for line in block.get("lines", []):
                line_text = " ".join(
                    span.get("text", "") for span in line.get("spans", [])
                ).strip()
                if not line_text:
                    continue
                line_words = set(line_text.lower().split())
                overlap = chunk_words & line_words
                if len(overlap) >= min(3, len(line_words)):
                    bbox = line["bbox"]
                    bboxes.append(BboxEntry(
                        page=page_idx + 1,
                        x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3]
                    ))

        return bboxes
