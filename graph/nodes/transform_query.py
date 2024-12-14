import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from graph.llm_config import get_llm



def transform_query(state):
    """
    Transform the query to produce a better question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates question key with a re-phrased question
    """

    logging.info("---TRANSFORM QUERY---")
    question = state["question"]
    documents = state["documents"]

    # Ensure that question re-writer is built
    system = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval. 
    Look at the input and try to reason about the underlying semantic intent / meaning. Only output the new question. 
    It should contain as good keywords as possible for the retrieval augentemnted generation as possible.


    
    """

    re_write_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),

            ("human", "Question: Tell me more about the New Patriotic Party?:"),
            ("assistant", "explain the standpoints of new patriotic party in ghana generally"),

            (
                "human",
                "Here is the initial question: \n\n {question} \n\nFormulate an improved question.",
            )
        ]
    )
    question_rewriter = re_write_prompt | get_llm() | StrOutputParser()

    # Re-write question
    better_question = question_rewriter.invoke({"question": question})
    return {"documents": documents, "question": better_question}
