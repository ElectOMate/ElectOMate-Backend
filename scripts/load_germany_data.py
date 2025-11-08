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
        shortname="FDP",
        fullname="Freie Demokratische Partei",
        description=(
            "Die FDP wurde 1948 gegründet und vertritt liberale sowie wirtschaftsliberale Prinzipien. "
            "Sie setzt sich für Bürgerrechte, eine freiheitliche Gesellschaft und marktwirtschaftliche Reformen ein. "
            "Die Partei plädiert für Digitalisierung, Bildung und steuerliche Entlastungen. "
            "Die FDP hatte wiederholt das Zünglein an der Waage in Koalitionsregierungen und ist besonders im Mittelstand "
            "und bei Unternehmern verankert. In Präsidentschaftswahlen unterstützt die FDP meist eigene Kandidaten mit "
            "liberalem Hintergrund oder spricht Wahlempfehlungen für bürgerliche Kandidaten aus."
        ),
        url=None,
    ),
    PartySeed(
        shortname="Linke",
        fullname="Die Linke",
        description=(
            "Die Linke ist Nachfolgepartei der PDS und sozialen Bewegungen der westdeutschen Linken. "
            "Sie versteht sich als sozialistische Partei für radikalen Umverteilungs- und sozialen Ausgleich, "
            "Ausbau öffentlicher Daseinsvorsorge sowie friedenspolitische Initiativen. "
            "Die Linke vertritt eine konsequente Ablehnung militarisierter Außenpolitik und fordert höhere Steuern auf Vermögen. "
            "Trotz Wahlerfolgen befindet sich die Partei nach wichtigen Abspaltungen wie der Gründung des BSW im Umbruch. "
            "Bei Präsidentenwahlen nominiert sie eigene Kandidierende, die klar links positioniert sind."
        ),
        url=None,
    ),
    PartySeed(
        shortname="AfD",
        fullname="Alternative für Deutschland",
        description=(
            "Die AfD wurde 2013 gegründet, zunächst europakritisch, mittlerweile rechtspopulistisch und nationalkonservativ. "
            "Schwerpunkte der Partei sind restriktive Migrationspolitik, Ablehnung der aktuellen EU-Institutionen sowie "
            "Skepsis gegenüber Klimaschutzmaßnahmen, die als teuer und ineffizient betrachtet werden. "
            "Die AfD schneidet in den neuen Bundesländern und im Osten besonders stark ab. "
            "Sie steht seit Jahren in Opposition zu den traditionellen Parteien und ist aufgrund extremistischer Strömungen "
            "innerhalb der Partei umstritten. Präsidentschaftskandidaten der AfD vertreten konservative bis nationalistische Positionen."
        ),
        url=None,
    ),
    PartySeed(
        shortname="Grüne",
        fullname="Bündnis 90/Die Grünen",
        description=(
            "Die Grünen entstanden Anfang der 1980er Jahre durch den Zusammenschluss umwelt- und friedensbewegter Gruppen. "
            "Sie stehen für ökologische Nachhaltigkeit, soziale Gerechtigkeit, Gleichstellung und ein pro-europäisches Weltbild. "
            "Die Partei forciert eine schnelle Klimawende, gesellschaftliche Modernisierung und Menschenrechte. "
            "Im Präsidentschaftswahlkontext benennen die Grünen meist eine eigene Kandidatur oder unterstützen progressive Kandidierende. "
            "Prominente Persönlichkeiten sind unter anderem Annalena Baerbock und Robert Habeck. "
            "Ihr Einfluss wächst besonders in städtischen und jüngeren Wählerschichten stetig."
        ),
        url=None,
    ),
    PartySeed(
        shortname="SPD",
        fullname="Sozialdemokratische Partei Deutschlands",
        description=(
            "Die SPD, gegründet 1863, ist Deutschlands älteste bestehende Partei und eine der bedeutendsten Akteure im "
            "politischen System der BRD. Sie versteht sich als links der Mitte, steht für soziale Gerechtigkeit, "
            "Arbeitnehmerrechte und einen aktiven Sozialstaat. International ist die SPD mit der Sozialistischen Internationale "
            "und der Progressiven Allianz verbunden. Olaf Scholz war zuletzt Kanzlerkandidat und Regierungschef. "
            "Die Partei setzt sich für die Bekämpfung sozialer Ungleichheit, Klimaschutz und Fortschritt in der Technologie- "
            "und Familienpolitik ein. Bei Präsidentschaftswahlen unterstützt sie gewöhnlich einen eigenen oder einen "
            "überparteilichen Kandidaten mit sozialdemokratischer Prägung."
        ),
        url=None,
    ),
    PartySeed(
        shortname="CDU",
        fullname="Christlich Demokratische Union Deutschlands/Christlich-Soziale Union in Bayern",
        description=(
            "Die CDU/CSU ist ein Bündnis aus zwei Schwesterparteien: der CDU (außerhalb Bayerns) und der CSU (nur in Bayern). "
            "Sie repräsentiert das konservative und christdemokratische Spektrum und war nach dem Zweiten Weltkrieg mehrfach "
            "Regierungspartei in Deutschland. Die CDU/CSU ist für eine marktwirtschaftliche Ordnung, eine pro-europäische Haltung "
            "und die Bewahrung traditioneller Werte bekannt. Ihre Spitzenkandidaten sind häufig zentrale Figuren im "
            "Präsidentschafts- und Bundestagswahlkampf. Friedrich Merz, aktueller Parteivorsitzender, steht für eine stärkere "
            "konservative Ausrichtung. Die Union setzt auf Haushaltsdisziplin, eine restriktivere Migrationspolitik und einen "
            "starken deutschen Beitrag innerhalb der NATO."
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

