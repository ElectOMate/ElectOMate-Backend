from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.crud import country as country_crud
from em_backend.routers.v2 import get_database_session
from em_backend.schemas.models import (
    CountryCreate,
    CountryResponse,
    CountryUpdate,
    CountryWithElections,
)

router = APIRouter(prefix="/countries", tags=["countries"])


@router.post("/", response_model=CountryResponse)
async def create_country(
    country_in: CountryCreate,
    db: AsyncSession = Depends(get_database_session),
) -> CountryResponse:
    """Create a new country."""
    try:
        country = await country_crud.create(db, obj_in=country_in.model_dump())
        await db.commit()
        return CountryResponse.model_validate(country)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[CountryResponse])
async def read_countries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_database_session),
) -> list[CountryResponse]:
    """Retrieve countries with pagination."""
    countries = await country_crud.get_multi(db, skip=skip, limit=limit)
    return [CountryResponse.model_validate(country) for country in countries]


@router.get("/{country_id}", response_model=CountryResponse)
async def read_country(
    country_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> CountryResponse:
    """Retrieve a specific country by ID."""
    country = await country_crud.get(db, id=country_id)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return CountryResponse.model_validate(country)


@router.get("/{country_id}/with-elections", response_model=CountryWithElections)
async def read_country_with_elections(
    country_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> CountryWithElections:
    """Retrieve a specific country with its elections."""
    country = await country_crud.get_with_relationships(
        db, id=country_id, relationships=["elections"]
    )
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")
    return CountryWithElections.model_validate(country)


@router.put("/{country_id}", response_model=CountryResponse)
async def update_country(
    country_id: UUID,
    country_in: CountryUpdate,
    db: AsyncSession = Depends(get_database_session),
) -> CountryResponse:
    """Update a country."""
    country = await country_crud.get(db, id=country_id)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")

    try:
        update_data = country_in.model_dump(exclude_unset=True)
        updated_country = await country_crud.update(
            db, db_obj=country, obj_in=update_data
        )
        await db.commit()
        return CountryResponse.model_validate(updated_country)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{country_id}")
async def delete_country(
    country_id: UUID,
    db: AsyncSession = Depends(get_database_session),
) -> dict[str, str]:
    """Delete a country."""
    country = await country_crud.remove(db, id=country_id)
    if country is None:
        raise HTTPException(status_code=404, detail="Country not found")

    try:
        await db.commit()
        return {"message": "Country deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
