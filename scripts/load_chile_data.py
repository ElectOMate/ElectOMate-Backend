from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pprint import pprint
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import desc

from em_backend.models.crud import (
    CandidateCreate,
    CandidateResponse,
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


def create_chile_candidate(
    client: TestClient,
    given_name: str,
    family_name: str,
    description: str,
    url: str,
    party_id: UUID,
) -> UUID:
    CANDIDATE = CandidateCreate(
        given_name=given_name,
        family_name=family_name,
        description=description,
        url=url,
        party_id=party_id,
    )
    response = client.post(
        "/v2/candidates/",
        content=CANDIDATE.model_dump_json(),
        headers={"content-type": "application/json"},
    )
    response.raise_for_status()
    content = CandidateResponse.model_validate_json(response.text)
    print(f"Inserted Candidate {content.given_name} {content.family_name}")
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
    create_chile_candidate(
        client,
        given_name="Jeannette",
        family_name="Jara",
        description="Jeannette Alejandra Jara Román (born 23 April 1974) is a Chilean lawyer, public administrator, who served as Minister of Labor and Social Welfare from 2022 to 2025 under President Gabriel Boric. Previously, she served as Undersecretary of Social Security in the second government of former President Michelle Bachelet between 2016 and 2018.",
        url="https://en.wikipedia.org/wiki/Jeannette_Jara",
        party_id=party_ids["PCCh"],
    )
    party_ids["PNL"] = create_chile_party(
        client,
        shortname="PNL",
        fullname="National Libertarian Party",
        description="The National Libertarian Party (Spanish: Partido Nacional Libertario) is a Chilean political party led by Johannes Kaiser.",
        url="https://en.wikipedia.org/wiki/National_Libertarian_Party",
        election_id=election_id,
    )
    create_chile_candidate(
        client,
        given_name="Johannes",
        family_name="Kaiser",
        description="Johannes Maximilian Kaiser Barents-von Hohenhagen (born 5 January 1976) is a Chilean politician, serving as a national deputy since March 2022, representing the 10th district of the Metropolitan Region of Santiago. Previously a member of the Republican Party, he founded the National Libertarian Party in 2024.",
        url="https://en.wikipedia.org/wiki/Johannes_Kaiser_(Chilean_politician)",
        party_id=party_ids["PNL"],
    )
    party_ids["PRCh"] = create_chile_party(
        client,
        shortname="PRCh",
        fullname="Republican Party of Chile",
        description="The Republican Party of Chile (Spanish: Partido Republicano de Chile; PRCh) is a right-wing populist and conservative political party in Chile. Its founder and former leader is Chilean presidential candidate José Antonio Kast.",
        url="https://en.wikipedia.org/wiki/Republican_Party_of_Chile",
        election_id=election_id,
    )
    create_chile_candidate(
        client,
        given_name="José Antonio",
        family_name="Kast",
        description="José Antonio Kast Rist (born 18 January 1966), also known by his initials JAK, is a Chilean lawyer and politician, who is currently serving as the Republican Party's presidential candidate in the 2025 Chilean general election. Part of the prominent Kast family, he served as a member of the Chamber of Deputies from 2002 to 2018.",
        url="https://en.wikipedia.org/wiki/Jos%C3%A9_Antonio_Kast",
        party_id=party_ids["PRCh"],
    )
    party_ids["UDI"] = create_chile_party(
        client,
        shortname="UDI",
        fullname="Independent Democratic Union",
        description="The Independent Democratic Union (Unión Demócrata Independiente, UDI) is a conservative and right-wing political party in Chile, founded in 1983. Its founder was the lawyer, politician, law professor and senator Jaime Guzmán, a civilian allied with Augusto Pinochet.",
        url="https://en.wikipedia.org/wiki/Independent_Democratic_Union",
        election_id=election_id,
    )
    create_chile_candidate(
        client,
        given_name="Evelyn",
        family_name="Matthei",
        description="Evelyn Rose Matthei Fornet (born 11 November 1953) is a Chilean politician, who served as mayor of Providencia, a commune in Santiago, from 2016 to 2024. She previously served as a member of the Chamber of Deputies from 1990 to 1998 and as a senator from 1998 to 2011. Under President Sebastián Piñera she served as Minister of Labor and Social Welfare from 2011 to 2013.",
        url="https://en.wikipedia.org/wiki/Evelyn_Matthei",
        party_id=party_ids["UDI"],
    )
    party_ids["PDG"] = create_chile_party(
        client,
        shortname="PDG",
        fullname="Party of the People",
        description="The Party of the People (Spanish: Partido de la Gente, PDG) is a Chilean political party, characterized as a centre-right to right-wing and populist.",
        url="https://en.wikipedia.org/wiki/Party_of_the_People_(Chile)",
        election_id=election_id,
    )
    create_chile_candidate(
        client,
        given_name="Franco",
        family_name="Parisi",
        description="Franco Aldo Parisi Fernández (born 25 August 1967) is a Chilean business engineer and economist. He received recognition for doing radio and television programs about economy along with his brother Antonino Parisi, and has been nicknamed 'the economist of the people'.",
        url="https://en.wikipedia.org/wiki/Franco_Parisi",
        party_id=party_ids["PDG"],
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
