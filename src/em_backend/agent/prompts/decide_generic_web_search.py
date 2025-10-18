from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from pydantic import BaseModel, Field


class GenericWebSearchDecision(BaseModel):
    use_web_search: bool = Field(
        ..., description="Whether to trigger web search for additional context."
    )
    reason: str = Field(
        ..., description="Short explanation of the decision for logging purposes."
    )


DECIDE_GENERIC_WEB_SEARCH = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            """# Role

Decide whether the assistant should enrich its answer with a live Perplexity web search.

# Context

- Election: {election_name} ({election_year})
- Today's date: {date}
- Preferred answer language: {response_language_name}

# Decision criteria

Use web search if the latest user message asks about:
- Recent developments after October 2023.
- Factual questions that likely require up-to-date news or statistics.
- Topics explicitly referencing "latest", "current", "today", or similar phrases.

Skip web search if:
- The question can be answered from timeless background knowledge.
- The user is asking about the platform itself.
- The conversation has already covered the answer with high confidence.
- The user is requesting guidance outside the project's scope.

Respond with `true` only when web search clearly adds value. Always provide a concise reason for your choice.
"""
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
