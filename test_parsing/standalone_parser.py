#!/usr/bin/env python3
"""
Standalone PDF Parser for Testing and Debugging

This script replicates the DocumentParser functionality but runs independently
for testing and debugging purposes. It includes enhanced debugging for page
number extraction and stores results locally.

Usage:
    python standalone_parser.py /path/to/your/document.pdf
"""

import argparse
import base64
import json
import logging
import os
import re
import sys
import textwrap
import time
from collections import Counter
from collections.abc import Generator, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

# Try to load .env or .env2 file
try:
    from dotenv import load_dotenv
    # Try .env2 first (your custom file), then .env
    env_file = Path(__file__).parent.parent / ".env2"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Loaded environment from: {env_file}")
    else:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print(f"✅ Loaded environment from: {env_file}")
        else:
            print("ℹ️ No .env or .env2 file found, using system environment variables")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables only")
    print("   Install with: pip install python-dotenv")

import tiktoken
from docling.datamodel.base_models import ConfidenceReport, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.transforms.serializer.markdown import MarkdownDocSerializer
from docling_core.types.doc.document import DoclingDocument
from docling_core.types.io import DocumentStream

try:  # Optional improved extraction / rendering
    import fitz  # type: ignore[import]
except ImportError:  # pragma: no cover
    fitz = None

# Use standalone configuration - no backend dependencies
OPENAI_MODEL = "gpt-4o"  # Default model for testing

# Try to import backend settings if available, but don't fail if not
try:
    # Only try if we're in the right environment
    backend_src = Path(__file__).parent.parent / "src"
    if backend_src.exists():
        sys.path.append(str(backend_src))
        try:
            from em_backend.core.config import settings
            OPENAI_MODEL = settings.openai_model_name
            print(f"✅ SUCCESS: Using backend model: {OPENAI_MODEL}")
        except Exception:
            print(f"❌ FAILED: Backend config import failed, using fallback model: {OPENAI_MODEL}")
    else:
        print(f"❌ FAILED: Backend source not found, using fallback model: {OPENAI_MODEL}")
except Exception:
    print(f"❌ FAILED: Exception during config import, using fallback model: {OPENAI_MODEL}")

# Configure extensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent / "debug.log", mode='w')  # Overwrite each run
    ]
)

logger = logging.getLogger("standalone_parser")


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
    enabled = os.getenv("VISION_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
    model = os.getenv("VISION_MODEL", "gpt-4o")
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
def render_pages_to_images(pdf_path: Path, page_numbers: Sequence[int], dpi: int = 300) -> Dict[int, bytes]:
    if fitz is None:
        logger.error("PyMuPDF is required to render pages for vision fallback.")
        return {}

    images: Dict[int, bytes] = {}
    try:
        doc = fitz.open(str(pdf_path))  # type: ignore[operator]
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
            except Exception as exc:  # pragma: no cover
                logger.exception("Failed to render page %s for vision fallback: %s", page_number, exc)
    finally:
        doc.close()

    return images


def recover_pages_with_openai(
    pdf_path: Path,
    page_numbers: Sequence[int],
    vision_config: OpenAIVisionConfig,
) -> Dict[int, str]:
    if not vision_config.enabled:
        logger.info("Vision fallback disabled via configuration.")
        return {}

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; skipping vision fallback.")
        return {}

    try:
        from openai import OpenAI  # type: ignore[import]
    except ImportError:  # pragma: no cover
        logger.error("OpenAI python client not installed. Cannot use vision fallback.")
        return {}

    images = render_pages_to_images(pdf_path, page_numbers)
    if not images:
        logger.warning("No images rendered for vision fallback; skipping.")
        return {}

    client = OpenAI()
    recovered: Dict[int, str] = {}

    for page_number in page_numbers:
        image_bytes = images.get(page_number)
        if not image_bytes:
            continue

        prompt = vision_config.user_prompt_template.format(
            doc_name=pdf_path.name,
            page_number=page_number,
        )

        payload = base64.b64encode(image_bytes).decode("utf-8")
        attempt = 0
        while attempt <= vision_config.max_retries:
            try:
                messages = [
                    {
                        "role": "system",
                        "content": vision_config.system_prompt,
                    },
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
            except Exception as exc:  # pragma: no cover
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
            except Exception:  # pragma: no cover
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

# Also configure docling loggers to be more verbose
docling_logger = logging.getLogger("docling")
docling_logger.setLevel(logging.DEBUG)

# Create a separate handler for very detailed logs
detailed_handler = logging.FileHandler(Path(__file__).parent / "detailed_debug.log", mode='w')
detailed_handler.setLevel(logging.DEBUG)
detailed_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s')
detailed_handler.setFormatter(detailed_formatter)
logger.addHandler(detailed_handler)


class StandaloneDocumentParser:
    """
    Standalone Document Parser for testing and debugging.
    
    This class replicates the DocumentParser functionality but with enhanced
    debugging capabilities, especially for page number extraction.
    """

    MAX_CHUNK_TOKENS = 1000  # Maximum tokens per chunk
    MIN_CHUNK_TOKENS = 400   # Minimum tokens per chunk when re-splitting
    CHUNK_OVERLAP_TOKENS = 150  # Token overlap between chunks
    _PLACEHOLDER_MARKERS = {"<!-- missing-text -->"}
    _GID_TOKEN = "/gid"
    MAX_DEBUG_ITEMS = 5

    def __init__(self, debug_mode: bool = True) -> None:
        logger.info("🚀 INITIALIZING StandaloneDocumentParser...")
        logger.debug(f"Debug mode: {debug_mode}")
        
        self.debug_mode = debug_mode
        
        # Setup Document converter using docling models
        logger.info("📄 Setting up DocumentConverter...")
        
        # Try multiple model cache locations in order of preference
        potential_caches = [
            Path(__file__).parent.parent / ".cache" / "docling" / "models",  # Project cache
            Path.home() / ".cache" / "docling" / "models",  # Home cache (where models were downloaded)
        ]
        
        cache_path = None
        for path in potential_caches:
            if path.exists() and (path / "model.safetensors").exists():
                cache_path = path
                logger.info(f"✅ Found models at: {cache_path}")
                break
        
        if cache_path is None:
            # Use home cache anyway (models might be there even if we can't check)
            cache_path = Path.home() / ".cache" / "docling" / "models"
            logger.warning(f"⚠️ Model validation failed, using default: {cache_path}")
        
        logger.debug(f"📁 Model cache path: {cache_path}")
        logger.debug(f"   Cache exists: {cache_path.exists()}")
        
        # Check what models are available
        if cache_path.exists():
            model_files = list(cache_path.rglob("*.safetensors"))
            logger.info(f"✅ Found {len(model_files)} model files:")
            for model in model_files[:5]:  # Show first 5
                logger.debug(f"   - {model.relative_to(cache_path)}")
            if len(model_files) > 5:
                logger.debug(f"   ... and {len(model_files) - 5} more")
        
        self._model_cache_path = cache_path
        try:
            # Use standard pipeline without docling OCR; rely on external vision fallback instead
            logger.info("🔧 Initializing DocumentConverter with standard pipeline (OCR disabled)...")

            pipeline_options = PdfPipelineOptions(
                artifacts_path=cache_path,
                do_ocr=False,
                do_table_structure=True,
            )

            self.doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
            logger.info("✅ SUCCESS: DocumentConverter initialized with OCR disabled")
            logger.info(f"   Using models from: {cache_path}")
            logger.info("   Features: Layout detection ✅, Table structure ✅, OCR ❌ (handled by OpenAI vision fallback)")

        except FileNotFoundError as e:
            logger.warning("⚠️ OCR models missing (%s). Falling back to text-only pipeline.", e)
            logger.warning("   Run `docling-tools models download` to enable OCR.")
            pipeline_options = PdfPipelineOptions(
                artifacts_path=cache_path,
                do_ocr=False,
                do_table_structure=True,
            )
            self.doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
            logger.info("✅ SUCCESS: DocumentConverter initialized without OCR fallback")
        except Exception as e:
            logger.error(f"❌ FAILED: DocumentConverter initialization error: {e}")
            logger.error(f"   Exception type: {type(e)}")
            logger.error(f"   Model cache: {cache_path}")
            logger.error("   ")
            logger.error("   💡 To download models, run:")
            logger.error("      docling-tools models download")
            raise

        # Setup Document chunker
        logger.info("🧩 Setting up chunking components...")
        logger.debug(f"Using OpenAI model: {OPENAI_MODEL}")
        
        try:
            self._encoding = tiktoken.encoding_for_model(OPENAI_MODEL)
            logger.info(f"✅ SUCCESS: Tiktoken encoding initialized for model: {OPENAI_MODEL}")
        except Exception as e:
            logger.error(f"❌ FAILED: Tiktoken encoding initialization error: {e}")
            raise
        
        try:
            self.tokenizer = OpenAITokenizer(
                tokenizer=self._encoding,
                max_tokens=self.MAX_CHUNK_TOKENS,
            )
            logger.info(f"✅ SUCCESS: OpenAI tokenizer initialized with max_tokens: {self.MAX_CHUNK_TOKENS}")
        except Exception as e:
            logger.error(f"❌ FAILED: OpenAI tokenizer initialization error: {e}")
            raise
        
        try:
            self.chunker = HybridChunker(
                tokenizer=self.tokenizer,
                chunk_size=self.MAX_CHUNK_TOKENS,
                chunk_overlap=self.CHUNK_OVERLAP_TOKENS,
            )
            logger.info("✅ SUCCESS: HybridChunker initialized successfully")
        except Exception as e:
            logger.error(f"❌ FAILED: HybridChunker initialization error: {e}")
            raise
        
        logger.info(f"🎯 Parser configuration summary:")
        logger.info(f"   ✅ Model: {OPENAI_MODEL}")
        logger.info(f"   ✅ Min chunk tokens: {self.MIN_CHUNK_TOKENS}")
        logger.info(f"   ✅ Max chunk tokens: {self.MAX_CHUNK_TOKENS}")
        logger.info(f"   ✅ Chunk overlap tokens: {self.CHUNK_OVERLAP_TOKENS}")
        logger.info(f"   ✅ Debug mode: {debug_mode}")
        logger.info("🎉 SUCCESS: StandaloneDocumentParser initialization COMPLETE!")
        self._current_pdf_path: Path | None = None
        self._fitz_doc = None
        self._model_cache_path = cache_path
        self.vision_config = build_openai_vision_config()

    def parse_document_from_file(self, file_path: Path) -> tuple[DoclingDocument, ConfidenceReport]:
        """Parse a document from a file path."""
        logger.info(f"📁 Starting document parsing from file: {file_path}")
        logger.debug(f"File path type: {type(file_path)}")
        logger.debug(f"File path absolute: {file_path.absolute()}")
        
        # Validate file existence
        if not file_path.exists():
            logger.error(f"❌ File does not exist: {file_path}")
            raise ValueError(f"File does not exist: {file_path}")
        logger.debug("✅ File exists")
        
        if not file_path.is_file():
            logger.error(f"❌ Path is not a file: {file_path}")
            raise ValueError(f"Path is not a file: {file_path}")
        logger.debug("✅ Path is a valid file")
        
        # Get file info
        file_stat = file_path.stat()
        file_size = file_stat.st_size
        logger.info(f"📊 File info:")
        logger.info(f"   - Name: {file_path.name}")
        logger.info(f"   - Size: {file_size:,} bytes ({file_size / 1024:.1f} KB)")
        logger.info(f"   - Extension: {file_path.suffix}")
        logger.debug(f"   - Modified: {datetime.fromtimestamp(file_stat.st_mtime)}")
        
        # Read file content
        logger.info("📖 Reading file content...")
        try:
            file_content = file_path.read_bytes()
            logger.debug(f"✅ Successfully read {len(file_content):,} bytes")
        except Exception as e:
            logger.error(f"❌ Failed to read file: {e}")
            raise
        
        # Remember path for fallbacks
        self._current_pdf_path = file_path
        self._fitz_doc = self._load_fitz_document(file_path)

        # Create BytesIO stream
        logger.debug("🔄 Creating BytesIO stream...")
        file_stream = BytesIO(file_content)
        logger.debug(f"✅ BytesIO stream created, size: {len(file_stream.getvalue()):,} bytes")
        
        # Create DocumentStream
        logger.debug("📄 Creating DocumentStream...")
        doc_stream = DocumentStream(name=file_path.name, stream=file_stream)
        logger.debug(f"✅ DocumentStream created with name: {doc_stream.name}")
        
        # Parse document
        logger.info("🔧 Starting document conversion with docling...")
        try:
            result = self.doc_converter.convert(doc_stream)
            logger.info("✅ Document conversion completed successfully!")
        except FileNotFoundError as e:
            logger.warning("⚠️ OCR resources missing during conversion (%s). Retrying without OCR.", e)
            self._initialize_converter_without_ocr()
            result = self.doc_converter.convert(doc_stream)
            logger.info("✅ Document conversion completed after retry without OCR.")
        except Exception as e:
            logger.error(f"❌ Document conversion failed: {e}")
            logger.error(f"Exception type: {type(e)}")
            raise
        
        # Analyze results
        logger.info("📊 Analyzing conversion results...")
        logger.info(f"   - Confidence mean grade: {result.confidence.mean_grade}")
        logger.debug(f"   - Result type: {type(result)}")
        logger.debug(f"   - Document type: {type(result.document)}")
        logger.debug(f"   - Confidence type: {type(result.confidence)}")
        
        if hasattr(result.confidence, 'report') and result.confidence.report:
            logger.info(f"   - Number of pages in confidence report: {len(result.confidence.report)}")
            for i, page_conf in enumerate(result.confidence.report):
                logger.debug(f"     Page {i+1}: {page_conf}")
        else:
            logger.debug("   - No detailed confidence report available")
        
        # Analyze document structure
        logger.info("🔍 Analyzing document structure...")
        doc = result.document
        logger.debug(f"Document attributes: {[attr for attr in dir(doc) if not attr.startswith('_')]}")
        
        if hasattr(doc, '_children') and doc._children:
            logger.info(f"   - Document has {len(doc._children)} child elements")
            for i, child in enumerate(doc._children[:5]):  # Show first 5
                logger.debug(f"     Child {i}: {type(child)} - {getattr(child, 'text', 'no text')[:50]}...")
        
        if hasattr(doc, 'pages'):
            logger.info(f"   - Document has {len(doc.pages)} pages")
            # doc.pages might be a dict, not a list
            try:
                pages_items = list(doc.pages.items())[:3] if hasattr(doc.pages, 'items') else list(doc.pages)[:3]
                for i, page_item in enumerate(pages_items):
                    if isinstance(page_item, tuple):
                        page_num, page = page_item
                        logger.debug(f"     Page {page_num}: {type(page)}")
                    else:
                        logger.debug(f"     Page {i+1}: {type(page_item)}")
            except Exception as e:
                logger.debug(f"     Could not iterate pages: {e}")
        
        logger.info("🎉 Document parsing completed successfully!")
        return result.document, result.confidence

    def serialize_document(self, doc: DoclingDocument) -> str:
        """Serialize document to markdown."""
        logger.info("📝 Starting document serialization to markdown...")
        logger.debug(f"Document type: {type(doc)}")
        
        # Create serializer
        logger.debug("🔧 Creating MarkdownDocSerializer...")
        try:
            serializer = MarkdownDocSerializer(doc=doc)
            logger.debug("✅ MarkdownDocSerializer created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create serializer: {e}")
            raise
        
        # Serialize document
        logger.info("🔄 Serializing document...")
        try:
            ser_result = serializer.serialize()
            logger.info("✅ Document serialization completed successfully")
        except Exception as e:
            logger.error(f"❌ Serialization failed: {e}")
            logger.error(f"Exception type: {type(e)}")
            raise
        
        # Analyze serialization result
        text_length = len(ser_result.text)
        line_count = ser_result.text.count('\n')
        word_count = len(ser_result.text.split())
        
        logger.info(f"📊 Serialization results:")
        logger.info(f"   - Total characters: {text_length:,}")
        logger.info(f"   - Total lines: {line_count:,}")
        logger.info(f"   - Total words: {word_count:,}")
        logger.debug(f"   - First 200 chars: {ser_result.text[:200]}...")
        
        if text_length == 0:
            logger.warning("⚠️ Serialization resulted in empty text!")
        
        logger.info("🎉 Document serialization analysis complete!")
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

    def debug_chunk_provenance(self, chunk, chunk_index: int) -> dict[str, Any]:
        """Debug chunk provenance information in detail."""
        logger.info(f"🔍 CHUNK {chunk_index} PROVENANCE ANALYSIS")
        logger.debug(f"=" * 60)
        
        debug_info = {
            "chunk_index": chunk_index,
            "has_prov_attr": hasattr(chunk, "prov"),
            "prov_value": None,
            "prov_type": None,
            "prov_len": None,
            "page_extraction_attempts": [],
            "chunk_type": str(type(chunk)),
            "chunk_attributes": []
        }
        
        # Analyze chunk itself
        logger.debug(f"📦 Chunk analysis:")
        logger.debug(f"   - Type: {type(chunk)}")
        logger.debug(f"   - Memory address: {id(chunk)}")
        
        # Get all chunk attributes
        chunk_attrs = [attr for attr in dir(chunk) if not attr.startswith('_')]
        debug_info["chunk_attributes"] = chunk_attrs
        logger.debug(f"   - Non-private attributes: {chunk_attrs}")
        
        # Special attributes to check
        special_attrs = ["text", "label", "parent", "children", "metadata"]
        for attr in special_attrs:
            if hasattr(chunk, attr):
                try:
                    value = getattr(chunk, attr)
                    logger.debug(f"   - {attr}: {type(value)} = {str(value)[:100]}...")
                except Exception as e:
                    logger.debug(f"   - {attr}: Error accessing - {e}")
        
        # Check for provenance attribute
        logger.info(f"🔗 Provenance analysis:")
        if hasattr(chunk, "prov"):
            logger.info("   ✅ Chunk HAS 'prov' attribute")
            debug_info["prov_value"] = str(chunk.prov)
            debug_info["prov_type"] = str(type(chunk.prov))
            
            logger.debug(f"   - Provenance value: {chunk.prov}")
            logger.debug(f"   - Provenance type: {type(chunk.prov)}")
            logger.debug(f"   - Provenance repr: {repr(chunk.prov)}")
            
            if chunk.prov is not None:
                # Get length
                try:
                    prov_len = len(chunk.prov) if hasattr(chunk.prov, '__len__') else "No __len__ method"
                    debug_info["prov_len"] = prov_len
                    logger.info(f"   - Provenance length: {prov_len}")
                except Exception as e:
                    debug_info["prov_len"] = f"Error getting length: {e}"
                    logger.debug(f"   - Error getting provenance length: {e}")
                
                # Analyze provenance structure
                logger.debug(f"   - Provenance attributes: {[attr for attr in dir(chunk.prov) if not attr.startswith('_')]}")
                
                # Try to iterate through provenance items
                try:
                    if hasattr(chunk.prov, '__iter__') and hasattr(chunk.prov, '__len__') and len(chunk.prov) > 0:
                        logger.info(f"   📄 Analyzing {len(chunk.prov)} provenance items:")
                        
                        for i, prov_item in enumerate(chunk.prov):
                            logger.debug(f"     Provenance item {i}:")
                            logger.debug(f"       - Type: {type(prov_item)}")
                            logger.debug(f"       - Value: {prov_item}")
                            logger.debug(f"       - Repr: {repr(prov_item)}")
                            
                            if i == 0:  # Focus on first item for page extraction
                                first_prov = prov_item
                                logger.info(f"   🎯 Analyzing first provenance item for page extraction:")
                                logger.debug(f"       - Attributes: {[attr for attr in dir(first_prov) if not attr.startswith('_')]}")
                                
                                # Try different page attribute names
                                page_attrs = ["page_no", "page_number", "page", "page_num", "page_idx", "page_id"]
                                for attr in page_attrs:
                                    attempt = {"attribute": attr, "exists": False, "value": None, "type": None}
                                    if hasattr(first_prov, attr):
                                        attempt["exists"] = True
                                        try:
                                            attr_value = getattr(first_prov, attr)
                                            attempt["value"] = attr_value
                                            attempt["type"] = str(type(attr_value))
                                            logger.info(f"       ✅ Found {attr}: {attr_value} (type: {type(attr_value)})")
                                        except Exception as e:
                                            attempt["value"] = f"Error: {e}"
                                            logger.debug(f"       ❌ Error getting {attr}: {e}")
                                    else:
                                        logger.debug(f"       ❌ No {attr} attribute")
                                    debug_info["page_extraction_attempts"].append(attempt)
                                
                                # Dump ALL attributes and their values
                                logger.debug(f"   📋 ALL first provenance item attributes:")
                                for attr_name in dir(first_prov):
                                    if not attr_name.startswith('_'):
                                        try:
                                            attr_value = getattr(first_prov, attr_name)
                                            attr_type = type(attr_value)
                                            attr_str = str(attr_value)[:100] if len(str(attr_value)) > 100 else str(attr_value)
                                            logger.debug(f"       {attr_name}: {attr_type} = {attr_str}")
                                        except Exception as e:
                                            logger.debug(f"       {attr_name}: Error getting value - {e}")
                            
                            if i >= 2:  # Don't analyze too many items
                                logger.debug(f"     ... (showing only first 3 items)")
                                break
                    else:
                        logger.warning("   ⚠️ Provenance is not iterable or is empty")
                        
                except Exception as e:
                    logger.error(f"   ❌ Error analyzing provenance items: {e}")
                    
            else:
                logger.warning("   ⚠️ Provenance attribute exists but is None")
        else:
            logger.warning("   ❌ Chunk does NOT have 'prov' attribute")
            logger.debug(f"   Available attributes: {chunk_attrs}")
        
        logger.debug(f"=" * 60)
        logger.info(f"🎉 CHUNK {chunk_index} PROVENANCE ANALYSIS COMPLETE")
        
        return debug_info

    def extract_page_number(self, chunk, chunk_index: int) -> int | None:
        """Extract page number from chunk with enhanced debugging."""
        logger.info(f"📄 EXTRACTING PAGE NUMBER FOR CHUNK {chunk_index}")
        
        # Get detailed debug info (this will do the deep analysis)
        debug_info = self.debug_chunk_provenance(chunk, chunk_index)
        
        page_number = None
        extraction_method = None
        
        logger.info(f"🔍 Attempting page number extraction...")
        
        # Method 1: Try provenance-based extraction
        if hasattr(chunk, "prov") and chunk.prov and len(chunk.prov) > 0:
            logger.info("   📋 Method 1: Provenance-based extraction")
            first_prov = chunk.prov[0]
            
            # Try standard attribute names from debug info
            for attempt in debug_info["page_extraction_attempts"]:
                if attempt["exists"] and attempt["value"] is not None:
                    # Validate the value
                    try:
                        # Try to convert to int if it's not already
                        if isinstance(attempt["value"], (int, float)):
                            page_number = int(attempt["value"])
                            extraction_method = f"provenance.{attempt['attribute']}"
                            logger.info(f"   ✅ SUCCESS: Found page {page_number} via {attempt['attribute']}")
                            break
                        elif isinstance(attempt["value"], str) and attempt["value"].isdigit():
                            page_number = int(attempt["value"])
                            extraction_method = f"provenance.{attempt['attribute']}"
                            logger.info(f"   ✅ SUCCESS: Found page {page_number} via {attempt['attribute']} (string->int)")
                            break
                        else:
                            logger.debug(f"   ❌ {attempt['attribute']} has non-numeric value: {attempt['value']}")
                    except (ValueError, TypeError) as e:
                        logger.debug(f"   ❌ {attempt['attribute']} conversion failed: {e}")
            
            if page_number is None:
                logger.warning("   ❌ No valid page number found in provenance attributes")
        else:
            logger.warning("   ❌ No provenance data available for extraction")
        
        # Method 2: Try alternative chunk attributes (if provenance failed)
        if page_number is None:
            logger.info("   📋 Method 2: Direct chunk attribute extraction")
            direct_page_attrs = ["page", "page_number", "page_no", "page_num"]
            for attr in direct_page_attrs:
                if hasattr(chunk, attr):
                    try:
                        value = getattr(chunk, attr)
                        if isinstance(value, (int, float)):
                            page_number = int(value)
                            extraction_method = f"chunk.{attr}"
                            logger.info(f"   ✅ SUCCESS: Found page {page_number} via chunk.{attr}")
                            break
                        elif isinstance(value, str) and value.isdigit():
                            page_number = int(value)
                            extraction_method = f"chunk.{attr}"
                            logger.info(f"   ✅ SUCCESS: Found page {page_number} via chunk.{attr} (string->int)")
                            break
                    except Exception as e:
                        logger.debug(f"   ❌ chunk.{attr} extraction failed: {e}")
            
            if page_number is None:
                logger.warning("   ❌ No page number found in direct chunk attributes")
        
        # Method 3: Try parent/container analysis (if still no page)
        if page_number is None:
            logger.info("   📋 Method 3: Parent/container analysis")
            if hasattr(chunk, 'parent') and chunk.parent:
                logger.debug("   - Checking parent element...")
                # Recursively check parent for page info
                # This could be extended based on document structure
            
        # Final result
        if page_number is not None:
            logger.info(f"🎉 PAGE EXTRACTION SUCCESS: Chunk {chunk_index} -> Page {page_number} (via {extraction_method})")
        else:
            logger.error(f"💥 PAGE EXTRACTION FAILED: Chunk {chunk_index} -> Page UNKNOWN")
            logger.error("   📊 Summary of failed attempts:")
            logger.error(f"   - Provenance available: {debug_info.get('has_prov_attr', False)}")
            logger.error(f"   - Provenance length: {debug_info.get('prov_len', 'N/A')}")
            logger.error(f"   - Extraction attempts: {len(debug_info.get('page_extraction_attempts', []))}")
        
        return page_number

    def chunk_document(self, doc: DoclingDocument) -> Generator[dict[str, Any]]:
        """
        Chunk document using markdown export with section parsing.

        Falls back to HybridChunker if markdown export fails or contains placeholders.
        Uses vision fallback for problematic pages.
        """
        logger.info("🧩 STARTING DOCUMENT CHUNKING...")
        logger.info("=" * 80)

        # Try markdown export + section parsing first (to get section headers)
        try:
            full_markdown = doc.export_to_markdown()
            logger.info(f"📄 Markdown export length: {len(full_markdown) if full_markdown else 0} chars")

            if full_markdown and not self._contains_gid(full_markdown):
                logger.info("✅ Using markdown export with section parsing...")
                markdown_chunks = self._chunk_document_markdown_aware(doc)
                logger.info(f"📊 Markdown-aware chunking produced {len(markdown_chunks)} chunks")

                if markdown_chunks:
                    collected_chunks: list[dict[str, Any]] = []
                    chunk_index = 0

                    for chunk_text, page_number in markdown_chunks:
                        if not chunk_text.strip():
                            continue

                        token_count = len(self._encoding.encode(chunk_text))

                        if token_count < self.MIN_INDEXABLE_TOKENS:
                            continue

                        chunk_data = {
                            "chunk_id": str(uuid4()),
                            "text": chunk_text,
                            "page_number": page_number,
                            "chunk_index": chunk_index,
                            "segment_index": 0,
                            "token_count": token_count,
                            "char_count": len(chunk_text),
                            "word_count": len(chunk_text.split()),
                            "extraction_method": "markdown_aware",
                        }

                        preview = repr(chunk_text[:100] if len(chunk_text) > 100 else chunk_text)
                        logger.info(f"✅ Chunk {chunk_index} (page {page_number}) tokens={token_count} preview={preview}")

                        collected_chunks.append(chunk_data)
                        yield chunk_data
                        chunk_index += 1

                    logger.info("=" * 80)
                    logger.info(f"🎉 MARKDOWN-AWARE CHUNKING COMPLETE! Total chunks: {len(collected_chunks)}")
                    return
                else:
                    logger.warning("⚠️ Markdown-aware chunking produced no chunks, falling back to HybridChunker")
            else:
                has_gid = self._contains_gid(full_markdown) if full_markdown else False
                logger.warning(f"⚠️ Markdown export check failed (empty={not full_markdown}, has_gid={has_gid}), falling back to HybridChunker")
        except Exception as e:
            logger.warning(f"❌ Markdown export failed: {e}, falling back to HybridChunker")

        # Fallback: Use HybridChunker
        logger.info("🔄 Using HybridChunker fallback...")
        serializer = MarkdownDocSerializer(doc=doc)
        placeholder_summary = {
            "chunks": 0,
            "segments": 0,
            "removed_segments": 0,
            "fallback_used": 0,
            "fallback_failed": 0,
        }

        collected_chunks: list[dict[str, Any]] = []
        chunk_index = 0

        # Use HybridChunker to get chunks with correct page numbers
        for raw_chunk in self.chunker.chunk(doc):
                placeholder_summary["chunks"] += 1
                logger.debug(f"Processing chunk {chunk_index}")

                (
                    combined_text,
                    page_number,
                    stats,
                    diagnostic,
                ) = self._extract_markdown_segment(
                    raw_chunk,
                    serializer,
                    self.chunker,
                    doc,
                    debug_chunk_index=chunk_index,
                )

                placeholder_summary["segments"] += stats["total_segments"]
                placeholder_summary["removed_segments"] += stats["removed_segments"]
                placeholder_summary["fallback_used"] += 1 if stats["fallback_used"] else 0
                placeholder_summary["fallback_failed"] += 1 if stats["fallback_failed"] else 0

                if not combined_text.strip():
                    logger.warning(
                        "   ⚠️ Chunk %s produced no usable text after placeholder filtering; skipping.",
                        chunk_index,
                    )
                    chunk_index += 1
                    continue

                segment_index = 0
                for text_segment in self._split_to_token_budget(combined_text):
                    token_count = len(self._encoding.encode(text_segment))
                    preview = repr(text_segment[:100] if len(text_segment) > 100 else text_segment)

                    chunk_data = {
                        "chunk_id": str(uuid4()),
                        "text": text_segment,
                        "page_number": page_number,
                        "chunk_index": chunk_index,
                        "segment_index": segment_index,
                        "token_count": token_count,
                        "char_count": len(text_segment),
                        "word_count": len(text_segment.split()),
                        "diagnostic": diagnostic if self.debug_mode else None,
                        "extraction_method": "docling",
                    }

                    if page_number is not None:
                        logger.info("✅ Chunk %s.%s (page %s) tokens=%s preview=%s",
                                    chunk_index, segment_index, page_number, token_count, preview)
                    else:
                        logger.warning("⚠️ Chunk %s.%s has unknown page, tokens=%s preview=%s",
                                       chunk_index, segment_index, token_count, preview)

                    if chunk_index < 5:
                        self._log_chunk_preview(chunk_data, chunk_index, segment_index)

                    collected_chunks.append(chunk_data)
                    segment_index += 1
                    chunk_index += 1

        logger.info("=" * 80)
        logger.info("🎉 DOCUMENT CHUNKING COMPLETE!")
        logger.info(
            "📊 Placeholder summary: chunks=%s segments=%s removed=%s fallback_used=%s fallback_failed=%s",
            placeholder_summary["chunks"],
            placeholder_summary["segments"],
            placeholder_summary["removed_segments"],
            placeholder_summary["fallback_used"],
            placeholder_summary["fallback_failed"],
        )
        fallback_needed = (
            placeholder_summary["fallback_used"] > 0
            and placeholder_summary["fallback_failed"] == placeholder_summary["fallback_used"]
        )

        if (fallback_needed or not collected_chunks) and self._current_pdf_path is not None:
            logger.warning(
                "Docling chunking left unresolved placeholders; attempting OpenAI vision fallback."
            )
            placeholder_pages = self._placeholder_pages_from_chunks(collected_chunks)
            fallback_chunks = self._chunk_with_openai_vision(placeholder_pages)
            if fallback_chunks:
                for chunk in fallback_chunks:
                    yield chunk
                return
            logger.warning("OpenAI vision fallback produced no usable chunks; using original output.")

        for chunk in collected_chunks:
            yield chunk

    def _extract_markdown_segment(
        self,
        chunk: Any,
        serializer: MarkdownDocSerializer,
        chunker: HybridChunker,
        doc: Optional[DoclingDocument],
        debug_chunk_index: int,
    ) -> tuple[str, Optional[int], dict[str, int | bool], dict[str, Any]]:
        text_parts: list[str] = []
        page_candidates: list[int] = []
        placeholder_removed = 0
        inspected = 0

        diagnostic: dict[str, Any] = {
            "chunk_index": debug_chunk_index,
            "doc_items": [],
            "fallback_candidates": [],
        }

        doc_items = getattr(getattr(chunk, "meta", None), "doc_items", None) or []

        for idx, item in enumerate(doc_items):
            inspected += 1
            resolved_item = self._resolve_doc_item(doc, item)
            resolved_text = self._serialize_doc_item(serializer, resolved_item)
            raw_text = self._serialize_doc_item(serializer, item)
            diagnostic_entry = {
                "item_index": idx,
                "resolved_len": len(resolved_text),
                "raw_len": len(raw_text),
                "resolved_preview": resolved_text[:120],
                "raw_preview": raw_text[:120],
                "resolved_placeholder": self._is_placeholder_text(resolved_text),
                "raw_placeholder": self._is_placeholder_text(raw_text),
            }

            if self._is_placeholder_text(resolved_text):
                placeholder_removed += 1
            else:
                text_parts.append(resolved_text.strip())

            page = self._first_page_number(resolved_item) or self._first_page_number(item)
            if page is not None:
                page_candidates.append(page)

            if idx < self.MAX_DEBUG_ITEMS:
                diagnostic["doc_items"].append(diagnostic_entry)

        if not text_parts:
            try:
                contextualized = chunker.contextualize(chunk)
            except Exception as exc:
                logger.warning("Failed to contextualize chunk %s: %s", debug_chunk_index, exc)
                contextualized = ""

            diagnostic["contextualized_preview"] = contextualized[:200]
            if contextualized and not self._is_placeholder_text(contextualized):
                text_parts.append(contextualized.strip())
                page = (
                    self._first_page_number(chunk.meta.doc_items[0])
                    if getattr(chunk, "meta", None) and getattr(chunk.meta, "doc_items", None)
                    else None
                )
                if page is not None:
                    page_candidates.append(page)
            else:
                if contextualized:
                    placeholder_removed += 1

        combined_text = "\n\n".join(part for part in text_parts if part)
        fallback_used = False
        fallback_failed = False

        if self._contains_gid(combined_text) or not combined_text:
            fallback_used = True
            fallback_text, candidates = self._attempt_fallback(chunk, chunker, page_candidates)
            diagnostic["fallback_candidates"] = candidates
            if fallback_text and not self._contains_gid(fallback_text):
                combined_text = fallback_text
            else:
                fallback_failed = True

        page_number = page_candidates[0] if page_candidates else None
        stats = {
            "total_segments": inspected,
            "removed_segments": placeholder_removed,
            "fallback_used": fallback_used,
            "fallback_failed": fallback_failed,
        }
        diagnostic["page_number"] = page_number
        diagnostic["combined_text_preview"] = combined_text[:200]

        return combined_text, page_number, stats, diagnostic

    def _attempt_fallback(
        self,
        chunk: Any,
        chunker: HybridChunker,
        page_candidates: list[int],
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Try Docling's fallback methods only - do NOT use PyMuPDF.
        PyMuPDF extracts garbage from scanned PDFs - only OpenAI Vision should handle those.
        """
        candidates_info: list[dict[str, Any]] = []
        candidate_texts: list[str] = []

        # Only try Docling's contextualize method
        try:
            contextualized = chunker.contextualize(chunk)
            if isinstance(contextualized, str) and contextualized.strip():
                candidate_texts.append(contextualized.strip())
                candidates_info.append(
                    {"source": "chunker.contextualize", "len": len(contextualized.strip()), "preview": contextualized[:120]}
                )
        except Exception as exc:
            logger.debug("Fallback contextualize() failed: %s", exc)
            candidates_info.append({"source": "chunker.contextualize", "error": str(exc)})

        # Check if we got valid text (not garbage/placeholders)
        for candidate in candidate_texts:
            if candidate and not self._contains_gid(candidate) and not self._is_placeholder_text(candidate):
                return candidate, candidates_info

        # No valid text found - will trigger OpenAI Vision fallback later
        return "", candidates_info

    @staticmethod
    def _is_placeholder_text(value: str) -> bool:
        if not value:
            return True
        normalized = value.strip()
        if not normalized:
            return True
        lowered = normalized.lower()
        if lowered in StandaloneDocumentParser._PLACEHOLDER_MARKERS:
            return True
        if StandaloneDocumentParser._contains_gid(lowered):
            return True
        stripped = lowered.lstrip(" -*•\u2022\t")
        if StandaloneDocumentParser._contains_gid(stripped):
            return True
        return False

    @staticmethod
    def _contains_gid(value: str) -> bool:
        return StandaloneDocumentParser._GID_TOKEN in value.lower()

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
            if StandaloneDocumentParser._is_placeholder_text(text):
                pages.add(int(page_number))
        return pages

    def _chunk_with_openai_vision(
        self,
        placeholder_pages: Optional[set[int]] = None,
    ) -> list[dict[str, Any]]:
        pdf_path = self._current_pdf_path
        if pdf_path is None:
            logger.error("Cannot run vision fallback without original PDF path.")
            return []

        if not self.vision_config.enabled:
            logger.info("Vision fallback disabled via configuration.")
            return []

        all_pages = self._list_pdf_pages(pdf_path)
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

        recovered = recover_pages_with_openai(pdf_path, fallback_candidates, self.vision_config)

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
            method = f"vision:{self.vision_config.model}"
            if not recovered_text:
                report_pages.append(
                    PageExtraction(
                        page_number=page_number,
                        text="",
                        method=method,
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
                method=method,
                needs_vision=False,
            )
            report_pages.append(page_entry)
            usable_pages.append(page_entry)

        chunks: list[dict[str, Any]] = []
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
                    token_count = len(self._encoding.encode(chunk_text))
                    chunk_data = {
                        "chunk_id": str(uuid4()),
                        "text": chunk_text,
                        "page_number": chunk_page or page.page_number,
                        "chunk_index": chunk_index,
                        "segment_index": 0,
                        "token_count": token_count,
                        "char_count": len(chunk_text),
                        "word_count": len(chunk_text.split()),
                        "extraction_method": page.method,
                    }
                    if chunk_index <= 5:
                        logger.debug("Fallback chunk %s preview: %s", chunk_index, repr(chunk_text[:100]))
                    chunks.append(chunk_data)
                    chunk_index += 1

        if not chunks:
            logger.error("OpenAI vision fallback yielded no chunks.")
            return []

        self._write_fallback_report(pdf_path, report_pages, chunks)
        logger.info("OpenAI vision fallback produced %s chunks.", len(chunks))
        return chunks

    def _list_pdf_pages(self, pdf_path: Path) -> list[int]:
        if fitz is None:
            logger.error("PyMuPDF is required to enumerate PDF pages for vision fallback.")
            return []

        try:
            document = fitz.open(str(pdf_path))  # type: ignore[operator]
        except Exception as exc:
            logger.exception("Unable to open PDF with PyMuPDF: %s", exc)
            return []

        try:
            return list(range(1, document.page_count + 1))
        finally:
            document.close()

    def _write_fallback_report(
        self,
        pdf_path: Path,
        pages: list[PageExtraction],
        chunks: list[dict[str, Any]],
    ) -> None:
        reports_dir = Path(__file__).parent / "results"
        reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"fallback_chunks_{timestamp}.md"

        lines: list[str] = []
        lines.append(f"# OpenAI Vision Fallback Report for {pdf_path.name}")
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
        except Exception as exc:
            logger.warning("Failed to write fallback report: %s", exc)

    @staticmethod
    def _serialize_doc_item(
        serializer: MarkdownDocSerializer, item: Optional[Any]
    ) -> str:
        if item is None:
            return ""
        try:
            result = serializer.serialize(item=item)
            return (result.text or "").strip()
        except Exception as exc:
            logger.debug("Doc item serialization failed: %s", exc)
            return (
                getattr(item, "text", "")
                or getattr(item, "orig", "")
                or getattr(item, "markdown", "")
            )

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
            except Exception as exc:
                logger.debug("Doc item resolve() failed: %s", exc)

        reference = getattr(item, "self_ref", None) or getattr(item, "cref", None)
        if isinstance(reference, str):
            resolved_ref = StandaloneDocumentParser._resolve_doc_reference(doc, reference)
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

    def _initialize_converter_without_ocr(self) -> None:
        cache_path = self._model_cache_path
        logger.info("🔄 Reinitializing DocumentConverter without OCR...")
        pipeline_options = PdfPipelineOptions(
            artifacts_path=cache_path,
            do_ocr=False,
            do_table_structure=True,
        )
        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )
        logger.info("✅ DocumentConverter ready (OCR disabled)")

    def _load_fitz_document(self, file_path: Path):
        try:
            import fitz  # type: ignore
        except ImportError:
            logger.info("PyMuPDF not available; skipping PDF text fallback.")
            return None

        try:
            return fitz.open(file_path)
        except Exception as exc:
            logger.warning("Failed to open PDF with PyMuPDF: %s", exc)
            return None

    def _extract_text_with_fitz(self, page_number: Optional[int]) -> str:
        if self._fitz_doc is None or page_number is None:
            return ""
        try:
            page_index = max(0, page_number - 1)
            if page_index >= self._fitz_doc.page_count:
                return ""
            page = self._fitz_doc.load_page(page_index)
            text = page.get_text("text")
            logger.debug(
                "PyMuPDF fallback extracted %s chars from page %s",
                len(text),
                page_number,
            )
            return text.strip()
        except Exception as exc:
            logger.debug("PyMuPDF extraction failed for page %s: %s", page_number, exc)
            return ""

    
    def _resolve_item_reference(self, doc: DoclingDocument, ref: str) -> Any:
        """
        Resolve a JSON reference like '#/texts/0' to the actual document item.
        """
        try:
            # Reference format is "#/collection_name/index"
            if ref.startswith('#/'):
                parts = ref.lstrip('#/').split('/')
                if len(parts) == 2:
                    collection_name, index_str = parts
                    index = int(index_str)
                    
                    logger.debug(f"      Resolving: {collection_name}[{index}]")
                    
                    # Get the collection from the document
                    if hasattr(doc, collection_name):
                        collection = getattr(doc, collection_name)
                        if collection and isinstance(collection, list) and index < len(collection):
                            logger.debug(f"      ✅ Found item in {collection_name}[{index}]")
                            return collection[index]
                        else:
                            logger.debug(f"      ❌ Index {index} out of range for {collection_name}")
                    else:
                        logger.debug(f"      ❌ Collection {collection_name} not found in document")
        except Exception as e:
            logger.debug(f"      ❌ Error resolving reference {ref}: {e}")
        
        return None

    def _log_chunk_preview(self, chunk_data: dict[str, Any], chunk_index: int, segment_index: int) -> None:
        """Log detailed preview of a chunk."""
        logger.info("📋 CHUNK PREVIEW")
        logger.info("-" * 60)
        logger.info(f"🔢 Chunk ID: {chunk_data['chunk_id']}")
        logger.info(f"📍 Position: Chunk {chunk_index}, Segment {segment_index}")
        logger.info(f"📄 Page Number: {chunk_data['page_number'] if chunk_data['page_number'] else '❌ UNKNOWN'}")
        logger.info(f"🔤 Token Count: {chunk_data['token_count']}")
        logger.info(f"📝 Character Count: {chunk_data['char_count']}")
        logger.info(f"📖 Word Count: {chunk_data['word_count']}")
        
        # Text preview
        text = chunk_data['text']
        preview_length = 200
        if len(text) > preview_length:
            preview = text[:preview_length] + "..."
            logger.info(f"📖 Text Preview ({preview_length} chars): {repr(preview)}")
            logger.info(f"📏 Full Text Length: {len(text)} characters")
        else:
            logger.info(f"📖 Full Text: {repr(text)}")
        
        # Show first and last few words
        words = text.split()
        if len(words) > 10:
            first_words = " ".join(words[:5])
            last_words = " ".join(words[-5:])
            logger.info(f"🔤 First 5 words: {repr(first_words)}")
            logger.info(f"🔤 Last 5 words: {repr(last_words)}")
        
        # Debug info summary
        if chunk_data.get('debug_info'):
            debug = chunk_data['debug_info']
            logger.info(f"🔍 Debug Info:")
            logger.info(f"   - Has provenance: {debug.get('has_prov_attr', False)}")
            logger.info(f"   - Provenance length: {debug.get('prov_len', 'N/A')}")
            logger.info(f"   - Page extraction attempts: {len(debug.get('page_extraction_attempts', []))}")
            
            # Show successful page extraction method if any
            for attempt in debug.get('page_extraction_attempts', []):
                if attempt.get('exists') and attempt.get('value') is not None:
                    logger.info(f"   ✅ Page found via: {attempt['attribute']} = {attempt['value']}")
                    break
            else:
                logger.info(f"   ❌ No page extraction succeeded")
        
        logger.info("-" * 60)

    def _log_chunking_summary(self, all_chunks: list[dict[str, Any]]) -> None:
        """Log summary statistics about all chunks."""
        total_chunks = len(all_chunks)
        chunks_with_pages = [c for c in all_chunks if c['page_number'] is not None]
        chunks_without_pages = [c for c in all_chunks if c['page_number'] is None]
        
        logger.info("📊 CHUNKING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📊 Total chunks generated: {total_chunks}")
        logger.info(f"✅ Chunks with page numbers: {len(chunks_with_pages)} ({len(chunks_with_pages)/total_chunks*100:.1f}%)")
        logger.info(f"❌ Chunks without page numbers: {len(chunks_without_pages)} ({len(chunks_without_pages)/total_chunks*100:.1f}%)")
        
        if chunks_with_pages:
            page_numbers = [c['page_number'] for c in chunks_with_pages]
            logger.info(f"📄 Page range: {min(page_numbers)} - {max(page_numbers)}")
            logger.info(f"📄 Unique pages: {len(set(page_numbers))}")
        
        # Token statistics
        token_counts = [c['token_count'] for c in all_chunks]
        chunks_below_min = [c for c in all_chunks if c['token_count'] < self.MIN_CHUNK_TOKENS]
        chunks_above_max = [c for c in all_chunks if c['token_count'] > self.MAX_CHUNK_TOKENS]
        chunks_in_range = [c for c in all_chunks if self.MIN_CHUNK_TOKENS <= c['token_count'] <= self.MAX_CHUNK_TOKENS]
        
        logger.info(f"🔢 Token statistics:")
        logger.info(f"   - Total tokens: {sum(token_counts):,}")
        logger.info(f"   - Average tokens per chunk: {sum(token_counts)/len(token_counts):.1f}")
        logger.info(f"   - Min tokens: {min(token_counts)}")
        logger.info(f"   - Max tokens: {max(token_counts)}")
        logger.info(f"   - Target range: {self.MIN_CHUNK_TOKENS} - {self.MAX_CHUNK_TOKENS} tokens")
        logger.info(f"   ✅ Chunks in target range: {len(chunks_in_range)} ({len(chunks_in_range)/total_chunks*100:.1f}%)")
        
        if chunks_below_min:
            logger.warning(f"   ⚠️ Chunks below minimum ({self.MIN_CHUNK_TOKENS}): {len(chunks_below_min)} ({len(chunks_below_min)/total_chunks*100:.1f}%)")
            for i, chunk in enumerate(chunks_below_min[:3]):
                logger.warning(f"     {i+1}. Chunk {chunk['chunk_index']}: {chunk['token_count']} tokens")
        
        if chunks_above_max:
            logger.warning(f"   ⚠️ Chunks above maximum ({self.MAX_CHUNK_TOKENS}): {len(chunks_above_max)} ({len(chunks_above_max)/total_chunks*100:.1f}%)")
            for i, chunk in enumerate(chunks_above_max[:3]):
                logger.warning(f"     {i+1}. Chunk {chunk['chunk_index']}: {chunk['token_count']} tokens")
        
        # Character statistics
        char_counts = [c['char_count'] for c in all_chunks]
        logger.info(f"📝 Character statistics:")
        logger.info(f"   - Total characters: {sum(char_counts):,}")
        logger.info(f"   - Average characters per chunk: {sum(char_counts)/len(char_counts):.1f}")
        
        # Show sample of chunks without pages for debugging
        if chunks_without_pages and len(chunks_without_pages) <= 10:
            logger.warning("❌ CHUNKS WITHOUT PAGE NUMBERS:")
            for i, chunk in enumerate(chunks_without_pages[:5]):
                logger.warning(f"   {i+1}. Chunk {chunk['chunk_index']}: {chunk['token_count']} tokens, text: {chunk['text'][:50]}...")
        elif len(chunks_without_pages) > 10:
            logger.warning(f"❌ {len(chunks_without_pages)} chunks without page numbers (showing first 3):")
            for i, chunk in enumerate(chunks_without_pages[:3]):
                logger.warning(f"   {i+1}. Chunk {chunk['chunk_index']}: {chunk['token_count']} tokens")
        
        logger.info("=" * 60)

    def _split_to_token_budget(self, text: str) -> Iterable[str]:
        """
        Split text to fit within token budget while ensuring minimum chunk size.
        
        Ensures chunks have at least MIN_CHUNK_TOKENS (1500) tokens and 
        at most MAX_CHUNK_TOKENS (2000) tokens.
        """
        tokens = self._encoding.encode(text)
        total_tokens = len(tokens)
        
        logger.debug(f"Splitting text with {total_tokens} tokens (min: {self.MIN_CHUNK_TOKENS}, max: {self.MAX_CHUNK_TOKENS})")
        
        # If text is smaller than minimum, return as single chunk
        if total_tokens <= self.MIN_CHUNK_TOKENS:
            logger.debug(f"Text has {total_tokens} tokens, below minimum {self.MIN_CHUNK_TOKENS}, returning as single chunk")
            return [text]
        
        # If text fits within maximum, return as single chunk
        if total_tokens <= self.MAX_CHUNK_TOKENS:
            logger.debug(f"Text has {total_tokens} tokens, within max {self.MAX_CHUNK_TOKENS}, returning as single chunk")
            return [text]

        segments: list[str] = []
        start = 0
        
        while start < total_tokens:
            # Try to create a chunk with maximum tokens
            end = min(start + self.MAX_CHUNK_TOKENS, total_tokens)
            segment_tokens = tokens[start:end]
            current_segment_size = len(segment_tokens)
            
            # Check if this would be the last chunk and if it's too small
            remaining_tokens = total_tokens - end
            next_chunk_would_be_too_small = (remaining_tokens > 0 and 
                                           remaining_tokens < self.MIN_CHUNK_TOKENS)
            
            if next_chunk_would_be_too_small:
                # Adjust current chunk size to ensure next chunk meets minimum
                # Calculate how many tokens we need to leave for the next chunk
                tokens_for_next = self.MIN_CHUNK_TOKENS
                available_for_current = total_tokens - start - tokens_for_next
                
                if available_for_current >= self.MIN_CHUNK_TOKENS:
                    # We can make current chunk smaller and still meet minimum
                    end = start + available_for_current
                    segment_tokens = tokens[start:end]
                    current_segment_size = len(segment_tokens)
                    logger.debug(f"Adjusted chunk size to {current_segment_size} tokens to ensure next chunk meets minimum")
                else:
                    # Current chunk would be too small if we adjust, so extend it to include remaining tokens
                    end = total_tokens
                    segment_tokens = tokens[start:end]
                    current_segment_size = len(segment_tokens)
                    logger.debug(f"Extended final chunk to {current_segment_size} tokens to avoid small remainder")
            
            segments.append(self._encoding.decode(segment_tokens))
            logger.debug(f"Created chunk with {current_segment_size} tokens (position {start}-{end})")
            
            if end == total_tokens:
                break
                
            # Calculate next start position with overlap, but ensure we don't create too small chunks
            next_start = max(end - self.CHUNK_OVERLAP_TOKENS, start + 1)
            remaining_after_next = total_tokens - next_start
            
            # If the remaining text after next start would be too small, adjust
            if remaining_after_next < self.MIN_CHUNK_TOKENS and remaining_after_next > 0:
                # Move start back to create a larger final chunk
                next_start = total_tokens - self.MIN_CHUNK_TOKENS
                logger.debug(f"Adjusted next start to {next_start} to ensure final chunk meets minimum size")
            
            start = next_start
        
        logger.info(f"Split {total_tokens} tokens into {len(segments)} segments")
        for i, segment in enumerate(segments):
            segment_token_count = len(self._encoding.encode(segment))
            logger.info(f"  Segment {i}: {segment_token_count} tokens (min: {self.MIN_CHUNK_TOKENS}, max: {self.MAX_CHUNK_TOKENS})")
            
            # Validate segment meets requirements
            if segment_token_count < self.MIN_CHUNK_TOKENS:
                logger.warning(f"  ⚠️ Segment {i} has only {segment_token_count} tokens, below minimum {self.MIN_CHUNK_TOKENS}")
            if segment_token_count > self.MAX_CHUNK_TOKENS:
                logger.warning(f"  ⚠️ Segment {i} has {segment_token_count} tokens, above maximum {self.MAX_CHUNK_TOKENS}")
        
        return segments


class LocalStorage:
    """Local storage for test results."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(exist_ok=True)
    
    def save_parsing_result(self, file_path: Path, document: DoclingDocument, 
                          confidence: ConfidenceReport, content: str, 
                          chunks: list[dict[str, Any]]) -> str:
        """Save parsing results to local storage."""
        logger.info("💾 STARTING RESULT SAVE PROCESS...")
        
        timestamp = datetime.now().isoformat()
        # Use PDF name for easier identification
        pdf_name = file_path.stem
        result_id = pdf_name
        
        # Analyze chunks for summary
        chunks_with_pages = [c for c in chunks if c.get('page_number') is not None]
        chunks_without_pages = [c for c in chunks if c.get('page_number') is None]
        
        result = {
            "result_id": result_id,
            "timestamp": timestamp,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "confidence": {
                "mean_grade": str(confidence.mean_grade),
                "num_pages": len(confidence.report) if hasattr(confidence, 'report') and confidence.report else 0
            },
            "content_length": len(content),
            "chunk_count": len(chunks),
            "chunks_with_pages": len(chunks_with_pages),
            "chunks_without_pages": len(chunks_without_pages),
            "page_extraction_success_rate": len(chunks_with_pages) / len(chunks) * 100 if chunks else 0,
            "chunks": chunks
        }
        
        logger.info(f"📊 Result summary:")
        logger.info(f"   - Result ID: {result_id}")
        logger.info(f"   - Total chunks: {len(chunks)}")
        logger.info(f"   ✅ Chunks with pages: {len(chunks_with_pages)} ({len(chunks_with_pages)/len(chunks)*100:.1f}%)")
        logger.info(f"   ❌ Chunks without pages: {len(chunks_without_pages)} ({len(chunks_without_pages)/len(chunks)*100:.1f}%)")
        
        # Save main result
        result_file = self.base_path / f"result_{result_id}.json"
        try:
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"✅ SUCCESS: Results saved to {result_file}")
        except Exception as e:
            logger.error(f"❌ FAILED: Could not save results: {e}")
            raise
        
        # Save content separately
        content_file = self.base_path / f"content_{result_id}.md"
        try:
            with open(content_file, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"✅ SUCCESS: Content saved to {content_file}")
        except Exception as e:
            logger.error(f"❌ FAILED: Could not save content: {e}")
            raise

        # Save detailed chunks report
        chunks_report_file = self.base_path / f"chunks_detailed_{result_id}.md"
        try:
            with open(chunks_report_file, "w", encoding="utf-8") as f:
                f.write(f"# Detailed Chunks Report for {file_path.name}\n\n")
                f.write(f"Generated: {timestamp}\n")
                f.write(f"Total chunks: {len(chunks)}\n")
                f.write(f"Chunks with pages: {len(chunks_with_pages)}\n")
                f.write(f"Chunks without pages: {len(chunks_without_pages)}\n\n")
                f.write("---\n\n")

                for chunk in chunks:
                    chunk_idx = chunk.get('chunk_index', 'unknown')
                    page_num = chunk.get('page_number', 'UNKNOWN')
                    token_count = chunk.get('token_count', 0)
                    extraction_method = chunk.get('extraction_method', 'unknown')

                    f.write(f"## Chunk {chunk_idx}\n\n")
                    f.write(f"- **Page**: {page_num}\n")
                    f.write(f"- **Tokens**: {token_count}\n")
                    f.write(f"- **Extraction Method**: {extraction_method}\n")
                    f.write(f"- **Characters**: {chunk.get('char_count', len(chunk.get('text', '')))}\n")
                    f.write(f"- **Words**: {chunk.get('word_count', len(chunk.get('text', '').split()))}\n\n")
                    f.write("### Text\n\n")
                    f.write("```markdown\n")
                    f.write(chunk.get('text', ''))
                    f.write("\n```\n\n")
                    f.write("---\n\n")

            logger.info(f"✅ SUCCESS: Detailed chunks report saved to {chunks_report_file}")
        except Exception as e:
            logger.error(f"❌ FAILED: Could not save chunks report: {e}")
            # Don't raise here, it's a nice-to-have
        
        # Save a human-readable summary
        summary_file = self.base_path / f"summary_{result_id}.txt"
        try:
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(f"PARSING RESULTS SUMMARY\n")
                f.write(f"{'='*50}\n\n")
                f.write(f"File: {file_path.name}\n")
                f.write(f"Processed: {timestamp}\n")
                f.write(f"Confidence: {confidence.mean_grade}\n")
                f.write(f"Content Length: {len(content):,} characters\n")
                f.write(f"Total Chunks: {len(chunks)}\n")
                f.write(f"✅ Chunks with pages: {len(chunks_with_pages)} ({len(chunks_with_pages)/len(chunks)*100:.1f}%)\n")
                f.write(f"❌ Chunks without pages: {len(chunks_without_pages)} ({len(chunks_without_pages)/len(chunks)*100:.1f}%)\n\n")
                
                if chunks_with_pages:
                    page_numbers = sorted(set(c['page_number'] for c in chunks_with_pages))
                    f.write(f"Page range: {min(page_numbers)} - {max(page_numbers)}\n")
                    f.write(f"Unique pages: {len(page_numbers)}\n\n")
                
                f.write("FIRST 3 CHUNKS PREVIEW:\n")
                f.write("-" * 30 + "\n")
                for i, chunk in enumerate(chunks[:3]):
                    f.write(f"Chunk {i}:\n")
                    f.write(f"  Page: {chunk.get('page_number', 'UNKNOWN')}\n")
                    f.write(f"  Tokens: {chunk.get('token_count', 0)}\n")
                    f.write(f"  Text: {chunk.get('text', '')[:100]}...\n\n")
            
            logger.info(f"✅ SUCCESS: Summary saved to {summary_file}")
        except Exception as e:
            logger.error(f"❌ FAILED: Could not save summary: {e}")
            # Don't raise here, summary is nice-to-have
        
        logger.info("🎉 SUCCESS: All result files saved successfully!")
        return result_id


def main():
    """Main function for standalone testing."""
    parser = argparse.ArgumentParser(
        description="Standalone PDF Parser for Testing and Debugging"
    )
    parser.add_argument(
        "file_path", 
        type=Path, 
        help="Absolute path to the PDF file to parse"
    )
    parser.add_argument(
        "--no-debug", 
        action="store_true", 
        help="Disable debug mode"
    )
    parser.add_argument(
        "--output-dir", 
        type=Path, 
        default=Path(__file__).parent / "results",
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    # Validate file path
    if not args.file_path.exists():
        logger.error(f"File does not exist: {args.file_path}")
        sys.exit(1)
    
    if not args.file_path.is_file():
        logger.error(f"Path is not a file: {args.file_path}")
        sys.exit(1)
    
    # Initialize components
    debug_mode = not args.no_debug
    doc_parser = StandaloneDocumentParser(debug_mode=debug_mode)
    storage = LocalStorage(args.output_dir)
    
    try:
        logger.info(f"Starting processing of: {args.file_path}")
        
        # Parse document
        document, confidence = doc_parser.parse_document_from_file(args.file_path)
        
        # Serialize to markdown
        content = doc_parser.serialize_document(document)
        
        # Chunk document
        chunks = list(doc_parser.chunk_document(document))
        
        # Save results
        result_id = storage.save_parsing_result(
            args.file_path, document, confidence, content, chunks
        )
        
        # Print summary
        print(f"\n{'='*60}")
        print("PARSING COMPLETE")
        print(f"{'='*60}")
        print(f"File: {args.file_path.name}")
        print(f"Result ID: {result_id}")
        print(f"Confidence: {confidence.mean_grade}")
        print(f"Content length: {len(content)} characters")
        print(f"Total chunks: {len(chunks)}")
        
        # Page number summary
        pages_found = [c["page_number"] for c in chunks if c["page_number"] is not None]
        pages_unknown = len([c for c in chunks if c["page_number"] is None])
        
        print(f"Chunks with page numbers: {len(pages_found)}")
        print(f"Chunks with unknown pages: {pages_unknown}")
        
        if pages_found:
            print(f"Page range: {min(pages_found)} - {max(pages_found)}")
        
        print(f"Results saved to: {args.output_dir}")
        print(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
