import os

from langchain.schema import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langchain_community.retrievers import AzureAISearchRetriever
from langchain_openai import ChatOpenAI

from typing import List, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

import logging
import dotenv

def get_llm():
    if not hasattr(get_llm, "llm"):
        get_llm.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
        )
    return get_llm.llm

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
    
    if not hasattr(scoping, "scoper"):
        class QueryScope(BaseModel):
            """Decide on the scope of the query."""
            
            scope: Literal["constitution", "movementforchange", "ndc", "npp", "thenewforce", "all"] = Field(
                ...,
                description="Given a user question choose to route it either to specific party in the Ghana 2024 elections, either to the constitution or just to look through all the documents.",
            )
        system = """You are an expert at deciding if a question refers to a specific party in Ghana or to its constitution. If the question refers to the Constitution of Ghana, use constitution. If the question refers to the New Patriotic Party (NPP) party, use npp. If the question refers to the National Democratic Congress (NDC) party, use ndc. If the question refers to the Movement for Change party, use movementforchange. If the question refers to The New Force party, use thenewforce. If the question refers to multiple parties, doesn't refer to one party in particular, or if cannot answer the question, you don't know or cannot decide, use all.\n"""
        route_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Question: {question}")
            ]
        )
        route_question.question_router = route_prompt | get_llm().with_structured_output(QueryScope)
    
    scope = route_question.question_router.invoke({"question": question})
    return {"question": question, "scope": scope.scope}

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
    if not hasattr(retrieve, "retriever"):
        retrieve.retriever = AzureAISearchRetriever(
            api_version="2024-07-01",
            content_key="chunk",
            top_k=5
        )
        
    # Set Filter
    if scope == "constitution":
        retrieve.retriever.filter = "title eq 'constitution.pdf'"
    elif scope == "npp":
        retrieve.retriever.filter = "title eq 'npp.pdf'"
    elif scope == "ndc":
        retrieve.retriever.filter = "title eq 'ndc.pdf'"
    elif scope == "movementforchange":
        retrieve.retriever.filter = "title eq 'movementforchange.pdf'"
    elif scope == "thenewforce":
        retrieve.retriever.filter = "title eq 'thenewforce.pdf'"
    else:
        retrieve.retriever.filter = None

    # Retrieval
    documents = retrieve.retriever.invoke(question)
    return {"documents": documents, "scope": scope, "question": question}


def generate(state):
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
    
    # Ensure RAG chain is built
    if not hasattr(generate, "rag_chain"):
        system = """You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer concise."""
        rag_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Questions: {question} \n Context: \n\n {context} \n Answer:")
            ]
        )
        generate.rag_chain = rag_prompt | get_llm() | StrOutputParser()
        

    # RAG generation
    generation = generate.rag_chain.invoke({"context": documents, "question": question})
    return {"documents": [document.page_content for document in documents], "scope": scope, "question": question, "generation": generation}


def grade_documents(state):
    """
    Determines whether the retrieved documents are relevant to the question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates documents key with only filtered relevant documents
    """

    logging.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    
    # Ensure grader is built
    if not hasattr(grade_documents, "retrieval_grader"):
        class GradeDocuments(BaseModel):
            """Binary score for relevance check on retrieved documents."""

            binary_score: str = Field(
                description="Documents are relevant to the question, 'yes' or 'no'"
            )
        system = """You are a grader assessing relevance of a retrieved document to a user question. If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. It does not need to be a stringent test. The goal is to filter out erroneous retrievals. Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
        grade_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Retrieved document: \n\n {document} \n\nUser Question: {question}"),
            ]
        )
        grade_documents.retrieval_grader = grade_prompt | get_llm().with_structured_output(GradeDocuments)
        
    # Score each doc
    filtered_docs = []
    for d in documents:
        score = grade_documents.retrieval_grader.invoke(
            {"question": question, "document": d.page_content}
        )
        grade = score.binary_score
        if grade == "yes":
            logging.info("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        else:
            logging.info("---GRADE: DOCUMENT NOT RELEVANT---")
            continue
    return {"documents": filtered_docs, "question": question}


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
    if not hasattr(transform_query, "question_rewriter"):
        system = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval. Look at the input and try to reason about the underlying semantic intent / meaning."""
        re_write_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                (
                    "human",
                    "Here is the initial question: \n\n {question} \n\nFormulate an improved question.",
                )
            ]
        )
        transform_query.question_rewriter = re_write_prompt | get_llm() | StrOutputParser()
        
    # Re-write question
    better_question = transform_query.question_rewriter.invoke({"question": question})
    return {"documents": documents, "question": better_question}

### Edges ###

def route_question(state):
    """
    Decide if the question is relevant.

    Args:
        state (dict): The current graph state

    Returns:
        str: Next node to call
    """

    logging.info("---ROUTE QUESTION---")
    question = state["question"]
    
    # Ensure question router is instantiated
    if not hasattr(route_question, "question_router"):
        class RouteQuery(BaseModel):
            """Route a user query to the most relevant datasource."""
            
            relevant: Literal["yes", "no"] = Field(
                ...,
                description="Given a user question choose if it is relevant in any way to the 2024 Ghana elections.",
            )
        system = """You are an expert at deciding if a question is relevant to the Ghana or elections. Decide broadly and don't be stringent about the conditions. If the question is in any way related to Ghana, decide yes. Otherwise, decide no.\n\n"""
        route_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Question: {question}")
            ]
        )
        route_question.question_router = route_prompt | get_llm().with_structured_output(RouteQuery)
        
    source = route_question.question_router.invoke({"question": question})
    print(source)
    if source.relevant == "yes":
        logging.info("---QUESTION IS RELEVANT---")
        return "yes"
    elif source.relevant == "no":
        logging.info("---QUESTION IS NOT RELEVANT---")
        return "end"


def decide_to_generate(state):
    """
    Determines whether to generate an answer, or re-generate a question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Binary decision for next node to call
    """

    logging.info("---ASSESS GRADED DOCUMENTS---")
    state["question"]
    filtered_documents = state["documents"]

    if not filtered_documents:
        # All documents have been filtered check_relevance
        # We will re-generate a new query
        logging.info(
            "---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---"
        )
        return "transform_query"
    else:
        # We have relevant documents, so generate answer
        logging.info("---DECISION: GENERATE---")
        return "generate"


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
    if not hasattr(grade_generation_v_documents_and_question, "hallucination_grader"):
        class GradeHallucinations(BaseModel):
            """Binary score for hallucination present in generation answer."""

            binary_score: str = Field(
                description="Answer is grounded in the facts, 'yes' or 'no'"
            )
        system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts. Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""
        hallucination_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"),
            ]
        )
        grade_generation_v_documents_and_question.hallucination_grader = hallucination_prompt | get_llm().with_structured_output(GradeHallucinations)

    # Ensure that answer grader is instantiated
    if not hasattr(grade_generation_v_documents_and_question, "answer_grader"):
        class GradeAnswer(BaseModel):
            """Binary score to assess wether the answer addresses the question."""

            binary_score: str = Field(
                description="Answer addresses the question, 'yes' or 'no'"
            )
        system = """You are a grader assessing whether an answer addresses / resolves a question. Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the question."""
        answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "User question: \n\n {question} \n\n LLM generation: {generation}"),
            ]
        )
        
        grade_generation_v_documents_and_question.answer_grader = answer_prompt | get_llm().with_structured_output(GradeAnswer)

    score = grade_generation_v_documents_and_question.hallucination_grader.invoke(
        {"documents": "\n\n".join(documents), "generation": generation}
    )
    grade = score.binary_score

    # Check hallucination
    if grade == "yes":
        logging.info("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        # Check question-answering
        logging.info("---GRADE GENERATION vs QUESTION---")
        score = grade_generation_v_documents_and_question.answer_grader.invoke({"question": question, "generation": generation})
        grade = score.binary_score
        if grade == "yes":
            logging.info("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        else:
            logging.info("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
    else:
        logging.info("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        return "not supported"

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
    """

    question: str
    generation: str
    documents: List[str]
    scope: str

def get_graph():
    if not hasattr(get_graph, 'app'):
        workflow = StateGraph(GraphState)

        # Define the nodes
        workflow.add_node("scoping", scoping)  # decide on scope
        workflow.add_node("retrieve", retrieve)  # retrieve
        workflow.add_node("grade_documents", grade_documents)  # grade documents
        workflow.add_node("generate", generate)  # generatae
        workflow.add_node("transform_query", transform_query)  # transform_query

        # Build graph
        workflow.add_conditional_edges(
            START,
            route_question,
            {
                "yes": "scoping",
                "end": END,
            },
        )
        workflow.add_edge("scoping", "retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )
        workflow.add_edge("transform_query", "retrieve")
        workflow.add_conditional_edges(
            "generate",
            grade_generation_v_documents_and_question,
            {
                "not supported": "generate",
                "useful": END,
                "not useful": "transform_query",
            },
        )

        # Compile
        get_graph.app = workflow.compile()
    
    return get_graph.app

if __name__ == "__main__":
    dotenv.load_dotenv()
    app = get_graph()
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    config = RunnableConfig(recursion_limit=10)
    try:
        for output in app.stream({'question': 'How does the New Patriotic Party want to improve the ghanaian economy?'}, config=config):
            for key, value in output.items():
                logging.info(f'Node: {key}\n---\n')
        print(value['generation'])
    except:
        logging.error("Graph recursion limit reached.")