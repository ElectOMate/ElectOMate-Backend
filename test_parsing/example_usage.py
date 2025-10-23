#!/usr/bin/env python3
"""
Example Usage of Standalone Parser

This script demonstrates how to use the standalone parser programmatically
for automated testing or integration into other scripts.
"""

from pathlib import Path
from standalone_parser import StandaloneDocumentParser, LocalStorage

def example_parse_single_file():
    """Example: Parse a single PDF file."""
    
    # You would replace this with your actual PDF path
    pdf_path = Path("/path/to/your/document.pdf")
    
    if not pdf_path.exists():
        print("❌ Please set a valid PDF path in this example")
        return
    
    print(f"🔍 Parsing: {pdf_path}")
    
    # Initialize parser with debug mode
    parser = StandaloneDocumentParser(debug_mode=True)
    storage = LocalStorage(Path("./results"))
    
    try:
        # Parse document
        document, confidence = parser.parse_document_from_file(pdf_path)
        print(f"✅ Parsing confidence: {confidence.mean_grade}")
        
        # Extract content
        content = parser.serialize_document(document)
        print(f"📄 Content length: {len(content)} characters")
        
        # Chunk document
        chunks = list(parser.chunk_document(document))
        print(f"🧩 Generated {len(chunks)} chunks")
        
        # Analyze page numbers
        pages_found = sum(1 for c in chunks if c["page_number"] is not None)
        pages_unknown = len(chunks) - pages_found
        
        print(f"📄 Chunks with page numbers: {pages_found}")
        print(f"❓ Chunks with unknown pages: {pages_unknown}")
        
        # Save results
        result_id = storage.save_parsing_result(pdf_path, document, confidence, content, chunks)
        print(f"💾 Results saved with ID: {result_id}")
        
        return chunks
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def example_analyze_page_extraction():
    """Example: Focus on page number extraction analysis."""
    
    pdf_path = Path("/path/to/your/document.pdf")
    
    if not pdf_path.exists():
        print("❌ Please set a valid PDF path in this example")
        return
    
    parser = StandaloneDocumentParser(debug_mode=True)
    
    try:
        document, _ = parser.parse_document_from_file(pdf_path)
        
        print("🔍 Analyzing page number extraction...")
        print("-" * 50)
        
        chunks = list(parser.chunk_document(document))
        
        # Group chunks by page number status
        with_pages = [c for c in chunks if c["page_number"] is not None]
        without_pages = [c for c in chunks if c["page_number"] is None]
        
        print(f"Chunks with page numbers: {len(with_pages)}")
        print(f"Chunks without page numbers: {len(without_pages)}")
        
        if with_pages:
            pages = [c["page_number"] for c in with_pages]
            print(f"Page range: {min(pages)} - {max(pages)}")
        
        # Show debug info for first few chunks without pages
        if without_pages:
            print("\nDebug info for chunks without page numbers:")
            for i, chunk in enumerate(without_pages[:3]):
                debug_info = chunk.get("debug_info", {})
                print(f"\nChunk {chunk['chunk_index']}:")
                print(f"  Has provenance: {debug_info.get('has_prov_attr', 'Unknown')}")
                print(f"  Provenance type: {debug_info.get('prov_type', 'Unknown')}")
                
                attempts = debug_info.get('page_extraction_attempts', [])
                for attempt in attempts:
                    if attempt['exists']:
                        print(f"  Found {attempt['attribute']}: {attempt['value']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Standalone Parser Example Usage")
    print("=" * 50)
    
    print("\n1. Basic parsing example:")
    example_parse_single_file()
    
    print("\n2. Page extraction analysis:")
    example_analyze_page_extraction()
    
    print("\n✅ Examples completed!")
    print("\nTo use with your own PDF:")
    print("1. Edit the pdf_path variables in the functions above")
    print("2. Run this script again")
    print("3. Or use the interactive runner: python run_test.py")



