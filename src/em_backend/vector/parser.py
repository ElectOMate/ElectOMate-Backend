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
        "You are an assistant that transcribes textual content from scanned document pages. "
        "Return clean plain text in the original language, preserving headings and structure. "
        "If you cannot read the page, respond exactly with 'UNREADABLE'."
    )
    system_prompt = os.getenv("VISION_SYSTEM_PROMPT", default_system_prompt)

    default_user_prompt = (
        "This is page {page_number} of the document '{doc_name}'. Extract all readable text "
        "and present it as plain text. Preserve headings, bullet points, and paragraph breaks. "
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
                                "image_url": {"url": f"data:image/png;base64,{payload}", "detail": "auto"},
                            },
                        ],
                    },
                ]

                response = client.chat.completions.create(
                    model=vision_config.model,
                    messages=messages,
                    max_tokens=vision_config.max_output_tokens,
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

    MAX_CHUNK_TOKENS = 500  # Maximum tokens per chunk
    MIN_CHUNK_TOKENS = 400   # Minimum tokens per chunk when re-splitting
    CHUNK_OVERLAP_TOKENS = 75  # Token overlap between chunks
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

    def chunk_document(self, doc: DoclingDocument) -> Generator[dict[str, Any]]:
        """
        Chunk document using HybridChunker while preserving page numbers.

        Uses contextualize() to get clean text from each chunk and extracts
        page numbers from chunk metadata.
        """
        serializer = MarkdownDocSerializer(doc=doc)
        encoding = self._encoding
        separator_text = "\n\n"
        separator_tokens = encoding.encode(separator_text) if separator_text else []

        segments: list[tuple[str, Optional[int]]] = []
        stats_summary = {
            "placeholder_segments": 0,
            "fallback_used": 0,
            "fallback_failed": 0,
        }

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
                continue
            segments.append((segment_text, segment_page))

        if not segments:
            logger.warning("No chunk segments produced from document; skipping chunking")
            return

        if any(stats_summary.values()):
            logger.info(
                "Placeholder filtering summary: removed=%s, fallback_used=%s, fallback_failed=%s",
                stats_summary["placeholder_segments"],
                stats_summary["fallback_used"],
                stats_summary["fallback_failed"],
            )

        tokens: list[int] = []
        token_pages: list[Optional[int]] = []
        for idx, (segment_text, segment_page) in enumerate(segments):
            segment_tokens = encoding.encode(segment_text)
            if not segment_tokens:
                continue
            tokens.extend(segment_tokens)
            token_pages.extend([segment_page] * len(segment_tokens))

            if idx < len(segments) - 1 and separator_tokens:
                tokens.extend(separator_tokens)
                token_pages.extend([segment_page] * len(separator_tokens))

        if not tokens:
            logger.warning("Chunk tokenisation produced no tokens; skipping chunk generation")
            return

        step = max(self.MAX_CHUNK_TOKENS - self.CHUNK_OVERLAP_TOKENS, 1)
        max_start = max(len(tokens) - self.MAX_CHUNK_TOKENS, 0)
        # Initialize summary tracking
        all_chunks: list[dict[str, Any]] = []
        fallback_attempted = False
        fallback_placeholder_count = 0
        fallback_success_count = 0
        fallback_failed_count = 0
        start_positions: set[int] = {0, max_start}

        current = step
        while current <= max_start:
            start_positions.add(current)
            current += step

        chunk_index = 0
        last_chunk_tokens: Optional[list[int]] = None
        collected_chunks: list[dict[str, Any]] = []

        for start in sorted(start_positions):
            end = min(start + self.MAX_CHUNK_TOKENS, len(tokens))
            chunk_tokens = tokens[start:end]
            if not chunk_tokens:
                continue

            if last_chunk_tokens is not None and chunk_tokens == last_chunk_tokens:
                continue

            chunk_text = encoding.decode(chunk_tokens)
            # Skip chunks containing placeholder markers
            if any(marker in chunk_text for marker in self._PLACEHOLDER_MARKERS):
                logger.info(
                    "Skipping placeholder chunk %s: contains marker", chunk_index
                )
                continue
            page_candidates = [
                page for page in token_pages[start:end] if page is not None
            ]
            page_number = page_candidates[0] if page_candidates else None

            token_count = len(chunk_tokens)
            # Skip tiny chunks to avoid indexing trivial content
            if token_count < 10:
                logger.info("Skipping small chunk %s: %s tokens", chunk_index, token_count)
                continue
            text_preview_raw = chunk_text[:100] if len(chunk_text) > 100 else chunk_text
            text_preview = repr(text_preview_raw)

            logger.info(
                "Generated chunk %s: %s tokens, page %s, text: %s",
                chunk_index,
                token_count,
                page_number if page_number is not None else "unknown",
                text_preview,
            )

            collected_chunks.append(
                {
                    "chunk_id": str(uuid4()),
                    "text": chunk_text,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "token_count": token_count,
                }
            )

            last_chunk_tokens = chunk_tokens
            chunk_index += 1

        gid_remaining = any(self._contains_gid(chunk["text"]) for chunk in collected_chunks)
        fallback_needed = stats_summary["fallback_failed"] > 0 or gid_remaining

        if fallback_needed or not collected_chunks:
            if self._current_pdf_bytes:
                logger.warning(
                    "Docling chunking left unresolved placeholders; attempting OpenAI vision fallback."
                )
                # Determine pages needing OCR
                placeholder_pages = self._placeholder_pages_from_chunks(collected_chunks)
                # Track fallback metrics
                fallback_attempted = True
                fallback_placeholder_count = len(placeholder_pages)
                # Run vision fallback
                fallback_chunks = self._chunk_with_openai_vision(placeholder_pages)
                # Count successes/failures
                fallback_success_count = len(fallback_chunks)
                fallback_failed_count = fallback_placeholder_count - fallback_success_count
                if fallback_chunks:
                    # Yield recovered chunks and write summary
                    for chunk in fallback_chunks:
                        yield chunk
                    self._write_summary_report(
                        chunks=fallback_chunks,
                        total_chunks=fallback_success_count,
                        attempted=fallback_placeholder_count,
                        succeeded=fallback_success_count,
                        failed=fallback_failed_count,
                    )
                    return
                logger.warning("OpenAI vision fallback produced no usable chunks; using original output.")
            else:
                logger.warning(
                    "Fallback needed but original PDF bytes unavailable; skipping OpenAI vision attempt."
                )

        # Yield all collected chunks and gather for reporting
        for chunk in collected_chunks:
            all_chunks.append(chunk)
            yield {
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
            }
        # Write a markdown summary report after chunking
        self._write_summary_report(
            chunks=all_chunks,
            total_chunks=len(all_chunks),
            attempted=fallback_placeholder_count,
            succeeded=fallback_success_count,
            failed=fallback_failed_count,
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

            for text_segment in self._split_to_token_budget(text):
                text_segment = text_segment.strip()
                if not text_segment:
                    continue
                token_count = len(encoding.encode(text_segment))
                chunk_data = {
                    "chunk_id": str(uuid4()),
                    "text": text_segment,
                    "page_number": page.page_number,
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
