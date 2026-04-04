#!/usr/bin/env python3
"""Extract page-level text from all Hungarian party manifesto PDFs.

Outputs a JSON index: {party_key: [{page: N, text: "..."}, ...]}
Uses both the backend assets/manifestos/ PDFs and the richer compiled PDFs
from HungaryElections2026/ when available.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pdfplumber

# Paths
BACKEND_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = BACKEND_ROOT / "assets" / "manifestos"
FRONTEND_ROOT = BACKEND_ROOT.parent / "ElectOMate-Frontend"
HU_ELECTIONS_DIR = FRONTEND_ROOT / "HungaryElections2026"

# Map party keys to ALL available PDFs (original + compiled)
# Each entry: (pdf_path, label, is_original)
# is_original=True means it's an authentic party document (Hungarian)
# is_original=False means it's a compiled research summary
PARTY_PDF_SOURCES: dict[str, list[tuple[Path, str, bool]]] = {
    "FIDESZ": [
        (HU_ELECTIONS_DIR / "Fidesz_KDNP_compiled_manifesto.pdf", "Fidesz-KDNP összefoglaló", False),
    ],
    "TISZA": [
        (HU_ELECTIONS_DIR / "tisza_manifesto.pdf", "A Működő és Emberséges Magyarország Alapjai", True),
        (HU_ELECTIONS_DIR / "TISZA_compiled_manifesto.pdf", "TISZA összefoglaló", False),
    ],
    "DK": [
        (HU_ELECTIONS_DIR / "dk_program.pdf", "DK 135 pontos program", True),
        (HU_ELECTIONS_DIR / "DK_compiled_program.pdf", "DK összefoglaló", False),
    ],
    "MI_HAZANK": [
        (HU_ELECTIONS_DIR / "virradat2.pdf", "Virradat 2.0 program", True),
        (HU_ELECTIONS_DIR / "Mi_Hazank_compiled_program.pdf", "Mi Hazánk összefoglaló", False),
    ],
    "MKKP": [
        (HU_ELECTIONS_DIR / "Magyar_Ketfarku_Kutya_Part_MKKP_program.pdf", "MKKP program", False),
    ],
    "JOBBIK": [
        (HU_ELECTIONS_DIR / "Jobbik_compiled_positions.pdf", "Jobbik pozíciók", False),
    ],
    "MSZP": [
        (HU_ELECTIONS_DIR / "MSZP_compiled_positions.pdf", "MSZP pozíciók", False),
    ],
}

# Map to served PDF filenames for the frontend
PARTY_SERVED_PDFS: dict[str, list[dict]] = {
    "FIDESZ": [{"filename": "Fidesz_KDNP_compiled_manifesto.pdf", "label": "Fidesz-KDNP összefoglaló", "is_original": False}],
    "TISZA": [
        {"filename": "tisza_manifesto.pdf", "label": "A Működő és Emberséges Magyarország Alapjai", "is_original": True},
        {"filename": "TISZA_compiled_manifesto.pdf", "label": "TISZA összefoglaló", "is_original": False},
    ],
    "DK": [
        {"filename": "dk_program.pdf", "label": "DK 135 pontos program", "is_original": True},
        {"filename": "DK_compiled_program.pdf", "label": "DK összefoglaló", "is_original": False},
    ],
    "MI_HAZANK": [
        {"filename": "virradat2.pdf", "label": "Virradat 2.0 program", "is_original": True},
        {"filename": "Mi_Hazank_compiled_program.pdf", "label": "Mi Hazánk összefoglaló", "is_original": False},
    ],
    "MKKP": [{"filename": "Magyar_Ketfarku_Kutya_Part_MKKP_program.pdf", "label": "MKKP program", "is_original": False}],
    "JOBBIK": [{"filename": "Jobbik_compiled_positions.pdf", "label": "Jobbik pozíciók", "is_original": False}],
    "MSZP": [{"filename": "MSZP_compiled_positions.pdf", "label": "MSZP pozíciók", "is_original": False}],
}


def extract_pages(pdf_path: Path) -> list[dict]:
    """Extract text per page from a PDF."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append({"page": i, "text": text})
    return pages


def main():
    output_dir = BACKEND_ROOT / "data" / "manifesto_pages"
    output_dir.mkdir(parents=True, exist_ok=True)

    index: dict[str, dict] = {}

    for party_key, pdf_entries in PARTY_PDF_SOURCES.items():
        party_docs = []

        for pdf_path, label, is_original in pdf_entries:
            if not pdf_path.exists():
                print(f"  [SKIP] {party_key}/{pdf_path.name}: not found")
                continue

            print(f"  [OK] {party_key}: extracting {pdf_path.name} ({'original' if is_original else 'compiled'})")
            pages = extract_pages(pdf_path)
            total_chars = sum(len(p["text"]) for p in pages)
            print(f"       → {len(pages)} pages, {total_chars} chars")

            party_docs.append({
                "pdf_filename": pdf_path.name,
                "label": label,
                "is_original": is_original,
                "total_pages": len(pages),
                "total_chars": total_chars,
                "pages": pages,
            })

        if not party_docs:
            print(f"  [SKIP] {party_key}: no PDFs found at all")
            continue

        index[party_key] = {
            "served_pdfs": PARTY_SERVED_PDFS[party_key],
            "documents": party_docs,
        }

    # Write individual party files
    for party_key, data in index.items():
        party_file = output_dir / f"{party_key}_pages.json"
        with open(party_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  [WROTE] {party_file.name}")

    # Write combined summary (no full text)
    summary = {}
    for party, data in index.items():
        summary[party] = {
            "served_pdfs": data["served_pdfs"],
            "documents": [
                {
                    "pdf_filename": d["pdf_filename"],
                    "label": d["label"],
                    "is_original": d["is_original"],
                    "total_pages": d["total_pages"],
                    "total_chars": d["total_chars"],
                }
                for d in data["documents"]
            ],
        }
    summary_file = output_dir / "index.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n  Summary written to {summary_file}")
    print(f"  Total: {len(index)} parties, {sum(len(d['documents']) for d in index.values())} documents")

    return index


if __name__ == "__main__":
    result = main()
