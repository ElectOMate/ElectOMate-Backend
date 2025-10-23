#!/usr/bin/env python3
"""
Use Backend Parser Directly

This script uses the actual backend's DocumentParser which should already
have models configured correctly.
"""

import sys
import json
from pathlib import Path
from io import BytesIO

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from em_backend.vector.parser import DocumentParser

def main():
    if len(sys.argv) < 2:
        print("Usage: python use_backend_parser.py /path/to/document.pdf")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    
    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"📁 Processing: {pdf_path.name}")
    print("=" * 60)
    
    # Initialize parser
    print("🔧 Initializing DocumentParser...")
    parser = DocumentParser()
    print("✅ Parser initialized")
    
    # Read file
    print("📖 Reading file...")
    file_content = pdf_path.read_bytes()
    file_stream = BytesIO(file_content)
    print(f"✅ Read {len(file_content):,} bytes")
    
    # Parse
    print("🔧 Parsing document...")
    try:
        document, confidence = parser.parse_document(pdf_path.name, file_stream)
        print(f"✅ Parsing complete! Confidence: {confidence.mean_grade}")
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Serialize
    print("📝 Serializing to markdown...")
    content = parser.serialize_document(document)
    print(f"✅ Serialized: {len(content):,} characters")
    
    # Chunk
    print("🧩 Chunking document...")
    chunks = list(parser.chunk_document(document))
    print(f"✅ Generated {len(chunks)} chunks")
    
    # Analyze chunks
    chunks_with_pages = [c for c in chunks if c.get('page_number') is not None]
    chunks_without_pages = [c for c in chunks if c.get('page_number') is None]
    
    print("\n" + "=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    print(f"Total chunks: {len(chunks)}")
    print(f"✅ With page numbers: {len(chunks_with_pages)} ({len(chunks_with_pages)/len(chunks)*100:.1f}%)")
    print(f"❌ Without page numbers: {len(chunks_without_pages)} ({len(chunks_without_pages)/len(chunks)*100:.1f}%)")
    
    if chunks_with_pages:
        pages = [c['page_number'] for c in chunks_with_pages]
        print(f"📄 Page range: {min(pages)} - {max(pages)}")
    
    print("\n" + "=" * 60)
    print("FIRST 3 CHUNKS:")
    print("=" * 60)
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i}:")
        print(f"  Page: {chunk.get('page_number', '❌ UNKNOWN')}")
        print(f"  Tokens: {len(chunk.get('text', '').split())}")
        print(f"  Text: {chunk.get('text', '')[:150]}...")
    
    # Save to file
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{pdf_path.stem}_chunks.json"
    
    with open(output_file, 'w') as f:
        json.dump(chunks, f, indent=2, default=str)
    
    print(f"\n✅ Results saved to: {output_file}")

if __name__ == "__main__":
    main()




