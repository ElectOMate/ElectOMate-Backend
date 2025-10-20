from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from em_backend.api.routers.v2 import get_database_session
from em_backend.database.crud import country as country_crud
from em_backend.models.crud import (
    CountryCreate,
    CountryResponse,
    CountryUpdate,
)

router = APIRouter(prefix="/countries", tags=["countries"])


@router.post("/")
async def create_country(
    country_in: CountryCreate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> CountryResponse:
    """Create a new country."""
    # First, check if country already exists to provide better error info
    from em_backend.database.models import Country
    from sqlalchemy import select
    
    stmt = select(Country).where(Country.code == country_in.code)
    result = await db.execute(stmt)
    existing_country = result.scalar_one_or_none()
    
    if existing_country:
        # Country already exists, return 409 with details
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_country_code",
                "message": f"Country with code '{country_in.code}' already exists",
                "existing_country": {
                    "id": str(existing_country.id),
                    "name": existing_country.name,
                    "code": existing_country.code,
                },
                "attempted_values": {
                    "name": country_in.name,
                    "code": country_in.code,
                },
            }
        )
    
    # Country doesn't exist, create it
    try:
        country = await country_crud.create(db, obj_in=country_in.model_dump())
        return CountryResponse.model_validate(country)
    except IntegrityError as e:
        # Rollback the failed transaction
        await db.rollback()
        
        # Handle race condition or other integrity errors
        if "country_table_code_key" in str(e.orig):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "duplicate_country_code",
                    "message": f"Country with code '{country_in.code}' already exists (race condition)",
                    "attempted_values": {
                        "name": country_in.name,
                        "code": country_in.code,
                    },
                }
            )
        
        # Other integrity error
        raise HTTPException(
            status_code=400,
            detail=f"Database integrity error: {str(e.orig)}"
        )


@router.get("/")
async def read_countries(
    db: Annotated[AsyncSession, Depends(get_database_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[CountryResponse]:
    """Retrieve countries with pagination."""
    countries = await country_crud.get_multi(db, skip=skip, limit=limit)
    return [CountryResponse.model_validate(country) for country in countries]


@router.get("/{country_id}")
async def read_country(
    country_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> CountryResponse:
    """Retrieve a specific country by ID."""
    country = await country_crud.get(db, id=country_id)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return CountryResponse.model_validate(country)


@router.put("/{country_id}")
async def update_country(
    country_id: UUID,
    country_in: CountryUpdate,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> CountryResponse:
    """Update a country."""
    country = await country_crud.get(db, id=country_id)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")

    update_data = country_in.model_dump(exclude_unset=True)
    updated_country = await country_crud.update(db, db_obj=country, obj_in=update_data)
    return CountryResponse.model_validate(updated_country)


@router.delete("/{country_id}")
async def delete_country(
    country_id: UUID,
    db: Annotated[AsyncSession, Depends(get_database_session)],
) -> dict[str, str]:
    """Delete a country."""
    country = await country_crud.remove(db, id=country_id)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")

    return {"message": "Country deleted successfully"}
