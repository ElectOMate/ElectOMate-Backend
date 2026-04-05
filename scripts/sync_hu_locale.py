#!/usr/bin/env python3
"""Synchronize Hungarian evaluation page locale data between en.json and hu.json.

Three operations:
A) Copy 396 enriched PDF chunks from en.json → hu.json (missing there)
B) Translate 638 legacy evidence chunk texts EN→HU via GPT-4o in hu.json
C) Swap text/text_en on enriched chunks in en.json (so English users see English first)

Usage:
    python scripts/sync_hu_locale.py [--skip-translate] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = BACKEND_ROOT.parent / "ElectOMate-Frontend"
EN_FILE = FRONTEND_ROOT / "src" / "assets" / "WebsiteContent" / "locales_Hungary" / "en.json"
HU_FILE = FRONTEND_ROOT / "src" / "assets" / "WebsiteContent" / "locales_Hungary" / "hu.json"


def copy_enriched_chunks_to_hu(en_data: dict, hu_data: dict) -> int:
    """Op A: Copy enriched PDF chunks from en.json to hu.json."""
    copied = 0
    en_questions = en_data["evaluationPage"]["questions_detailed"]
    hu_questions = hu_data["evaluationPage"]["questions_detailed"]

    # Build lookup by question id
    hu_by_id = {q["id"]: q for q in hu_questions}

    for en_q in en_questions:
        qid = en_q["id"]
        hu_q = hu_by_id.get(qid)
        if not hu_q:
            print(f"  [WARN] Q{qid} missing in hu.json")
            continue

        for stance in ["pro", "neutral", "contra", "not_given"]:
            en_parties = en_q.get("positions", {}).get(stance, {}).get("parties", {})
            hu_parties = hu_q.get("positions", {}).get(stance, {}).get("parties", {})

            for party_name, en_entry in en_parties.items():
                if not isinstance(en_entry, dict):
                    continue

                # Get enriched chunks from en.json
                en_chunks = en_entry.get("evidence_chunks", [])
                enriched = [c for c in en_chunks if c.get("pdf_url") and c.get("page_number")]
                if not enriched:
                    continue

                # Get or create hu entry
                hu_entry = hu_parties.get(party_name)
                if hu_entry is None:
                    # Party missing in hu.json for this stance — skip
                    continue
                if not isinstance(hu_entry, dict):
                    hu_parties[party_name] = {"reasoning": hu_entry if isinstance(hu_entry, str) else "", "evidence_chunks": []}
                    hu_entry = hu_parties[party_name]

                hu_chunks = hu_entry.get("evidence_chunks", [])

                # Check which enriched chunks are already present (by pdf_url + page_number)
                existing_keys = {
                    (c.get("pdf_url"), c.get("page_number"))
                    for c in hu_chunks
                    if c.get("pdf_url")
                }

                for chunk in enriched:
                    key = (chunk.get("pdf_url"), chunk.get("page_number"))
                    if key not in existing_keys:
                        hu_chunks.append(chunk)
                        copied += 1

                hu_entry["evidence_chunks"] = hu_chunks

    return copied


def collect_legacy_texts(hu_data: dict) -> list[tuple[int, str, str, str, int, str]]:
    """Collect all legacy evidence chunk texts that need translation.

    Returns list of (qid, stance, party_name, chunk_index, text).
    """
    items = []
    for q in hu_data["evaluationPage"]["questions_detailed"]:
        qid = q["id"]
        for stance in ["pro", "neutral", "contra", "not_given"]:
            parties = q.get("positions", {}).get(stance, {}).get("parties", {})
            for party_name, entry in parties.items():
                if not isinstance(entry, dict):
                    continue
                for idx, chunk in enumerate(entry.get("evidence_chunks", [])):
                    # Legacy = no pdf_url
                    if not chunk.get("pdf_url") and chunk.get("text"):
                        items.append((qid, stance, party_name, idx, chunk["text"]))
    return items


def batch_translate(client, texts: list[str], batch_size: int = 15) -> list[str]:
    """Translate English texts to Hungarian in batches via GPT-4o."""
    from openai import OpenAI

    all_translations = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        numbered = "\n".join(f"[{j+1}] {t}" for j, t in enumerate(batch))

        prompt = f"""Translate these English evidence summaries about Hungarian politics into natural Hungarian.
Keep the factual tone and political terminology. Maintain proper nouns (party names, person names, place names) unchanged.
Return ONLY a JSON array of translated strings, in the same order. No markdown.

{numbered}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)

            # Handle {"translations": [...]} or bare [...]
            if isinstance(parsed, dict):
                for v in parsed.values():
                    if isinstance(v, list):
                        parsed = v
                        break

            if isinstance(parsed, list) and len(parsed) == len(batch):
                all_translations.extend(parsed)
            else:
                print(f"    [WARN] Batch {i//batch_size}: got {len(parsed) if isinstance(parsed, list) else 'non-list'}, expected {len(batch)}")
                # Fall back to originals
                all_translations.extend(batch)
        except Exception as exc:
            print(f"    [ERROR] Batch {i//batch_size}: {exc}")
            all_translations.extend(batch)

        # Rate limiting
        if i + batch_size < len(texts):
            time.sleep(0.5)

        if (i // batch_size) % 5 == 0:
            print(f"    Translated {min(i + batch_size, len(texts))}/{len(texts)} chunks...")

    return all_translations


def apply_translations(hu_data: dict, items: list[tuple], translations: list[str]) -> int:
    """Write translated texts back into hu.json."""
    # Build lookup: qid → question
    q_by_id = {q["id"]: q for q in hu_data["evaluationPage"]["questions_detailed"]}

    applied = 0
    for (qid, stance, party_name, chunk_idx, _orig_text), translated in zip(items, translations):
        q = q_by_id.get(qid)
        if not q:
            continue
        entry = q.get("positions", {}).get(stance, {}).get("parties", {}).get(party_name)
        if not isinstance(entry, dict):
            continue
        chunks = entry.get("evidence_chunks", [])
        if chunk_idx < len(chunks):
            chunks[chunk_idx]["text"] = translated
            applied += 1

    return applied


def swap_text_text_en_in_en(en_data: dict) -> int:
    """Op C: Swap text/text_en on enriched chunks in en.json."""
    swapped = 0
    for q in en_data["evaluationPage"]["questions_detailed"]:
        for stance in ["pro", "neutral", "contra", "not_given"]:
            parties = q.get("positions", {}).get(stance, {}).get("parties", {})
            for party_name, entry in parties.items():
                if not isinstance(entry, dict):
                    continue
                for chunk in entry.get("evidence_chunks", []):
                    if chunk.get("pdf_url") and chunk.get("text_en"):
                        # Swap: text (HU) ↔ text_en (EN)
                        hu_text = chunk["text"]
                        en_text = chunk["text_en"]
                        chunk["text"] = en_text       # Now English (primary for EN locale)
                        chunk["text_en"] = hu_text    # Now Hungarian (secondary)
                        swapped += 1
    return swapped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-translate", action="store_true", help="Skip GPT-4o translation of legacy chunks")
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    args = parser.parse_args()

    print("Loading locale files...")
    with open(EN_FILE, encoding="utf-8") as f:
        en_data = json.load(f)
    with open(HU_FILE, encoding="utf-8") as f:
        hu_data = json.load(f)

    # Op A: Copy enriched chunks to hu.json
    print("\n[A] Copying enriched PDF chunks to hu.json...")
    copied = copy_enriched_chunks_to_hu(en_data, hu_data)
    print(f"    Copied {copied} enriched chunks")

    # Op B: Translate legacy chunks in hu.json
    if not args.skip_translate:
        print("\n[B] Collecting legacy evidence texts for translation...")
        items = collect_legacy_texts(hu_data)
        # Deduplicate texts to minimize API calls
        unique_texts = list(dict.fromkeys(t[4] for t in items))
        print(f"    {len(items)} legacy chunks, {len(unique_texts)} unique texts")

        if not args.dry_run and unique_texts:
            from dotenv import load_dotenv
            from openai import OpenAI

            load_dotenv(BACKEND_ROOT / ".env")
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

            print("    Translating via GPT-4o...")
            translations = batch_translate(client, unique_texts)

            # Build lookup: original text → translated text
            translation_map = dict(zip(unique_texts, translations))

            # Map back to full items list
            full_translations = [translation_map[t[4]] for t in items]
            applied = apply_translations(hu_data, items, full_translations)
            print(f"    Applied {applied} translations")
        else:
            print("    Skipped (dry-run or no texts)")
    else:
        print("\n[B] Skipping translation (--skip-translate)")

    # Op C: Swap text/text_en in en.json
    print("\n[C] Swapping text/text_en in en.json for enriched chunks...")
    swapped = swap_text_text_en_in_en(en_data)
    print(f"    Swapped {swapped} chunks")

    # Write output
    if not args.dry_run:
        print("\nWriting files...")
        with open(EN_FILE, "w", encoding="utf-8") as f:
            json.dump(en_data, f, ensure_ascii=False, indent=2)
        print(f"  Wrote {EN_FILE.name} ({EN_FILE.stat().st_size:,} bytes)")

        with open(HU_FILE, "w", encoding="utf-8") as f:
            json.dump(hu_data, f, ensure_ascii=False, indent=2)
        print(f"  Wrote {HU_FILE.name} ({HU_FILE.stat().st_size:,} bytes)")
    else:
        print("\nDry run — no files written")

    print(f"\nSummary: {copied} chunks copied, {swapped} swapped")


if __name__ == "__main__":
    main()
