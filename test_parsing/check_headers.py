#!/usr/bin/env python3
"""
Analyze how section headers appear in chunks.
"""

import json
import sys
from pathlib import Path


def analyze_headers(json_path: Path):
    """Analyze header patterns in chunks."""

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks = data.get('chunks', [])
    print(f"Analyzing {len(chunks)} chunks")
    print("=" * 80)

    # Count how often each header appears
    header_counts = {}

    for chunk in chunks[:50]:  # First 50 chunks
        text = chunk.get('text', '')
        lines = text.split('\n')

        # Extract headers (lines starting with #)
        headers = [line for line in lines if line.strip().startswith('#')]

        print(f"\nChunk {chunk['chunk_index']} (Page {chunk.get('page_number')}):")
        print(f"Headers: {len(headers)}")
        for header in headers[:5]:
            print(f"  {header}")
            header_counts[header] = header_counts.get(header, 0) + 1

        if len(headers) > 5:
            print(f"  ... and {len(headers) - 5} more headers")

        # Show first 200 chars of content (non-header)
        content_lines = [line for line in lines if not line.strip().startswith('#') and line.strip() and line.strip() != '[...]']
        if content_lines:
            content = '\n'.join(content_lines[:3])
            print(f"Content preview: {content[:150]}...")

    print("\n" + "=" * 80)
    print("\nMOST COMMON HEADERS:")
    sorted_headers = sorted(header_counts.items(), key=lambda x: x[1], reverse=True)
    for header, count in sorted_headers[:20]:
        print(f"{count:4d}x  {header}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_headers.py <result_json_path>")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"File not found: {json_path}")
        sys.exit(1)

    analyze_headers(json_path)
