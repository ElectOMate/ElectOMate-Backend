from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.crud import party as party_crud
from em_backend.routers.v2 import get_database_session
from em_backend.schemas.models import (
    PartyCreate,
    PartyResponse,
    PartyUpdate,
    PartyWithDetails,
)

router = APIRouter(prefix="/parties", tags=["parties"])


@router.post("/", response_model=PartyResponse)
async def create_party(
    party_in: PartyCreate,
    db: AsyncSession = Depends(get_database_session),
) -> PartyResponse:
    """Create a new party."""
    try:
        party = await party_crud.create(db, obj_in=party_in.model_dump())
        await db.commit()
        return PartyResponse.model_validate(party)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/", response_model=list[PartyResponse])
async def read_parties(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_session),
) -> list[PartyResponse]:
    """Retrieve parties with pagination."""
    parties = await party_crud.get_multi(db, skip=skip, limit=limit)
    return [PartyResponse.model_validate(party) for party in parties]


@router.get("/{party_id}", response_model=PartyResponse)
async def read_party(
    party_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> PartyResponse:
    """Retrieve a specific party by ID."""
    party = await party_crud.get(db, id=party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")
    return PartyResponse.model_validate(party)


@router.get("/{party_id}/with-details", response_model=PartyWithDetails)
async def read_party_with_details(
    party_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> PartyWithDetails:
    """Retrieve a specific party with all relationships."""
    party = await party_crud.get_with_relationships(
        db,
        id=party_id,
        relationships=["election", "candidate", "documents", "proposed_questions"],
    )
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")
    return PartyWithDetails.model_validate(party)


@router.put("/{party_id}", response_model=PartyResponse)
async def update_party(
    party_id: UUID,
    party_in: PartyUpdate,
    db: AsyncSession = Depends(get_database_session),
) -> PartyResponse:
    """Update a party."""
    party = await party_crud.get(db, id=party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")

    try:
        update_data = party_in.model_dump(exclude_unset=True)
        updated_party = await party_crud.update(db, db_obj=party, obj_in=update_data)
        await db.commit()
        return PartyResponse.model_validate(updated_party)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{party_id}")
async def delete_party(
    party_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> dict[str, str]:
    """Delete a party."""
    party = await party_crud.remove(db, id=party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")

    try:
        await db.commit()
        return {"message": "Party deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
