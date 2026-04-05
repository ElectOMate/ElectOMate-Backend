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

    @staticmethod
    def _merge_rects(rects: list[fitz.Rect]) -> list[fitz.Rect]:
        """Merge overlapping or vertically adjacent rectangles into larger ones."""
        if not rects:
            return []
        # Sort by y0, then x0
        sorted_rects = sorted(rects, key=lambda r: (r.y0, r.x0))
        merged: list[fitz.Rect] = [fitz.Rect(sorted_rects[0])]
        for rect in sorted_rects[1:]:
            last = merged[-1]
            # Merge if on same line (y overlap) or vertically adjacent (gap < 5pt)
            if rect.y0 <= last.y1 + 5:
                merged[-1] = fitz.Rect(
                    min(last.x0, rect.x0),
                    min(last.y0, rect.y0),
                    max(last.x1, rect.x1),
                    max(last.y1, rect.y1),
                )
            else:
                merged.append(fitz.Rect(rect))
        return merged

    @staticmethod
    def _normalize_dashes(text: str) -> str:
        """Normalize various dash/hyphen characters to ASCII hyphen for matching."""
        return text.replace("—", "-").replace("–", "-").replace("−", "-").replace("·", "-")

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
        found_via_search = False

        for page_idx in search_pages:
            page = doc[page_idx]  # 0-indexed

            # Try exact search first, then with normalized dashes
            hits = page.search_for(excerpt)
            if not hits:
                normalized = self._normalize_dashes(excerpt)
                if normalized != excerpt:
                    hits = page.search_for(normalized)
            # Also try shorter phrase if full one fails
            if not hits and len(excerpt) > 40:
                short = excerpt[:40]
                last_space = short.rfind(' ')
                if last_space > 15:
                    short = short[:last_space]
                hits = page.search_for(short)

            if hits:
                # Merge overlapping/adjacent hit rects into one bounding box
                # per contiguous group rather than keeping per-word fragments.
                merged = self._merge_rects(hits)
                for rect in merged:
                    bboxes.append(BboxEntry(
                        page=page_idx + 1,  # 1-indexed
                        x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1
                    ))
                found_via_search = True
                break  # Found the page, stop searching

        # Fallback: if search_for failed on all pages, try paragraph-level
        # matching on the hinted page (or first page).
        # Use the first matched line as anchor to restrict the area.
        if not found_via_search:
            fallback_page_idx = max(0, (page_hint or 1) - 1)
            if fallback_page_idx < len(doc):
                page = doc[fallback_page_idx]
                para_bboxes = self._get_paragraph_bboxes(
                    page, fallback_page_idx, text
                )
                if para_bboxes:
                    # Use first match as anchor, filter to ±200pt
                    anchor = para_bboxes[0].y0
                    bboxes = [
                        b for b in para_bboxes
                        if abs(b.y0 - anchor) <= 200
                    ]

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
        """Extract a clean phrase for PDF text search.

        Strips Docling markdown formatting before searching — Docling outputs
        headings/bold/lists in chunk text, but the raw PDF has no markdown chars.

        Skips heading lines and continuation markers ([...]) so the search phrase
        comes from actual body content that exists in the PDF.
        """
        lines = text.strip().splitlines()

        # Skip heading lines, empty lines, and [...] markers to find body content
        body_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r'^#{1,6}\s+', stripped):
                continue
            if stripped == '[...]':
                continue
            body_lines.append(stripped)

        if not body_lines:
            # Fallback: use heading text if no body content
            body_lines = [l.strip() for l in lines if l.strip()]

        def _clean_line(line: str) -> str:
            line = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', line)
            line = re.sub(r'`[^`]+`', '', line)
            line = re.sub(r'^[-*+]\s+', '', line)
            line = re.sub(r'[»«]', '', line)
            return re.sub(r'\s+', ' ', line).strip()

        # Pick the best single line for searching — longest cleaned line,
        # since joining disjoint lines creates strings absent from the PDF.
        candidates = [_clean_line(l) for l in body_lines]
        candidates = [c for c in candidates if len(c) >= 10]
        if not candidates:
            candidates = [_clean_line(l) for l in body_lines if _clean_line(l)]
        if not candidates:
            return ''

        # Prefer the longest line for best search_for hit chance
        best = max(candidates, key=len)
        if len(best) <= length:
            return best
        phrase = best[:length]
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
        self,
        page: fitz.Page,
        page_idx: int,
        text: str,
        anchor_y: Optional[float] = None,
    ) -> list[BboxEntry]:
        """Get line-level bboxes for lines whose text appears in the chunk.

        Uses **exact substring matching only**: a PDF line is highlighted only
        if its full text (lowered) appears verbatim inside the chunk text.

        When *anchor_y* is provided (from a search_for hit), only lines within
        a vertical band around the anchor are considered. This prevents matching
        page headers/footers or unrelated sections that happen to share text.
        """
        # Strip markdown from chunk text for matching
        clean_text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        clean_text = re.sub(r'\[\.{3}\]', '', clean_text)
        clean_text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', clean_text)
        # Normalize dashes for matching
        clean_text = self._normalize_dashes(clean_text).lower()

        # Vertical band: anchor ± 400pt (roughly half a page).
        # Generous enough to cover multi-paragraph chunks but excludes
        # distant headers/footers.
        y_min = (anchor_y - 400) if anchor_y is not None else -1e9
        y_max = (anchor_y + 400) if anchor_y is not None else 1e9

        bboxes = []
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        for block in blocks:
            if block.get("type") != 0:  # Skip images
                continue
            for line in block.get("lines", []):
                line_bbox = line["bbox"]
                # Skip lines outside the vertical band
                if line_bbox[1] < y_min or line_bbox[1] > y_max:
                    continue
                line_text = " ".join(
                    span.get("text", "") for span in line.get("spans", [])
                ).strip()
                if not line_text or len(line_text) < 8:
                    continue
                # Exact substring match only — the full line must appear in the chunk
                line_lower = self._normalize_dashes(line_text).lower()
                if line_lower in clean_text:
                    bboxes.append(BboxEntry(
                        page=page_idx + 1,
                        x0=line_bbox[0], y0=line_bbox[1],
                        x1=line_bbox[2], y1=line_bbox[3],
                    ))

        return bboxes
