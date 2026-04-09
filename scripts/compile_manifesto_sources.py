#!/usr/bin/env python3
"""
Compile verbatim party source excerpts into Markdown and PDF documents.

Usage:
    python scripts/compile_manifesto_sources.py FIDESZ JOBBIK MSZP MKKP
    python scripts/compile_manifesto_sources.py  # compiles all 4
"""

import json
import sys
from pathlib import Path
from datetime import date

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = REPO_ROOT / "assets" / "manifestos" / "sources"
MD_OUTPUT_DIR = REPO_ROOT / "assets" / "manifestos" / "compiled_markdown"
PDF_OUTPUT_DIR = REPO_ROOT / "assets" / "manifestos"

DEFAULT_PARTIES = ["FIDESZ", "JOBBIK", "MSZP", "MKKP"]


def load_excerpts(party_key: str) -> dict:
    """Load excerpts.json for a party."""
    path = SOURCES_DIR / party_key.lower() / "excerpts.json"
    if not path.exists():
        raise FileNotFoundError(f"No excerpts.json found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_markdown(data: dict, output_path: Path) -> str:
    """Generate Markdown from structured excerpts. Returns the markdown string."""
    lines: list[str] = []

    # Title
    lines.append(f"# {data['party_name']} — Hivatalos források alapján")
    lines.append("")
    lines.append(f"**Összeállítva:** {data['compilation_date']}")
    lines.append("")

    # Disclaimer
    lines.append("> **FONTOS MEGJEGYZÉS**")
    lines.append(">")
    for disclaimer_line in data["disclaimer"].split(". "):
        disclaimer_line = disclaimer_line.strip()
        if disclaimer_line and not disclaimer_line.endswith("."):
            disclaimer_line += "."
        if disclaimer_line:
            lines.append(f"> {disclaimer_line}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Build source lookup
    source_map = {s["id"]: s for s in data.get("sources_used", [])}

    # Table of contents
    lines.append("## Tartalomjegyzék")
    lines.append("")
    for i, section in enumerate(data.get("sections", []), 1):
        topic = section["topic"]
        topic_en = section.get("topic_en", "")
        anchor = topic.lower().replace(" ", "-").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ö", "o").replace("ő", "o").replace("ú", "u").replace("ü", "u").replace("ű", "u")
        suffix = f" ({topic_en})" if topic_en else ""
        lines.append(f"{i}. [{topic}{suffix}](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections
    for section in data.get("sections", []):
        topic = section["topic"]
        topic_en = section.get("topic_en", "")
        suffix = f" ({topic_en})" if topic_en else ""
        lines.append(f"## {topic}{suffix}")
        lines.append("")

        for excerpt in section.get("excerpts", []):
            # Excerpt text as blockquote
            text = excerpt["text"].strip()
            for text_line in text.split("\n"):
                lines.append(f"> {text_line}")
            lines.append(">")

            # Source citation
            source_id = excerpt.get("source_id", "")
            source = source_map.get(source_id, {})
            source_name = source.get("name", excerpt.get("source_name", "Ismeretlen forrás"))
            source_date = source.get("date", excerpt.get("source_date", ""))
            source_url = source.get("url", excerpt.get("source_url", ""))
            page_info = excerpt.get("page_or_timestamp", "")

            citation_parts = [f"**Forrás:** {source_name}"]
            if source_date:
                citation_parts.append(f"{source_date}")
            if page_info:
                citation_parts.append(f"{page_info}")
            if source_url:
                citation_parts.append(f"[Link]({source_url})")

            lines.append(f"*{' | '.join(citation_parts)}*")
            lines.append("")

            # Context note if present
            if excerpt.get("context"):
                lines.append(f"*Kontextus: {excerpt['context']}*")
                lines.append("")

        lines.append("---")
        lines.append("")

    # Source bibliography
    lines.append("## Forrásjegyzék")
    lines.append("")
    for i, source in enumerate(data.get("sources_used", []), 1):
        name = source.get("name", "")
        src_date = source.get("date", "")
        url = source.get("url", "")
        src_type = source.get("type", "")

        entry = f"{i}. **{name}**"
        if src_date:
            entry += f" ({src_date})"
        if src_type:
            entry += f" — *{src_type}*"
        if url:
            entry += f" — [{url}]({url})"
        lines.append(entry)
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Összeállítva: {data['compilation_date']} | Ez nem hivatalos pártprogram.*")

    md_content = "\n".join(lines)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"  Markdown: {output_path}")
    return md_content


def generate_pdf(data: dict, output_path: Path) -> None:
    """Generate PDF from structured excerpts via weasyprint."""
    from weasyprint import HTML

    source_map = {s["id"]: s for s in data.get("sources_used", [])}

    # Build HTML
    html_parts: list[str] = []
    html_parts.append("""<!DOCTYPE html>
<html lang="hu">
<head>
<meta charset="UTF-8">
<style>
@page {
    size: A4;
    margin: 2.5cm 2cm 3cm 2cm;
    @bottom-center {
        content: "Összeállítva: """ + data['compilation_date'] + """ | Ez nem hivatalos pártprogram — " counter(page) ". oldal";
        font-size: 8pt;
        color: #666;
        font-family: 'DejaVu Sans', 'Noto Sans', sans-serif;
    }
}
body {
    font-family: 'DejaVu Sans', 'Noto Sans', 'Helvetica Neue', sans-serif;
    font-size: 10pt;
    line-height: 1.5;
    color: #1a1a1a;
}
h1 {
    font-size: 18pt;
    color: #1a1a1a;
    margin-bottom: 5pt;
    text-align: center;
}
.subtitle {
    text-align: center;
    font-size: 11pt;
    color: #555;
    margin-bottom: 20pt;
}
.disclaimer {
    background: #f0f0f0;
    border: 1px solid #ccc;
    border-left: 4px solid #d32f2f;
    padding: 12pt 15pt;
    margin: 15pt 0 25pt 0;
    font-size: 9pt;
    line-height: 1.4;
    color: #333;
}
.disclaimer strong {
    color: #d32f2f;
}
h2 {
    font-size: 14pt;
    color: #2c3e50;
    border-bottom: 2px solid #2c3e50;
    padding-bottom: 4pt;
    margin-top: 25pt;
    page-break-after: avoid;
}
.excerpt {
    background: #fafafa;
    border-left: 3px solid #3498db;
    padding: 8pt 12pt;
    margin: 10pt 0 4pt 0;
    font-size: 10pt;
    line-height: 1.5;
}
.citation {
    font-size: 8pt;
    color: #777;
    font-style: italic;
    margin: 2pt 0 12pt 12pt;
}
.context {
    font-size: 8.5pt;
    color: #888;
    font-style: italic;
    margin: 2pt 0 8pt 12pt;
}
.toc {
    margin: 15pt 0;
}
.toc-item {
    font-size: 10pt;
    margin: 3pt 0;
}
.toc-item a {
    color: #2c3e50;
    text-decoration: none;
}
a, a:link, a:visited, a:hover, a:active {
    color: #555 !important;
    text-decoration: underline !important;
}
.citation a, .citation a:link, .citation a:visited,
.bib-entry a, .bib-entry a:link, .bib-entry a:visited {
    color: #555 !important;
    text-decoration: underline !important;
}
.bib-entry {
    font-size: 9pt;
    margin: 4pt 0;
    line-height: 1.4;
}
.url {
    color: #555;
    word-break: break-all;
}
.page-break {
    page-break-before: always;
}
hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 15pt 0;
}
</style>
</head>
<body>
""")

    # Title
    html_parts.append(f"<h1>{_esc(data['party_name'])}</h1>")
    html_parts.append('<p class="subtitle">Hivatalos források alapján összeállítva</p>')
    html_parts.append(f'<p class="subtitle">Összeállítva: {data["compilation_date"]}</p>')

    # Disclaimer
    html_parts.append('<div class="disclaimer">')
    html_parts.append(f"<strong>FONTOS MEGJEGYZÉS:</strong> {_esc(data['disclaimer'])}")
    html_parts.append("</div>")

    # TOC
    html_parts.append('<div class="toc">')
    html_parts.append("<h2>Tartalomjegyzék</h2>")
    for i, section in enumerate(data.get("sections", []), 1):
        topic = section["topic"]
        topic_en = section.get("topic_en", "")
        suffix = f" ({topic_en})" if topic_en else ""
        anchor = f"section-{i}"
        html_parts.append(f'<div class="toc-item">{i}. <a href="#{anchor}">{_esc(topic)}{suffix}</a></div>')
    html_parts.append("</div>")
    html_parts.append("<hr>")

    # Sections
    for i, section in enumerate(data.get("sections", []), 1):
        topic = section["topic"]
        topic_en = section.get("topic_en", "")
        suffix = f" ({topic_en})" if topic_en else ""
        anchor = f"section-{i}"

        html_parts.append(f'<h2 id="{anchor}">{i}. {_esc(topic)}{suffix}</h2>')

        for excerpt in section.get("excerpts", []):
            text = excerpt["text"].strip()
            # Preserve paragraph breaks
            paragraphs = text.split("\n\n")
            html_parts.append('<div class="excerpt">')
            for para in paragraphs:
                para_lines = para.strip().split("\n")
                html_parts.append(f"<p>{_esc(chr(10).join(para_lines))}</p>")
            html_parts.append("</div>")

            # Citation
            source_id = excerpt.get("source_id", "")
            source = source_map.get(source_id, {})
            source_name = source.get("name", excerpt.get("source_name", "Ismeretlen forrás"))
            source_date = source.get("date", excerpt.get("source_date", ""))
            source_url = source.get("url", excerpt.get("source_url", ""))
            page_info = excerpt.get("page_or_timestamp", "")

            cite_parts = [f"Forrás: {_esc(source_name)}"]
            if source_date:
                cite_parts.append(source_date)
            if page_info:
                cite_parts.append(page_info)
            if source_url:
                cite_parts.append(f'<span class="url">{_esc(source_url)}</span>')

            html_parts.append(f'<div class="citation">{" | ".join(cite_parts)}</div>')

            if excerpt.get("context"):
                html_parts.append(f'<div class="context">Kontextus: {_esc(excerpt["context"])}</div>')

    # Bibliography
    html_parts.append('<div class="page-break"></div>')
    html_parts.append("<h2>Forrásjegyzék</h2>")
    for i, source in enumerate(data.get("sources_used", []), 1):
        name = source.get("name", "")
        src_date = source.get("date", "")
        url = source.get("url", "")
        src_type = source.get("type", "")

        entry = f"<strong>{_esc(name)}</strong>"
        if src_date:
            entry += f" ({src_date})"
        if src_type:
            entry += f" — <em>{_esc(src_type)}</em>"
        if url:
            entry += f' — <span class="url">{_esc(url)}</span>'
        html_parts.append(f'<div class="bib-entry">{i}. {entry}</div>')

    html_parts.append("</body></html>")

    html_str = "\n".join(html_parts)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_str).write_pdf(str(output_path))
    print(f"  PDF: {output_path}")


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def compile_party(party_key: str) -> None:
    """Full pipeline: load excerpts → markdown → pdf."""
    print(f"\n{'='*60}")
    print(f"Compiling: {party_key}")
    print(f"{'='*60}")

    data = load_excerpts(party_key)

    md_path = MD_OUTPUT_DIR / f"{party_key}_sources.md"
    pdf_path = PDF_OUTPUT_DIR / f"{party_key}.pdf"

    generate_markdown(data, md_path)
    generate_pdf(data, pdf_path)

    # Stats
    sections = data.get("sections", [])
    total_excerpts = sum(len(s.get("excerpts", [])) for s in sections)
    total_sources = len(data.get("sources_used", []))
    print(f"  Topics: {len(sections)} | Excerpts: {total_excerpts} | Sources: {total_sources}")
    print(f"  Done!")


if __name__ == "__main__":
    parties = sys.argv[1:] or DEFAULT_PARTIES
    for party in parties:
        party = party.upper()
        try:
            compile_party(party)
        except FileNotFoundError as e:
            print(f"\n  SKIP {party}: {e}")
        except Exception as e:
            print(f"\n  ERROR {party}: {e}")
            raise
