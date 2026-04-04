#!/usr/bin/env python3
"""Enrich Hungarian ElectoMate evaluation evidence with page-level manifesto citations.

For each question × party, this script:
1. Loads the existing evidence (reasoning + evidence_chunks) from en.json
2. Searches all available manifesto PDFs for that party to find relevant pages
3. Uses GPT-4o to extract direct quotes with page numbers
4. Outputs enriched evidence with page_number, pdf_filename, pdf_url, and verified quotes

Usage:
    python scripts/enrich_evidence_with_sources.py [--party FIDESZ] [--question 1] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from openai import OpenAI

# ── paths ──────────────────────────────────────────────────────────────
BACKEND_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = BACKEND_ROOT.parent / "ElectOMate-Frontend"
LOCALE_FILE = FRONTEND_ROOT / "src" / "assets" / "WebsiteContent" / "locales_Hungary" / "en.json"
PAGES_DIR = BACKEND_ROOT / "data" / "manifesto_pages"
OUTPUT_DIR = BACKEND_ROOT / "data" / "enriched_evidence"

# ── party name mapping (locale full names → party keys) ─────────────
PARTY_NAME_TO_KEY = {
    "Fidesz - Magyar Polgári Szövetség": "FIDESZ",
    "TISZA - Tisztelet és Szabadság Párt": "TISZA",
    "Demokratikus Koalíció": "DK",
    "Mi Hazánk Mozgalom": "MI_HAZANK",
    "Magyar Kétfarkú Kutya Párt": "MKKP",
    "Jobbik Magyarországért Mozgalom": "JOBBIK",
    "Magyar Szocialista Párt": "MSZP",
}

PARTY_KEY_TO_NAME = {v: k for k, v in PARTY_NAME_TO_KEY.items()}

# PDF base URL for frontend serving
PDF_BASE_URL = "/country-storage/HU/manifestos"


def load_manifesto_pages(party_key: str) -> list[dict]:
    """Load all page texts for a party from the extracted JSON."""
    pages_file = PAGES_DIR / f"{party_key}_pages.json"
    if not pages_file.exists():
        return []
    with open(pages_file, encoding="utf-8") as f:
        data = json.load(f)

    # Flatten all documents' pages, tagging each with the source PDF
    all_pages = []
    for doc in data.get("documents", []):
        pdf_filename = doc["pdf_filename"]
        label = doc["label"]
        is_original = doc["is_original"]
        for page in doc["pages"]:
            all_pages.append({
                "page": page["page"],
                "text": page["text"],
                "pdf_filename": pdf_filename,
                "label": label,
                "is_original": is_original,
            })
    return all_pages


def find_relevant_pages(
    question_text: str,
    reasoning: str,
    existing_evidence: list[dict],
    manifesto_pages: list[dict],
    party_key: str,
    max_pages: int = 15,
) -> list[dict]:
    """Use keyword matching to pre-filter manifesto pages relevant to a question.

    Returns the top N pages sorted by relevance score (simple keyword overlap).
    """
    # Build keyword set from question + reasoning + existing evidence
    keywords = set()
    for text in [question_text, reasoning] + [e.get("text", "") for e in existing_evidence]:
        # Extract meaningful words (>3 chars)
        words = text.lower().split()
        keywords.update(w.strip(".,;:!?()[]\"'") for w in words if len(w) > 3)

    # Remove very common stop words
    stop_words = {
        "that", "this", "with", "from", "have", "been", "will", "would", "could",
        "should", "than", "their", "there", "they", "which", "were", "what", "when",
        "into", "also", "more", "most", "such", "only", "other", "about", "over",
        "some", "very", "after", "before", "between", "through", "during", "under",
        "against", "while", "because", "each", "both", "being", "does", "itself",
        # Hungarian stop words
        "amely", "amelyet", "mint", "által", "vagy", "volt", "csak", "még",
        "nem", "már", "lesz", "kell", "lehet", "között", "szerint", "mellett",
        "ellen", "felé", "után", "előtt", "alatt", "felett",
    }
    keywords -= stop_words

    scored_pages = []
    for page_info in manifesto_pages:
        page_text_lower = page_info["text"].lower()
        # Count keyword hits
        hits = sum(1 for kw in keywords if kw in page_text_lower)
        if hits > 0:
            scored_pages.append({**page_info, "_score": hits})

    scored_pages.sort(key=lambda x: x["_score"], reverse=True)
    return scored_pages[:max_pages]


def enrich_with_gpt4o(
    client: OpenAI,
    question: dict,
    party_name: str,
    party_key: str,
    position: str,
    reasoning: str,
    existing_evidence: list[dict],
    relevant_pages: list[dict],
) -> list[dict]:
    """Use GPT-4o to extract precise quotes and page references from manifesto pages."""

    if not relevant_pages:
        return existing_evidence  # No manifesto pages found, keep existing

    # Build page context (limit to avoid token overflow)
    page_context = ""
    for p in relevant_pages[:10]:  # Max 10 pages to stay within token limits
        page_context += f"\n--- {p['pdf_filename']} | Page {p['page']} | {p['label']} ---\n"
        page_context += p["text"][:3000] + "\n"  # Cap per page

    prompt = f"""You are enriching political party evidence with verifiable source citations.

QUESTION: {question['q']}
TOPIC: {question.get('t', 'N/A')}
PARTY: {party_name} ({party_key})
POSITION: {position}

CURRENT REASONING:
{reasoning}

EXISTING EVIDENCE (from research files, no page numbers):
{json.dumps([{"text": e.get("text", ""), "source": e.get("source", "")} for e in existing_evidence], ensure_ascii=False, indent=2)}

MANIFESTO PAGES (search these for direct quotes):
{page_context}

TASK: Find direct quotes from the manifesto pages that support or explain this party's position on this question. For each quote:

1. Extract the EXACT text from the manifesto (copy verbatim, in the original language)
2. Note the PDF filename and page number where it appears
3. Explain briefly (in English) why this quote is relevant
4. Rate confidence 0.0-1.0 that this quote genuinely supports the position

Return a JSON array of evidence chunks. Each chunk:
{{
  "text": "exact quote from manifesto (original language)",
  "text_en": "English translation of the quote",
  "page_number": <int>,
  "pdf_filename": "filename.pdf",
  "relevance_note": "why this quote matters",
  "confidence": <float 0.0-1.0>,
  "is_original_document": <bool>
}}

Rules:
- Only include quotes that ACTUALLY appear in the provided manifesto text
- Prefer original party documents over compiled summaries
- Include 2-5 quotes per party-question pair
- If no relevant content found in manifestos, return an empty array []
- Keep quotes concise but complete (1-3 sentences)

Return a JSON object with a single key "quotes" containing the array of evidence chunks.
Example: {{"quotes": [{{"text": "...", "text_en": "...", "page_number": 1, "pdf_filename": "...", "relevance_note": "...", "confidence": 0.9, "is_original_document": false}}]}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        # Handle {"quotes": [...]} or {"evidence": [...]} or bare [...]
        if isinstance(parsed, dict):
            for key in ("quotes", "evidence", "chunks"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                # Try first list value
                for v in parsed.values():
                    if isinstance(v, list):
                        parsed = v
                        break
                else:
                    parsed = []

        if not isinstance(parsed, list):
            parsed = []

        if parsed:
            print(f"    [GPT-4o] extracted {len(parsed)} manifesto quotes")

        # Transform to our evidence chunk format
        enriched = []
        for chunk in parsed:
            if not isinstance(chunk, dict):
                continue
            enriched.append({
                "score": chunk.get("confidence", 0.8),
                "text": chunk.get("text", ""),
                "text_en": chunk.get("text_en", ""),
                "page_number": chunk.get("page_number"),
                "file_name": chunk.get("pdf_filename", ""),
                "file_path": f"HungaryElections2026/{chunk.get('pdf_filename', '')}",
                "pdf_url": f"{PDF_BASE_URL}/{chunk.get('pdf_filename', '')}",
                "source": "manifesto",
                "doc_type": "pdf",
                "is_original_document": chunk.get("is_original_document", False),
                "relevance_note": chunk.get("relevance_note", ""),
                "ingested_at": "2026-04-04T00:00:00Z",
            })

        # Merge: keep existing evidence + add new manifesto-sourced evidence
        # Mark existing evidence as non-PDF
        for e in existing_evidence:
            if "page_number" not in e:
                e["page_number"] = None
            if "pdf_url" not in e:
                e["pdf_url"] = None

        return existing_evidence + enriched

    except Exception as exc:
        print(f"    [ERROR] GPT-4o call failed: {exc}")
        return existing_evidence


def process_all(
    client: OpenAI,
    locale_data: dict,
    party_filter: str | None = None,
    question_filter: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Process all questions and parties, enriching evidence with manifesto citations."""

    questions = locale_data["evaluationPage"]["questions_detailed"]
    total = len(questions)
    enriched_count = 0
    api_calls = 0

    for qi, question in enumerate(questions):
        qid = question["id"]
        if question_filter is not None and qid != question_filter:
            continue

        print(f"\n[Q{qid:02d}/{total}] {question['q'][:80]}...")

        for stance in ["pro", "neutral", "contra", "not_given"]:
            parties = question.get("positions", {}).get(stance, {}).get("parties", {})
            if not parties:
                continue

            for party_name, entry in parties.items():
                party_key = PARTY_NAME_TO_KEY.get(party_name)
                if not party_key:
                    continue
                if party_filter and party_key != party_filter:
                    continue

                reasoning = entry.get("reasoning", "") if isinstance(entry, dict) else ""
                existing_evidence = entry.get("evidence_chunks", []) if isinstance(entry, dict) else []

                # Load manifesto pages for this party
                manifesto_pages = load_manifesto_pages(party_key)
                if not manifesto_pages:
                    print(f"  [{party_key}] No manifesto pages available, skipping")
                    continue

                # Pre-filter relevant pages
                relevant = find_relevant_pages(
                    question["q"], reasoning, existing_evidence, manifesto_pages, party_key
                )

                if not relevant:
                    print(f"  [{party_key}] No keyword matches in manifestos")
                    continue

                print(f"  [{party_key}] {len(relevant)} relevant pages found (top score: {relevant[0]['_score']})")

                if dry_run:
                    continue

                # Call GPT-4o for enrichment
                enriched_chunks = enrich_with_gpt4o(
                    client, question, party_name, party_key,
                    stance, reasoning, existing_evidence, relevant
                )

                # Update the entry
                if isinstance(entry, dict):
                    entry["evidence_chunks"] = enriched_chunks
                else:
                    parties[party_name] = {
                        "reasoning": entry if isinstance(entry, str) else "",
                        "evidence_chunks": enriched_chunks,
                    }

                new_chunks = len(enriched_chunks) - len(existing_evidence)
                if new_chunks > 0:
                    enriched_count += new_chunks
                    print(f"  [{party_key}] +{new_chunks} manifesto citations added")

                api_calls += 1
                # Rate limiting
                if api_calls % 5 == 0:
                    time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Enrichment complete: {enriched_count} new manifesto citations added")
    print(f"API calls made: {api_calls}")

    return locale_data


def main():
    parser = argparse.ArgumentParser(description="Enrich evidence with manifesto sources")
    parser.add_argument("--party", type=str, help="Only process this party (e.g., FIDESZ)")
    parser.add_argument("--question", type=int, help="Only process this question ID")
    parser.add_argument("--dry-run", action="store_true", help="Show matches without calling GPT-4o")
    parser.add_argument("--output", type=str, help="Output file path (default: data/enriched_evidence/en_enriched.json)")
    args = parser.parse_args()

    # Load locale data
    print(f"Loading locale data from {LOCALE_FILE}...")
    with open(LOCALE_FILE, encoding="utf-8") as f:
        locale_data = json.load(f)

    questions = locale_data["evaluationPage"]["questions_detailed"]
    print(f"Found {len(questions)} questions")

    # Check manifesto pages exist
    if not PAGES_DIR.exists():
        print("ERROR: Run extract_manifesto_pages.py first!")
        sys.exit(1)

    # Initialize OpenAI client
    from dotenv import load_dotenv
    load_dotenv(BACKEND_ROOT / ".env")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    client = OpenAI(api_key=api_key) if not args.dry_run else None

    # Run enrichment
    enriched = process_all(
        client=client,
        locale_data=locale_data,
        party_filter=args.party,
        question_filter=args.question,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("\nDry run complete — no changes made")
        return

    # Save output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output) if args.output else OUTPUT_DIR / "en_enriched.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"\nEnriched data written to {output_path}")


if __name__ == "__main__":
    main()
