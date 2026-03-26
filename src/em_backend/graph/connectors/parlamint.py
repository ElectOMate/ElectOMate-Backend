"""Connector for the ParlaMint HU parliamentary speech corpus.

Loads Hungarian parliamentary speech data (interpellations, urgent questions)
from the ParlaMint corpus (TEI XML format).

Corpus: https://github.com/poltextlab/CLARIN_ParlaMint_HU
- Terms 7 and 8 (May 2014 - December 2020)
- 3,086 speeches, 1,114,495 words
- TEI XML with speaker metadata, party affiliation, speech text
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import structlog
from lxml import etree

from em_backend.graph.connectors.base import (
    IngestedDocument,
    Modality,
    SourceType,
    SpeakerInfo,
    TextSegment,
)

logger = structlog.get_logger(__name__)

PARLAMINT_REPO_URL = "https://github.com/poltextlab/CLARIN_ParlaMint_HU.git"

# TEI XML namespaces used in ParlaMint files
TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"tei": TEI_NS, "xml": XML_NS}

# Mapping of Hungarian party abbreviations/variants to standard shortnames
PARTY_SHORTNAME_MAP: dict[str, str] = {
    "fidesz": "FIDESZ",
    "fidesz-kdnp": "FIDESZ",
    "fidesz-magyar polgári szövetség": "FIDESZ",
    "kdnp": "KDNP",
    "mszp": "MSZP",
    "jobbik": "JOBBIK",
    "jobbik magyarországért mozgalom": "JOBBIK",
    "lmp": "LMP",
    "lehet más a politika": "LMP",
    "dk": "DK",
    "demokratikus koalíció": "DK",
    "momentum": "MOMENTUM",
    "párbeszéd": "PARBESZED",
    "dialogue": "PARBESZED",
    "mi hazánk": "MI_HAZANK",
    "mi hazánk mozgalom": "MI_HAZANK",
    "mkkp": "MKKP",
    "independent": "INDEPENDENT",
    "független": "INDEPENDENT",
}


def _normalize_party(raw: str | None) -> str | None:
    """Normalize a party name/abbreviation to a standard shortname."""
    if not raw:
        return None
    key = raw.strip().lower()
    if key in PARTY_SHORTNAME_MAP:
        return PARTY_SHORTNAME_MAP[key]
    # Try prefix matching for compound names like "Fidesz-KDNP"
    for prefix, shortname in PARTY_SHORTNAME_MAP.items():
        if key.startswith(prefix):
            return shortname
    logger.debug("unknown_party_abbreviation", raw=raw)
    return raw.strip().upper()


def _extract_text(element: etree._Element) -> str:
    """Extract all text content from an element, including tail text of children."""
    return "".join(element.itertext()).strip()


def _parse_date(date_str: str | None) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD) into a date object."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        logger.warning("unparseable_date", date_str=date_str)
        return None


def _build_speaker_map(header: etree._Element) -> dict[str, SpeakerInfo]:
    """Build a mapping from speaker IDs to SpeakerInfo from <listPerson>.

    Searches for <person> elements in <listPerson> within the TEI header
    and extracts name, party affiliation, and role.
    """
    speaker_map: dict[str, SpeakerInfo] = {}

    for person in header.iter(f"{{{TEI_NS}}}person"):
        person_id = person.get(f"{{{XML_NS}}}id", "")
        if not person_id:
            continue

        # Extract name — try <persName> first
        name = ""
        pers_name = person.find(f".//{{{TEI_NS}}}persName", NS)
        if pers_name is not None:
            # May have <surname> and <forename> children
            surname = pers_name.findtext(f"{{{TEI_NS}}}surname", default="")
            forename = pers_name.findtext(f"{{{TEI_NS}}}forename", default="")
            if surname or forename:
                name = f"{surname} {forename}".strip()
            else:
                name = _extract_text(pers_name)
        if not name:
            name = person_id

        # Extract party affiliation from <affiliation>
        party_raw: str | None = None
        for affiliation in person.findall(f".//{{{TEI_NS}}}affiliation", NS):
            role_attr = affiliation.get("role", "")
            if role_attr == "member" or not role_attr:
                ref = affiliation.get("ref", "")
                if ref.startswith("#"):
                    party_raw = ref[1:]
                elif ref:
                    party_raw = ref
                else:
                    party_raw = affiliation.text
                break

        # Extract role (e.g., MP, minister)
        role: str | None = None
        for affiliation in person.findall(f".//{{{TEI_NS}}}affiliation", NS):
            role_attr = affiliation.get("role", "")
            if role_attr and role_attr != "member":
                role = role_attr
                break

        speaker_map[f"#{person_id}"] = SpeakerInfo(
            name=name,
            party=_normalize_party(party_raw),
            role=role,
            party_at_time=_normalize_party(party_raw),
        )

    logger.debug("speaker_map_built", count=len(speaker_map))
    return speaker_map


def _parse_org_names(header: etree._Element) -> dict[str, str]:
    """Parse <listOrg> to map org IDs to readable party names."""
    org_map: dict[str, str] = {}
    for org in header.iter(f"{{{TEI_NS}}}org"):
        org_id = org.get(f"{{{XML_NS}}}id", "")
        if not org_id:
            continue
        org_name_el = org.find(f"{{{TEI_NS}}}orgName", NS)
        if org_name_el is not None and org_name_el.text:
            org_map[org_id] = org_name_el.text.strip()
    return org_map


def download_parlamint_corpus(target_dir: str | Path) -> Path:
    """Clone the ParlaMint HU corpus from GitHub.

    Args:
        target_dir: Directory where the repo will be cloned into.

    Returns:
        Path to the cloned repository root.
    """
    target = Path(target_dir)
    repo_dir = target / "CLARIN_ParlaMint_HU"

    if repo_dir.exists() and (repo_dir / ".git").exists():
        logger.info("parlamint_corpus_already_exists", path=str(repo_dir))
        # Pull latest changes
        try:
            subprocess.run(
                ["git", "-C", str(repo_dir), "pull", "--ff-only"],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            logger.info("parlamint_corpus_updated", path=str(repo_dir))
        except subprocess.SubprocessError as exc:
            logger.warning("parlamint_pull_failed", error=str(exc))
        return repo_dir

    target.mkdir(parents=True, exist_ok=True)
    logger.info("cloning_parlamint_corpus", url=PARLAMINT_REPO_URL, target=str(target))

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", PARLAMINT_REPO_URL, str(repo_dir)],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.SubprocessError as exc:
        logger.error("parlamint_clone_failed", error=str(exc))
        raise RuntimeError(f"Failed to clone ParlaMint corpus: {exc}") from exc

    logger.info("parlamint_corpus_cloned", path=str(repo_dir))
    return repo_dir


def parse_tei_file(xml_path: str | Path) -> list[IngestedDocument]:
    """Parse a single ParlaMint TEI XML file into IngestedDocuments.

    Each <u> (utterance) element becomes one IngestedDocument, with its
    <seg> children becoming TextSegments.

    Args:
        xml_path: Path to the TEI XML file.

    Returns:
        List of IngestedDocument instances, one per utterance.
    """
    xml_path = Path(xml_path)
    if not xml_path.exists():
        logger.error("tei_file_not_found", path=str(xml_path))
        return []

    try:
        tree = etree.parse(str(xml_path))  # noqa: S320
    except etree.XMLSyntaxError as exc:
        logger.error("tei_xml_parse_error", path=str(xml_path), error=str(exc))
        return []

    root = tree.getroot()

    # Handle namespaced and non-namespaced TEI files
    if root.tag == f"{{{TEI_NS}}}TEI" or root.tag == "TEI":
        tei_root = root
    elif root.tag == f"{{{TEI_NS}}}teiCorpus" or root.tag == "teiCorpus":
        # Corpus file — may contain multiple <TEI> elements
        tei_elements = root.findall(f"{{{TEI_NS}}}TEI", NS) or root.findall("TEI")
        documents: list[IngestedDocument] = []
        for tei_el in tei_elements:
            documents.extend(_parse_single_tei(tei_el, xml_path))
        return documents
    else:
        logger.warning("unexpected_root_element", tag=root.tag, path=str(xml_path))
        tei_root = root

    return _parse_single_tei(tei_root, xml_path)


def _parse_single_tei(
    tei_root: etree._Element, xml_path: Path
) -> list[IngestedDocument]:
    """Parse a single <TEI> element into IngestedDocuments."""
    documents: list[IngestedDocument] = []

    # Extract header metadata
    header = tei_root.find(f"{{{TEI_NS}}}teiHeader", NS)
    if header is None:
        header = tei_root.find("teiHeader")
    if header is None:
        logger.warning("no_tei_header", path=str(xml_path))
        header = etree.Element("teiHeader")  # empty placeholder

    # Build speaker lookup
    speaker_map = _build_speaker_map(header)
    org_map = _parse_org_names(header)

    # Extract session/document title
    title_el = header.find(f".//{{{TEI_NS}}}title", NS)
    if title_el is None:
        title_el = header.find(".//title")
    doc_title = _extract_text(title_el) if title_el is not None else xml_path.stem

    # Extract session date from <setting><date>
    session_date: date | None = None
    date_el = header.find(f".//{{{TEI_NS}}}date", NS)
    if date_el is None:
        date_el = header.find(".//date")
    if date_el is not None:
        session_date = _parse_date(
            date_el.get("when") or date_el.get("from") or date_el.text
        )

    # Find the body with utterances
    body = tei_root.find(f".//{{{TEI_NS}}}body", NS)
    if body is None:
        body = tei_root.find(".//body")
    if body is None:
        logger.warning("no_body_element", path=str(xml_path))
        return documents

    # Process each utterance <u>
    for utterance in body.iter(f"{{{TEI_NS}}}u"):
        _process_utterance(
            utterance=utterance,
            speaker_map=speaker_map,
            org_map=org_map,
            session_date=session_date,
            doc_title=doc_title,
            xml_path=xml_path,
            documents=documents,
        )

    # Also check for non-namespaced <u> elements
    if not documents:
        for utterance in body.iter("u"):
            _process_utterance(
                utterance=utterance,
                speaker_map=speaker_map,
                org_map=org_map,
                session_date=session_date,
                doc_title=doc_title,
                xml_path=xml_path,
                documents=documents,
            )

    logger.debug(
        "tei_file_parsed",
        path=str(xml_path),
        utterance_count=len(documents),
    )
    return documents


def _process_utterance(
    *,
    utterance: etree._Element,
    speaker_map: dict[str, SpeakerInfo],
    org_map: dict[str, str],
    session_date: date | None,
    doc_title: str,
    xml_path: Path,
    documents: list[IngestedDocument],
) -> None:
    """Process a single <u> utterance element into an IngestedDocument."""
    who = utterance.get("who", "")
    utterance_id = utterance.get(f"{{{XML_NS}}}id", utterance.get("id", ""))

    # Resolve speaker
    speaker_info = speaker_map.get(who)
    if speaker_info is None and who:
        # Create a minimal speaker entry from the @who attribute
        speaker_name = who.lstrip("#").replace(".", " ").replace("_", " ")
        speaker_info = SpeakerInfo(name=speaker_name)

    # Extract segments from <seg> children
    segments: list[TextSegment] = []
    seg_elements = utterance.findall(f"{{{TEI_NS}}}seg", NS) or utterance.findall(
        "seg"
    )

    if seg_elements:
        for idx, seg in enumerate(seg_elements):
            text = _extract_text(seg)
            if text:
                segments.append(
                    TextSegment(
                        text=text,
                        speaker=speaker_info.name if speaker_info else None,
                        paragraph_index=idx,
                        metadata={
                            "seg_id": seg.get(f"{{{XML_NS}}}id", seg.get("id", "")),
                        },
                    )
                )
    else:
        # No <seg> children — use the utterance text directly
        text = _extract_text(utterance)
        if text:
            segments.append(
                TextSegment(
                    text=text,
                    speaker=speaker_info.name if speaker_info else None,
                    paragraph_index=0,
                )
            )

    if not segments:
        return

    raw_text = "\n\n".join(seg.text for seg in segments)

    # Build utterance-level metadata
    metadata: dict[str, Any] = {
        "utterance_id": utterance_id,
        "source_file": xml_path.name,
    }
    ana = utterance.get("ana", "")
    if ana:
        metadata["speech_type"] = ana

    speakers: list[SpeakerInfo] = []
    if speaker_info:
        speakers.append(speaker_info)

    utterance_title = f"{doc_title} - {speaker_info.name}" if speaker_info else doc_title

    documents.append(
        IngestedDocument(
            source_type=SourceType.SPEECH,
            modality=Modality.XML,
            source_url=PARLAMINT_REPO_URL,
            source_path=str(xml_path),
            title=utterance_title,
            date=session_date,
            language="hu",
            speakers=speakers,
            segments=segments,
            raw_text=raw_text,
            metadata=metadata,
        )
    )


def load_parlamint_corpus(
    corpus_dir: str | Path,
    limit: int | None = None,
) -> list[IngestedDocument]:
    """Load all TEI XML files from a ParlaMint corpus directory.

    Args:
        corpus_dir: Root directory of the ParlaMint corpus (the cloned repo).
        limit: Maximum number of documents to return. None for all.

    Returns:
        List of IngestedDocument instances from all parsed files.
    """
    corpus_path = Path(corpus_dir)
    if not corpus_path.exists():
        logger.error("corpus_dir_not_found", path=str(corpus_path))
        return []

    # ParlaMint files are typically in the root or a subdirectory
    xml_files = sorted(corpus_path.rglob("*.xml"))

    # Filter out schema/XSLT files and keep only TEI content files
    xml_files = [
        f
        for f in xml_files
        if not f.name.startswith(".")
        and "schema" not in f.name.lower()
        and f.suffix == ".xml"
    ]

    if not xml_files:
        logger.warning("no_xml_files_found", path=str(corpus_path))
        return []

    logger.info("loading_parlamint_corpus", file_count=len(xml_files))

    all_documents: list[IngestedDocument] = []

    for xml_file in xml_files:
        docs = parse_tei_file(xml_file)
        all_documents.extend(docs)

        if limit is not None and len(all_documents) >= limit:
            all_documents = all_documents[:limit]
            logger.info("document_limit_reached", limit=limit)
            break

    logger.info(
        "parlamint_corpus_loaded",
        total_documents=len(all_documents),
        total_files_processed=len(xml_files),
    )
    return all_documents
