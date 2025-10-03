from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from em_backend.core.config import settings
from em_backend.database.models import Country, Election, Party


@asynccontextmanager
async def create_database_sessionmaker() -> AsyncGenerator[async_sessionmaker]:
    engine = create_async_engine(url=settings.postgres_url)
    yield async_sessionmaker(engine)
    await engine.dispose()


async def get_parties_enum(session: AsyncSession, election: Election) -> type[StrEnum]:
    # Get all party shortnames for the country
    party_stmt = select(Party.shortname).where(Party.election == election)
    party_result = await session.execute(party_stmt)
    all_party_shortnames = [row[0] for row in party_result.fetchall()]

    return StrEnum(
        "Parties", {shortname.upper(): shortname for shortname in all_party_shortnames}
    )  # pyright: ignore[reportReturnType]


async def get_missing_party_shortnames(
    session: AsyncSession, election: Election, given_party_shortnames: list[Party]
) -> list[str]:
    """
    Get all party shortnames available in a country that are not in the given list.

    Args:
        session: SQLAlchemy async session
        country_code: Two-character country code
        given_party_shortnames: List of party shortnames to exclude

    Returns:
        List of party shortnames that exist in the country but are not in the given list
    """
    # Get all party shortnames for the country
    party_stmt = select(Party.shortname).where(Party.election == election)
    party_result = await session.execute(party_stmt)
    all_party_shortnames = [row[0] for row in party_result.fetchall()]

    # Return shortnames that are not in the given list
    return [
        shortname
        for shortname in all_party_shortnames
        if shortname not in given_party_shortnames
    ]


async def get_country_from_shortcode(
    session: AsyncSession, country_code: str
) -> Country | None:
    country_stmt = select(Country).where(Country.code == country_code)
    country_result = await session.execute(country_stmt)
    return country_result.scalar()


async def get_election_from_election_id(
    session: AsyncSession, election_id: UUID
) -> Election | None:
    return await session.get(Election, election_id)


async def get_party_from_name_list(
    session: AsyncSession, party_name: list[str]
) -> list[Party]:
    party_stmt = select(Party).where(Party.shortname.in_(party_name))
    party_result = await session.execute(party_stmt)
    return list(party_result.scalars().all())
