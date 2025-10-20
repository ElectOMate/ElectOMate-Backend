#!/usr/bin/env python3
"""
Easy Test Runner for PDF Parsing

This script provides a simple interface to test PDF parsing with minimal setup.
Just run it and input the path to your PDF file.
"""

import sys
from pathlib import Path

def main():
    print("="*60)
    print("PDF PARSING TEST RUNNER")
    print("="*60)
    
    # Get file path from user
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
    else:
        file_path_str = input("Enter the absolute path to your PDF file: ").strip()
        if not file_path_str:
            print("No file path provided. Exiting.")
            sys.exit(1)
        file_path = Path(file_path_str)
    
    # Validate file
    if not file_path.exists():
        print(f"❌ File does not exist: {file_path}")
        sys.exit(1)
    
    if not file_path.is_file():
        print(f"❌ Path is not a file: {file_path}")
        sys.exit(1)
    
    if not file_path.suffix.lower() == '.pdf':
        print(f"⚠️  Warning: File does not have .pdf extension: {file_path}")
        proceed = input("Continue anyway? (y/N): ").strip().lower()
        if proceed != 'y':
            sys.exit(1)
    
    print(f"✅ File found: {file_path}")
    print(f"📁 Size: {file_path.stat().st_size / 1024:.1f} KB")
    
    # Ask for debug mode
    debug_choice = input("Enable debug mode? (Y/n): ").strip().lower()
    debug_mode = debug_choice != 'n'
    
    print("\n" + "="*60)
    print("STARTING PARSING...")
    print("="*60)
    
    # Import and run the parser
    try:
        from standalone_parser import StandaloneDocumentParser, LocalStorage
        
        # Setup
        results_dir = Path(__file__).parent / "results"
        doc_parser = StandaloneDocumentParser(debug_mode=debug_mode)
        storage = LocalStorage(results_dir)
        
        # Parse
        document, confidence = doc_parser.parse_document_from_file(file_path)
        content = doc_parser.serialize_document(document)
        chunks = list(doc_parser.chunk_document(document))
        
        # Save
        result_id = storage.save_parsing_result(
            file_path, document, confidence, content, chunks
        )
        
        # Summary
        print("\n" + "="*60)
        print("✅ PARSING COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"📄 File: {file_path.name}")
        print(f"🔍 Result ID: {result_id}")
        print(f"📊 Confidence: {confidence.mean_grade}")
        print(f"📝 Content: {len(content):,} characters")
        print(f"🧩 Total chunks: {len(chunks)}")
        
        # Page analysis
        pages_with_numbers = [c for c in chunks if c["page_number"] is not None]
        pages_unknown = [c for c in chunks if c["page_number"] is None]
        
        print(f"📄 Chunks with page numbers: {len(pages_with_numbers)}")
        print(f"❓ Chunks with unknown pages: {len(pages_unknown)}")
        
        if pages_with_numbers:
            page_numbers = [c["page_number"] for c in pages_with_numbers]
            print(f"📄 Page range: {min(page_numbers)} - {max(page_numbers)}")
        
        print(f"💾 Results saved to: {results_dir}")
        
        if debug_mode:
            print(f"🔍 Debug info saved to: {results_dir / 'debug_provenance.json'}")
        
        print("\n" + "="*60)
        
        # Offer to show some sample chunks
        show_samples = input("Show sample chunks? (y/N): ").strip().lower()
        if show_samples == 'y':
            print("\nSAMPLE CHUNKS:")
            print("-" * 40)
            for i, chunk in enumerate(chunks[:3]):
                print(f"Chunk {i}: Page {chunk['page_number']}, {chunk['token_count']} tokens")
                print(f"Text preview: {chunk['text'][:100]}...")
                print("-" * 40)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
