import asyncio
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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import get_logger

from em_backend.api.routers.v2 import (
    get_database_session,
    get_document_parser,
    get_sessionmaker,
    get_vector_database,
)
from pydantic import BaseModel, Field

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
            document_chunks = document_parser.chunk_document(parsed_document)

            # Use the loaded objects (they're detached but have all attributes in memory)
            indexing_success = weaviate_database.insert_chunks(
                election,       # Use the full loaded Election object
                party,          # Use the full loaded Party object
                document_view,  # Use document_view (has id and title)
                document_chunks,
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


class ChunkDebugRequest(BaseModel):
    file_path: str = Field(..., description="Absolute path to the PDF file to chunk")


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
    # Document parsing is in the background
    background_tasks.add_task(
        process_document,
        document.id,
        BytesIO(await file.read()),
        sessionmaker,
        weaviate_database,
        document_parser,
        autocreate_callback_url,
        country_code,
        party_name,
    )

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

3
@router.post("/debug/chunks")
async def debug_chunk_document(
    payload: ChunkDebugRequest,
    document_parser: Annotated[DocumentParser, Depends(get_document_parser)],
) -> dict[str, object]:
    file_path = Path(payload.file_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Provided file path does not exist")

    file_bytes = file_path.read_bytes()
    document, confidence = document_parser.parse_document(
        file_path.name,
        BytesIO(file_bytes),
    )

    chunks = list(document_parser.chunk_document(document))
    preview: list[dict[str, object]] = []
    for idx, chunk in enumerate(chunks[:5]):
        preview.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "page_number": chunk.get("page_number"),
                "chunk_index": chunk.get("chunk_index"),
                "text_preview": (chunk.get("text") or "")[:200],
            }
        )

    return {
        "file": str(file_path),
        "chunk_count": len(chunks),
        "confidence": confidence.model_dump(),
        "preview": preview,
    }
