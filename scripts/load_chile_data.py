from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pprint import pprint
from uuid import UUID

from fastapi.testclient import TestClient

from em_backend.models.crud import (
    CountryCreate,
    CountryResponse,
    ElectionCreate,
    ElectionResponse,
    PartyCreate,
    PartyResponse,
)


@contextmanager
def get_app_client() -> Generator[TestClient]:
    from em_backend.main import app

    with TestClient(app) as client:
        yield client


def create_chile_country(client: TestClient) -> UUID:
    CHILE_COUNTRY = CountryCreate(name="Chile", code="cl")
    response = client.post(
        "/v2/countries",
        content=CHILE_COUNTRY.model_dump_json(),
        headers={"content-type": "application/json"},
    )
    response.raise_for_status()
    content = CountryResponse.model_validate_json(response.text)
    print("Inserted Chile:")
    pprint(content)
    return content.id


def create_chile_election(client: TestClient, country_id: UUID) -> UUID:
    CHILE_ELECTION = ElectionCreate(
        name="Chilean general election",
        year=2025,
        date=datetime(year=2025, month=11, day=16),
        url="https://en.wikipedia.org/wiki/2025_Chilean_general_election",
        wv_collection="D2025chileangeneralelection",
        country_id=country_id,
    )
    response = client.post(
        "/v2/elections",
        content=CHILE_ELECTION.model_dump_json(),
        headers={"content-type": "application/json"},
    )
    response.raise_for_status()
    content = ElectionResponse.model_validate_json(response.text)
    print("Inserted Chile Elections:")
    pprint(content)
    return content.id


def create_chile_party(
    client: TestClient,
    shortname: str,
    fullname: str,
    description: str,
    url: str,
    election_id: UUID,
) -> UUID:
    PARTY = PartyCreate(
        shortname=shortname,
        fullname=fullname,
        description=description,
        url=url,
        election_id=election_id,
    )
    response = client.post(
        "/v2/parties/",
        content=PARTY.model_dump_json(),
        headers={"content-type": "application/json"},
    )
    response.raise_for_status()
    content = PartyResponse.model_validate_json(response.text)
    print(f"Inserted Party {shortname}:")
    pprint(content)
    return content.id


def create_chile_parties(client: TestClient, election_id: UUID) -> dict[str, UUID]:
    party_ids: dict[str, UUID] = {}
    party_ids["PCCh"] = create_chile_party(
        client,
        shortname="PCCh",
        fullname="Communist Party of Chile",
        description="The Communist Party of Chile (Spanish: Partido Comunista de Chile, PCCh) is a communist party in Chile.",
        url="https://en.wikipedia.org/wiki/National_Libertarian_Party",
        election_id=election_id,
    )
    party_ids["PNL"] = create_chile_party(
        client,
        shortname="PNL",
        fullname="National Libertarian Party",
        description="The National Libertarian Party (Spanish: Partido Nacional Libertario) is a Chilean political party led by Johannes Kaiser.",
        url="https://en.wikipedia.org/wiki/National_Libertarian_Party",
        election_id=election_id,
    )
    party_ids["PRCh"] = create_chile_party(
        client,
        shortname="PRCh",
        fullname="Republican Party of Chile",
        description="The Republican Party of Chile (Spanish: Partido Republicano de Chile; PRCh) is a right-wing populist and conservative political party in Chile. Its founder and former leader is Chilean presidential candidate José Antonio Kast.",
        url="https://en.wikipedia.org/wiki/Republican_Party_of_Chile",
        election_id=election_id,
    )
    party_ids["UDI"] = create_chile_party(
        client,
        shortname="UDI",
        fullname="Independent Democratic Union",
        description="The Independent Democratic Union (Unión Demócrata Independiente, UDI) is a conservative and right-wing political party in Chile, founded in 1983. Its founder was the lawyer, politician, law professor and senator Jaime Guzmán, a civilian allied with Augusto Pinochet.",
        url="https://en.wikipedia.org/wiki/Independent_Democratic_Union",
        election_id=election_id,
    )
    party_ids["PDG"] = create_chile_party(
        client,
        shortname="PDG",
        fullname="Party of the People",
        description="The Party of the People (Spanish: Partido de la Gente, PDG) is a Chilean political party, characterized as a centre-right to right-wing and populist.",
        url="https://en.wikipedia.org/wiki/Party_of_the_People_(Chile)",
        election_id=election_id,
    )
    return party_ids


def main() -> None:
    with get_app_client() as client:
        country_id = create_chile_country(client)
        election_id = create_chile_election(client, country_id)
        party_ids = create_chile_parties(client, election_id)
        print("Party ids:")
        pprint(party_ids)


if __name__ == "__main__":
    main()
