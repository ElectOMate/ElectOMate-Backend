from pydantic import BaseModel, Field, model_validator, HttpUrl
from typing import Literal, Union
from typing_extensions import Self
from enum import Enum
from typing import Optional


class SupportedLanguages(str, Enum):
    DE = "de"
    EN = "en"


class SupportedParties(str, Enum):
    AFD = "afd"
    BSW = "bsw"
    BUENDNIS = "buendnis"
    CDU = "cdu"
    FDP = "fdp"
    FREIE = "freie"
    GRUNE = "grune"
    LINKE = "linke"
    MLPD = "mlpd"
    SPD = "spd"
    VOLT = "volt"


class Question(BaseModel):
    question: str = Field(
        max_length=500, description="The question asked to the RAG pipeline."
    )
    use_web_search: bool = Field(
        description="Wether the AI is allowed to do a web search", default=False
    )
    use_database_search: bool = Field(
        description="Wether the AI is allowed to do a manifesto search", default=True
    )
    selected_parties: list[SupportedParties] = Field(
        description="The parties selected to answer"
    )

    @model_validator(mode="after")
    def check_model(self) -> Self:
        if self.use_web_search is False and self.use_database_search is False:
            return ValueError(
                "Model Validation Error. You have to at least use one of web search or database search."
            )
        if self.use_web_search is True and len(self.selected_parties) > 1:
            return ValueError(
                "Model Validation Error. Web search cannot be activated when parties are selected."
            )
        return self


class ChatFunctionCallRequest(BaseModel):
    country_code: SupportedLanguages = Field(
        description="The language the question was asked in."
    )
    question_body: Question


class ManifestoCitation(BaseModel):
    type: Literal["manifesto-citation"]
    title: str = Field(description="The title of the paragraph citation")
    content: str = Field(description="The content of the paragraph citation")
    manifesto: SupportedParties = Field(
        description="The party whose manifesto is cited"
    )
    citation_start: int = Field(
        description="The start index of the citation in the answer"
    )
    citation_end: int = Field(description="The end index of the citation in the answer")


class WebCitation(BaseModel):
    type: Literal["web-citation"]
    title: str = Field(description="The title of the web page")
    content: str = Field(description="The content of web page")
    url: HttpUrl = Field(description="The url of the web page")
    citation_start: int = Field(
        description="The start index of the citation in the answer"
    )
    citation_end: int = Field(description="The end index of the citation in the answer")


class Citation(BaseModel):
    citation: Union[ManifestoCitation, WebCitation] = Field(discriminator="type")


class StandardAnswer(BaseModel):
    type: Literal["standard-answer"]
    answer: str = Field(description="The answer returned by the LLM")
    citations: list[Citation]


class SinglePartyAnswer(BaseModel):
    answer: str = Field(
        description="The answer returned by the LLM for that specific party"
    )
    party: SupportedParties = Field(description="The party the LLM answer is based on")
    citations: list[Citation]


class MultiPartyAnswer(BaseModel):
    type: Literal["multi-party-answer"]
    answers: list[SinglePartyAnswer]


class Answer(BaseModel):
    answer: Union[StandardAnswer, MultiPartyAnswer] = Field(discriminator="type")


class AnswerTypeChunk(BaseModel):
    type: Literal["answer-type-chunk"]
    answer_type: Literal["standard-answer", "multi-party-answer"]


class StandardAnswerChunk(BaseModel):
    type: Literal["standard-answer-chunk"]
    answer_delta: str = Field(description="A sub-part of the LLLM answer")


class MultiPartyAnswerChunk(BaseModel):
    type: Literal["multi-party-answer-chunk"]
    answer_delta: str = Field(
        description="A sub-part of the LLM answer for the specific party"
    )
    party: SupportedParties = Field(description="The party the LLM answer is based on")


class CitationChunk(BaseModel):
    type: Literal["manifesto-citation-chunk"]
    citation: Citation


class AnswerChunk(BaseModel):
    chunk: Union[
        AnswerTypeChunk, StandardAnswerChunk, MultiPartyAnswerChunk, CitationChunk
    ] = Field(discriminator="type")


class RealtimeToken(BaseModel):
    client_secret: str = Field(
        description="A realtime session token to be used in the browser directly."
    )


class CustomAnswer(BaseModel):
    question: str
    question_id: int
    users_answer: int
    wheights: str
    Skipped: str
    custom_answer: str


class EvaluationRequest(BaseModel):
    custom_answers: list[CustomAnswer]


class QuestionnaireQuestion(BaseModel):
    q: str
    id: int
    context: Optional[str] = Field(default=None)


class UserAnswer(BaseModel):
    custom_answer: str
    users_answer: str
    wheights: str
    skipped: bool