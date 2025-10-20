import logging
from collections.abc import Generator, Iterable
from typing import Any
from uuid import uuid4
from io import BytesIO
from pathlib import Path

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

logger = logging.getLogger("em_parser")


class DocumentParser:
    """Parse PDF files."""

    MAX_CHUNK_TOKENS = 2000
    CHUNK_OVERLAP_TOKENS = 150

    def __init__(self) -> None:
        # Setup Document converter
        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=PdfPipelineOptions(
                        artifacts_path=Path.home() / ".cache" / "docling" / "models"
                    )
                )
            }
        )

        # Setup Document chunker
        self._encoding = tiktoken.encoding_for_model(settings.openai_model_name)
        self.tokenizer = OpenAITokenizer(
            tokenizer=self._encoding,
            max_tokens=self.MAX_CHUNK_TOKENS,
        )
        self.chunker = HybridChunker(
            tokenizer=self.tokenizer,
            chunk_size=self.MAX_CHUNK_TOKENS,
            chunk_overlap=self.CHUNK_OVERLAP_TOKENS,
        )

    def parse_document(
        self,
        filename: str,
        file: BytesIO,
    ) -> tuple[DoclingDocument, ConfidenceReport]:
        result = self.doc_converter.convert(DocumentStream(name=filename, stream=file))
        return result.document, result.confidence

    def serialize_document(self, doc: DoclingDocument) -> str:
        serializer = MarkdownDocSerializer(doc=doc)
        ser_result = serializer.serialize()
        return ser_result.text

    def chunk_document(self, doc: DoclingDocument) -> Generator[dict[str, Any]]:
        """
        Chunk document while preserving page numbers from provenance.
        
        The HybridChunker doesn't preserve provenance on chunks, so we need to
        extract page numbers from the original DoclingDocument items which DO
        have provenance information.
        """
        chunk_index = 0
        
        # Collect all items from the document that have text content
        # These items have provenance with page numbers
        items_with_provenance = []
        
        # Get text items (paragraphs, headers, etc.)
        if hasattr(doc, 'texts') and doc.texts:
            items_with_provenance.extend(doc.texts)
        
        # Get table items
        if hasattr(doc, 'tables') and doc.tables:
            items_with_provenance.extend(doc.tables)
        
        # Get picture captions
        if hasattr(doc, 'pictures') and doc.pictures:
            items_with_provenance.extend(doc.pictures)
        
        logger.debug(f"Found {len(items_with_provenance)} items with potential provenance")
        
        # Process each item
        for item in items_with_provenance:
            # Extract page number from item's provenance
            page_number = None
            if hasattr(item, 'prov') and item.prov and len(item.prov) > 0:
                first_prov = item.prov[0]
                page_number = getattr(first_prov, 'page_no', None)
                
                logger.debug(
                    f"Item {chunk_index}: page_number={page_number}, "
                    f"prov_count={len(item.prov)}"
                )
            
            # Extract text from item (different items have different text fields)
            text = None
            if hasattr(item, 'text') and item.text:
                text = item.text
            elif hasattr(item, 'orig') and item.orig:
                text = item.orig
            elif hasattr(item, 'caption') and hasattr(item.caption, 'text'):
                text = item.caption.text
            
            # Skip items without text
            if not text:
                logger.debug(f"Skipping item without text content")
                continue
            
            # Chunk this item's text
            for text_segment in self._split_to_token_budget(text):
                token_count = len(self._encoding.encode(text_segment))
                
                # Create preview of text (truncate if too long)
                text_preview = text_segment[:100] if len(text_segment) > 100 else text_segment
                text_preview = repr(text_preview)  # Show escaped characters
                
                logger.info(
                    f"Generated chunk {chunk_index}: {token_count} tokens, "
                    f"page {page_number if page_number is not None else 'unknown'}, "
                    f"text: {text_preview}"
                )
                yield {
                    "chunk_id": str(uuid4()),
                    "text": text_segment,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                }
                chunk_index += 1

    def _split_to_token_budget(self, text: str) -> Iterable[str]:
        tokens = self._encoding.encode(text)
        if len(tokens) <= self.MAX_CHUNK_TOKENS:
            return [text]

        segments: list[str] = []
        start = 0
        while start < len(tokens):
            end = min(start + self.MAX_CHUNK_TOKENS, len(tokens))
            segment_tokens = tokens[start:end]
            segments.append(self._encoding.decode(segment_tokens))
            if end == len(tokens):
                break
            start = max(end - self.CHUNK_OVERLAP_TOKENS, start + 1)
        return segments
