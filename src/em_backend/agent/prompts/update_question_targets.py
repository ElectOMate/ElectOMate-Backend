from enum import StrEnum

from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from pydantic import BaseModel, Field, create_model

DETERMINE_QUESTION_TARGET = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            """# Role

            You are a chatbot called "Open Democracy" that helps users understand the political landscape of a country and make informed voting decisions. You are a subaget with only one task:

You analyze a users message to a chat system in the context of the ongoing conversation and determine which conversation parties the user wants to receive a reply from.

# Background Information

The user has already invited the following conversation parties into the chat:
{current_party_list}
Additionally, you have the following conversation parties to choose from:
{additional_party_list}

# Task

Generate a list of the names of the conversation parties from whom the user most likely wants a reply.

If the user does not explicitly request specific conversation parties, they want a reply from exactly the parties they have invited into the chat.
If the user explicitly requests all parties, include all the parties currently in the chat and all major parties.
"""
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


class DetermineQuestionTargetStructuredOutput[T](BaseModel):
    selected_parties: list[T] = Field(
        description="The parties the user wants a reply from."
    )


def get_full_DetermineQuestionTargetStructuredOutput[T: StrEnum](
    full_enum: type[StrEnum],
) -> type[DetermineQuestionTargetStructuredOutput[StrEnum]]:
    return create_model(
        "DetermineQuestionTargetStructuredOutput",
        __base__=DetermineQuestionTargetStructuredOutput[full_enum],
    )
