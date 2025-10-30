from typing import Annotated
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.api.routers.v2 import get_database_session, get_vector_database
from em_backend.database.crud import election as election_crud
from em_backend.database.models import Country
from em_backend.models.crud import (
    ElectionCreate,
    ElectionResponse,
    ElectionUpdate,
    _generate_hybrid_wv_collection_name,
)
from em_backend.vector.db import VectorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/elections", tags=["elections"])


@router.post("/")
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

    # Generate hybrid collection name if not provided
    election_data = election_in.model_dump()
    if not election_data.get("wv_collection"):
        election_data["wv_collection"] = _generate_hybrid_wv_collection_name(election_data)
        logger.info(f"Generated Weaviate collection name: {election_data['wv_collection']} for election '{election_data['name']}'")

    election = await election_crud.create(
        db, obj_in=election_data | {"country": country}
    )

    # Create election documents
    if not await weaviate_database.has_election_collection(election):
        await weaviate_database.create_election_collection(election)
        logger.info(f"Created Weaviate collection: {election.wv_collection}")

    return ElectionResponse.model_validate(election)


@router.get("/")
async def read_elections(
    db: Annotated[AsyncSession, Depends(get_database_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[ElectionResponse]:
    """Retrieve elections with pagination."""
    elections = await election_crud.get_multi(db, skip=skip, limit=limit)
    return [ElectionResponse.model_validate(election) for election in elections]


@router.get("/{election_id}")
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
    election = await election_crud.remove(db, id=election_id)
    if election is None:
        raise HTTPException(status_code=404, detail="Election not found")

    if await weaviate_database.has_election_collection(election):
        await weaviate_database.delete_collection(election)

    return {"message": "Election deleted successfully"}
