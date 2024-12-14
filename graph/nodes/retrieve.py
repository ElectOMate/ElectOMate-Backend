import logging

from langchain_community.retrievers import AzureAISearchRetriever


def retrieve(state):
    """
    Retrieve documents

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    logging.info("---RETRIEVE---")
    question = state["question"]
    scope = state["scope"].lower()

    # ensure retriever is define
    retriever = AzureAISearchRetriever(
        api_version="2024-07-01",
        content_key="chunk",
        top_k=7
    )

    # Set Filter
    if scope == "constitution":
        retriever.filter = "title eq 'constitution.pdf'"
    elif scope == "npp":
        retriever.filter = "title eq 'npp.pdf'"
    elif scope == "ndc":
        retriever.filter = "title eq 'ndc.pdf'"
    elif scope == "movementforchange":
        retriever.filter = "title eq 'movementforchange.pdf'"
    elif scope == "thenewforce":
        retriever.filter = "title eq 'thenewforce.pdf'"
    else:
        retriever.filter = None

    # Retrieval
    documents = retriever.invoke(question)
    return {"documents": documents, "scope": scope, "question": question}
