from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.api.routers.v2 import get_database_session
from em_backend.database.crud import candidate as candidate_crud
from em_backend.database.models import Party
from em_backend.models.crud import (
    CandidateCreate,
    CandidateResponse,
    CandidateUpdate,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/")
async def create_candidate(
    candidate_in: CandidateCreate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> CandidateResponse:
    """Create a new candidate."""
    # Ensure party exists
    party = await db.get(Party, candidate_in.party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found.")

    candidate = await candidate_crud.create(
        db, obj_in=candidate_in.model_dump() | {"party": party}
    )
    return CandidateResponse.model_validate(candidate)


@router.get("/")
async def read_candidates(
    db: Annotated[AsyncSession, Depends(get_database_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[CandidateResponse]:
    """Retrieve candidates with pagination."""
    candidates = await candidate_crud.get_multi(db, skip=skip, limit=limit)
    return [CandidateResponse.model_validate(candidate) for candidate in candidates]


@router.get("/{candidate_id}")
async def read_candidate(
    candidate_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> CandidateResponse:
    """Retrieve a specific candidate by ID."""
    candidate = await candidate_crud.get(db, id=candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateResponse.model_validate(candidate)


@router.put("/{candidate_id}")
async def update_candidate(
    candidate_id: UUID,
    candidate_in: CandidateUpdate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> CandidateResponse:
    """Update a candidate."""
    candidate = await candidate_crud.get(db, id=candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    update_data = candidate_in.model_dump(exclude_unset=True)
    updated_candidate = await candidate_crud.update(
        db, db_obj=candidate, obj_in=update_data
    )
    return CandidateResponse.model_validate(updated_candidate)


@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> dict[str, str]:
    """Delete a candidate."""
    candidate = await candidate_crud.remove(db, id=candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return {"message": "Candidate deleted successfully"}
