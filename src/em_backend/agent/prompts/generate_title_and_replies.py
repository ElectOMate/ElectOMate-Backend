from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from pydantic import BaseModel, Field

GENERATE_TITLE_AND_REPLIES = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            """# Role

You generate the title and quick replies for a chat in which the following parties are represented:
{party_list}
You receive a conversation history and generate a title for the chat as well as quick replies for the user.

# Instructions

## For the Chat Title

Generate a short title for the chat. It should briefly and concisely describe the content of the chat in 3–5 words.

## For the Quick Replies

Generate 3 quick replies that the user could send in response to the parties latest messages.
The 3 quick replies should cover the following response types (in this order):

- A direct follow-up question to the answer(s) given since the user's last message. Use formulations like “How do you want to…?”, “What is your stance on…?”, “How can…?” etc.
- A question asking for definitions or explanations of complicated terms. If this refers to terms from a specific party only, include that party’s name in the question (e.g., “What does <Party-Name> mean by…?”).
- A question that switches to a different, specific campaign topic.

Make sure that:

- The quick replies are directed at the party/parties.
- The quick replies are especially relevant or pressing in relation to the given party/parties.
- The quick replies are short and concise. Quick replies must be no longer than seven words.

# Output Format

Stick to the required JSON answer structure.
"""
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


class GenerateTitleAndRepliedStructuredOutput(BaseModel):
    conversation_title: str = Field(description="Title for the conversation")
    follow_up_one: str = Field(description="Direct follow-up question")
    follow_up_two: str = Field(description="Follow-up asking for definitions")
    follow_up_three: str = Field(description="Question switching to a different topic")
