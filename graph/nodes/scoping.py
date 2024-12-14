from langchain_core.prompts import ChatPromptTemplate

import logging
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from graph.llm_config import get_llm



def scoping(state):
    """
    Define the scope of the question

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, scope, that defines the scope of the query
    """
    logging.info("---SCOPE---")
    question = state["question"]

    class QueryScope(BaseModel):
        """Decide on the scope of the query."""

        # "movementforchange", "ndc", "npp", "thenewforce",
        scope: Literal["constitution", "all"] = Field(
            ...,
            description="Given a user question choose to route it either to specific party in the Ghana 2024 elections, either to the constitution or just to look through all the documents.",
        )

    system = """You are an expert at deciding if a question refers to the constitution of Ghana or requires general information. 
    If the question refers to the Constitution of Ghana, use "constitution". If the question refers to multiple topics, 
    doesn't refer to the constitution specifically, or if you cannot decide, use "all". Only answer with one of these two words: all OR constitution\n """
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", "Question: {question}")
        ]
    )
    question_router = route_prompt | get_llm().with_structured_output(QueryScope)

    scope = question_router.invoke({"question": question})
    return {"question": question, "scope": scope.scope}
