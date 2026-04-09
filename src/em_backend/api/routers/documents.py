import asyncio
import json
from io import BytesIO
from pathlib import Path
from typing import Annotated, cast
from uuid import UUID

import httpx
from docling.datamodel.base_models import QualityGrade
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import get_logger

from em_backend.api.routers.v2 import (
    get_database_session,
    get_document_parser,
    get_sessionmaker,
    get_vector_database,
)
from ipaddress import ip_address
from urllib.parse import urlparse

from em_backend.config.manifesto_urls import (
    LOCAL_MANIFESTO_DIR,
    MANIFESTO_LOCAL_NAMES,
    MANIFESTO_URLS,
    PARTY_SHORTNAME_TO_MANIFESTO_KEY,
)
from em_backend.database.crud import document as document_crud
from em_backend.database.models import Document, Election, Party
from em_backend.models.crud import (
    DocumentResponse,
    DocumentResponseWithContent,
    DocumentUpdate,
)
from em_backend.models.enums import (
    IndexingSuccess,
    ParsingQuality,
    SupportedDocumentFormats,
)
from em_backend.services.pdf_bbox_extractor import PDFBboxExtractor
from em_backend.vector.db import VectorDatabase
from em_backend.vector.parser import DocumentParser

logger = get_logger()

DOCUMENT_TYPE_MAPPING = {
    "pdf": SupportedDocumentFormats.PDF,
    "docx": SupportedDocumentFormats.DOCX,
    "xlsx": SupportedDocumentFormats.XLSX,
    "pptx": SupportedDocumentFormats.PPTX,
    "md": SupportedDocumentFormats.MARKDOWN,
    "txt": SupportedDocumentFormats.ASCII,
    "html": SupportedDocumentFormats.HTML,
    "xhtml": SupportedDocumentFormats.XHTML,
    "csv": SupportedDocumentFormats.CSV,
}

PARSING_QUALITY_MAPPING = {
    QualityGrade.EXCELLENT: ParsingQuality.EXCELLENT,
    QualityGrade.FAIR: ParsingQuality.FAIR,
    QualityGrade.GOOD: ParsingQuality.GOOD,
    QualityGrade.POOR: ParsingQuality.POOR,
    QualityGrade.UNSPECIFIED: ParsingQuality.UNSPECIFIED,
}


async def process_document(
    document_id: UUID,
    file_content: BytesIO,
    sessionmaker: async_sessionmaker[AsyncSession],
    weaviate_database: VectorDatabase,
    document_parser: DocumentParser,
    callback_url: str | None = None,
    country_code: str | None = None,
    party_name: str | None = None,
) -> None:
    logger.info(f"Processing document {document_id}")

    try:
        # Step 1: Wait for document to appear in database and mark as processing
        # Keep this connection short - just for initial setup
        sleep_seconds = 1
        async with sessionmaker() as session:
            document_view: Document | None = None
            while document_view is None:
                document_view = await session.get(Document, document_id)
                if document_view is None:
                    if sleep_seconds > 32:
                        raise ValueError("Could not fetch document in the database.")
                    await asyncio.sleep(sleep_seconds)
                    sleep_seconds *= 2

            document_view.parsing_quality = ParsingQuality.FAILED
            document_view.indexing_success = IndexingSuccess.NO_INDEXING
            await session.commit()

            # Refresh object to load all attributes before session closes
            await session.refresh(document_view)

            # Get document title before closing session
            document_title = document_view.title
        # ← DB connection closed after ~30 seconds max

        # Step 2: Parse document (LONG operation - 6+ minutes!)
        # No DB connection held during this time!
        logger.info(f"Parsing {document_id}...")
        parsed_document, confidence = document_parser.parse_document(
            document_title, file_content
        )
        document_content = document_parser.serialize_document(parsed_document)
        logger.info(f"Parsed {document_id}")

        # Step 3: Update database with parsing results
        # Open new short-lived connection just for this update
        async with sessionmaker() as session:
            document_view = await session.get(Document, document_id)
            if document_view is None:
                raise ValueError(f"Document {document_id} disappeared from database")

            document_view.parsing_quality = PARSING_QUALITY_MAPPING[confidence.mean_grade]
            document_view.content = document_content
            document_view.indexing_success = IndexingSuccess.FAILED

            try:
                await session.commit()
            except Exception:
                await session.rollback()
                document_view.parsing_quality = ParsingQuality.FAILED
                document_view.indexing_success = IndexingSuccess.NO_INDEXING
                await session.commit()
                raise

            # Load party and election relationships AND all attributes before closing connection
            party = cast("Party", await document_view.awaitable_attrs.party)
            election = await party.awaitable_attrs.election

            # These objects are now in memory - they'll stay accessible after session closes
        # ← DB connection closed after quick update

        # Step 4: Chunk and insert to Weaviate (LONG operation - 3-6+ minutes!)
        # No DB connection held during this time!
        logger.info(f"Chunking {document_id}...")
        try:
            # Materialize chunks so we can run the bbox extraction pass before insertion
            document_chunks = list(document_parser.chunk_document(parsed_document))

            # Secondary pass: extract PyMuPDF bboxes for citation highlighting.
            # Uses the PDF bytes cached by the parser during parse_document().
            # Wrapped in try/except — bbox failure must never block ingestion.
            try:
                pdf_bytes = document_parser._current_pdf_bytes
                if pdf_bytes:
                    bbox_extractor = PDFBboxExtractor()
                    fitz_doc = bbox_extractor.extract_from_bytes(pdf_bytes)
                    chunk_inputs = [
                        {
                            "chunk_id": chunk["chunk_id"],
                            "text": chunk.get("text", ""),
                            "page_number": chunk.get("page_number"),
                        }
                        for chunk in document_chunks
                    ]
                    try:
                        bbox_map = bbox_extractor.extract_bboxes_for_chunks(fitz_doc, chunk_inputs)
                    finally:
                        fitz_doc.close()
                    for chunk in document_chunks:
                        chunk["bbox_data"] = json.dumps(bbox_map.get(chunk["chunk_id"], []))
                    logger.info(
                        f"bbox extraction complete for {document_id}, "
                        f"{len(document_chunks)} chunks annotated"
                    )
                else:
                    logger.warning(
                        f"No PDF bytes cached for bbox extraction on {document_id}, "
                        "continuing without bboxes"
                    )
                    for chunk in document_chunks:
                        chunk.setdefault("bbox_data", "[]")
            except Exception as bbox_err:
                logger.warning(
                    f"bbox extraction failed for {document_id}, "
                    f"continuing without bboxes: {bbox_err}"
                )
                for chunk in document_chunks:
                    chunk.setdefault("bbox_data", "[]")

            # Use the loaded objects (they're detached but have all attributes in memory)
            indexing_success = weaviate_database.insert_chunks(
                election,       # Use the full loaded Election object
                party,          # Use the full loaded Party object
                document_view,  # Use document_view (has id and title)
                iter(document_chunks),
            )
        except Exception as e:
            logger.error(f"Chunking error for {document_id}: {e}")
            indexing_success = IndexingSuccess.FAILED

        logger.info(f"Indexed {document_id}")

        # Step 5: Final update - only takes a few milliseconds
        async with sessionmaker() as session:
            document_view = await session.get(Document, document_id)
            if document_view is None:
                raise ValueError(f"Document {document_id} disappeared from database")

            document_view.indexing_success = indexing_success
            await session.commit()
        # ← DB connection closed after quick update

        # Step 6: Send callback to AutoCreate (outside DB session)
        if callback_url and country_code and party_name:
            # Validate callback URL to prevent SSRF
            try:
                parsed = urlparse(callback_url)
                if parsed.scheme not in ("https", "http"):
                    raise ValueError("Only HTTP(S) callback URLs allowed")
                hostname = parsed.hostname or ""
                try:
                    addr = ip_address(hostname)
                    if addr.is_private or addr.is_loopback or addr.is_reserved:
                        raise ValueError("Callback URL must not target private/internal networks")
                except ValueError as ip_err:
                    if "Callback URL" in str(ip_err):
                        raise
                    # hostname is a domain name, not an IP — allow it
            except ValueError as url_err:
                logger.warning(f"Invalid callback URL for {document_id}: {url_err}")
                callback_url = None

            if callback_url:
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        callback_payload = {
                            "country_code": country_code,
                            "document_id": str(document_id),
                            "party_name": party_name,
                        }
                        response = await client.post(callback_url, json=callback_payload)
                        if response.status_code != 200:
                            logger.warning(f"Callback returned {response.status_code} for {document_id}")
                except Exception as callback_error:
                    logger.warning(f"Callback failed for {document_id}: {str(callback_error)}")

        logger.info(f"Completed {document_id}")
    except Exception as e:
        logger.error(f"Failed processing {document_id}: {str(e)}")
        raise


router = APIRouter(prefix="/documents", tags=["documents"])


# ---------------------------------------------------------------------------
# PDF proxy helpers
# ---------------------------------------------------------------------------

def _serve_local_pdf(path: Path) -> StreamingResponse:
    """Stream a local PDF file with CORS headers."""

    def iterfile():
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{path.name}"',
            "Cache-Control": "public, max-age=86400",
        },
    )


async def _proxy_remote_pdf(url: str) -> Response:
    """Proxy a remote PDF with CORS headers."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch PDF: {e}")

    return Response(
        content=resp.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "public, max-age=3600",
        },
    )


# ---------------------------------------------------------------------------
# Manifesto PDF endpoint — placed BEFORE /{document_id} to avoid shadowing
# ---------------------------------------------------------------------------

@router.get("/pdf/{party_key}")
async def get_manifesto_pdf(party_key: str) -> Response:
    """
    Serve a manifesto PDF by party key with CORS headers.

    Tries the local copy in assets/manifestos/ first, then falls back to
    proxying the party's remote URL.

    Supported party keys (case-insensitive):
        CDU, SPD, GRUNE, FDP, AFD, LINKE, BSW, BUENDNIS, FREIE, MLPD, VOLT
    """
    # Normalize: DB shortnames use umlauts (Grüne, AfD, Linke) but manifesto keys are
    # ASCII-only (GRUNE, AFD, LINKE). Try the explicit mapping first, then fall back to
    # plain .upper() for keys that already match (CDU, SPD, FDP, etc.).
    key = PARTY_SHORTNAME_TO_MANIFESTO_KEY.get(party_key) or party_key.upper()

    # 1. Try local file
    local_name = MANIFESTO_LOCAL_NAMES.get(key)
    if local_name:
        local_path = LOCAL_MANIFESTO_DIR / local_name
        if local_path.exists():
            return _serve_local_pdf(local_path)

    # 2. Fall back to remote proxy
    remote_url = MANIFESTO_URLS.get(key)
    if not remote_url:
        raise HTTPException(
            status_code=404, detail=f"No PDF found for party: {party_key}"
        )

    return await _proxy_remote_pdf(remote_url)


@router.post("/")
async def create_document(
    file: UploadFile,
    party_id: Annotated[UUID, Form()],
    session: Annotated[AsyncSession, Depends(get_database_session)],
    document_parser: Annotated[DocumentParser, Depends(get_document_parser)],
    weaviate_database: Annotated[VectorDatabase, Depends(get_vector_database)],
    sessionmaker: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_sessionmaker)
    ],
    background_tasks: BackgroundTasks,
    is_document_already_parsed: Annotated[bool, Form()] = False,
    autocreate_callback_url: Annotated[str | None, Form()] = None,
    country_code: Annotated[str | None, Form()] = None,
    party_name: Annotated[str | None, Form()] = None,
) -> DocumentResponse:
    """Create a new document from uploaded file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # Determine document type from file extension
    file_extension = file.filename.lower().split(".")[-1]

    if file_extension not in DOCUMENT_TYPE_MAPPING:
        supported_types = list(DOCUMENT_TYPE_MAPPING.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_extension}. "
            f"Supported types: {supported_types}",
        )

    # Ensure party exists
    party = await session.get(Party, party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")

    # Create document data
    document = await document_crud.create(
        session,
        obj_in={
            "title": file.filename,
            "type": DOCUMENT_TYPE_MAPPING[file_extension],
            "party_id": party.id,
            "party": party,
        },
    )
    # Document parsing is in the background.
    # Wrap in a tracked asyncio.Task so graceful shutdown can wait for it.
    from em_backend.main import active_document_tasks

    file_bytes = await file.read()

    async def _tracked_process() -> None:
        task = asyncio.current_task()
        if task:
            active_document_tasks.add(task)
        try:
            await process_document(
                document.id,
                BytesIO(file_bytes),
                sessionmaker,
                weaviate_database,
                document_parser,
                autocreate_callback_url,
                country_code,
                party_name,
            )
        finally:
            if task:
                active_document_tasks.discard(task)

    background_tasks.add_task(_tracked_process)

    response = DocumentResponse.model_validate(document)
    await session.commit()
    return response


@router.get("/")
async def read_documents(
    db: Annotated[AsyncSession, Depends(get_database_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[DocumentResponse]:
    """Retrieve documents with pagination."""
    documents = await document_crud.get_multi(db, skip=skip, limit=limit)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}")
async def read_document(
    document_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> DocumentResponseWithContent:
    """Retrieve a specific document by ID."""
    document = await document_crud.get(db, id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponseWithContent.model_validate(document)


@router.get("/{document_id}/status")
async def get_document_indexing_status(
    document_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> dict:
    """
    Get the indexing status of a document.

    Returns:
        - parsing_quality: UNSPECIFIED | LOW | MEDIUM | HIGH | FAILED
        - indexing_success: NO_INDEXING | SUCCESS | FAILED
        - error_message: Optional error message if indexing failed
    """
    document = await document_crud.get(db, id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": str(document.id),
        "parsing_quality": document.parsing_quality.value,
        "indexing_success": document.indexing_success.value,
        "error_message": None,  # Could be extended to store error messages in DB
    }


@router.post("/batch-status")
async def get_documents_batch_status(
    document_ids: list[UUID],
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> dict:
    """
    Get the indexing status of multiple documents in one request.

    Returns a summary with counts of documents by status.
    """
    from sqlalchemy import select
    from em_backend.database.models import Document

    # Fetch all documents in one query
    result = await db.execute(
        select(Document).where(Document.id.in_(document_ids))
    )
    documents = result.scalars().all()

    # Build response
    statuses = []
    for doc in documents:
        statuses.append({
            "document_id": str(doc.id),
            "parsing_quality": doc.parsing_quality.value,
            "indexing_success": doc.indexing_success.value,
        })

    # Calculate summary counts
    total = len(statuses)
    indexed_success = sum(1 for s in statuses if s["indexing_success"] == "SUCCESS")
    indexed_failed = sum(1 for s in statuses if s["indexing_success"] == "FAILED")
    indexing_pending = sum(1 for s in statuses if s["indexing_success"] == "NO_INDEXING")

    return {
        "documents": statuses,
        "summary": {
            "total": total,
            "indexed_success": indexed_success,
            "indexed_failed": indexed_failed,
            "indexing_pending": indexing_pending,
        }
    }


@router.put("/{document_id}")
async def update_document(
    document_id: UUID,
    document_in: DocumentUpdate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> DocumentResponse:
    """Update a document."""
    document = await document_crud.get(db, id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    update_data = document_in.model_dump(exclude_unset=True)
    updated_document = await document_crud.update(
        db, db_obj=document, obj_in=update_data
    )
    await db.commit()
    return DocumentResponse.model_validate(updated_document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
    weaviate_database: Annotated[VectorDatabase, Depends(get_vector_database)],
) -> dict[str, str]:
    """Delete a document."""
    document = await document_crud.remove(db, id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    election = cast(
        "Election",
        await (await document.awaitable_attrs.party).awaitable_attrs.election,
    )
    await weaviate_database.delete_chunks(election, document)

    return {"message": "Document deleted successfully"}


