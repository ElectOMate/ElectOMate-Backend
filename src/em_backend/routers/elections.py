from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.crud import election as election_crud
from em_backend.routers.v2 import get_database_session
from em_backend.schemas.models import (
    ElectionCreate,
    ElectionResponse,
    ElectionUpdate,
    ElectionWithDetails,
)

router = APIRouter(prefix="/elections", tags=["elections"])


@router.post("/", response_model=ElectionResponse)
async def create_election(
    election_in: ElectionCreate,
    db: AsyncSession = Depends(get_database_session),
) -> ElectionResponse:
    """Create a new election."""
    try:
        election = await election_crud.create(db, obj_in=election_in.model_dump())
        await db.commit()
        return ElectionResponse.model_validate(election)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/", response_model=list[ElectionResponse])
async def read_elections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_session),
) -> list[ElectionResponse]:
    """Retrieve elections with pagination."""
    elections = await election_crud.get_multi(db, skip=skip, limit=limit)
    return [ElectionResponse.model_validate(election) for election in elections]


@router.get("/{election_id}", response_model=ElectionResponse)
async def read_election(
    election_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> ElectionResponse:
    """Retrieve a specific election by ID."""
    election = await election_crud.get(db, id=election_id)
    if election is None:
        raise HTTPException(status_code=404, detail="Election not found")
    return ElectionResponse.model_validate(election)


@router.get("/{election_id}/with-details", response_model=ElectionWithDetails)
async def read_election_with_details(
    election_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> ElectionWithDetails:
    """Retrieve a specific election with country and parties."""
    election = await election_crud.get_with_relationships(
        db, id=election_id, relationships=["country", "parties"]
    )
    if election is None:
        raise HTTPException(status_code=404, detail="Election not found")
    return ElectionWithDetails.model_validate(election)


@router.put("/{election_id}", response_model=ElectionResponse)
async def update_election(
    election_id: UUID,
    election_in: ElectionUpdate,
    db: AsyncSession = Depends(get_database_session),
) -> ElectionResponse:
    """Update an election."""
    election = await election_crud.get(db, id=election_id)
    if election is None:
        raise HTTPException(status_code=404, detail="Election not found")

    try:
        update_data = election_in.model_dump(exclude_unset=True)
        updated_election = await election_crud.update(
            db, db_obj=election, obj_in=update_data
        )
        await db.commit()
        return ElectionResponse.model_validate(updated_election)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{election_id}")
async def delete_election(
    election_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> dict[str, str]:
    """Delete an election."""
    election = await election_crud.remove(db, id=election_id)
    if election is None:
        raise HTTPException(status_code=404, detail="Election not found")

    try:
        await db.commit()
        return {"message": "Election deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
