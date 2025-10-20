#!/usr/bin/env python3
"""
Simple PDF Test - No AI Models Required

This script uses PyPDF2 for basic text extraction and tests the chunking logic
without needing docling's AI models.
"""

import json
import sys
from pathlib import Path
from io import BytesIO
from uuid import uuid4

# Try to use PyPDF2 or pypdf
try:
    from pypdf import PdfReader
    print("✅ Using pypdf library")
except ImportError:
    try:
        from PyPDF2 import PdfReader
        print("✅ Using PyPDF2 library")
    except ImportError:
        print("❌ Neither pypdf nor PyPDF2 is installed")
        print("Install with: pip install pypdf")
        sys.exit(1)

# Add backend to path for chunking logic
sys.path.append(str(Path(__file__).parent.parent / "src"))

try:
    from em_backend.vector.parser import DocumentParser
    print("✅ Imported backend DocumentParser")
    use_backend_chunker = True
except Exception as e:
    print(f"⚠️ Could not import backend parser: {e}")
    print("Will use simple chunking")
    use_backend_chunker = False

import tiktoken

def extract_text_from_pdf(pdf_path: Path) -> dict:
    """Extract text from PDF using PyPDF2."""
    print(f"\n📁 Processing: {pdf_path.name}")
    print("=" * 60)
    
    reader = PdfReader(str(pdf_path))
    
    print(f"📄 Total pages: {len(reader.pages)}")
    
    # Extract text page by page
    pages_text = {}
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        pages_text[page_num] = text
        print(f"✅ Extracted page {page_num}: {len(text)} characters")
    
    # Combine all text
    full_text = "\n\n---PAGE_BREAK---\n\n".join(pages_text.values())
    
    return {
        "full_text": full_text,
        "pages": pages_text,
        "page_count": len(reader.pages)
    }

def simple_chunk(text: str, max_tokens: int = 2000, overlap: int = 150) -> list:
    """Simple chunking based on tokens."""
    encoding = tiktoken.encoding_for_model("gpt-4o")
    
    tokens = encoding.encode(text)
    chunks = []
    
    start = 0
    chunk_index = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        
        chunks.append({
            "chunk_id": str(uuid4()),
            "chunk_index": chunk_index,
            "text": chunk_text,
            "token_count": len(chunk_tokens),
            "char_count": len(chunk_text),
            "page_number": None  # Can't determine from simple chunking
        })
        
        print(f"✅ Chunk {chunk_index}: {len(chunk_tokens)} tokens")
        
        if end == len(tokens):
            break
        start = max(end - overlap, start + 1)
        chunk_index += 1
    
    return chunks

def main():
    if len(sys.argv) < 2:
        print("Usage: python simple_test.py /path/to/document.pdf")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    
    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    # Extract text
    extracted = extract_text_from_pdf(pdf_path)
    
    print("\n" + "=" * 60)
    print("🧩 CHUNKING")
    print("=" * 60)
    
    # Chunk the text
    chunks = simple_chunk(extracted["full_text"])
    
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    print(f"Total chunks: {len(chunks)}")
    print(f"Total pages: {extracted['page_count']}")
    
    # Show first 3 chunks
    print("\n" + "=" * 60)
    print("FIRST 3 CHUNKS:")
    print("=" * 60)
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i}:")
        print(f"  Tokens: {chunk['token_count']}")
        print(f"  Characters: {chunk['char_count']}")
        print(f"  Text preview: {chunk['text'][:150]}...")
    
    # Save results
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    result_file = output_dir / f"{pdf_path.stem}_simple_chunks.json"
    with open(result_file, 'w') as f:
        json.dump({
            "file": str(pdf_path),
            "page_count": extracted["page_count"],
            "chunks": chunks
        }, f, indent=2)
    
    print(f"\n✅ Results saved to: {result_file}")

if __name__ == "__main__":
    main()

