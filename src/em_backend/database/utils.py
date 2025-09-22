from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from em_backend.database.models import Election, Party


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
