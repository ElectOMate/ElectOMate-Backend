"""Connector for extracting text from Hungarian political party manifesto PDFs."""

from __future__ import annotations

from pathlib import Path

import pdfplumber
import structlog

from em_backend.config.manifesto_urls import LOCAL_MANIFESTO_DIR, MANIFESTO_LOCAL_NAMES
from em_backend.graph.connectors.base import (
    IngestedDocument,
    Modality,
    SourceType,
    TextSegment,
)

logger = structlog.get_logger(__name__)

# Hungarian party shortnames that have local manifesto PDFs.
HUNGARIAN_PARTIES: list[str] = [
    "FIDESZ",
    "TISZA",
    "DK",
    "MI_HAZANK",
    "MKKP",
    "JOBBIK",
    "MSZP",
]


def extract_manifesto(
    pdf_path: str | Path,
    party_shortname: str,
) -> IngestedDocument:
    """Extract text from a single manifesto PDF, one segment per page.

    Args:
        pdf_path: Path to the PDF file.
        party_shortname: ASCII key for the party (e.g. ``"FIDESZ"``).

    Returns:
        An ``IngestedDocument`` with one ``TextSegment`` per page.

    Raises:
        FileNotFoundError: If *pdf_path* does not exist.
        RuntimeError: If pdfplumber cannot open or parse the PDF.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Manifesto PDF not found: {pdf_path}")

    log = logger.bind(party=party_shortname, path=str(pdf_path))
    log.info("extracting_manifesto")

    segments: list[TextSegment] = []
    raw_parts: list[str] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                if not text:
                    log.debug("empty_page", page=page_num)
                    continue
                segments.append(
                    TextSegment(
                        text=text,
                        page_number=page_num,
                        metadata={"party": party_shortname},
                    )
                )
                raw_parts.append(text)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to parse manifesto PDF for {party_shortname}: {exc}"
        ) from exc

    doc = IngestedDocument(
        source_type=SourceType.MANIFESTO,
        modality=Modality.PDF,
        source_path=str(pdf_path),
        title=f"{party_shortname} manifesto",
        language="hu",
        segments=segments,
        raw_text="\n\n".join(raw_parts),
        metadata={"party_shortname": party_shortname, "total_pages": len(segments)},
    )

    log.info(
        "manifesto_extracted",
        pages=len(segments),
        chars=len(doc.raw_text),
    )
    return doc


def extract_all_hungarian_manifestos() -> list[IngestedDocument]:
    """Extract text from all 7 Hungarian party manifesto PDFs.

    Skips any PDF that is missing or fails to parse, logging the error
    rather than aborting the entire batch.

    Returns:
        A list of ``IngestedDocument`` objects (one per successfully parsed PDF).
    """
    documents: list[IngestedDocument] = []

    for party_key in HUNGARIAN_PARTIES:
        filename = MANIFESTO_LOCAL_NAMES.get(party_key)
        if filename is None:
            logger.warning("no_filename_mapping", party=party_key)
            continue

        pdf_path = LOCAL_MANIFESTO_DIR / filename

        try:
            doc = extract_manifesto(pdf_path, party_shortname=party_key)
            documents.append(doc)
        except (FileNotFoundError, RuntimeError) as exc:
            logger.error("manifesto_skipped", party=party_key, error=str(exc))

    logger.info(
        "all_hungarian_manifestos_done",
        total=len(documents),
        parties=[d.metadata["party_shortname"] for d in documents],
    )
    return documents
