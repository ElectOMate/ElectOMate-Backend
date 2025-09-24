from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CHAR, ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

from em_backend.models.enums import (
    IndexingSuccess,
    ParsingQuality,
    SupportedDocumentFormats,
)


class Base(MappedAsDataclass, DeclarativeBase, AsyncAttrs):
    """Base Class for all SQLAlchemy models."""

    pass


class Country(Base):
    __tablename__ = "country_table"

    name: Mapped[str]
    code: Mapped[str] = mapped_column(CHAR(2), unique=True)

    elections: Mapped[list["Election"]] = relationship(
        default_factory=list, back_populates="country"
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)


class Election(Base):
    __tablename__ = "election_table"

    name: Mapped[str]
    year: Mapped[int]
    date: Mapped[datetime]
    url: Mapped[str]
    wv_collection: Mapped[str]

    country_id: Mapped[UUID] = mapped_column(ForeignKey("country_table.id"))
    country: Mapped[Country] = relationship(default=None)

    parties: Mapped[list["Party"]] = relationship(
        default_factory=list, back_populates="election"
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)


class Party(Base):
    __tablename__ = "party_table"

    shortname: Mapped[str]
    fullname: Mapped[str]
    description: Mapped[str | None]
    url: Mapped[str | None]

    election_id: Mapped[UUID] = mapped_column(ForeignKey("election_table.id"))
    election: Mapped[Election] = relationship(default=None)

    candidate: Mapped["Candidate"] = relationship(default=None, back_populates="party")

    documents: Mapped[list["Document"]] = relationship(
        default_factory=list, back_populates="party"
    )

    proposed_questions: Mapped[list["ProposedQuestion"]] = relationship(
        default_factory=list, back_populates="party"
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)


class Candidate(Base):
    __tablename__ = "candidate_table"

    given_name: Mapped[str]
    family_name: Mapped[str]
    description: Mapped[str | None]
    url: Mapped[str | None]

    party_id: Mapped[UUID] = mapped_column(ForeignKey("party_table.id"))
    party: Mapped[Party] = relationship(default=None)

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)


class Document(Base):
    __tablename__ = "document_table"

    title: Mapped[str]
    type: Mapped[SupportedDocumentFormats]

    party_id: Mapped[UUID] = mapped_column(ForeignKey("party_table.id"))
    party: Mapped[Party] = relationship(default=None)

    content: Mapped[str | None] = mapped_column(default=None)
    parsing_quality: Mapped[ParsingQuality] = mapped_column(
        default=ParsingQuality.NO_PARSING
    )
    indexing_sucess: Mapped[IndexingSuccess] = mapped_column(
        default=IndexingSuccess.NO_INDEXING
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)


class ProposedQuestion(Base):
    __tablename__ = "proposed_question_table"

    question: Mapped[str]

    party_id: Mapped[UUID] = mapped_column(ForeignKey("party_table.id"))
    party: Mapped[Party] = relationship(default=None)

    cached_answer: Mapped[str | None] = mapped_column(default=None)

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
