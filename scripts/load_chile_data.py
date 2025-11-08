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
    party_ids["PC"] = create_chile_party(
        client,
        shortname="PC",
        fullname="Partido Comunista de Chile",
        description="El Partido Comunista de Chile es una fuerza política de izquierda, parte fundamental de la coalición Unidad por Chile. Fundado en 1922, ha desempeñado un papel histórico en la lucha por los derechos laborales y sociales, con énfasis en la igualdad social y económica. El PCCh apoya la expansión del Estado en la educación, salud y redistribución de la riqueza. Para la elección presidencial de 2025, presenta como candidata a Jeannette Jara, que encabeza las propuestas del bloque oficialista. El partido ha impulsado reformas constitucionales y sociales desde la presidencia de Gabriel Boric.",
        url="https://en.wikipedia.org/wiki/Communist_Party_of_Chile",
        election_id=election_id,
    )
    create_chile_candidate(
        client,
        given_name="Jeannette",
        family_name="Jara",
        description="Jeannette Alejandra Jara Román (born 23 April 1974) is a Chilean lawyer, public administrator, who served as Minister of Labor and Social Welfare from 2022 to 2025 under President Gabriel Boric. Previously, she served as Undersecretary of Social Security in the second government of former President Michelle Bachelet between 2016 and 2018.",
        url="https://en.wikipedia.org/wiki/Jeannette_Jara",
        party_id=party_ids["PC"],
    )
    party_ids["REP"] = create_chile_party(
        client,
        shortname="REP",
        fullname="Partido Republicano",
        description="El Partido Republicano es una agrupación de extrema derecha fundada en 2019 por José Antonio Kast, quien actualmente es nuevamente candidato presidencial. Defiende políticas conservadoras en temas sociales, migratorios y de seguridad, y una marcada tendencia liberal en economía. Se opone a las reformas progresistas promovidas por la izquierda y busca limitar el rol del Estado en áreas como educación y salud. Ha ganado popularidad tras el estallido social y la polarización política vista en Chile desde 2019, atrayendo a sectores descontentos con el gobierno de Boric.",
        url="https://en.wikipedia.org/wiki/Republican_Party_of_Chile",
        election_id=election_id,
    )
    create_chile_candidate(
        client,
        given_name="José Antonio",
        family_name="Kast",
        description="José Antonio Kast Rist (born 18 January 1966), also known by his initials JAK, is a Chilean lawyer and politician, who is currently serving as the Republican Party's presidential candidate in the 2025 Chilean general election. Part of the prominent Kast family, he served as a member of the Chamber of Deputies from 2002 to 2018.",
        url="https://en.wikipedia.org/wiki/Jos%C3%A9_Antonio_Kast",
        party_id=party_ids["REP"],
    )
    party_ids["UDI"] = create_chile_party(
        client,
        shortname="UDI",
        fullname="Unión Demócrata Independiente",
        description="La UDI, fundada en 1983, es un partido conservador y uno de los principales referentes de la derecha chilena. Integrante de la coalición Chile Grande y Unido, defiende posiciones conservadoras en temas religiosos, sociales y económicos, abogando por el libre mercado, la inversión y la seguridad ciudadana. Históricamente ha tenido fuerte presencia legislativa y es clave en la conformación de candidaturas presidenciales de la centroderecha.",
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
        fullname="Partido de la Gente",
        description="El Partido de la Gente surgió en 2021 como una respuesta a la ciudadanía desencantada con los partidos tradicionales, con Franco Parisi como su principal líder y candidato. Defiende políticas anticorrupción, mayor participación ciudadana y reducción de privilegios de la clase política. En 2025 Parisi compite como independiente, aunque el partido lo respalda formalmente como su abanderado.",
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
    party_ids["PartidoNacionalLibertari"] = create_chile_party(
        client,
        shortname="PartidoNacionalLibertari",
        fullname="Partido Nacional Libertario",
        description="El Partido Nacional Libertario es una fuerza de derecha radical que postula a Johannes Kaiser como candidato presidencial para 2025. Su plataforma gira en torno a la reducción del Estado, la defensa de nuevas libertades económicas y la liberalización de leyes sobre armas y migración. Busca atraer votantes descontentos con los partidos de centroderecha y extrema derecha tradicionales.",
        url="https://en.wikipedia.org/wiki/National_Libertarian_Party",
        election_id=election_id,
    )
    create_chile_candidate(
        client,
        given_name="Johannes",
        family_name="Kaiser",
        description="Johannes Maximilian Kaiser Barents-von Hohenhagen (born 5 January 1976) is a Chilean politician, serving as a national deputy since March 2022, representing the 10th district of the Metropolitan Region of Santiago. Previously a member of the Republican Party, he founded the National Libertarian Party in 2024.",
        url="https://en.wikipedia.org/wiki/Johannes_Kaiser_(Chilean_politician)",
        party_id=party_ids["PartidoNacionalLibertari"],
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
