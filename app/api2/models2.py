from pydantic import BaseModel, Field, HttpUrl, field_validator
from enum import Enum
from typing import Union, Literal, List, Dict

class SupportedLanguages(str, Enum):
    DE = "de"
    EN = "en"

class SupportedParties(str, Enum):
  CDU_CSU = "CDU/CSU",
  SPD = "SPD",
  GRUENE = "GRUENE",
  FDP = "FDP",
  AFD = "AfD",
  DIE_LINKE = "DIE LINKE",
  FREIE_WAEHLER = "FREIE WÄHLER",
  VOLT = "Volt",
  MLPD = "MLPD",
  BUENDNIS_DEUTSCHLAND = "BÜNDNIS DEUTSCHLAND",
  BSW = "BSW",
  # Example mapping if 'CDU/CSU' should map to 'cdu'

class Question(BaseModel):
    question: str = Field(max_length=500)
    web_search: bool = Field(default=False)
    selected_parties: List[str] = Field(default=[])

    @field_validator('selected_parties', mode='before')
    def map_selected_parties(cls, v):
        party_map = {
            'CDU/CSU': SupportedParties.CDU_CSU,
            'SPD': SupportedParties.SPD,
            'GRUENE': SupportedParties.GRUENE,
            'FDP': SupportedParties.FDP,
            'AfD': SupportedParties.AFD,
            'DIE LINKE': SupportedParties.DIE_LINKE,
            'FREIE WÄHLER': SupportedParties.FREIE_WAEHLER,
            'Volt': SupportedParties.VOLT,
            'MLPD': SupportedParties.MLPD,
            'BÜNDNIS DEUTSCHLAND': SupportedParties.BUENDNIS_DEUTSCHLAND,
            'BSW': SupportedParties.BSW
        }
        if isinstance(v, list):
            return [party_map.get(item, item) for item in v]
        return v

    @field_validator('web_search')
    def validate_web_search(cls, v, info):
        if v and len(info.data.get('selected_parties', [])) > 0:
            raise ValueError("Web search cannot be combined with party selection")
        return v

class ManifestoCitation(BaseModel):
    title: str
    content: str
    manifesto: SupportedParties
    text: str

class WebCitation(BaseModel):
    title: str
    content: str
    url: HttpUrl
    text: str

class AnswerTypeChunk(BaseModel):
    type: Literal["answer-type-chunk"]
    answer_type: Literal["standard-answer", "multi-party-answer", "web-search-answer"]

class StandardAnswerChunk(BaseModel):
    type: Literal["standard-answer-chunk"]
    answer_delta: str

class MultiPartyAnswerChunk(BaseModel):
    type: Literal["multi-party-answer-chunk"]
    answer_delta: str
    party: SupportedParties

class WebSearchAnswerChunk(BaseModel):
    type: Literal["web-search-answer-chunk"]
    answer_delta: str

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
    ] = Field(..., discriminator="type")

class ChatFunctionCallRequest(BaseModel):
    country_code: SupportedLanguages
    question_body: Question 