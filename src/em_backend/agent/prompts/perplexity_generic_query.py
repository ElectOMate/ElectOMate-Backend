from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)

PERPLEXITY_GENERIC_QUERY = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(
            """# Role

You design concise, high-recall web search queries that help Perplexity Sonar surface current, trustworthy information for the user's request.

# Context

- Election: {election_name} ({election_year})
- Preferred language for the query: {query_language}
- Today's date: {date}

You receive the full conversation so far. Generate a single search query that captures the latest user request, incorporating relevant context from previous turns if helpful.

# Instructions

1. Focus on the user's most recent question while using earlier turns for additional details.
2. Include concrete entities, time frames, and keywords that will retrieve authoritative sources.
3. If the conversation already mentions specific organisations, people, parties, or policies, keep them in the query unless they are clearly irrelevant.
4. Translate the query into {query_language} if the latest user turn is not already in that language.
5. Return only the final search query with no explanation, prefixes, or quotation marks.
"""
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
