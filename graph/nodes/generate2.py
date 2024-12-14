import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from graph.llm_config import get_llm
from .generate2_prompts import system_prompt, human_prompt_1, assistant_prompt_1, human_prompt_2


def generate2(state):
    """
    Generate answer

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    logging.info("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    scope = state["scope"]

    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", human_prompt_1),
        ("assistant", assistant_prompt_1),
        ("human", human_prompt_2)
    ])

    rag_chain = rag_prompt | get_llm() | StrOutputParser()

    # RAG generation
    generation = rag_chain.invoke({"context": documents, "question": question})
    return {"documents": [document.page_content for document in documents], "scope": scope, "question": question,
            "generation": generation, "loopfix": True}
