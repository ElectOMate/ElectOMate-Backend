#!/usr/bin/env python3
"""
Analyze chunk duplicates and overlaps from parser results.

This script reads a result JSON file and identifies:
1. Exact duplicate chunks
2. Overlapping chunks (same text appearing in multiple chunks)
3. The pattern of overlap (how much text is shared)
"""

import json
import sys
from pathlib import Path
from difflib import SequenceMatcher


def analyze_result_file(json_path: Path):
    """Analyze a result JSON file for duplicates and overlaps."""

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks = data.get('chunks', [])
    print(f"Analyzing {len(chunks)} chunks from {json_path.name}")
    print("=" * 80)

    # 1. Check for exact duplicates
    print("\n1. EXACT DUPLICATES:")
    text_to_chunks = {}
    for chunk in chunks:
        text = chunk.get('text', '')
        if text in text_to_chunks:
            text_to_chunks[text].append(chunk)
        else:
            text_to_chunks[text] = [chunk]

    duplicates = {text: chunks_list for text, chunks_list in text_to_chunks.items() if len(chunks_list) > 1}

    if duplicates:
        print(f"   Found {len(duplicates)} sets of exact duplicates:")
        for i, (text, dup_chunks) in enumerate(list(duplicates.items())[:5]):
            print(f"\n   Duplicate set {i+1}: {len(dup_chunks)} chunks with identical text")
            print(f"   Chunk indices: {[c['chunk_index'] for c in dup_chunks]}")
            print(f"   Pages: {[c.get('page_number') for c in dup_chunks]}")
            print(f"   Text preview: {text[:100]}...")
    else:
        print("   ✅ No exact duplicates found!")

    # 2. Check for overlapping chunks (sequential chunks sharing text)
    print("\n\n2. OVERLAPPING CHUNKS (Sequential):")
    overlaps = []

    for i in range(len(chunks) - 1):
        current_text = chunks[i].get('text', '')
        next_text = chunks[i+1].get('text', '')

        # Find longest common substring
        matcher = SequenceMatcher(None, current_text, next_text)
        match = matcher.find_longest_match(0, len(current_text), 0, len(next_text))

        if match.size > 100:  # More than 100 chars overlap
            overlap_text = current_text[match.a:match.a + match.size]
            overlaps.append({
                'chunk1_idx': chunks[i]['chunk_index'],
                'chunk2_idx': chunks[i+1]['chunk_index'],
                'chunk1_page': chunks[i].get('page_number'),
                'chunk2_page': chunks[i+1].get('page_number'),
                'overlap_size': match.size,
                'overlap_text': overlap_text[:200]
            })

    if overlaps:
        print(f"   Found {len(overlaps)} pairs with significant overlap:")
        for i, overlap in enumerate(overlaps[:10]):
            print(f"\n   Overlap {i+1}:")
            print(f"   - Chunks: {overlap['chunk1_idx']} -> {overlap['chunk2_idx']}")
            print(f"   - Pages: {overlap['chunk1_page']} -> {overlap['chunk2_page']}")
            print(f"   - Overlap: {overlap['overlap_size']} characters")
            print(f"   - Text: {overlap['overlap_text'][:100]}...")
    else:
        print("   ✅ No significant overlaps found!")

    # 3. Analyze chunk patterns
    print("\n\n3. CHUNK PATTERN ANALYSIS:")

    # Check for chunks with [...] markers
    chunks_with_start_marker = [c for c in chunks if '[...]' in c.get('text', '')[:50]]
    chunks_with_end_marker = [c for c in chunks if '[...]' in c.get('text', '')[-50:]]
    chunks_with_both = [c for c in chunks if '[...]' in c.get('text', '')[:50] and '[...]' in c.get('text', '')[-50:]]

    print(f"   - Chunks with leading [...]: {len(chunks_with_start_marker)}")
    print(f"   - Chunks with trailing [...]: {len(chunks_with_end_marker)}")
    print(f"   - Chunks with both markers: {len(chunks_with_both)}")

    # Check for chunks with section headers (## markers)
    chunks_with_headers = [c for c in chunks if c.get('text', '').strip().startswith('#')]
    print(f"   - Chunks with section headers: {len(chunks_with_headers)}")

    # 4. Page number distribution
    print("\n\n4. PAGE NUMBER DISTRIBUTION:")
    page_counts = {}
    for chunk in chunks:
        page = chunk.get('page_number', 'UNKNOWN')
        page_counts[page] = page_counts.get(page, 0) + 1

    print(f"   - Unique pages: {len(page_counts)}")
    print(f"   - Page distribution:")
    for page in sorted(page_counts.keys())[:20]:
        print(f"      Page {page}: {page_counts[page]} chunks")

    if len(page_counts) > 20:
        print(f"      ... and {len(page_counts) - 20} more pages")

    # 5. Token distribution
    print("\n\n5. TOKEN DISTRIBUTION:")
    token_counts = [c.get('token_count', 0) for c in chunks]
    print(f"   - Min tokens: {min(token_counts)}")
    print(f"   - Max tokens: {max(token_counts)}")
    print(f"   - Avg tokens: {sum(token_counts) / len(token_counts):.1f}")

    # Chunks outside expected range
    too_small = [c for c in chunks if c.get('token_count', 0) < 400]
    too_large = [c for c in chunks if c.get('token_count', 0) > 1000]

    if too_small:
        print(f"   - ⚠️ {len(too_small)} chunks < 400 tokens")
        for c in too_small[:3]:
            print(f"      Chunk {c['chunk_index']}: {c.get('token_count')} tokens, page {c.get('page_number')}")

    if too_large:
        print(f"   - ⚠️ {len(too_large)} chunks > 1000 tokens")
        for c in too_large[:3]:
            print(f"      Chunk {c['chunk_index']}: {c.get('token_count')} tokens, page {c.get('page_number')}")

    print("\n" + "=" * 80)

    # Write detailed overlap report
    if overlaps:
        report_path = json_path.parent / f"overlap_report_{json_path.stem}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("DETAILED OVERLAP REPORT\n")
            f.write("=" * 80 + "\n\n")

            for i, overlap in enumerate(overlaps):
                f.write(f"\nOverlap {i+1}:\n")
                f.write(f"Chunk {overlap['chunk1_idx']} (page {overlap['chunk1_page']}) -> ")
                f.write(f"Chunk {overlap['chunk2_idx']} (page {overlap['chunk2_page']})\n")
                f.write(f"Overlap size: {overlap['overlap_size']} characters\n\n")
                f.write("Overlapping text:\n")
                f.write("-" * 40 + "\n")
                f.write(overlap['overlap_text'])
                f.write("\n" + "-" * 40 + "\n\n")

        print(f"Detailed overlap report saved to: {report_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_duplicates.py <result_json_path>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"File not found: {json_path}")
        sys.exit(1)

    analyze_result_file(json_path)
