import string
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from em_backend.models.enums import (
    IndexingSuccess,
    ParsingQuality,
    SupportedDocumentFormats,
)


# Base schemas
class CountryBase(BaseModel):
    name: str = Field(max_length=255)
    code: str = Field(max_length=2)


class CountryCreate(CountryBase):
    pass


class CountryUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    code: str | None = Field(None, max_length=2)


class CountryResponse(CountryBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Election schemas
class ElectionBase(BaseModel):
    name: str = Field(max_length=255)
    year: int
    date: datetime
    url: str = Field(max_length=500)
    wv_collection: str = Field(
        default_factory=lambda data: "D"
        + str(data["year"])
        + "".join(ch for ch in data["name"].lower() if ch in string.ascii_lowercase),
        pattern=r"[A-Za-z0-9]+",
    )


class ElectionCreate(ElectionBase):
    country_id: UUID


class ElectionUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    year: int | None = None
    date: datetime | None = None
    url: str | None = Field(None, max_length=500)
    country_id: UUID | None = None
    wv_collection: str | None = Field(
        default=None,
        pattern=r"[A-Za-z0-9]+",
    )


class ElectionResponse(ElectionBase):
    id: UUID
    country_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Party schemas
class PartyBase(BaseModel):
    shortname: str = Field(max_length=100)
    fullname: str = Field(max_length=255)
    description: str | None = None
    url: str | None = Field(None, max_length=500)


class PartyCreate(PartyBase):
    election_id: UUID


class ExistingPartyCreate(PartyBase):
    election_id: UUID
    existing_documents: list["ExistingDocumentCreate"] = Field(default_factory=list)


class PartyUpdate(BaseModel):
    shortname: str | None = Field(None, max_length=100)
    fullname: str | None = Field(None, max_length=255)
    description: str | None = None
    url: str | None = Field(None, max_length=500)
    election_id: UUID | None = None


class PartyResponse(PartyBase):
    id: UUID
    election_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Candidate schemas
class CandidateBase(BaseModel):
    given_name: str = Field(max_length=100)
    family_name: str = Field(max_length=100)
    description: str | None = None
    url: str | None = Field(None, max_length=500)


class CandidateCreate(CandidateBase):
    party_id: UUID


class CandidateUpdate(BaseModel):
    given_name: str | None = Field(None, max_length=100)
    family_name: str | None = Field(None, max_length=100)
    description: str | None = None
    url: str | None = Field(None, max_length=500)
    party_id: UUID | None = None


class CandidateResponse(CandidateBase):
    id: UUID
    party_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Document schemas
class DocumentBase(BaseModel):
    title: str = Field(max_length=255)
    type: SupportedDocumentFormats
    parsing_quality: ParsingQuality = ParsingQuality.UNSPECIFIED
    indexing_success: IndexingSuccess = IndexingSuccess.NO_INDEXING


class DocumentCreate(DocumentBase):
    content: str | None = None
    party_id: UUID


class ExistingDocumentCreate(DocumentBase):
    id: UUID


class DocumentUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    content: str | None = None
    type: SupportedDocumentFormats | None = None
    party_id: UUID | None = None
    parsing_quality: ParsingQuality | None = None
    indexing_success: IndexingSuccess | None = None


class DocumentResponse(DocumentBase):
    id: UUID
    party_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentResponseWithContent(DocumentResponse):
    content: str


# ProposedQuestion schemas
class ProposedQuestionBase(BaseModel):
    question: str = Field(max_length=1000)
    cached_answer: str | None = None


class ProposedQuestionCreate(ProposedQuestionBase):
    party_id: UUID


class ProposedQuestionUpdate(BaseModel):
    question: str | None = Field(None, max_length=1000)
    cached_answer: str | None = None
    party_id: UUID | None = None


class ProposedQuestionResponse(ProposedQuestionBase):
    id: UUID
    party_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
