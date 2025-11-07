import base64
import logging
import os
import time
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional, Sequence
from uuid import uuid4

import tiktoken
from docling.datamodel.base_models import ConfidenceReport, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.transforms.serializer.markdown import MarkdownDocSerializer
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.io import DocumentStream

from em_backend.core.config import settings

try:  # Optional improved extraction/rendering
    import fitz  # type: ignore[import]
except ImportError:  # pragma: no cover - optional
    fitz = None

logger = logging.getLogger("em_parser")


@dataclass
class PageExtraction:
    page_number: int
    text: str
    method: str
    needs_vision: bool = False


@dataclass
class OpenAIVisionConfig:
    enabled: bool
    model: str
    max_retries: int
    system_prompt: str
    user_prompt_template: str
    max_output_tokens: Optional[int]
    retry_backoff_seconds: float


def build_openai_vision_config() -> OpenAIVisionConfig:
    # Determine if Vision fallback is enabled and log its source
    raw_enabled = os.getenv("VISION_ENABLED")
    if raw_enabled is not None:
        source = "env:VISION_ENABLED"
        enabled_str = raw_enabled
    else:
        source = "default:VISION_ENABLED('true')"
        enabled_str = "true"
    enabled = enabled_str.lower() in {"1", "true", "yes", "on"}
    logger.info("VISION_ENABLED=%r => enabled=%s (source=%s)", enabled_str, enabled, source)
    model = os.getenv("VISION_MODEL", "gpt-4o-mini")
    max_retries = int(os.getenv("VISION_MAX_RETRIES", "2"))
    max_output_tokens_env = os.getenv("VISION_MAX_OUTPUT_TOKENS")
    max_output_tokens = int(max_output_tokens_env) if max_output_tokens_env else None
    retry_backoff_seconds = float(os.getenv("VISION_RETRY_BACKOFF", "2.0"))

    default_system_prompt = (
        "Extract all text from this document page and format it as Markdown. "
        "Preserve ALL formatting:\n"
        "- Headings with ## or ###\n"
        "- **Bold text**\n"
        "- *Italic text*\n"
        "- Bullet points with -\n"
        "- Numbered lists with 1. 2. 3.\n"
        "- Tables in markdown format\n"
        "- Paragraph breaks (double newlines)\n\n"
        "IMPORTANT:\n"
        "- Do NOT include image URLs or links\n"
        "- Do NOT use markdown image syntax like ![...](https://...)\n"
        "- Skip images completely, only extract TEXT\n"
        "- Do NOT add any explanations or metadata\n\n"
        "Return ONLY the formatted text content as markdown. "
        "If you cannot read the page, respond exactly with 'UNREADABLE'."
    )
    system_prompt = os.getenv("VISION_SYSTEM_PROMPT", default_system_prompt)

    default_user_prompt = (
        "Extract and format page {page_number} of '{doc_name}' as markdown. "
        "Preserve all formatting including headings, bold, italic, lists, and tables. "
        "If you cannot read the page, respond with 'UNREADABLE'."
    )
    user_prompt_template = os.getenv("VISION_USER_PROMPT_TEMPLATE", default_user_prompt)

    return OpenAIVisionConfig(
        enabled=enabled,
        model=model,
        max_retries=max_retries,
        system_prompt=system_prompt,
        user_prompt_template=user_prompt_template,
        max_output_tokens=max_output_tokens,
        retry_backoff_seconds=retry_backoff_seconds,
    )


def text_requires_ocr(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    alpha_chars = sum(ch.isalpha() for ch in stripped)
    if alpha_chars >= 30:
        return False
    lower = stripped.lower()
    if "/gid" in lower or "gid" in lower:
        return True
    gid_hits = lower.count("gid")
    word_count = max(1, len(stripped.split()))
    gid_ratio = gid_hits / word_count
    if gid_ratio > 0.2:
        return True
    alpha_ratio = alpha_chars / max(len(stripped), 1)
    return alpha_ratio < 0.05
def render_pages_to_images(
    pdf_bytes: bytes,
    page_numbers: Sequence[int],
    dpi: int = 300,
) -> Dict[int, bytes]:
    if fitz is None:
        logger.error("PyMuPDF is required to render pages for vision fallback.")
        return {}

    images: Dict[int, bytes] = {}
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")  # type: ignore[call-arg]
    except Exception as exc:
        logger.exception("Unable to open PDF with PyMuPDF for rendering: %s", exc)
        return {}

    try:
        scale = dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        for page_number in page_numbers:
            try:
                page = doc.load_page(page_number - 1)
                pix = page.get_pixmap(matrix=matrix)
                images[page_number] = pix.tobytes("png")
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Failed to render page %s for vision fallback: %s", page_number, exc)
    finally:
        doc.close()

    return images


def recover_pages_with_openai(
    pdf_bytes: bytes,
    pdf_name: str,
    page_numbers: Sequence[int],
    vision_config: OpenAIVisionConfig,
) -> Dict[int, str]:
    if not vision_config.enabled:
        logger.info("Vision fallback disabled via configuration.")
        return {}

    if not settings.openai_api_key:
        logger.warning("OpenAI API key unavailable; skipping vision fallback.")
        return {}

    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError:  # pragma: no cover - defensive
        logger.error("OpenAI python client not installed. Cannot use vision fallback.")
        return {}

    images = render_pages_to_images(pdf_bytes, page_numbers)
    if not images:
        logger.warning("No images rendered for vision fallback; skipping.")
        return {}

    client = OpenAI(api_key=settings.openai_api_key)
    recovered: Dict[int, str] = {}

    for page_number in page_numbers:
        image_bytes = images.get(page_number)
        if not image_bytes:
            continue

        prompt = vision_config.user_prompt_template.format(
            doc_name=pdf_name,
            page_number=page_number,
        )

        payload = base64.b64encode(image_bytes).decode("utf-8")
        attempt = 0
        while attempt <= vision_config.max_retries:
            try:
                messages = [
                    {"role": "system", "content": vision_config.system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{payload}", "detail": "high"},  # Use high detail for better formatting detection
                            },
                        ],
                    },
                ]

                response = client.chat.completions.create(
                    model=vision_config.model,
                    messages=messages,
                    max_tokens=vision_config.max_output_tokens or 2000,  # Increase for markdown
                )
            except Exception as exc:  # pragma: no cover - defensive
                attempt += 1
                logger.exception(
                    "Vision API call failed for page %s (attempt %s/%s): %s",
                    page_number,
                    attempt,
                    vision_config.max_retries,
                    exc,
                )
                if attempt > vision_config.max_retries:
                    logger.error("Max retries exceeded for page %s vision fallback", page_number)
                    break
                time.sleep(vision_config.retry_backoff_seconds * attempt)
                continue

            text = ""
            try:
                for choice in getattr(response, "choices", []) or []:
                    message = getattr(choice, "message", None)
                    content = getattr(message, "content", None)
                    if content:
                        text = content.strip()
                        if text:
                            break
            except Exception:  # pragma: no cover - defensive
                text = ""

            text = (text or "").strip()
            if not text:
                logger.warning("Vision model returned empty text for page %s", page_number)
            elif text.upper() == "UNREADABLE":
                logger.warning("Vision model reported page %s as unreadable", page_number)
            else:
                recovered[page_number] = text
                logger.info(
                    "Vision model recovered %s characters for page %s",
                    len(text),
                    page_number,
                )
            break

    return recovered


class DocumentParser:
    """Parse PDF files."""

    MAX_CHUNK_TOKENS = 1000  # Maximum tokens per chunk
    MIN_CHUNK_TOKENS = 400   # Minimum tokens per chunk when re-splitting
    CHUNK_OVERLAP_TOKENS = 150  # Token overlap between chunks
    MIN_INDEXABLE_TOKENS = 10  # Minimum tokens required for a chunk to be indexed
    _PLACEHOLDER_MARKERS = {"<!-- missing-text -->"}
    _GID_TOKEN = "/gid"

    def __init__(self) -> None:
        # Setup Document converter
        artifacts_path = Path.home() / ".cache" / "docling" / "models"
        pdf_options = PdfPipelineOptions(
            artifacts_path=artifacts_path,
            do_ocr=False,
            do_table_structure=True,
        )

        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pdf_options,
                )
            }
        )

        # Setup Document chunker with token limits
        self._encoding = tiktoken.encoding_for_model(settings.openai_model_name)
        self.tokenizer = OpenAITokenizer(
            tokenizer=self._encoding,
            max_tokens=self.MAX_CHUNK_TOKENS,  # Set max chunk size
        )
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
            chunk_size=self.MAX_CHUNK_TOKENS,  # Maximum chunk size
            chunk_overlap=self.CHUNK_OVERLAP_TOKENS,  # Overlap between chunks
        )
        self._current_pdf_bytes: Optional[bytes] = None
        self._current_pdf_name: Optional[str] = None
        self.vision_config = build_openai_vision_config()
        self._ocr_language_default = (
            os.getenv("OCR_LANGUAGE") or os.getenv("OCR_LANG") or "spa+eng"
        )
        # Reports directory at repository root
        repo_root = Path(__file__).resolve().parents[3]
        self._reports_dir = repo_root / "chunk_reports"
        try:
            self._reports_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Unable to create reports directory %s: %s", self._reports_dir, exc)

    def parse_document(
        self,
        filename: str,
        file: BytesIO,
    ) -> tuple[DoclingDocument, ConfidenceReport]:
        if hasattr(file, "getvalue"):
            file_bytes = file.getvalue()
        else:
            if hasattr(file, "seek"):
                file.seek(0)
            file_bytes = file.read()
            if hasattr(file, "seek"):
                file.seek(0)

        if not isinstance(file_bytes, bytes):
            raise ValueError("Unable to obtain PDF bytes for parsing.")

        self._current_pdf_bytes = file_bytes
        self._current_pdf_name = filename

        pdf_stream = BytesIO(file_bytes)
        result = self.doc_converter.convert(DocumentStream(name=filename, stream=pdf_stream))
        return result.document, result.confidence

    def serialize_document(self, doc: DoclingDocument) -> str:
        serializer = MarkdownDocSerializer(doc=doc)
        ser_result = serializer.serialize()
        return ser_result.text

    def _chunk_document_markdown_aware(self, doc: DoclingDocument) -> list[tuple[str, Optional[int]]]:
        """
        Chunk document using markdown-aware processing.
        Returns list of (text, page_number) tuples where text includes ## headers and [...] markers.
        """
        try:
            # Export full document as markdown
            full_markdown = doc.export_to_markdown()
        except Exception as e:
            logger.warning(f"Failed to export markdown, using fallback: {e}")
            return []

        if not full_markdown or self._contains_gid(full_markdown):
            logger.warning("Document has gid markers or empty markdown content")
            return []

        # Build a mapping of text content to page numbers from document structure
        page_mapping = self._build_page_mapping(doc)

        # Parse markdown into sections with heading hierarchy
        sections = self._parse_markdown_sections(full_markdown, doc)
        logger.info(f"📑 Parsed {len(sections)} sections from markdown")

        # Enhance sections with page numbers from mapping
        sections = self._enhance_sections_with_pages(sections, page_mapping)
        logger.info(f"📍 Enhanced sections with page numbers")

        # Chunk each section with context markers (adds ## headers and [...])
        chunks = []
        for section in sections:
            section_chunks = self._chunk_section_with_context(section)
            chunks.extend(section_chunks)

        logger.info(f"✂️ Generated {len(chunks)} chunks from {len(sections)} sections")
        return chunks

    def _build_page_mapping(self, doc: DoclingDocument) -> dict[str, int]:
        """
        Build a mapping from text content to page numbers by analyzing document structure.
        Returns dict mapping text snippets to their page numbers.
        """
        page_mapping = {}

        # Iterate through document elements to build text -> page mapping
        if hasattr(doc, 'texts') and doc.texts:
            for text_item in doc.texts:
                # Extract text
                text_content = getattr(text_item, 'text', None) or getattr(text_item, 'orig', '')
                if not text_content or len(text_content.strip()) < 10:
                    continue

                # Extract page number from provenance
                page_num = self._first_page_number(text_item)
                if page_num:
                    # Use first ~50 chars as key (enough to match sections)
                    key = text_content.strip()[:50].lower()
                    page_mapping[key] = page_num

        logger.debug(f"Built page mapping with {len(page_mapping)} entries")
        return page_mapping

    def _enhance_sections_with_pages(
        self,
        sections: list[dict[str, Any]],
        page_mapping: dict[str, int]
    ) -> list[dict[str, Any]]:
        """
        Enhance sections with page numbers from the page mapping.
        Tries to match section content against mapped text to find page numbers.
        """
        import re

        for section in sections:
            # Try to find page number by matching section content
            content_text = "\n".join(section["content"])

            # Strip markdown formatting for matching (remove ##, -, *, etc.)
            clean_content = re.sub(r'^#{1,6}\s+', '', content_text, flags=re.MULTILINE)
            clean_content = re.sub(r'^\s*[-*]\s+', '', clean_content, flags=re.MULTILINE)
            clean_content = clean_content.strip()

            # Try exact match with different lengths
            matched = False
            for length in [50, 100, 150, 30, 20]:
                key = clean_content[:length].lower()
                if key in page_mapping:
                    section["page_number"] = page_mapping[key]
                    logger.debug(f"Matched section to page {section['page_number']}")
                    matched = True
                    break

            # If no match found, try matching just the title (cleaned)
            if not matched and section["title"]:
                title_clean = section["title"].strip().lower()
                # Try to find this title in any mapped text
                for mapped_text, page_num in page_mapping.items():
                    if title_clean in mapped_text or mapped_text[:len(title_clean)] == title_clean:
                        section["page_number"] = page_num
                        logger.debug(f"Title matched section to page {page_num}")
                        matched = True
                        break

        # Fill gaps: if we have some page numbers, interpolate missing ones
        for i in range(1, len(sections)):
            if sections[i]["page_number"] == 1 and sections[i-1]["page_number"] > 1:
                # Likely continuation of previous page or next page
                sections[i]["page_number"] = sections[i-1]["page_number"]
                logger.debug(f"Interpolated page {sections[i]['page_number']} for section")

        return sections

    def _parse_markdown_sections(self, markdown_text: str, doc: DoclingDocument) -> list[dict[str, Any]]:
        """
        Parse markdown text into sections with heading hierarchy.
        Returns list of sections with: {title, level, content, page_number, heading_stack}
        """
        import re

        sections = []
        lines = markdown_text.split("\n")

        current_section = {
            "title": "",
            "level": 0,
            "content": [],
            "page_number": 1,
            "heading_stack": []
        }

        for line in lines:
            # Check for markdown heading (##, ###, etc.)
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if heading_match:
                # Save previous section if it has content
                if current_section["content"]:
                    sections.append(current_section.copy())

                # Start new section
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Update heading stack (track hierarchy)
                heading_stack = current_section["heading_stack"][:level-1]
                heading_stack.append(title)

                current_section = {
                    "title": title,
                    "level": level,
                    "content": [line],  # Include heading in content
                    "page_number": current_section["page_number"],
                    "heading_stack": heading_stack
                }
            else:
                current_section["content"].append(line)

        # Add final section
        if current_section["content"]:
            sections.append(current_section)

        return sections

    def _chunk_section_with_context(self, section: dict[str, Any]) -> list[tuple[str, Optional[int]]]:
        """
        Chunk a section while preserving markdown and adding context.
        Adds section title hierarchy and [...] markers for split content.
        Returns list of (text, page_number) tuples.
        """
        content_text = "\n".join(section["content"])
        tokens = self._encoding.encode(content_text)
        token_count = len(tokens)

        # If section fits in one chunk, return as-is
        if token_count <= self.MAX_CHUNK_TOKENS:
            return [(content_text, section["page_number"])]

        # Section needs to be split - add context markers
        chunks = []
        section_header = self._format_section_header(section)

        # Calculate header overhead
        header_tokens = len(self._encoding.encode(section_header + "\n\n"))
        marker_tokens = len(self._encoding.encode("[...]\n\n"))

        # Adjust chunk size to account for header overhead
        effective_chunk_size = self.MAX_CHUNK_TOKENS - header_tokens - (2 * marker_tokens)

        # Split content into token-sized chunks
        char_positions = []
        for i in range(len(tokens)):
            char_pos = len(self._encoding.decode(tokens[:i]))
            char_positions.append(char_pos)
        char_positions.append(len(content_text))

        start_token = 0

        while start_token < token_count:
            end_token = min(start_token + effective_chunk_size, token_count)

            # Get character positions
            start_char = char_positions[start_token]
            end_char = char_positions[end_token]

            chunk_text = content_text[start_char:end_char]

            # Add section header and continuation markers
            is_first = (start_token == 0)
            is_last = (end_token >= token_count)

            formatted_chunk = self._format_chunk_with_context(
                chunk_text=chunk_text,
                section_header=section_header,
                is_first=is_first,
                is_last=is_last
            )

            chunks.append((formatted_chunk, section["page_number"]))

            # Move to next chunk with overlap
            if end_token >= token_count:
                break

            start_token = end_token - self.CHUNK_OVERLAP_TOKENS

        return chunks

    def _format_section_header(self, section: dict[str, Any]) -> str:
        """Format section header with full heading hierarchy."""
        heading_stack = section.get("heading_stack", [section["title"]])

        # Build hierarchical header
        lines = []
        for i, heading in enumerate(heading_stack):
            level = i + 1
            lines.append(f"{'#' * level} {heading}")

        return "\n".join(lines)

    def _format_chunk_with_context(
        self,
        chunk_text: str,
        section_header: str,
        is_first: bool,
        is_last: bool
    ) -> str:
        """
        Format chunk with section header and continuation markers.

        Format:
        ## Section Title

        [...]

        Content here...

        [...]
        """
        parts = []

        # Add section header
        parts.append(section_header)
        parts.append("")  # Empty line

        # Add leading continuation marker if not first chunk
        if not is_first:
            parts.append("[...]")
            parts.append("")

        # Add content
        parts.append(chunk_text.strip())

        # Add trailing continuation marker if not last chunk
        if not is_last:
            parts.append("")
            parts.append("[...]")

        return "\n".join(parts)

    def _parse_markdown_sections_simple(self, markdown_text: str, page_number: int) -> list[dict[str, Any]]:
        """
        Simplified markdown parser for vision-extracted text (per-page).
        Returns list of sections with: {title, level, content, page_number}
        """
        import re

        sections = []
        lines = markdown_text.split("\n")

        current_section = {
            "title": "",
            "level": 0,
            "content": [],
            "page_number": page_number,
            "heading_stack": []
        }

        for line in lines:
            # Check for markdown heading
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if heading_match:
                # Save previous section if it has content
                if current_section["content"]:
                    sections.append(current_section.copy())

                # Start new section
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Update heading stack (track hierarchy)
                heading_stack = current_section["heading_stack"][:level-1]
                heading_stack.append(title)

                current_section = {
                    "title": title,
                    "level": level,
                    "content": [line],  # Include heading in content
                    "page_number": page_number,
                    "heading_stack": heading_stack
                }
            else:
                current_section["content"].append(line)

        # Add final section
        if current_section["content"]:
            sections.append(current_section)

        # If no sections found (no headings), create one section with all content
        if not sections:
            sections.append({
                "title": f"Page {page_number}",
                "level": 1,
                "content": lines,
                "page_number": page_number,
                "heading_stack": [f"Page {page_number}"]
            })

        return sections

    def chunk_document(self, doc: DoclingDocument) -> Generator[dict[str, Any]]:
        """
        Chunk document using markdown export with section parsing.

        Falls back to HybridChunker if markdown export fails or contains placeholders.
        Uses vision fallback for problematic pages.
        """
        # Try markdown export + section parsing first (to get section headers)
        try:
            full_markdown = doc.export_to_markdown()
            logger.info(f"Markdown export length: {len(full_markdown) if full_markdown else 0} chars")

            if full_markdown and not self._contains_gid(full_markdown):
                logger.info("Using markdown export with section parsing...")
                markdown_chunks = self._chunk_document_markdown_aware(doc)
                logger.info(f"Markdown-aware chunking produced {len(markdown_chunks)} chunks")

                if markdown_chunks:
                    collected_chunks: list[dict[str, Any]] = []
                    chunk_index = 0

                    for chunk_text, page_number in markdown_chunks:
                        if not chunk_text.strip():
                            continue

                        token_count = len(self._encoding.encode(chunk_text))

                        if token_count < self.MIN_INDEXABLE_TOKENS:
                            continue

                        text_preview = chunk_text[:100] if len(chunk_text) > 100 else chunk_text

                        chunk_data = {
                            "chunk_id": str(uuid4()),
                            "text": chunk_text,
                            "page_number": page_number,
                            "chunk_index": chunk_index,
                            "token_count": token_count,
                        }

                        logger.info(
                            f"Generated chunk {chunk_index}: {token_count} tokens, page {page_number}, text: {repr(text_preview)}"
                        )

                        collected_chunks.append(chunk_data)
                        chunk_index += 1

                    # Yield chunks and write summary
                    for chunk in collected_chunks:
                        yield chunk

                    self._write_summary_report(
                        chunks=collected_chunks,
                        total_chunks=len(collected_chunks),
                        attempted=0,
                        succeeded=0,
                        failed=0,
                    )
                    return
                else:
                    logger.warning("Markdown-aware chunking produced no chunks, falling back to HybridChunker")
            else:
                has_gid = self._contains_gid(full_markdown) if full_markdown else False
                logger.warning(f"Markdown export check failed (empty={not full_markdown}, has_gid={has_gid}), falling back to HybridChunker")
        except Exception as e:
            logger.warning(f"Markdown export failed: {e}, falling back to HybridChunker")

        # Fallback: Use HybridChunker
        logger.info("Using HybridChunker fallback...")
        serializer = MarkdownDocSerializer(doc=doc)
        encoding = self._encoding

        collected_chunks = []
        chunk_index = 0

        stats_summary = {
            "placeholder_segments": 0,
            "fallback_used": 0,
            "fallback_failed": 0,
        }

        # Use HybridChunker to get chunks
        for raw_chunk in self.chunker.chunk(doc):
            segment_text, segment_page, segment_stats = self._extract_markdown_segment(
                raw_chunk, serializer, self.chunker, doc
            )
            stats_summary["placeholder_segments"] += segment_stats["placeholder_segments"]
            if segment_stats["fallback_used"]:
                stats_summary["fallback_used"] += 1
            if segment_stats["fallback_failed"]:
                stats_summary["fallback_failed"] += 1

            if not segment_text.strip():
                chunk_index += 1
                continue

            # Split segment into token-sized chunks
            for text_segment in self._split_to_token_budget(segment_text):
                token_count = len(encoding.encode(text_segment))

                if token_count < self.MIN_INDEXABLE_TOKENS:
                    continue

                text_preview = text_segment[:100] if len(text_segment) > 100 else text_segment

                chunk_data = {
                    "chunk_id": str(uuid4()),
                    "text": text_segment,
                    "page_number": segment_page,
                    "chunk_index": chunk_index,
                    "token_count": token_count,
                }

                logger.info(
                    f"Generated chunk {chunk_index}: {token_count} tokens, page {segment_page}, text: {repr(text_preview)}"
                )

                collected_chunks.append(chunk_data)
                chunk_index += 1

        # Check if we need vision fallback
        fallback_needed = (
            stats_summary["fallback_failed"] > 0
            or not collected_chunks
            or any(self._contains_gid(c["text"]) for c in collected_chunks)
        )

        if fallback_needed and self._current_pdf_bytes:
            logger.warning(
                "Docling chunking left unresolved placeholders; attempting OpenAI vision fallback"
            )
            placeholder_pages = self._placeholder_pages_from_chunks(collected_chunks)
            fallback_chunks = self._chunk_with_openai_vision(placeholder_pages)

            if fallback_chunks:
                for chunk in fallback_chunks:
                    yield chunk
                self._write_summary_report(
                    chunks=fallback_chunks,
                    total_chunks=len(fallback_chunks),
                    attempted=len(placeholder_pages),
                    succeeded=len(fallback_chunks),
                    failed=len(placeholder_pages) - len(fallback_chunks),
                )
                return
            logger.warning("OpenAI vision fallback produced no usable chunks; using original output")

        # Yield all collected chunks
        for chunk in collected_chunks:
            yield chunk

        self._write_summary_report(
            chunks=collected_chunks,
            total_chunks=len(collected_chunks),
            attempted=0,
            succeeded=0,
            failed=0,
        )

    def _write_summary_report(
        self,
        chunks: list[dict[str, Any]],
        total_chunks: int,
        attempted: int,
        succeeded: int,
        failed: int,
    ) -> None:
        """Write a markdown summary of chunking results to disk."""
        try:
            # Build report lines
            report_lines: list[str] = []
            report_lines.append(f"# Chunking Report for {self._current_pdf_name}")
            report_lines.append("")
            report_lines.append(f"- Total chunks: {total_chunks}")
            report_lines.append(f"- Vision fallback attempted: {attempted}")
            report_lines.append(f"- Vision fallback succeeded: {succeeded}")
            report_lines.append(f"- Vision fallback failed: {failed}")
            report_lines.append("")
            report_lines.append("## Chunk Details")
            report_lines.append("| Index | Page | Tokens | Preview |")
            report_lines.append("|-------|------|--------|---------|")
            for ch in chunks:
                idx = ch.get("chunk_index", "")
                page = ch.get("page_number", "")
                tokens = ch.get("token_count", "")
                # truncate preview, escape pipes
                text = ch.get("text", "").replace("\n", " ")
                preview = text[:50].replace("|", "\\|")
                report_lines.append(f"| {idx} | {page} | {tokens} | {preview} |")
            report_text = "\n".join(report_lines)
            # Ensure reports directory exists
            self._reports_dir.mkdir(parents=True, exist_ok=True)
            # Filename based on document name
            fname = Path(self._current_pdf_name).stem + "_chunk_summary.md"
            target = self._reports_dir / fname
            with open(target, "w", encoding="utf-8") as f:
                f.write(report_text)
            logger.info(f"Chunk summary report written to {target}")
        except Exception as e:
            logger.error(f"Failed to write chunk summary report: {e}")

    @staticmethod
    def _extract_markdown_segment(
        chunk: Any,
        serializer: MarkdownDocSerializer,
        chunker: HybridChunker,
        doc: Optional[DoclingDocument],
    ) -> tuple[str, Optional[int], dict[str, bool | int]]:
        text_parts: list[str] = []
        page_candidates: list[int] = []
        placeholder_segments = 0

        doc_items = None
        if hasattr(chunk, "meta") and chunk.meta is not None:
            doc_items = getattr(chunk.meta, "doc_items", None)

        if doc_items:
            for item in doc_items:
                resolved_item = DocumentParser._resolve_doc_item(doc, item)

                serialized_text = DocumentParser._serialize_doc_item(
                    serializer, resolved_item
                )

                if DocumentParser._is_placeholder_text(serialized_text):
                    placeholder_segments += 1
                    serialized_text = DocumentParser._serialize_doc_item(
                        serializer, item
                    )

                if DocumentParser._is_placeholder_text(serialized_text):
                    placeholder_segments += 1
                    continue

                text_parts.append(serialized_text.strip())

                page = (
                    DocumentParser._first_page_number(resolved_item)
                    if resolved_item is not None
                    else None
                )
                if page is None:
                    page = DocumentParser._first_page_number(item)
                if page is not None:
                    page_candidates.append(page)

        if not text_parts:
            try:
                contextualized = chunker.contextualize(chunk)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to contextualize chunk: %s", exc)
                contextualized = ""

            if contextualized and not DocumentParser._is_placeholder_text(contextualized):
                text_parts.append(contextualized.strip())

                meta = getattr(chunk, "meta", None)
                if meta is not None and hasattr(meta, "doc_items") and meta.doc_items:
                    page = DocumentParser._first_page_number(meta.doc_items[0])
                    if page is not None:
                        page_candidates.append(page)

        combined_text = "\n\n".join(part for part in text_parts if part)
        fallback_attempted = False
        fallback_success = False

        if combined_text:
            if DocumentParser._contains_gid(combined_text):
                fallback_attempted = True
                fallback = DocumentParser._fallback_chunk_text(chunker, chunk)
                if fallback and not DocumentParser._contains_gid(fallback):
                    combined_text = fallback
                    fallback_success = True
                else:
                    combined_text = ""
        else:
            fallback_attempted = True
            fallback = DocumentParser._fallback_chunk_text(chunker, chunk)
            if fallback and not DocumentParser._contains_gid(fallback):
                combined_text = fallback
                fallback_success = True

        page_number = page_candidates[0] if page_candidates else None

        stats = {
            "placeholder_segments": placeholder_segments,
            "fallback_used": fallback_success,
            "fallback_failed": fallback_attempted and not fallback_success,
        }

        return combined_text, page_number, stats

    @staticmethod
    def _is_placeholder_text(value: str) -> bool:
        if not value:
            return True
        normalized = value.strip()
        if not normalized:
            return True
        lowered = normalized.lower()
        if lowered in DocumentParser._PLACEHOLDER_MARKERS:
            return True
        if DocumentParser._contains_gid(lowered):
            return True
        stripped_bullet = lowered.lstrip(" -*•\u2022\t")
        if DocumentParser._contains_gid(stripped_bullet):
            return True
        return False

    @staticmethod
    def _serialize_doc_item(
        serializer: MarkdownDocSerializer, item: Optional[Any]
    ) -> str:
        if item is None:
            return ""
        try:
            result = serializer.serialize(item=item)
            return (result.text or "").strip()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Doc item serialization failed: %s", exc)
            return (
                getattr(item, "text", "")
                or getattr(item, "orig", "")
                or getattr(item, "markdown", "")
            )

    @staticmethod
    def _resolve_doc_item(
        doc: Optional[DoclingDocument], item: Optional[Any]
    ) -> Optional[Any]:
        if item is None or doc is None:
            return item

        resolver = getattr(item, "resolve", None)
        if callable(resolver):
            try:
                resolved = resolver(doc)
                if resolved is not None:
                    return resolved
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Doc item resolve() failed: %s", exc)

        reference = getattr(item, "self_ref", None) or getattr(item, "cref", None)
        if isinstance(reference, str):
            resolved_ref = DocumentParser._resolve_doc_reference(doc, reference)
            if resolved_ref is not None:
                return resolved_ref

        return item

    @staticmethod
    def _resolve_doc_reference(doc: DoclingDocument, reference: str) -> Optional[Any]:
        if not reference or not reference.startswith("#/"):
            return None

        target: Any = doc
        for component in reference.lstrip("#/").split("/"):
            if target is None:
                return None
            if isinstance(target, list):
                if not component.isdigit():
                    return None
                index = int(component)
                if index < 0 or index >= len(target):
                    return None
                target = target[index]
                continue
            if isinstance(target, dict):
                target = target.get(component)
                continue
            if hasattr(target, component):
                target = getattr(target, component)
                continue
            return None

        return target

    @staticmethod
    def _first_page_number(item: Any) -> Optional[int]:
        """Extract first page number from item provenance."""
        if hasattr(item, "prov") and item.prov:
            for provenance in item.prov:
                page = getattr(provenance, "page_no", None)
                if page is not None:
                    return page
        return None

    @staticmethod
    def _contains_gid(value: str) -> bool:
        if not value:
            return False
        return DocumentParser._GID_TOKEN in value.lower()

    @staticmethod
    def _placeholder_pages_from_chunks(
        chunks: Sequence[dict[str, Any]]
    ) -> set[int]:
        pages: set[int] = set()
        for chunk in chunks:
            page_number = chunk.get("page_number")
            if page_number is None:
                continue
            text = chunk.get("text", "")
            if DocumentParser._is_placeholder_text(text):
                pages.add(int(page_number))
        return pages

    @staticmethod
    def _fallback_chunk_text(chunker: HybridChunker, chunk: Any) -> str:
        candidates: list[str] = []

        serialize_fn = getattr(chunker, "serialize", None)
        if callable(serialize_fn):
            try:
                serialized_text = serialize_fn(chunk)
                if isinstance(serialized_text, str) and serialized_text.strip():
                    candidates.append(serialized_text.strip())
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Chunk serialize fallback failed: %s", exc)

        try:
            contextualized = chunker.contextualize(chunk)
            if isinstance(contextualized, str) and contextualized.strip():
                candidates.append(contextualized.strip())
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Chunk contextualize fallback failed: %s", exc)

        for candidate in candidates:
            if not DocumentParser._contains_gid(candidate) and not DocumentParser._is_placeholder_text(candidate):
                return candidate
        return ""

    def _chunk_with_openai_vision(
        self,
        placeholder_pages: Optional[set[int]] = None,
    ) -> list[dict[str, Any]]:
        pdf_bytes = self._current_pdf_bytes
        if not pdf_bytes:
            logger.error("Cannot run vision fallback without original PDF bytes.")
            return []

        pdf_name = self._current_pdf_name or "document.pdf"
        if not self.vision_config.enabled:
            logger.info("Vision fallback disabled via configuration.")
            return []

        all_pages = self._list_pdf_pages(pdf_bytes)
        if not all_pages:
            logger.error("Unable to enumerate PDF pages for vision fallback.")
            return []

        fallback_candidates = (
            sorted(set(placeholder_pages or set()).intersection(all_pages))
            if placeholder_pages
            else list(all_pages)
        )
        if not fallback_candidates:
            fallback_candidates = list(all_pages)

        recovered = recover_pages_with_openai(
            pdf_bytes,
            pdf_name,
            fallback_candidates,
            self.vision_config,
        )

        missing_pages = set(fallback_candidates) - set(recovered.keys())
        if missing_pages:
            logger.warning(
                "Vision fallback returned no text for pages: %s",
                sorted(missing_pages),
            )

        if not recovered:
            logger.warning("Vision fallback did not recover any text.")
            return []

        report_pages: list[PageExtraction] = []
        usable_pages: list[PageExtraction] = []

        for page_number in fallback_candidates:
            recovered_text = (recovered.get(page_number) or "").strip()
            if not recovered_text:
                report_pages.append(
                    PageExtraction(
                        page_number=page_number,
                        text="",
                        method=f"vision:{self.vision_config.model}",
                        needs_vision=True,
                    )
                )
                continue

            words = recovered_text.replace("\n", " ").split()
            snippet = " ".join(words[:200])
            logger.info(
                "[Vision] Page %s recovered text (first %s words): %s",
                page_number,
                min(200, len(words)),
                snippet,
            )

            page_entry = PageExtraction(
                page_number=page_number,
                text=recovered_text,
                method=f"vision:{self.vision_config.model}",
                needs_vision=False,
            )
            report_pages.append(page_entry)
            usable_pages.append(page_entry)

        chunks: list[dict[str, Any]] = []
        encoding = self._encoding
        chunk_index = 0
        for page in usable_pages:
            text = page.text.strip()
            if not text:
                logger.warning("Page %s still has no extractable text; skipping.", page.page_number)
                continue

            # Parse recovered text as markdown sections
            try:
                sections = self._parse_markdown_sections_simple(text, page.page_number)
            except Exception as e:
                logger.warning(f"Failed to parse markdown for page {page.page_number}: {e}")
                sections = [{
                    "title": f"Page {page.page_number}",
                    "level": 1,
                    "content": text.split("\n"),
                    "page_number": page.page_number,
                    "heading_stack": [f"Page {page.page_number}"]
                }]

            # Chunk each section with context
            for section in sections:
                section_chunks = self._chunk_section_with_context(section)
                for chunk_text, chunk_page in section_chunks:
                    token_count = len(encoding.encode(chunk_text))
                    chunk_data = {
                        "chunk_id": str(uuid4()),
                        "text": chunk_text,
                        "page_number": chunk_page or page.page_number,
                        "chunk_index": chunk_index,
                        "token_count": token_count,
                        "extraction_method": page.method,
                    }
                    chunks.append(chunk_data)
                    chunk_index += 1

        if not chunks:
            logger.error("OpenAI vision fallback yielded no chunks.")
            return []

        self._write_fallback_report(pdf_name, report_pages, chunks)

        logger.info("OpenAI vision fallback produced %s chunks.", len(chunks))
        # Filter out tiny fallback chunks as well
        filtered = [chunk for chunk in chunks if len(encoding.encode(chunk["text"])) >= 10]
        if len(filtered) < len(chunks):
            logger.info("Filtered out %s small fallback chunks", len(chunks) - len(filtered))
        return [
            {
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "page_number": chunk["page_number"],
                "chunk_index": index,
            }
            for index, chunk in enumerate(filtered)
        ]

    def _list_pdf_pages(self, pdf_bytes: bytes) -> list[int]:
        if fitz is None:
            logger.error("PyMuPDF is required to enumerate PDF pages for vision fallback.")
            return []

        try:
            document = fitz.open(stream=pdf_bytes, filetype="pdf")  # type: ignore[call-arg]
        except Exception as exc:
            logger.exception("Unable to open PDF with PyMuPDF: %s", exc)
            return []

        try:
            return list(range(1, document.page_count + 1))
        finally:
            document.close()

    def _split_to_token_budget(self, text: str) -> Iterable[str]:
        encoding = self._encoding
        tokens = encoding.encode(text)
        total_tokens = len(tokens)

        if total_tokens == 0:
            return []

        if total_tokens <= self.MAX_CHUNK_TOKENS:
            return [text]

        segments: list[str] = []
        start = 0
        while start < total_tokens:
            end = min(start + self.MAX_CHUNK_TOKENS, total_tokens)
            segment_tokens = tokens[start:end]
            remaining_tokens = total_tokens - end

            if remaining_tokens and remaining_tokens < self.MIN_CHUNK_TOKENS:
                end = total_tokens
                segment_tokens = tokens[start:end]
                remaining_tokens = 0

            segment_text = encoding.decode(segment_tokens)
            segments.append(segment_text)

            if end >= total_tokens:
                break

            start = end - self.CHUNK_OVERLAP_TOKENS
            start = max(start, 0)

        return segments

    def _write_fallback_report(
        self,
        pdf_name: str,
        pages: list[PageExtraction],
        chunks: list[dict[str, Any]],
    ) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = Path(pdf_name).stem or "document"
        report_path = self._reports_dir / f"{safe_name}_fallback_{timestamp}.md"

        lines: list[str] = []
        lines.append(f"# OpenAI Vision Fallback Report for {pdf_name}")
        lines.append("")
        lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
        lines.append(f"Total fallback chunks: {len(chunks)}")
        lines.append("")

        for page in pages:
            lines.append(f"## Page {page.page_number} (method={page.method})")
            lines.append("")
            snippet = page.text.strip()
            if len(snippet) > 2000:
                snippet = snippet[:2000] + " …"
            lines.append("```text")
            lines.append(snippet)
            lines.append("```")
            lines.append("")

        try:
            report_path.write_text("\n".join(lines), encoding="utf-8")
            logger.info("Fallback markdown report written to %s", report_path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to write fallback report: %s", exc)
