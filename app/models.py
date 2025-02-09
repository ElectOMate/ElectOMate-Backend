from pydantic import BaseModel, Field, model_validator, HttpUrl
from typing import Literal, Optional, Dict, Union
from typing_extensions import Self
from enum import Enum


class SupportedLanguages(str, Enum):
    DE = "de"
    EN = "en"


class SupportedParties(str, Enum):
    AFD = "afd"
    BSW = "bsw"
    CDU = "cdu"
    FDP = "fdp"
    GRUNE = "grune"
    LINKE = "linke"
    SPD = "spd"


class Question(BaseModel):
    question: str = Field(
        max_length=500, description="The question asked to the RAG pipeline."
    )
    web_search: bool = Field(
        description="Wether the AI is allowed to do a web search", default=False
    )
    selected_parties: list[SupportedParties] = Field(
        description="The parties selected to answer"
    )

    @model_validator(mode="after")
    def check_model(self) -> Self:
        if self.web_search is True and len(self.selected_parties) > 1:
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
    title: str = Field(description="The title of the paragraph citation")
    content: str = Field(description="The content of the paragraph citation")
    manifesto: SupportedParties = Field(
        description="The party whose manifesto is cited"
    )
    text: str = Field(description="The part of the answer this citation corresponds to")


class WebCitation(BaseModel):
    title: str = Field(description="The title of the web page")
    content: str = Field(description="The content of web page")
    url: HttpUrl = Field(description="The url of the web page")
    text: str = Field(description="The part of the answer this citation corresponds to")


class StandardAnswer(BaseModel):
    type: Literal["standard-answer"]
    answer: str = Field(description="The answer returned by the LLM")
    citations: list[ManifestoCitation]


class SinglePartyAnswer(BaseModel):
    answer: str = Field(
        description="The answer returned by the LLM for that specific party"
    )
    party: SupportedParties = Field(description="The party the LLM answer is based on")
    citations: list[ManifestoCitation]


class MultiPartyAnswer(BaseModel):
    type: Literal["multi-party-answer"]
    answers: list[SinglePartyAnswer]


class WebSearchAnswer(BaseModel):
    type: Literal["web-search-answer"]
    answer: str = Field(description="The answer returned by the LLM")
    citations: list[WebCitation]


class Answer(BaseModel):
    answer: Union[StandardAnswer, MultiPartyAnswer, WebSearchAnswer] = Field(
        discriminator="type"
    )


class AnswerTypeChunk(BaseModel):
    type: Literal["answer-type-chunk"]
    answer_type: Literal["standard-answer", "multi-party-answer", "web-search-answer"]


class StandardAnswerChunk(BaseModel):
    type: Literal["standard-answer-chunk"]
    answer_delta: str = Field(description="A sub-part of the LLLM answer")


class MultiPartyAnswerChunk(BaseModel):
    type: Literal["multi-party-answer-chunk"]
    answer_delta: str = Field(
        description="A sub-part of the LLM answer for the specific party"
    )
    party: SupportedParties = Field(description="The party the LLM answer is based on")


class WebSearchAnswerChunk(BaseModel):
    type: Literal["web-search-answer-chunk"]
    answer_delta: str = Field(description="the sub-part of the LLM answer")


class ManifestoCitationChunk(BaseModel):
    type: Literal["manifesto-citation-chunk"]
    citation: ManifestoCitation


class WebCitationChunk(BaseModel):
    type: Literal["web-citation-chunk"]
    citation: WebCitation


class AnswerChunk(BaseModel):
    chunk: Union[
        AnswerTypeChunk,
        StandardAnswerChunk,
        MultiPartyAnswerChunk,
        WebSearchAnswerChunk,
        ManifestoCitationChunk,
        WebCitationChunk,
    ] = Field(discriminator="type")


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
