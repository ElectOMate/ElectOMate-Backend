from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.crud import candidate as candidate_crud
from em_backend.routers.v2 import get_database_session
from em_backend.schemas.models import (
    CandidateCreate,
    CandidateResponse,
    CandidateUpdate,
    CandidateWithParty,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/", response_model=CandidateResponse)
async def create_candidate(
    candidate_in: CandidateCreate,
    db: AAsyncSession = Depends(get_database_session),
) -> CandidateResponse:
    """Create a new candidate."""
    try:
        candidate = await candidate_crud.create(db, obj_in=candidate_in.model_dump())
        await db.commit()
        return CandidateResponse.model_validate(candidate)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/", response_model=list[CandidateResponse])
async def read_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_session),
) -> list[CandidateResponse]:
    """Retrieve candidates with pagination."""
    candidates = await candidate_crud.get_multi(db, skip=skip, limit=limit)
    return [CandidateResponse.model_validate(candidate) for candidate in candidates]


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def read_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> CandidateResponse:
    """Retrieve a specific candidate by ID."""
    candidate = await candidate_crud.get(db, id=candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateResponse.model_validate(candidate)


@router.get("/{candidate_id}/with-party", response_model=CandidateWithParty)
async def read_candidate_with_party(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> CandidateWithParty:
    """Retrieve a specific candidate with party information."""
    candidate = await candidate_crud.get_with_relationships(
        db, id=candidate_id, relationships=["party"]
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateWithParty.model_validate(candidate)


@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: UUID,
    candidate_in: CandidateUpdate,
    db: AsyncSession = Depends(get_database_session),
) -> CandidateResponse:
    """Update a candidate."""
    candidate = await candidate_crud.get(db, id=candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        update_data = candidate_in.model_dump(exclude_unset=True)
        updated_candidate = await candidate_crud.update(
            db, db_obj=candidate, obj_in=update_data
        )
        await db.commit()
        return CandidateResponse.model_validate(updated_candidate)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{candidate_id}")
async def delete_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> dict[str, str]:
    """Delete a candidate."""
    candidate = await candidate_crud.remove(db, id=candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        await db.commit()
        return {"message": "Candidate deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
