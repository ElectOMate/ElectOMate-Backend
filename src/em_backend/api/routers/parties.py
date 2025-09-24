from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.api.routers.v2 import get_database_session
from em_backend.database.crud import party as party_crud
from em_backend.database.models import Election
from em_backend.models.crud import (
    PartyCreate,
    PartyResponse,
    PartyUpdate,
)

router = APIRouter(prefix="/parties", tags=["parties"])


@router.post("/")
async def create_party(
    party_in: PartyCreate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> PartyResponse:
    """Create a new party."""
    # Ensure election exists
    election = await db.get(Election, party_in.election_id)
    if election is None:
        raise HTTPException(status_code=404, detail="Election not found.")

    party = await party_crud.create(
        db, obj_in=party_in.model_dump() | {"election": election}
    )
    return PartyResponse.model_validate(party)


@router.get("/")
async def read_parties(
    db: Annotated[AsyncSession, Depends(get_database_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[PartyResponse]:
    """Retrieve parties with pagination."""
    parties = await party_crud.get_multi(db, skip=skip, limit=limit)
    return [PartyResponse.model_validate(party) for party in parties]


@router.get("/{party_id}")
async def read_party(
    party_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> PartyResponse:
    """Retrieve a specific party by ID."""
    party = await party_crud.get(db, id=party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")
    return PartyResponse.model_validate(party)


@router.put("/{party_id}")
async def update_party(
    party_id: UUID,
    party_in: PartyUpdate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> PartyResponse:
    """Update a party."""
    party = await party_crud.get(db, id=party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")

    update_data = party_in.model_dump(exclude_unset=True)
    updated_party = await party_crud.update(db, db_obj=party, obj_in=update_data)
    return PartyResponse.model_validate(updated_party)


@router.delete("/{party_id}")
async def delete_party(
    party_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> dict[str, str]:
    """Delete a party."""
    party = await party_crud.remove(db, id=party_id)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found")

    return {"message": "Party deleted successfully"}
