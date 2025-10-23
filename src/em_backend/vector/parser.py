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
    MIN_CHUNK_TOKENS = 1500  # Ensure chunks have at least 1500 tokens
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
                
                # Check if chunk meets minimum requirements
                meets_min = token_count >= self.MIN_CHUNK_TOKENS
                meets_max = token_count <= self.MAX_CHUNK_TOKENS
                meets_requirements = meets_min and meets_max
                
                status_emoji = "✅" if meets_requirements else "⚠️"
                status_text = f"({self.MIN_CHUNK_TOKENS}-{self.MAX_CHUNK_TOKENS} target)"
                
                logger.info(
                    f"{status_emoji} Generated chunk {chunk_index}: {token_count} tokens {status_text}, "
                    f"page {page_number if page_number is not None else 'unknown'}, "
                    f"text: {text_preview}"
                )
                
                # Log warnings for chunks outside target range
                if not meets_min:
                    logger.warning(f"Chunk {chunk_index} has only {token_count} tokens, below minimum {self.MIN_CHUNK_TOKENS}")
                elif not meets_max:
                    logger.warning(f"Chunk {chunk_index} has {token_count} tokens, above maximum {self.MAX_CHUNK_TOKENS}")
                yield {
                    "chunk_id": str(uuid4()),
                    "text": text_segment,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                }
                chunk_index += 1

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
