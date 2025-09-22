from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.crud import document as document_crud
from em_backend.routers.v2 import get_database_session
from em_backend.schemas.models import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    DocumentWithParty,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentResponse)
async def create_document(
    document_in: DocumentCreate,
    db: AsyncSession = Depends(get_database_session),
) -> DocumentResponse:
    """Create a new document."""
    try:
        document = await document_crud.create(db, obj_in=document_in.model_dump())
        await db.commit()
        return DocumentResponse.model_validate(document)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/", response_model=list[DocumentResponse])
async def read_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_session),
) -> list[DocumentResponse]:
    """Retrieve documents with pagination."""
    documents = await document_crud.get_multi(db, skip=skip, limit=limit)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def read_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> DocumentResponse:
    """Retrieve a specific document by ID."""
    document = await document_crud.get(db, id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/with-party", response_model=DocumentWithParty)
async def read_document_with_party(
    document_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> DocumentWithParty:
    """Retrieve a specific document with party information."""
    document = await document_crud.get_with_relationships(
        db, id=document_id, relationships=["party"]
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentWithParty.model_validate(document)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    document_in: DocumentUpdate,
    db: AsyncSession = Depends(get_database_session),
) -> DocumentResponse:
    """Update a document."""
    document = await document_crud.get(db, id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        update_data = document_in.model_dump(exclude_unset=True)
        updated_document = await document_crud.update(
            db, db_obj=document, obj_in=update_data
        )
        await db.commit()
        return DocumentResponse.model_validate(updated_document)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> dict[str, str]:
    """Delete a document."""
    document = await document_crud.remove(db, id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        await db.commit()
        return {"message": "Document deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
