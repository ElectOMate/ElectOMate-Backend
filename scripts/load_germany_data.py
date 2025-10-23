from __future__ import annotations

from datetime import datetime
from pprint import pprint
from uuid import UUID

from em_backend.models.crud import CountryCreate

from scripts.load_utils import (
    ElectionSeed,
    PartySeed,
    create_country,
    create_election,
    create_party,
    get_app_client,
)


GERMANY_COUNTRY = CountryCreate(name="Germany", code="DE")
GERMANY_ELECTION = ElectionSeed(
    name="Bundestagswahl 2025",
    year=2025,
    date=datetime.fromisoformat("2025-01-01T00:00:00"),
    url="https://en.wikipedia.org/wiki/Germany_2025_election",
    wv_collection="D2025bundestagswahl",
)

GERMANY_PARTIES: list[PartySeed] = [
    PartySeed(
        shortname="CDU",
        fullname="Christlich Demokratische Union Deutschlands / Christlich-Soziale Union in Bayern",
        description=(
            "Die CDU/CSU ist ein Bündnis von Mitte-rechts-Parteien und dominiert traditionell"
            " das konservative Lager in Deutschland. Die CDU ist in allen Bundesländern außer"
            " Bayern aktiv, während die CSU ausschließlich in Bayern kandidiert. Die Union"
            " setzt sich für wirtschaftlichen Liberalismus, christlich-soziale Werte, eine"
            " starke Rolle Deutschlands in der EU und konservative Gesellschaftspolitik ein."
            " Mit Friedrich Merz als Spitzenkandidat gewann die Union 2025 die Bundestagswahl."
            " Sie ist regelmäßig eine Regierungspartei und stellt oft den/die Kanzler/kandidaten"
            " bei Präsidentschaftswahlen. Die Partei schließt eine Zusammenarbeit mit der AfD"
            " kategorisch aus."
        ),
        url=None,
    ),
    PartySeed(
        shortname="SPD",
        fullname="Sozialdemokratische Partei Deutschlands",
        description=(
            "Die SPD ist Deutschlands älteste Partei und vertritt sozialdemokratische sowie"
            " progressive Werte. Ihr Schwerpunkt liegt auf sozialer Gerechtigkeit, Stärkung"
            " des Sozialstaats, Arbeitnehmerrechten sowie der europäischen Integration. Sie"
            " führte bis 2024 die Bundesregierung unter Olaf Scholz, verlor 2025 jedoch"
            " deutlich an Zustimmung. Die SPD nominiert regelmäßig Kandidaten zu"
            " Präsidentschaftswahlen und war historisch an fast allen Bundesregierungen"
            " beteiligt. Sie positioniert sich als Gegengewicht zur konservativen Union."
        ),
        url=None,
    ),
    PartySeed(
        shortname="AfD",
        fullname="Alternative für Deutschland",
        description=(
            "Die AfD ist eine rechtspopulistische und euroskeptische Partei, gegründet 2013."
            " Ursprünglich mit Fokus auf Eurokritik, stehen heute nationale Identität,"
            " restriktive Einwanderungspolitik, Ablehnung der EU-Zentralisierung und"
            " Klimaskepsis im Mittelpunkt. In Ostdeutschland ist sie besonders stark. Sie"
            " erreichte 2025 mit einer Anti-Establishment-Kampagne ihr bisher bestes"
            " bundesweites Wahlergebnis. Die AfD stellt eigene Kandidaten zur"
            " Präsidentschaftswahl auf, ist jedoch von anderen Parteien isoliert."
        ),
        url=None,
    ),
]


def _load_country(client) -> UUID:
    response = create_country(client, GERMANY_COUNTRY)
    print("Inserted Germany:")
    pprint(response)
    return response.id


def _load_election(client, country_id: UUID) -> UUID:
    election = create_election(client, GERMANY_ELECTION.to_create(country_id))
    print("Inserted Germany Election:")
    pprint(election)
    return election.id


def _load_parties(client, election_id: UUID) -> dict[str, UUID]:
    party_ids: dict[str, UUID] = {}
    for party_seed in GERMANY_PARTIES:
        party = create_party(client, party_seed.to_create(election_id))
        party_ids[party_seed.shortname] = party.id
        print(f"Inserted Party {party_seed.shortname}:")
        pprint(party)
    return party_ids


def main() -> None:
    with get_app_client() as client:
        country_id = _load_country(client)
        election_id = _load_election(client, country_id)
        party_ids = _load_parties(client, election_id)
        print("Party ids:")
        pprint(party_ids)


if __name__ == "__main__":
    main()

