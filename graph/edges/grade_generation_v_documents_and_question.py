import logging

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from graph.llm_config import get_llm


def grade_generation_v_documents_and_question(state):
    """
    Determines whether the generation is grounded in the document and answers question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Decision for next node to call
    """

    logging.info("---CHECK HALLUCINATIONS---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]

    # Ensure that hallucination grader is instantiated
    # class GradeHallucinations(BaseModel):
    #     """Binary score for hallucination present in generation answer."""

    #     binary_score: str = Field(
    #         description="Answer is grounded in the facts, 'yes' or 'no'"
    #     )
    # system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts. Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""
    # hallucination_prompt = ChatPromptTemplate.from_messages(
    #     [
    #         ("system", system),
    #         ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"),
    #     ]
    # )
    # hallucination_grader = hallucination_prompt | get_llm().with_structured_output(GradeHallucinations)

    # Ensure that answer grader is instantiated
    class GradeAnswer(BaseModel):
        """Binary score to assess wether the answer addresses the question."""

        binary_score: str = Field(
            description="Answer addresses the question, 'yes' or 'no'"
        )

    system = """You are a grader assessing whether an answer addresses / resolves a question. Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the question, "No" means that the answer does not resolve the question.
    You are part of a RAG pipeline for a chatbot to help people infrm themselves for the elections in Ghana. 
    Ask yourself if the generation handed over to you is a good answer to the question. 
    It doesnt have to resolve the question entirely, 
    but it should be a good answer. Say no if the generation halucinates something nonsensical.
    
    
    """
    answer_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),

            ("human", """User question: \n\n Who was the president in 2009? \n\n LLM generation: \n\n  John Atta Mills was the President of Ghana in 2009.

He was elected in the 2008 elections and served as President until his death in July 2012, after which John Mahama, then Vice President, took over the presidency.

Source: Wahlen in Ghana.pdf"""),

            ("assistant", "yes"),

            ("human", "User question: \n\n {question} \n\n LLM generation: {generation}"),
        ]
    )

    answer_grader = answer_prompt | get_llm().with_structured_output(GradeAnswer)

    # score = hallucination_grader.invoke(
    #     {"documents": "\n\n".join(documents), "generation": generation}
    # )
    # grade = score.binary_score
    grade = 'yes'

    # Check hallucination

    # Check question-answering

    if grade == "yes":
        logging.info("---GRADE GENERATION vs QUESTION---")
        score = answer_grader.invoke({"question": question, "generation": generation})
        grade = score.binary_score
        generation = state["generation"]

        if grade == "yes":
            logging.info("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        else:
            logging.info("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
    else:
        logging.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        return "not supported"
