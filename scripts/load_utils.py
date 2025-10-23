from __future__ import annotations

from collections.abc import Generator, Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi.testclient import TestClient

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


@dataclass(frozen=True, slots=True)
class ElectionSeed:
    name: str
    year: int
    date: datetime
    url: str
    wv_collection: str

    def to_create(self, country_id: UUID) -> ElectionCreate:
        return ElectionCreate(
            name=self.name,
            year=self.year,
            date=self.date,
            url=self.url,
            wv_collection=self.wv_collection,
            country_id=country_id,
        )


@dataclass(frozen=True, slots=True)
class PartySeed:
    shortname: str
    fullname: str
    description: str
    url: str | None

    def to_create(self, election_id: UUID) -> PartyCreate:
        return PartyCreate(
            shortname=self.shortname,
            fullname=self.fullname,
            description=self.description,
            url=self.url,
            election_id=election_id,
        )


@dataclass(frozen=True, slots=True)
class CandidateSeed:
    given_name: str
    family_name: str
    description: str
    url: str

    def to_create(self, party_id: UUID) -> CandidateCreate:
        return CandidateCreate(
            given_name=self.given_name,
            family_name=self.family_name,
            description=self.description,
            url=self.url,
            party_id=party_id,
        )


@contextmanager
def get_app_client() -> Generator[TestClient, None, None]:
    from em_backend.main import app

    with TestClient(app) as client:
        yield client


def create_country(client: TestClient, payload: CountryCreate) -> CountryResponse:
    response = client.post(
        "/v2/countries",
        content=payload.model_dump_json(),
        headers={"content-type": "application/json"},
    )
    response.raise_for_status()
    return CountryResponse.model_validate_json(response.text)


def create_election(
    client: TestClient, payload: ElectionCreate
) -> ElectionResponse:
    response = client.post(
        "/v2/elections",
        content=payload.model_dump_json(),
        headers={"content-type": "application/json"},
    )
    response.raise_for_status()
    return ElectionResponse.model_validate_json(response.text)


def create_party(
    client: TestClient, payload: PartyCreate
) -> PartyResponse:
    response = client.post(
        "/v2/parties/",
        content=payload.model_dump_json(),
        headers={"content-type": "application/json"},
    )
    response.raise_for_status()
    return PartyResponse.model_validate_json(response.text)


def create_candidate(
    client: TestClient, payload: CandidateCreate
) -> CandidateResponse:
    response = client.post(
        "/v2/candidates/",
        content=payload.model_dump_json(),
        headers={"content-type": "application/json"},
    )
    response.raise_for_status()
    return CandidateResponse.model_validate_json(response.text)


def create_parties(
    client: TestClient,
    party_payloads: Iterable[PartyCreate],
) -> dict[str, UUID]:
    party_ids: dict[str, UUID] = {}
    for payload in party_payloads:
        response = create_party(client, payload)
        party_ids[payload.shortname] = response.id
    return party_ids

