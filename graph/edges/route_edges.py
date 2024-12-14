import logging
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from graph.llm_config import get_llm



def route_question(state):
    """
    Decide if the question is relevant and if it needs context.

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """
    logging.info("---ROUTE QUESTION---")
    question = state["question"]

    class RouteQuery(BaseModel):
        """Route a user query to the most relevant path."""

        decision: Literal["needs_context", "generic_response", "irrelevant"] = Field(
            ...,
            description="Determine how to handle the question: 'needs_context' for questions requiring Ghana elections info, 'generic_response' for simple/greeting questions, 'irrelevant' for unrelated questions.",
        )

    system = """
You are an expert at determining how to handle user questions about the 2024 Ghana elections.

Instructions:
- If the question requires specific information about Ghana elections or politics (expect the user to ask within the context of the ghana elections, even if its not clear of which country the user is asking about): choose 'needs_context'
- If the question is a simple greeting, a question about you or your capabilities or a question that can be answered without specific Ghana knowledge: choose 'generic_response'
- If the question is completely unrelated to Ghana: choose 'irrelevant'

Examples:
1. Question: "What are the main policies of the New Patriotic Party?"
   Decision: needs_context

2. Question: "Tell me about the weather in Canada."
   Decision: irrelevant

3. Question: "Hey, how are you?"
   Decision: generic_response

4. Question: "Hi, what can you help me with?"
   Decision: generic_response

5. Question: "When is the 2024 election date?"
   Decision: needs_context

6. Question: "rgasdgfccdc45646..0§&/"
   Decision: irrelevant
"""

    route_prompt = ChatPromptTemplate.from_messages([
        ("human", "Question: What are the main policies of the New Patriotic Party?\nDecision:"),
        ("assistant", "needs_context"),

        ("human", "Question: Tell me about the weather in Canada.\nDecision:"),
        ("assistant", "irrelevant"),

        ("human", "Question: Hey, how are you?\nDecision:"),
        ("assistant", "generic_response"),

        ("human", "Question: Hi, what can you help me with?\nDecision:"),
        ("assistant", "generic_response"),

        ("human", "Question: When is the 2024 election date?\nDecision:"),
        ("assistant", "needs_context"),

        ("human", "Question: rgasdgfccdc45646..0§&/\nDecision:"),
        ("assistant", "irrelevant"),

        ("human", "Question: Who are you?\nDecision:"),
        ("assistant", "generic_response"),

        ("human", "Question: What's the role of Parliament in Ghana?\nDecision:"),
        ("assistant", "needs_context"),

        ("human", "Question: Can you explain what you do?\nDecision:"),
        ("assistant", "generic_response"),

        ("human", "Question: Hello!\nDecision:"),
        ("assistant", "generic_response"),

        ("human", "Question: who has been the president in ghana in 2015\nDecision:"),
        ("assistant", "needs_context"),

        ("human", "Question: {question}\nDecision:")
    ])

    question_router = route_prompt | get_llm().with_structured_output(RouteQuery)

    source = question_router.invoke({"question": question})
    logging.info(source)

    if source.decision == "needs_context":
        logging.info("---QUESTION NEEDS CONTEXT---")
        return "needs_context"
    elif source.decision == "generic_response":
        logging.info("---GENERIC RESPONSE---")
        return "generic"
    else:
        logging.info("---QUESTION IS IRRELEVANT---")
        return "end"
