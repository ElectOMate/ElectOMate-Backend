import asyncio
from io import BytesIO
from typing import Annotated, cast
from uuid import UUID

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
) -> None:
    logger.info(f"Started processing document {document_id}")

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
        await session.refresh(document_view)

        parsed_document, confidence = document_parser.parse_document(
            document_view.title, file_content
        )
        document_content = document_parser.serialize_document(parsed_document)

        document_view.parsing_quality = PARSING_QUALITY_MAPPING[confidence.mean_grade]
        document_view.content = document_content
        document_view.indexing_success = IndexingSuccess.FAILED

        try:
            await session.commit()
            await session.refresh(document_view)
        except Exception:
            await session.rollback()
            document_view.parsing_quality = ParsingQuality.FAILED
            document_view.indexing_success = IndexingSuccess.NO_INDEXING
            await session.commit()
            raise

        logger.info(f"Finished parsing {document_id}")

        try:
            document_chunks = document_parser.chunk_document(parsed_document)
            party = cast("Party", await document_view.awaitable_attrs.party)
            indexing_success = weaviate_database.insert_chunks(
                await party.awaitable_attrs.election,
                party,
                document_view,
                document_chunks,
            )
        except Exception:
            await session.rollback()
            document_view.indexing_success = IndexingSuccess.FAILED
            await session.commit()
            raise

        document_view.indexing_success = indexing_success
        await session.commit()

        logger.info(f"Finished chunking {document_id}")


router = APIRouter(prefix="/documents", tags=["documents"])


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
