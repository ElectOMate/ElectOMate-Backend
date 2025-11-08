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


class CreatedAtMixin(MappedAsDataclass):
    """Adds a column in the relationship with a UTC created_at timestamp."""

    created_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, init=False
    )


class Country(Base, CreatedAtMixin):
    __tablename__ = "country_table"

    name: Mapped[str]
    code: Mapped[str] = mapped_column(CHAR(2), unique=True)

    elections: Mapped[list["Election"]] = relationship(
        default_factory=list, back_populates="country", cascade="all, delete-orphan"
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)

    def __repr__(self) -> str:
        return f"Country(id={self.id}, name='{self.name}', code='{self.code}')"


class Election(Base, CreatedAtMixin):
    __tablename__ = "election_table"

    name: Mapped[str]
    year: Mapped[int]
    date: Mapped[datetime]
    url: Mapped[str]
    wv_collection: Mapped[str]

    country_id: Mapped[UUID] = mapped_column(ForeignKey("country_table.id", ondelete="CASCADE"))
    country: Mapped[Country] = relationship(default=None)

    parties: Mapped[list["Party"]] = relationship(
        default_factory=list, back_populates="election", cascade="all, delete-orphan"
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)

    def __repr__(self) -> str:
        return (
            f"Election(id={self.id}, name='{self.name}', "
            f"year={self.year}, country_id={self.country_id})"
        )


class Party(Base, CreatedAtMixin):
    __tablename__ = "party_table"

    shortname: Mapped[str]
    fullname: Mapped[str]
    description: Mapped[str | None]
    url: Mapped[str | None]

    election_id: Mapped[UUID] = mapped_column(ForeignKey("election_table.id", ondelete="CASCADE"))
    election: Mapped[Election] = relationship(default=None)

    candidate: Mapped["Candidate"] = relationship(default=None, back_populates="party", cascade="all, delete-orphan")

    documents: Mapped[list["Document"]] = relationship(
        default_factory=list, back_populates="party", cascade="all, delete-orphan"
    )

    proposed_questions: Mapped[list["ProposedQuestion"]] = relationship(
        default_factory=list, back_populates="party", cascade="all, delete-orphan"
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)

    def __repr__(self) -> str:
        return (
            f"Party(id={self.id}, shortname='{self.shortname}', "
            f"fullname='{self.fullname}', election_id={self.election_id})"
        )


class Candidate(Base, CreatedAtMixin):
    __tablename__ = "candidate_table"

    given_name: Mapped[str]
    family_name: Mapped[str]
    description: Mapped[str | None]
    url: Mapped[str | None]

    party_id: Mapped[UUID] = mapped_column(ForeignKey("party_table.id", ondelete="CASCADE"))
    party: Mapped[Party] = relationship(default=None)

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)

    def __repr__(self) -> str:
        return (
            f"Candidate(id={self.id}, given_name='{self.given_name}', "
            f"family_name='{self.family_name}', party_id={self.party_id})"
        )


class Document(Base, CreatedAtMixin):
    __tablename__ = "document_table"

    title: Mapped[str]
    type: Mapped[SupportedDocumentFormats]

    party_id: Mapped[UUID] = mapped_column(ForeignKey("party_table.id", ondelete="CASCADE"))
    party: Mapped[Party] = relationship(default=None)

    content: Mapped[str | None] = mapped_column(default=None)
    parsing_quality: Mapped[ParsingQuality] = mapped_column(
        default=ParsingQuality.NO_PARSING
    )
    indexing_success: Mapped[IndexingSuccess] = mapped_column(
        default=IndexingSuccess.NO_INDEXING
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)

    def __repr__(self) -> str:
        return (
            f"Document(id={self.id}, title='{self.title}', "
            f"type={self.type}, party_id={self.party_id})"
        )


class ProposedQuestion(Base, CreatedAtMixin):
    __tablename__ = "proposed_question_table"

    question: Mapped[str]

    party_id: Mapped[UUID] = mapped_column(ForeignKey("party_table.id", ondelete="CASCADE"))
    party: Mapped[Party] = relationship(default=None)

    cached_answer: Mapped[str | None] = mapped_column(default=None)

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)

    def __repr__(self) -> str:
        question_preview = (
            self.question[:50] + "..." if len(self.question) > 50 else self.question
        )
        return (
            f"ProposedQuestion(id={self.id}, question='{question_preview}', "
            f"party_id={self.party_id})"
        )


class QuizQuestion(Base, CreatedAtMixin):
    __tablename__ = "quiz_question_table"

    question: Mapped[str]
    option_a: Mapped[str]
    option_b: Mapped[str]
    option_c: Mapped[str]
    option_d: Mapped[str]
    correct_answer: Mapped[int | None] = mapped_column(default=None)  # 0-3, or None if no correct answer
    category: Mapped[str | None] = mapped_column(default=None)
    difficulty: Mapped[str | None] = mapped_column(default=None)  # easy, medium, hard
    is_active: Mapped[bool] = mapped_column(default=True)

    country_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("country_table.id", ondelete="SET NULL"), default=None
    )
    country: Mapped[Country | None] = relationship(default=None, init=False)

    submissions: Mapped[list["QuizSubmission"]] = relationship(
        default_factory=list, back_populates="question", cascade="all, delete-orphan", init=False
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, init=False)

    def __repr__(self) -> str:
        question_preview = (
            self.question[:50] + "..." if len(self.question) > 50 else self.question
        )
        return (
            f"QuizQuestion(id={self.id}, question='{question_preview}', "
            f"category='{self.category}')"
        )


class QuizSubmission(Base, CreatedAtMixin):
    __tablename__ = "quiz_submission_table"

    selected_option: Mapped[int]  # 0-3 corresponding to A, B, C, D
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("quiz_question_table.id", ondelete="CASCADE")
    )
    session_id: Mapped[str | None] = mapped_column(default=None)  # To group submissions from same quiz session
    user_id: Mapped[str | None] = mapped_column(default=None)  # For authenticated users

    question: Mapped[QuizQuestion] = relationship(default=None, init=False)

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, init=False)

    def __repr__(self) -> str:
        return (
            f"QuizSubmission(id={self.id}, question_id={self.question_id}, "
            f"selected_option={self.selected_option})"
        )


# ===== Quiz Results Storage Tables =====
# These tables store complete quiz results with all question details
# Questions are loaded from frontend JSON files, not from QuizQuestion table


class QuizResult(Base, CreatedAtMixin):
    """
    Stores overall quiz submission results.

    This is denormalized storage that duplicates question text from frontend JSON files
    to maintain a complete historical record of what the user saw and answered.
    """
    __tablename__ = "quiz_result_table"

    submission_id: Mapped[str] = mapped_column(unique=True, index=True)
    submitted_at: Mapped[datetime]
    score: Mapped[int]  # Percentage 0-100
    correct_count: Mapped[int]
    total_questions: Mapped[int]
    session_id: Mapped[str | None] = mapped_column(default=None)
    user_id: Mapped[str | None] = mapped_column(default=None)
    country_code: Mapped[str | None] = mapped_column(default=None)  # 2-letter country code (e.g., 'DE', 'CL')

    # Relationships
    answers: Mapped[list["QuizResultAnswer"]] = relationship(
        back_populates="quiz_result",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, init=False)

    def __repr__(self) -> str:
        return (
            f"QuizResult(id={self.id}, submission_id={self.submission_id}, "
            f"score={self.score}, correct_count={self.correct_count}/{self.total_questions})"
        )


class QuizResultAnswer(Base, CreatedAtMixin):
    """
    Stores individual answer details for each quiz result.

    This stores the complete question text and selected answer to maintain
    a historical record, since questions come from frontend JSON files.
    """
    __tablename__ = "quiz_result_answer_table"

    question_number: Mapped[int]
    question_text: Mapped[str]
    selected_answer: Mapped[str]  # Letter: A, B, C, or D
    selected_answer_text: Mapped[str]
    is_correct: Mapped[bool]

    # Foreign key to quiz result
    quiz_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("quiz_result_table.id", ondelete="CASCADE"),
        init=False,
    )

    # Relationship back to quiz result
    quiz_result: Mapped[QuizResult] = relationship(
        back_populates="answers",
        default=None,
        init=False,
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, init=False)

    def __repr__(self) -> str:
        return (
            f"QuizResultAnswer(id={self.id}, question_number={self.question_number}, "
            f"selected={self.selected_answer}, correct={self.is_correct})"
        )


# ===== Questionnaire Results Storage Tables =====
# These tables store complete questionnaire results with all question answers
# This is for the yes/no/neutral political questionnaire feature


class QuestionnaireResult(Base, CreatedAtMixin):
    """
    Stores overall questionnaire submission results.

    This stores the complete anonymous questionnaire submission including all user answers.
    """
    __tablename__ = "questionnaire_result_table"

    result_id: Mapped[str] = mapped_column(unique=True, index=True)
    user_id: Mapped[str]  # Anonymous persistent user ID from localStorage
    submitted_at: Mapped[datetime]
    total_questions: Mapped[int]
    answered_questions: Mapped[int]  # Questions not skipped
    weighted_questions: Mapped[int]  # Questions with weight enabled
    custom_answers_count: Mapped[int]  # Questions with custom text answers
    country_code: Mapped[str | None] = mapped_column(default=None)  # 2-letter country code (e.g., 'DE', 'CL')

    # Relationship to individual question answers
    questions: Mapped[list["QuestionnaireAnswer"]] = relationship(
        back_populates="questionnaire_result",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )

    # Relationship to party rankings
    party_rankings: Mapped[list["PartyRanking"]] = relationship(
        back_populates="questionnaire_result",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, init=False)

    def __repr__(self) -> str:
        return (
            f"QuestionnaireResult(id={self.id}, result_id={self.result_id}, "
            f"user_id={self.user_id[:8]}..., answered={self.answered_questions}/{self.total_questions})"
        )


class QuestionnaireAnswer(Base, CreatedAtMixin):
    """
    Stores individual question answers for each questionnaire result.

    This stores the complete question text and user's answer (yes/no/neutral/skipped)
    along with weight preference and optional custom text answer.
    """
    __tablename__ = "questionnaire_answer_table"

    question_number: Mapped[int]
    question_text: Mapped[str]
    answer: Mapped[str]  # yes, no, neutral, or skipped
    weight_enabled: Mapped[bool]
    custom_answer: Mapped[str | None] = mapped_column(default=None)

    # Foreign key to questionnaire result
    questionnaire_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("questionnaire_result_table.id", ondelete="CASCADE"),
        init=False,
    )

    # Relationship back to questionnaire result
    questionnaire_result: Mapped[QuestionnaireResult] = relationship(
        back_populates="questions",
        default=None,
        init=False,
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, init=False)

    def __repr__(self) -> str:
        return (
            f"QuestionnaireAnswer(id={self.id}, question_number={self.question_number}, "
            f"answer={self.answer}, weight_enabled={self.weight_enabled})"
        )


class PartyRanking(Base, CreatedAtMixin):
    """
    Stores party ranking results calculated from questionnaire answers.

    Each row represents a single party's score/ranking for a specific questionnaire submission.
    This allows efficient querying of which parties users matched with most.
    """
    __tablename__ = "party_ranking_table"

    party_short_name: Mapped[str]  # e.g., "CDU", "SPD"
    party_full_name: Mapped[str]  # e.g., "Christian Democratic Union"
    score: Mapped[float]  # Match percentage (0-100)
    rank: Mapped[int]  # Position in ranking (1 = highest match, 2 = second, etc.)

    # Foreign key to questionnaire result
    questionnaire_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("questionnaire_result_table.id", ondelete="CASCADE"),
        init=False,
    )

    # Relationship back to questionnaire result
    questionnaire_result: Mapped[QuestionnaireResult] = relationship(
        back_populates="party_rankings",
        default=None,
        init=False,
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, init=False)

    def __repr__(self) -> str:
        return (
            f"PartyRanking(id={self.id}, party={self.party_short_name}, "
            f"score={self.score:.1f}%, rank={self.rank})"
        )
