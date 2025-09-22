from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from em_backend.old_models import SupportedDocumentFormats


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

    class Config:
        from_attributes = True


class CountryWithElections(CountryResponse):
    elections: list["ElectionResponse"] = []


# Election schemas
class ElectionBase(BaseModel):
    name: str = Field(max_length=255)
    year: int
    date: datetime
    url: str = Field(max_length=500)


class ElectionCreate(ElectionBase):
    country_id: UUID


class ElectionUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    year: int | None = None
    date: datetime | None = None
    url: str | None = Field(None, max_length=500)
    country_id: UUID | None = None


class ElectionResponse(ElectionBase):
    id: UUID
    country_id: UUID

    class Config:
        from_attributes = True


class ElectionWithDetails(ElectionResponse):
    country: CountryResponse
    parties: list["PartyResponse"] = []


# Party schemas
class PartyBase(BaseModel):
    shortname: str = Field(max_length=100)
    fullname: str = Field(max_length=255)
    description: str | None = None
    url: str | None = Field(None, max_length=500)


class PartyCreate(PartyBase):
    election_id: UUID


class PartyUpdate(BaseModel):
    shortname: str | None = Field(None, max_length=100)
    fullname: str | None = Field(None, max_length=255)
    description: str | None = None
    url: str | None = Field(None, max_length=500)
    election_id: UUID | None = None


class PartyResponse(PartyBase):
    id: UUID
    election_id: UUID

    class Config:
        from_attributes = True


class PartyWithDetails(PartyResponse):
    election: ElectionResponse
    candidate: "CandidateResponse | None" = None
    documents: list["DocumentResponse"] = []
    proposed_questions: list["ProposedQuestionResponse"] = []


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

    class Config:
        from_attributes = True


class CandidateWithParty(CandidateResponse):
    party: PartyResponse


# Document schemas
class DocumentBase(BaseModel):
    title: str = Field(max_length=255)
    type: SupportedDocumentFormats
    is_indexed: bool = False
    is_manifesto: bool = False


class DocumentCreate(DocumentBase):
    content: bytes
    party_id: UUID


class DocumentUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    content: bytes | None = None
    type: SupportedDocumentFormats | None = None
    party_id: UUID | None = None
    is_indexed: bool | None = None
    is_manifesto: bool | None = None


class DocumentResponse(DocumentBase):
    id: UUID
    party_id: UUID

    class Config:
        from_attributes = True


class DocumentWithParty(DocumentResponse):
    party: PartyResponse


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

    class Config:
        from_attributes = True


class ProposedQuestionWithParty(ProposedQuestionResponse):
    party: PartyResponse


# Update forward references
CountryWithElections.model_rebuild()
ElectionWithDetails.model_rebuild()
PartyWithDetails.model_rebuild()
CandidateWithParty.model_rebuild()
DocumentWithParty.model_rebuild()
ProposedQuestionWithParty.model_rebuild()
