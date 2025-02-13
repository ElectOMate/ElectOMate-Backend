from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict
from enum import Enum


class SupportedLanguages(str, Enum):
    DE = "de"
    EN = "en"


class Question(BaseModel):
    question: str = Field(
        max_length=500, description="The question asked to the RAG pipeline."
    )
    rerank: bool = Field(
        default=False, description="Use more advanced reranking models"
    )


class ChatFunctionCallRequest(BaseModel):
    country_code: str
    question_body: Question  # e.g. "question": "User's RAG query"


class Answer(BaseModel):
    answer: str = Field(description="The response of the RAG pipeline.")
    citations: list[dict[str, str]] = Field(
        default_factory=list,
        description="A list of citations with a title and content.",
    )


class AnswerChunk(BaseModel):
    type: Literal["response-chunk", "citation"] = Field(
        description="The type of the chunk, either a chunk of the response or a citation."
    )
    title: Optional[str] = Field(
        description="The title of the citation if the type of the chunk is 'citation'"
    )
    text: Optional[str] = Field(
        description="The chunk content. A part of the answer if chunk type is 'response-chunk'. The citation content if chunk type is 'citation'"
    )


class RealtimeToken(BaseModel):
    client_secret: str = Field(
        description="A realtime session token to be used in the browser directly."
    )


class PartyResponse(BaseModel):
    party: str
    policies: list[str]


class AskAllPartiesResponse(BaseModel):
    responses: list[PartyResponse]


class AskAllPartiesRequest(BaseModel):
    question_body: Question
    selected_parties: Dict[str, bool]


class SearchQuery(BaseModel):
    query: str


class QuestionnaireQuestion(BaseModel):
    q: str
    id: int
    context: Optional[str] = None


class UserAnswer(BaseModel):
    custom_answer: str
    users_answer: str
    wheights: str
    skipped: bool
