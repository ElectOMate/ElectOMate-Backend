from io import BytesIO
from typing import Annotated
from uuid import UUID

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

from em_backend.crud import document as document_crud
from em_backend.database.models import Document, Party
from em_backend.models.crud import (
    DocumentResponse,
    DocumentResponseWithContent,
    DocumentUpdate,
)
from em_backend.old_models import SupportedDocumentFormats
from em_backend.parser.parser import DocumentParser
from em_backend.routers.v2 import (
    get_database_session,
    get_document_parser,
    get_sessionmaker,
    get_vector_database,
)
from em_backend.vector.db import VectorDatabase

router = APIRouter(prefix="/documents", tags=["documents"])
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


async def process_document(
    document: Document,
    file_content: BytesIO,
    sessionmaker: async_sessionmaker[AsyncSession],
    weaviate_database: VectorDatabase,
    document_parser: DocumentParser,
) -> None:
    async with sessionmaker() as session:
        document = await session.merge(document)

        # Parse file
        parsed_document = await document_parser.parse_document(
            document.title, file_content
        )
        document.content = document_parser.serialize_document(parsed_document)
        await session.commit()

        # Chunk and vectorize file
        document_chunks = document_parser.chunk_document(parsed_document)
        party = await document.awaitable_attrs.party
        weaviate_database.insert_chunks(
            party.election_id, document.party.id, document_chunks
        )
        document.is_indexed = True
        await session.commit()


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
        document,
        BytesIO(await file.read()),
        sessionmaker,
        weaviate_database,
        document_parser,
    )
    return DocumentResponse.model_validate(document)


@router.get("/")
async def read_documents(
    db: Annotated[AsyncSession, Depends(get_database_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
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
) -> dict[str, str]:
    """Delete a document."""
    document = await document_crud.remove(db, id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"message": "Document deleted successfully"}
