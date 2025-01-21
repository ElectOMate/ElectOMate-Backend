from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List

class SupportedCountries(str, Enum):
    DE = "de"
    
class Question(BaseModel):
    question: Optional[str] = Field(
        max_length=500,
        description="The question asked to the RAG pipeline."
    )
    
class Response(BaseModel):
    r: str = Field(
        description="The response of the RAG pipeline."
    )

class UserAnswer(BaseModel):
    users_answer: int  # -1, 0, +1
    wheights: str      # "true" / "false"
    Skipped: str       # "true" / "false"
    custom_answer: str

    @classmethod
    def from_json(cls, data: dict):
        return cls(**data)

class QuestionnaireQuestion(BaseModel):
    q: str
    t: str
    fact: str

    @classmethod
    def from_json(cls, data: dict):
        return cls(**data)

class CustomAnswerEvaluationRequest(BaseModel):
    custom_answers: List[UserAnswer]
    questionnaire_questions: List[QuestionnaireQuestion]

    @classmethod
    def from_json(cls, data: dict):
        return cls(**data)


class PartyResponse(BaseModel):
    party: str
    description: str
    policies: List[str]


class AskAllPartiesResponse(BaseModel):
    responses: List[PartyResponse]