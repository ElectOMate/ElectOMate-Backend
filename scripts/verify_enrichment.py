#!/usr/bin/env python3
"""Verify enrichment quality: check that quoted text appears on cited pages.

Usage:
    python scripts/verify_enrichment.py [--samples 20]
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
ENRICHED_FILE = BACKEND_ROOT / "data" / "enriched_evidence" / "en_enriched.json"
PAGES_DIR = BACKEND_ROOT / "data" / "manifesto_pages"

PARTY_NAME_TO_KEY = {
    "Fidesz - Magyar Polgári Szövetség": "FIDESZ",
    "TISZA - Tisztelet és Szabadság Párt": "TISZA",
    "Demokratikus Koalíció": "DK",
    "Mi Hazánk Mozgalom": "MI_HAZANK",
    "Magyar Kétfarkú Kutya Párt": "MKKP",
    "Jobbik Magyarországért Mozgalom": "JOBBIK",
    "Magyar Szocialista Párt": "MSZP",
}


def load_page_text(party_key: str, pdf_filename: str, page_num: int) -> str | None:
    """Load the text of a specific page from the extracted pages JSON."""
    pages_file = PAGES_DIR / f"{party_key}_pages.json"
    if not pages_file.exists():
        return None
    with open(pages_file, encoding="utf-8") as f:
        data = json.load(f)
    for doc in data.get("documents", []):
        if doc["pdf_filename"] == pdf_filename:
            for page in doc["pages"]:
                if page["page"] == page_num:
                    return page["text"]
    return None


def verify_quote(page_text: str, quote: str, threshold: float = 0.5) -> tuple[bool, float]:
    """Check if a quote (or substantial part) appears on the page.

    Returns (match, overlap_ratio).
    Uses word-level overlap since GPT-4o may slightly paraphrase.
    """
    if not page_text or not quote:
        return False, 0.0

    # Normalize: lowercase, strip punctuation
    def normalize(s: str) -> set[str]:
        import re
        return {re.sub(r'[^\w]', '', w).lower() for w in s.split() if len(w) > 2}

    page_words = normalize(page_text)
    quote_words = normalize(quote)

    if not quote_words:
        return False, 0.0

    overlap = len(quote_words & page_words)
    ratio = overlap / len(quote_words)

    return ratio >= threshold, ratio


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()

    if not ENRICHED_FILE.exists():
        print(f"ERROR: {ENRICHED_FILE} not found. Run enrichment first.")
        sys.exit(1)

    with open(ENRICHED_FILE, encoding="utf-8") as f:
        data = json.load(f)

    # Collect all PDF-sourced evidence chunks
    pdf_chunks = []
    for q in data["evaluationPage"]["questions_detailed"]:
        for stance in ["pro", "neutral", "contra", "not_given"]:
            parties = q.get("positions", {}).get(stance, {}).get("parties", {})
            for party_name, entry in parties.items():
                if not isinstance(entry, dict):
                    continue
                for chunk in entry.get("evidence_chunks", []):
                    if chunk.get("page_number") and chunk.get("file_name"):
                        pdf_chunks.append({
                            "question_id": q["id"],
                            "question": q["q"][:60],
                            "party": party_name,
                            "party_key": PARTY_NAME_TO_KEY.get(party_name, "?"),
                            "stance": stance,
                            **chunk,
                        })

    print(f"Total PDF-sourced evidence chunks: {len(pdf_chunks)}")
    print(f"Sampling {min(args.samples, len(pdf_chunks))} for verification\n")

    if not pdf_chunks:
        print("No PDF-sourced chunks found!")
        sys.exit(1)

    samples = random.sample(pdf_chunks, min(args.samples, len(pdf_chunks)))

    passed = 0
    failed = 0
    skipped = 0

    for i, chunk in enumerate(samples, 1):
        page_text = load_page_text(
            chunk["party_key"],
            chunk["file_name"],
            chunk["page_number"],
        )

        if page_text is None:
            print(f"  [{i:02d}] SKIP — page not found: {chunk['party_key']}/{chunk['file_name']} p.{chunk['page_number']}")
            skipped += 1
            continue

        match, ratio = verify_quote(page_text, chunk["text"])

        status = "PASS" if match else "FAIL"
        if match:
            passed += 1
        else:
            failed += 1

        print(f"  [{i:02d}] {status} ({ratio:.0%} overlap) — Q{chunk['question_id']} {chunk['party_key']} p.{chunk['page_number']}")
        if not match:
            print(f"       Quote: \"{chunk['text'][:80]}...\"")
            print(f"       Page starts: \"{page_text[:80]}...\"")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"Accuracy: {passed/(passed+failed)*100:.0f}%" if (passed+failed) > 0 else "N/A")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
