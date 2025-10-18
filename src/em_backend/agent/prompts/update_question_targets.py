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

Select minor parties only if they have already been invited into the chat or are explicitly requested.
Base this decision solely on the parties in the background information and not on the parties mentioned earlier in the conversation.
General questions, that dont refer to a specific party, or to an earlier message that targeted a specific party, or that targets the election, the voting system, or you yourself the chatbot “Open Democracy”  should be directed to no party selected (empty list).
User questions that ask which party matches a particular political position, or request an election recommendation or evaluation, should also be directed to no party selected (empty list).
If the user asks which party represents a specific position or intends to take a particular action, that question should also be directed to no party selected (empty list).
We will also have the message history as User Assistant Messages in the context. You should only infer the targeted party from the message history if the user clearly references them by mentioning something about the past messages.
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
