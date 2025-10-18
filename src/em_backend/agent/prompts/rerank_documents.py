from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from pydantic import BaseModel, Field

RERANK_DOCUMENTS = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            """# Role

You are a reranking system that orders the given sources in descending order of usefulness for answering a user's question.
You return a list of the indices in the corresponding order.

# Instructions

You receive a user question and the conversation history, and you sort the indices of the sources below by their usefulness for answering the user's question.

Rank the indices of the sources by relevance to answering the user's question. Specifically:

- Sources that directly address the question or contain relevant information should be ranked higher, with their index appearing earlier in the list.
- Prioritize sources that refer to applicable, topic-relevant policies or statements when determining usefulness. Chunks mentioning specific policies, proposals, or statements directly related to the user question should be ranked highest.
- Sources that are vague, irrelevant, or redundant should be ranked lower, with their index appearing later in the list.

The conversation history can provide context to better assess relevance, but only if the latest user message refers to an earlier context; otherwise, only take the latest user message into account.

# Output Format

Return a list of indices sorted in descending order of usefulness for answering the user's question.

# Sources

{sources}
"""
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


class RerankDocumentsStructuredOutput(BaseModel):
    """The reranked list of relevant documents."""

    reranked_doc_indices: list[int] = Field(
        description="The indices of the documents ranked by relevance in descending order."
    )
