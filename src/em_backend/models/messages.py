from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))


class UserMessage(BaseMessage):
    type: Literal["user"] = "user"

    content: str


class AssistantMessage(BaseMessage):
    type: Literal["assistant"] = "assistant"

    content: str


AnyMessage = Annotated[UserMessage | AssistantMessage, Field(discriminator="type")]
