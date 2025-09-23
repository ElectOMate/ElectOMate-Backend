from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.crud import election as election_crud
from em_backend.database.models import Country
from em_backend.models.crud import (
    ElectionCreate,
    ElectionResponse,
    ElectionUpdate,
)
from em_backend.routers.v2 import get_database_session, get_vector_database
from em_backend.vector.db import VectorDatabase

router = APIRouter(prefix="/elections", tags=["elections"])


@router.post("/", response_model=ElectionResponse)
async def create_election(
    election_in: ElectionCreate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
    weaviate_database: Annotated[VectorDatabase, Depends(get_vector_database)],
) -> ElectionResponse:
    """Create a new election."""
    # Ensure country exists
    country = await db.get(Country, election_in.country_id)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found.")

    election = await election_crud.create(
        db, obj_in=election_in.model_dump() | {"country": country}
    )

    # Create election documents
    await weaviate_database.create_election_document_collection(election.id)

    return ElectionResponse.model_validate(election)


@router.get("/", response_model=list[ElectionResponse])
async def read_elections(
    db: Annotated[AsyncSession, Depends(get_database_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[ElectionResponse]:
    """Retrieve elections with pagination."""
    elections = await election_crud.get_multi(db, skip=skip, limit=limit)
    return [ElectionResponse.model_validate(election) for election in elections]


@router.get("/{election_id}", response_model=ElectionResponse)
async def read_election(
    election_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> ElectionResponse:
    """Retrieve a specific election by ID."""
    election = await election_crud.get(db, id=election_id)
    if election is None:
        raise HTTPException(status_code=404, detail="Election not found")
    return ElectionResponse.model_validate(election)


@router.put("/{election_id}")
async def update_election(
    election_id: UUID,
    election_in: ElectionUpdate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> ElectionResponse:
    """Update an election."""
    election = await election_crud.get(db, id=election_id)
    if election is None:
        raise HTTPException(status_code=404, detail="Election not found")

    update_data = election_in.model_dump(exclude_unset=True)
    updated_election = await election_crud.update(
        db, db_obj=election, obj_in=update_data
    )
    return ElectionResponse.model_validate(updated_election)


@router.delete("/{election_id}")
async def delete_election(
    election_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
    weaviate_database: Annotated[VectorDatabase, Depends(get_vector_database)],
) -> dict[str, str]:
    """Delete an election."""
    await weaviate_database.delete_collection(election_id)
    election = await election_crud.remove(db, id=election_id)
    if election is None:
        raise HTTPException(status_code=404, detail="Election not found")

    return {"message": "Election deleted successfully"}
