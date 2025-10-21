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
import json
import logging
import sys
from collections.abc import Generator, Iterable
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
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

    MAX_CHUNK_TOKENS = 2000
    CHUNK_OVERLAP_TOKENS = 150

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
        
        try:
            # Use standard pipeline with full models (recommended)
            logger.info("🔧 Initializing DocumentConverter with standard pipeline...")
            
            pipeline_options = PdfPipelineOptions(
                artifacts_path=cache_path,
                do_ocr=False,  # Disable OCR for faster processing
                do_table_structure=True,  # Enable table detection
            )
            
            self.doc_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
            logger.info("✅ SUCCESS: DocumentConverter initialized with full docling pipeline")
            logger.info(f"   Using models from: {cache_path}")
            logger.info("   Features: Layout detection ✅, Table structure ✅, OCR ❌")
            
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
        logger.info(f"   ✅ Max chunk tokens: {self.MAX_CHUNK_TOKENS}")
        logger.info(f"   ✅ Chunk overlap tokens: {self.CHUNK_OVERLAP_TOKENS}")
        logger.info(f"   ✅ Debug mode: {debug_mode}")
        logger.info("🎉 SUCCESS: StandaloneDocumentParser initialization COMPLETE!")

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
        Chunk document using HybridChunker while preserving page numbers.
        
        Uses HybridChunker for intelligent chunking, then extracts page numbers
        from the chunk's metadata which links back to source items with provenance.
        """
        chunk_index = 0
        all_chunks = []
        all_metadata_analysis = []
        
        logger.info("🧩 STARTING DOCUMENT CHUNKING (USING HYBRIDCHUNKER)...")
        logger.info("=" * 80)
        
        # Use HybridChunker to get properly-sized chunks
        for chunk in self.chunker.chunk(doc):
            logger.debug(f"Processing chunk {chunk_index}")
            
            # Get the contextualized text
            contextualized = self.chunker.contextualize(chunk)
            logger.debug(f"   📝 Contextualized text length: {len(contextualized)} characters")
            
            # Extract page number from chunk metadata
            page_number = None
            chunk_meta_info = {"chunk_index": chunk_index, "has_meta": False, "meta_structure": {}}
            
            # Analyze chunk metadata
            if hasattr(chunk, 'meta') and chunk.meta is not None:
                chunk_meta_info["has_meta"] = True
                logger.debug(f"   ✅ Chunk has metadata")
                logger.debug(f"   📋 Metadata type: {type(chunk.meta)}")
                logger.debug(f"   📋 Metadata attributes: {[attr for attr in dir(chunk.meta) if not attr.startswith('_')]}")
                
                # Get the doc_items that this chunk came from
                if hasattr(chunk.meta, 'doc_items') and chunk.meta.doc_items:
                    source_items = chunk.meta.doc_items
                    chunk_meta_info["doc_items_count"] = len(source_items)
                    logger.info(f"   ✅ Found {len(source_items)} source doc_items in metadata")
                    
                    if len(source_items) > 0:
                        # The source item IS the actual object (not a string reference!)
                        source_item = source_items[0]
                        chunk_meta_info["first_item_ref"] = str(source_item)[:200]  # Truncate for logging
                        chunk_meta_info["first_item_type"] = type(source_item).__name__
                        logger.debug(f"   📦 First item type: {type(source_item).__name__}")
                        
                        # Extract page number directly from the item's provenance
                        if hasattr(source_item, 'prov') and source_item.prov:
                            if len(source_item.prov) > 0:
                                first_prov = source_item.prov[0]
                                page_number = getattr(first_prov, 'page_no', None)
                                chunk_meta_info["page_number"] = page_number
                                logger.info(f"   🎉 SUCCESS: Extracted page {page_number} from {type(source_item).__name__}")
                        else:
                            logger.warning(f"   ❌ Source item has no provenance")
                else:
                    logger.warning(f"   ❌ Metadata has no doc_items attribute")
            else:
                logger.warning(f"   ❌ Chunk has no metadata")
            
            all_metadata_analysis.append(chunk_meta_info)
            
            # If metadata approach didn't work
            if page_number is None:
                logger.warning(f"   💥 FAILED to extract page number for chunk {chunk_index}")
            
            # Split contextualized text into token budget
            segment_index = 0
            for text_segment in self._split_to_token_budget(contextualized):
                token_count = len(self._encoding.encode(text_segment))
                
                # Create preview of text (truncate if too long)
                text_preview = text_segment[:100] if len(text_segment) > 100 else text_segment
                text_preview = repr(text_preview)  # Show escaped characters
                
                chunk_data = {
                    "chunk_id": str(uuid4()),
                    "text": text_segment,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "segment_index": segment_index,
                    "token_count": token_count,
                    "char_count": len(text_segment),
                    "word_count": len(text_segment.split()),
                    "metadata_info": chunk_meta_info if self.debug_mode else None
                }
                
                all_chunks.append(chunk_data)
                
                # Log chunk generation with text preview
                if page_number is not None:
                    logger.info(f"✅ SUCCESS: Generated chunk {chunk_index}.{segment_index}: {token_count} tokens, page {page_number}, text: {text_preview}")
                else:
                    logger.warning(f"❌ PARTIAL: Generated chunk {chunk_index}.{segment_index}: {token_count} tokens, page UNKNOWN, text: {text_preview}")
                
                # Show detailed preview for first few chunks
                if chunk_index < 5:
                    self._log_chunk_preview(chunk_data, chunk_index, segment_index)
                
                yield chunk_data
                segment_index += 1
                chunk_index += 1
        
        # Final summary
        logger.info("=" * 80)
        logger.info("🎉 DOCUMENT CHUNKING COMPLETE!")
        self._log_chunking_summary(all_chunks)
        
        # Save metadata analysis
        if self.debug_mode:
            metadata_file = Path(__file__).parent / "results" / "chunk_metadata_analysis.json"
            metadata_file.parent.mkdir(exist_ok=True)
            try:
                with open(metadata_file, "w") as f:
                    json.dump(all_metadata_analysis, f, indent=2, default=str)
                logger.info(f"✅ SUCCESS: Metadata analysis saved to {metadata_file}")
            except Exception as e:
                logger.error(f"❌ FAILED: Could not save metadata analysis: {e}")
    
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
        logger.info(f"🔢 Token statistics:")
        logger.info(f"   - Total tokens: {sum(token_counts):,}")
        logger.info(f"   - Average tokens per chunk: {sum(token_counts)/len(token_counts):.1f}")
        logger.info(f"   - Min tokens: {min(token_counts)}")
        logger.info(f"   - Max tokens: {max(token_counts)}")
        
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
        """Split text to fit within token budget."""
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
        result_id = str(uuid4())
        
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
