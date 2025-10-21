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
        Chunk document using HybridChunker while preserving page numbers.
        
        Uses HybridChunker for intelligent chunking, then extracts page numbers
        from the chunk's metadata which links back to source items with provenance.
        """
        chunk_index = 0
        
        # Use HybridChunker to get properly-sized chunks
        for chunk in self.chunker.chunk(doc):
            # Get the contextualized text
            contextualized = self.chunker.contextualize(chunk)
            
            # Extract page number from chunk metadata
            page_number = None
            
            # HybridChunker chunks have metadata linking to source doc items
            if hasattr(chunk, 'meta') and chunk.meta is not None:
                # Get the doc_items that this chunk came from
                if hasattr(chunk.meta, 'doc_items') and chunk.meta.doc_items:
                    # Get the first source item
                    source_items = chunk.meta.doc_items
                    if len(source_items) > 0:
                        # The source item IS the actual item object (not a string reference!)
                        source_item = source_items[0]
                        
                        # Extract page number directly from the item's provenance
                        if hasattr(source_item, 'prov') and source_item.prov:
                            if len(source_item.prov) > 0:
                                first_prov = source_item.prov[0]
                                page_number = getattr(first_prov, 'page_no', None)
                                
                                logger.debug(
                                    f"Chunk {chunk_index}: Extracted page {page_number} from source item"
                                )
            
            # If metadata approach didn't work
            if page_number is None:
                logger.debug(f"Chunk {chunk_index}: Could not extract page from metadata")
            
            # Split contextualized text into token budget
            for text_segment in self._split_to_token_budget(contextualized):
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
