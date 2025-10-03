from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from em_backend.models.messages import AnyMessage
from em_backend.vector.db import DocumentChunk


class BaseChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))


class BasePartyChunk(BaseChunk):
    party: str


class PartyTokenChunk(BasePartyChunk):
    type: Literal["party_response"] = "party_response"

    content: str


class PartySourcesChunk(BasePartyChunk):
    type: Literal["party_response_sources"] = "party_response_sources"

    documents: list[DocumentChunk]


class PartyMessageChunk(BasePartyChunk):
    type: Literal["party_message_chunk"] = "party_message_chunk"

    message: AnyMessage


class ComparisonTokenChunk(BaseChunk):
    type: Literal["comparison_response"] = "comparison_response"

    content: str


class ComparisonSourcesChunk(BaseChunk):
    type: Literal["comparison_response_sources"] = "comparison_response_sources"

    documents: dict[str, list[DocumentChunk]]


class ComparisonMessageChunk(BaseChunk):
    type: Literal["message"] = "message"

    message: AnyMessage


class TitleChunk(BaseChunk):
    type: Literal["title"] = "title"

    title: str


class FollowUpQuestionsChunk(BaseChunk):
    type: Literal["follow_up"] = "follow_up"

    follow_up_questions: list[str]


AnyChunk = Annotated[
    PartyTokenChunk
    | PartySourcesChunk
    | PartyMessageChunk
    | ComparisonTokenChunk
    | ComparisonSourcesChunk
    | ComparisonMessageChunk
    | TitleChunk
    | FollowUpQuestionsChunk,
    Field(discriminator="type"),
]
