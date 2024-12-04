# import os

# from langchain.schema import Document
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnableConfig
# from langgraph.graph import START, END, StateGraph
# from langchain_community.retrievers import AzureAISearchRetriever
# from langchain_openai import ChatOpenAI
# from langgraph.errors import GraphRecursionError

# from typing import List, Literal
# from typing_extensions import TypedDict
# from pydantic import BaseModel, Field

# import logging
# import dotenv

# def get_llm():
#     return ChatOpenAI(
#         model="gpt-4o",
#         temperature=0,
#     )

# def scoping(state):
#     """
#     Define the scope of the question
    
#     Args:
#         state (dict): The current graph state

#     Returns:
#         state (dict): New key added to state, scope, that defines the scope of the query
#     """
#     logging.debug("---SCOPE---")
#     question = state["question"]
    
#     class QueryScope(BaseModel):
#         """Decide on the scope of the query."""
        
#         scope: Literal["constitution", "movementforchange", "ndc", "npp", "thenewforce", "all"] = Field(
#             ...,
#             description="Given a user question choose to route it either to specific party in the Ghana 2024 elections, either to the constitution or just to look through all the documents.",
#         )
#     system = """You are an expert at deciding if a question refers to a specific party in Ghana or to its constitution. If the question refers to the Constitution of Ghana, use constitution. If the question refers to the New Patriotic Party (NPP) party, use npp. If the question refers to the National Democratic Congress (NDC) party, use ndc. If the question refers to the Movement for Change party, use movementforchange. If the question refers to The New Force party, use thenewforce. If the question refers to multiple parties, doesn't refer to one party in particular, or if cannot answer the question, you don't know or cannot decide, use all.\n"""
#     route_prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system", system),
#             ("human", "Question: {question}")
#         ]
#     )
#     question_router = route_prompt | get_llm().with_structured_output(QueryScope)
    
#     scope = question_router.invoke({"question": question})
#     return {"question": question, "scope": scope.scope}

# def retrieve(state):
#     """
#     Retrieve documents

#     Args:
#         state (dict): The current graph state

#     Returns:
#         state (dict): New key added to state, documents, that contains retrieved documents
#     """
#     logging.debug("---RETRIEVE---")
#     question = state["question"]
#     scope = state["scope"].lower()
    
#     # ensure retriever is define
#     retriever = AzureAISearchRetriever(
#         api_version="2024-07-01",
#         content_key="chunk",
#         top_k=5
#     )
        
#     # Set Filter
#     if scope == "constitution":
#         retriever.filter = "title eq 'constitution.pdf'"
#     elif scope == "npp":
#         retriever.filter = "title eq 'npp.pdf'"
#     elif scope == "ndc":
#         retriever.filter = "title eq 'ndc.pdf'"
#     elif scope == "movementforchange":
#         retriever.filter = "title eq 'movementforchange.pdf'"
#     elif scope == "thenewforce":
#         retriever.filter = "title eq 'thenewforce.pdf'"
#     else:
#         retriever.filter = None

#     # Retrieval
#     documents = retriever.invoke(question)
#     return {"documents": documents, "scope": scope, "question": question}












# def generate(state):
#     """
#     Generate answer

#     Args:
#         state (dict): The current graph state

#     Returns:
#         state (dict): New key added to state, generation, that contains LLM generation
#     """
#     logging.debug("---GENERATE---")
#     question = state["question"]
#     documents = state["documents"]
#     scope = state["scope"]
    
#     # Ensure RAG chain is built
#     system = """You are an expert assistant on Ghana's political landscape and elections. Use the provided context to answer questions accurately and concisely. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer focused.

# Key guidelines:
# 1. Base your answers primarily on the retrieved documents and general context
# 2. Be specific and factual
# 3. If information seems outdated or conflicts between sources, prioritize the most recent source
# 4. For policy questions, cite the specific party or document source
# 5. Alays answe in english
# 6. DO NOT GIVE ANY ADVICE ON WHO TO VOTE FOR
# 7. YOU ARE POLITICALLY NEUTRAL




# General Election Context:

# # GHANA ELECTIONS AND POLITICAL LANDSCAPE
# Last Updated: 2023-10-01

# ## 1. ELECTORAL SYSTEM OVERVIEW

# ### Electoral Framework

# - **Government Type**: Constitutional democracy with multi-party system.
# - **Executive**: President elected for a four-year term; maximum of two terms.
# - **Legislature**: Unicameral Parliament with 275 seats.
# - **Electoral System**:
#   - **Presidential**: Simple majority.
#   - **Parliamentary**: First-past-the-post in single-member constituencies.
# - **Electoral Body**: Independent Electoral Commission (EC) of Ghana.

# ### Voter Eligibility

# - **Age**: 18 years and above.
# - **Citizenship**: Ghanaian.
# - **Residency**: Resident in registering constituency.
# - **Disqualifications**: Unsound mind or certain convictions.

# ### Registration Process

# - **Continuous Registration**: At district offices.
# - **Biometric Data**: Fingerprints and photos to prevent duplicates.
# - **Required Documents**:
#   - National ID card.
#   - Passport.

# ### Voting Procedures

# - **Method**: Manual paper ballots.
# - **Locations**: Schools, community centers, public buildings.
# - **Hours**: 7:00 AM to 5:00 PM.
# - **Identification**: Voter ID card required.

# ### Electoral Calendar

# - **Election Cycle**: Every four years.
# - **Next Election**: 2024-12-07.
# - **Key Dates**:
#   - **Nominations**: Two months before election day.
#   - **Campaign Period**: Ends 24 hours before election day.

# ### Constituencies

# - **Total**: 275 single-member constituencies.
# - **Boundary Reviews**: Periodic updates by the EC.

# ## 2. POLITICAL PARTIES

# ### Major Parties

# #### New Patriotic Party (NPP)

# - **Leadership**:
#   - **Chairman**: Freddie Blay.
#   - **General Secretary**: John Boadu.
# - **Key Figures**:
#   - **Nana Akufo-Addo**: President since 2017.
#   - **Dr. Mahamudu Bawumia**: Vice President.
# - **Ideology**: Liberal democracy, free-market principles.
# - **Achievements**:
#   - Free Senior High School policy.
#   - "One District, One Factory" program.
# - **Recent Performance**:
#   - **2016**: Won presidency and parliamentary majority.
#   - **2020**: Retained presidency; slim parliamentary majority.

# #### National Democratic Congress (NDC)

# - **Leadership**:
#   - **Chairman**: Samuel Ofosu-Ampofo.
#   - **General Secretary**: Johnson Asiedu Nketia.
# - **Key Figures**:
#   - **John Mahama**: Former President (2012-2017).
# - **Ideology**: Social democracy, inclusive governance.
# - **Achievements**:
#   - Infrastructure expansion.
#   - National Health Insurance Scheme.
# - **Recent Performance**:
#   - **2012**: Won presidency and majority.
#   - **2020**: Narrow losses in presidency and Parliament.

# ## 3. POLITICAL TIMELINE

# ### Governments Since Independence

# | Period        | Leader                     | Government Type         |
# |---------------|----------------------------|-------------------------|
# | 1957-1966     | Kwame Nkrumah              | First Republic (CPP)    |
# | 1966-1969     | Military Junta             | National Liberation     |
# | 1969-1972     | Kofi Abrefa Busia          | Second Republic         |
# | 1981-1992     | Jerry John Rawlings        | PNDC Military Govt.     |
# | 1992-Present  | Multiple Leaders           | Fourth Republic         |

# ### Major Events

# - **1966-02-24**: Nkrumah's government overthrown.
# - **1981-12-31**: Rawlings establishes PNDC.
# - **1992**: Return to constitutional rule.

# ### Recent Election Results

# - **2020 Presidential**:
#   - **NPP**: Nana Akufo-Addo - 51.3%.
#   - **NDC**: John Mahama - 47.4%.
# - **Parliament**:
#   - **NPP**: 137 seats.
#   - **NDC**: 137 seats.

# ### Government Structure

# - **Presidential Term Limit**: Two four-year terms.
# - **Parliamentary Terms**: Four years, no term limits.
# - **Branches**:
#   - **Executive**: President and ministers.
#   - **Legislature**: Unicameral Parliament.
#   - **Judiciary**: Independent Supreme Court.

# ## 4. CURRENT POLITICAL LANDSCAPE

# ### Key Figures

# - **President**: Nana Akufo-Addo (NPP).
# - **Vice President**: Dr. Mahamudu Bawumia.
# - **Opposition Leader**: John Mahama (NDC).
# - **Speaker of Parliament**: Alban Bagbin (NDC).

# ### Parliamentary Composition

# - **Total Seats**: 275.
# - **NPP**: 137 seats.
# - **NDC**: 137 seats.
# - **Independent**: 1 seat (aligns with NPP).

# ## 5. ECONOMIC INDICATORS

# ### GDP Growth (Past 5 Years)

# | Year | Growth Rate (%) |
# |------|-----------------|
# | 2017 | 8.1             |
# | 2018 | 6.3             |
# | 2019 | 6.5             |
# | 2020 | 0.9             |
# | 2021 | 5.4             |

# ### Inflation Rates

# - **2020**: 9.9%.
# - **2021**: 9.8%.
# - **2022**: Increased due to global factors.

# ### Economic Challenges

# - **Debt**: Public debt at ~76.6% of GDP (2021).
# - **Fiscal Deficit**: Expanded due to COVID-19.
# - **Currency**: Depreciation of the Ghanaian Cedi.
# - **Unemployment**: High youth unemployment rates.

# ### Key Sectors

# - **Agriculture**: Cocoa, timber.
# - **Mining**: Gold, oil.
# - **Services**: Banking, tourism.
# - **Manufacturing**: Emerging sector.

# ### Foreign Investment

# - **FDI Inflows (2020)**: ~$2.65 billion.
# - **Major Investors**: China, UK, USA.

# ## 6. POLICY CHALLENGES

# ### National Issues

# 1. **Economic Stability**: Inflation and debt management.
# 2. **Employment**: Youth job creation.
# 3. **Healthcare**: Infrastructure and access.
# 4. **Education**: Quality and resources.
# 5. **Infrastructure**: Roads, energy, digitalization.

# ### Infrastructure Status

# - **Roads**: Ongoing improvements.
# - **Energy**: Increased capacity; stability issues.
# - **Digital**: National addressing system implemented.

# ### Education and Healthcare

# - **Education**:
#   - Free Senior High School since 2017.
#   - Challenges: Overcrowding, teacher training.
# - **Healthcare**:
#   - National Health Insurance Scheme.
#   - Issues: Funding, rural access.

# ### Environmental Concerns

# - **Illegal Mining**: Water pollution.
# - **Deforestation**: From logging and farming.
# - **Climate Change**: Affects agriculture.

# ## 7. FOREIGN RELATIONS

# ### International Partnerships

# - **ECOWAS**: Active member.
# - **African Union**: Founding member.
# - **United Nations**: Peacekeeping contributions.

# ### Regional Role

# - **Diplomacy**: Mediator in conflicts.
# - **Trade**: Promotes intra-African trade.
# - **AfCFTA**: Hosts the Secretariat.

# ### Trade Agreements

# - **AfCFTA**: Continental free trade.
# - **EU Agreement**: Interim Economic Partnership.

# ### Diplomatic Missions

# - **Global Embassies**: Extensive network.
# - **Foreign Missions**: Over 60 in Ghana.

# ## 8. VOTING PROCESS

# ### Procedure Steps

# 1. **Arrival**: At assigned polling station.
# 2. **Verification**: Present Voter ID.
# 3. **Biometric Check**: Fingerprint scan.
# 4. **Ballot Issuance**: Receive ballots.
# 5. **Voting**: Mark choices privately.
# 6. **Casting**: Deposit ballots.
# 7. **Ink Marking**: Finger marked.
# 8. **Departure**: Exit polling station.

# ### Required Documentation

# - **Voter ID Card**: Primary ID.
# - **Alternate ID**: National ID or passport (if accepted).

# ### Polling Operations

# - **Staff**: Presiding officer and assistants.
# - **Observers**: Party agents, accredited monitors.
# - **Security**: Police presence.

# ### Vote Counting

# - **On-site Counting**: Immediate after polls close.
# - **Transparency**: Open to observers.
# - **Result Transmission**: Sent to constituency centers.

# ### Results Announcement

# - **Collation**: Constituency and national levels.
# - **Declaration**: By EC Chairperson.
# - **Timeframe**: Within 72 hours.

# ---

# **Note**: Information is accurate as of 2023-10-01. For updates, refer to official sources like the Electoral Commission of Ghana.

# [End of general information]





# """

#     rag_prompt = ChatPromptTemplate.from_messages([
#         ("system", system),
#         ("human", """Question: {question}

# Please provide a clear and concise answer based on the above information.
# Retrieved Context:
# {context}


# """)
#     ])

    
#     rag_chain = rag_prompt | get_llm() | StrOutputParser()
        
#     # RAG generation
#     generation = rag_chain.invoke({"context": documents, "question": question})
    
#     # Handle document content type
#     if documents and isinstance(documents[0], Document):
#         documents = [document.page_content for document in documents]
        
#     return {"documents": documents, "scope": scope, "question": question, "generation": generation}













# def grade_documents(state):
#     """
#     Determines whether the retrieved documents are relevant to the question.

#     Args:
#         state (dict): The current graph state

#     Returns:
#         state (dict): Updates documents key with only filtered relevant documents
#     """

#     logging.debug("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
#     question = state["question"]
#     documents = state["documents"]
    
#     # Ensure grader is built
#     class GradeDocuments(BaseModel):
#         """Binary score for relevance check on retrieved documents."""

#         binary_score: str = Field(
#             description="Documents are relevant to the question, 'yes' or 'no'"
#         )
#     system = """You are a grader assessing relevance of a retrieved document to a user question. If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. It does not need to be a stringent test. The goal is to filter out erroneous retrievals. Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
#     grade_prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system", system),
#             ("human", "Retrieved document: \n\n {document} \n\nUser Question: {question}"),
#         ]
#     )
#     retrieval_grader = grade_prompt | get_llm().with_structured_output(GradeDocuments)
        
#     # Score each doc
#     filtered_docs = []
#     for d in documents:
#         score = retrieval_grader.invoke(
#             {"question": question, "document": d.page_content}
#         )
#         grade = score.binary_score
#         if grade == "yes":
#             logging.debug("---GRADE: DOCUMENT RELEVANT---")
#             filtered_docs.append(d)
#         else:
#             logging.debug("---GRADE: DOCUMENT NOT RELEVANT---")
#             continue
#     return {"documents": filtered_docs, "question": question}
















# def transform_query(state):
#     """
#     Transform the query to produce a better question.

#     Args:
#         state (dict): The current graph state

#     Returns:
#         state (dict): Updates question key with a re-phrased question
#     """

#     logging.debug("---TRANSFORM QUERY---")
#     question = state["question"]
#     documents = state["documents"]
    
#     # Ensure that question re-writer is built
#     system = """You are a question re-writer that converts an input question to a better version that is optimized for vectorstore retrieval. Look at the input and try to reason about the underlying semantic intent / meaning."""
#     re_write_prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system", system),
#             (
#                 "human",
#                 "Here is the initial question: \n\n {question} \n\nFormulate an improved question.",
#             )
#         ]
#     )
#     question_rewriter = re_write_prompt | get_llm() | StrOutputParser()
        
#     # Re-write question
#     better_question = question_rewriter.invoke({"question": question})
#     return {"documents": documents, "question": better_question}

# ### Edges ###













# def route_question(state):
#     """
#     Decide if the question is relevant.

#     Args:
#         state (dict): The current graph state

#     Returns:
#         dict: Updated state with decision and a message if irrelevant
#     """

#     logging.debug("---ROUTE QUESTION---")
#     question = state["question"]

#     class RouteQuery(BaseModel):
#         """Route a user query to the most relevant datasource."""
        
#         relevant: Literal["yes", "no"] = Field(
#             ...,
#             description="Determine if the question is relevant to the 2024 Ghana elections.",
#         )

#     system = """
# You are an expert at determining if a question is relevant to the 2024 Ghana elections.

# Instructions:
# - If the question is in any way related to Ghana or its elections, decide 'yes'.
# - If the question is not related to Ghana or its elections, decide 'no'.

# Examples:
# 1. Question: "What are the main policies of the New Patriotic Party?"
#    Decision: yes

# 2. Question: "Tell me about the weather in Canada."
#    Decision: no

# 3. Question: "Who won the last election in Ghana?"
#    Decision: yes

# 4. Question: "How to cook Italian pasta?"
#    Decision: no

# Respond with 'yes' or 'no' accordingly.
# """

#     route_prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system", system),

#             ("human", "Question: What are the main policies of the New Patriotic Party?\nDecision:"),
#             ("assistant", "yes"),

#             ("human", "Question: Tell me about the weather in Canada.\nDecision:"),
#             ("assistant", "no"), 

#             ("human", "Question: Who won the last election in Ghana?\nDecision:"),
#             ("assistant", "yes"),

#             ("human", "Question: How to cook Italian pasta?\nDecision:"),
#             ("assistant", "no"),

#             ("human", "Question: When is the 2024 election date?\nDecision:"),
#             ("assistant", "yes"),



#             ("human", "Question: hey\nDecision:"),
#             ("assistant", "no"),


#             ("human", "Question: hey, what are you here for?\nDecision:"),
#             ("assistant", "no"),


#             ("human", "Question: hey\nDecision:"),
#             ("assistant", "no"),


#             ("human", "Question: hey\nDecision:"),
#             ("assistant", "no"),
#             ("human", "Question: {question}\nDecision:")
#         ]
#     )
#     question_router = route_prompt | get_llm().with_structured_output(RouteQuery)

#     source = question_router.invoke({"question": question})
#     logging.debug(f"Relevance decision: {source.relevant}")

#     if source.relevant == "yes":
#         logging.debug("---QUESTION IS RELEVANT---")
#         return "yes"
#     else:
#         logging.debug("---QUESTION IS NOT RELEVANT---")
#         state["message"] = (
#             "I'm here to help with questions about the 2024 Ghana elections. "
#             "It seems your question is not related to that topic. "
#             "I'm prompted to only answer questions specifically about the Ghana elections and adjacent topics"
#         )
#         return "end_with_message"












# def decide_to_generate(state):
#     """
#     Determines whether to generate an answer, or re-generate a question.

#     Args:
#         state (dict): The current graph state

#     Returns:
#         str: Binary decision for next node to call
#     """

#     logging.debug("---ASSESS GRADED DOCUMENTS---")
#     state["question"]
#     filtered_documents = state["documents"]

#     if not filtered_documents:
#         # All documents have been filtered check_relevance
#         # We will re-generate a new query
#         logging.debug(
#             "---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---"
#         )
#         return "transform_query"
#     else:
#         # We have relevant documents, so generate answer
#         logging.debug("---DECISION: GENERATE---")
#         return "generate"













# def grade_generation_v_documents_and_question(state):
#     """
#     Determines whether the generation is grounded in the document and answers question.

#     Args:
#         state (dict): The current graph state

#     Returns:
#         str: Decision for next node to call
#     """

#     logging.debug("---CHECK HALLUCINATIONS---")
#     question = state["question"]
#     documents = state["documents"]
#     generation = state["generation"]
    
#     # Ensure that hallucination grader is instantiated
#     # class GradeHallucinations(BaseModel):
#     #     """Binary score for hallucination present in generation answer."""

#     #     binary_score: str = Field(
#     #         description="Answer is grounded in the facts, 'yes' or 'no'"
#     #     )
#     # system = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts. Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""
#     # hallucination_prompt = ChatPromptTemplate.from_messages(
#     #     [
#     #         ("system", system),
#     #         ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}"),
#     #     ]
#     # )
#     # hallucination_grader = hallucination_prompt | get_llm().with_structured_output(GradeHallucinations)

#     # Ensure that answer grader is instantiated










#     class GradeAnswer(BaseModel):
#         """Binary score to assess wether the answer addresses the question."""

#         binary_score: str = Field(
#             description="Answer addresses the question, 'yes' or 'no'"
#         )
#     system = """You are a grader assessing whether an answer addresses / resolves a question. Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the question."""
#     answer_prompt = ChatPromptTemplate.from_messages(
#         [
#             ("system", system),
#             ("human", "User question: \n\n {question} \n\n LLM generation: {generation}"),
#         ]
#     )
    
#     answer_grader = answer_prompt | get_llm().with_structured_output(GradeAnswer)

#     # score = hallucination_grader.invoke(
#     #     {"documents": "\n\n".join(documents), "generation": generation}
#     # )
#     # grade = score.binary_score
#     grade = 'yes'

    
#     # Check hallucination
#     if grade == "yes":
#         logging.debug("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
#         # Check question-answering
#         logging.debug("---GRADE GENERATION vs QUESTION---")
#         score = answer_grader.invoke({"question": question, "generation": generation})
#         grade = score.binary_score
#         if grade == "yes":
#             logging.debug("---DECISION: GENERATION ADDRESSES QUESTION---")
#             return "useful"
#         else:
#             logging.debug("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
#             return "not useful"
#     else:
#         logging.debug("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
#         return "not supported"

















# class GraphState(TypedDict):
#     """
#     Represents the state of our graph.

#     Attributes:
#         question: question
#         generation: LLM generation
#         documents: list of documents
#     """

#     question: str
#     generation: str
#     documents: List[str]
#     scope: str

# def get_graph():
#     if not hasattr(get_graph, 'app'):
#         workflow = StateGraph(GraphState)

#         # Define the nodes
#         workflow.add_node("scoping", scoping)  # decide on scope
#         workflow.add_node("retrieve", retrieve)  # retrieve
#         workflow.add_node("grade_documents", grade_documents)  # grade documents
#         workflow.add_node("generate", generate)  # generate
#         workflow.add_node("transform_query", transform_query)  # transform_query
#         workflow.add_node("end_with_message", end_with_message)  # new node

#         # Build graph
#         workflow.add_conditional_edges(
#             START,
#             route_question,
#             {
#                 "yes": "scoping",
#                 "end_with_message": "end_with_message",
#             },
#         )
#         workflow.add_edge("scoping", "retrieve")
#         workflow.add_edge("retrieve", "grade_documents")
#         workflow.add_conditional_edges(
#             "grade_documents",
#             decide_to_generate,
#             {
#                 "transform_query": "transform_query",
#                 "generate": "generate",
#             },
#         )
#         workflow.add_edge("transform_query", "retrieve")
#         workflow.add_conditional_edges(
#             "generate",
#             grade_generation_v_documents_and_question,
#             {
#                 "not supported": "generate",
#                 "useful": END,
#                 "not useful": "transform_query",
#             },
#         )

#         # Compile
#         get_graph.app = workflow.compile()
    
#     return get_graph.app


















# if __name__ == "__main__":
#     dotenv.load_dotenv()
#     app = get_graph()
#     logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
#     config = RunnableConfig(recursion_limit=10)
#     try:
#         for output in app.stream({'question': 'How does the New Patriotic Party want to improve the ghanaian economy?'}, config=config):
#             for key, value in output.items():
#                 logging.info(f'Node: {key}\n---\n')
#         print(value['generation'])
#     except:
#         logging.error("Graph recursion limit reached.")

# def end_with_message(state):
#     """
#     Returns the message for irrelevant questions.

#     Args:
#         state (dict): The current graph state

#     Returns:
#         dict: Contains the message to be returned to the user
#     """
#     logging.info("---END WITH MESSAGE---")
#     return {"generation": state["message"]}






# Inserting Jonsthan working version now:


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
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0,
    )

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
    question_router = route_prompt | get_llm().with_structured_output(QueryScope)
    
    scope = question_router.invoke({"question": question})
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
    retriever = AzureAISearchRetriever(
        api_version="2024-07-01",
        content_key="chunk",
        top_k=5
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
    
#     # Ensure RAG chain is built
    system = """You are an expert assistant on Ghana's political landscape and elections. Use the provided context to answer questions accurately and concisely. If you don't know the answer, just say that you don't know. Use three sentences maximum and keep the answer focused.

Key guidelines:
1. Base your answers primarily on the retrieved documents and general context
2. Be specific and factual
3. If information seems outdated or conflicts between sources, prioritize the most recent source
4. For policy questions, cite the specific party or document source
5. Alays answe in english
6. DO NOT GIVE ANY ADVICE ON WHO TO VOTE FOR
7. YOU ARE POLITICALLY NEUTRAL




General Election Context:

# GHANA ELECTIONS AND POLITICAL LANDSCAPE
Last Updated: 2023-10-01

## 1. ELECTORAL SYSTEM OVERVIEW

### Electoral Framework

- **Government Type**: Constitutional democracy with multi-party system.
- **Executive**: President elected for a four-year term; maximum of two terms.
- **Legislature**: Unicameral Parliament with 275 seats.
- **Electoral System**:
  - **Presidential**: Simple majority.
  - **Parliamentary**: First-past-the-post in single-member constituencies.
- **Electoral Body**: Independent Electoral Commission (EC) of Ghana.

### Voter Eligibility

- **Age**: 18 years and above.
- **Citizenship**: Ghanaian.
- **Residency**: Resident in registering constituency.
- **Disqualifications**: Unsound mind or certain convictions.

### Registration Process

- **Continuous Registration**: At district offices.
- **Biometric Data**: Fingerprints and photos to prevent duplicates.
- **Required Documents**:
  - National ID card.
  - Passport.

### Voting Procedures

- **Method**: Manual paper ballots.
- **Locations**: Schools, community centers, public buildings.
- **Hours**: 7:00 AM to 5:00 PM.
- **Identification**: Voter ID card required.

### Electoral Calendar

- **Election Cycle**: Every four years.
- **Next Election**: 2024-12-07.
- **Key Dates**:
  - **Nominations**: Two months before election day.
  - **Campaign Period**: Ends 24 hours before election day.

### Constituencies

- **Total**: 275 single-member constituencies.
- **Boundary Reviews**: Periodic updates by the EC.

## 2. POLITICAL PARTIES

### Major Parties

#### New Patriotic Party (NPP)

- **Leadership**:
  - **Chairman**: Freddie Blay.
  - **General Secretary**: John Boadu.
- **Key Figures**:
  - **Nana Akufo-Addo**: President since 2017.
  - **Dr. Mahamudu Bawumia**: Vice President.
- **Ideology**: Liberal democracy, free-market principles.
- **Achievements**:
  - Free Senior High School policy.
  - "One District, One Factory" program.
- **Recent Performance**:
  - **2016**: Won presidency and parliamentary majority.
  - **2020**: Retained presidency; slim parliamentary majority.

#### National Democratic Congress (NDC)

- **Leadership**:
  - **Chairman**: Samuel Ofosu-Ampofo.
  - **General Secretary**: Johnson Asiedu Nketia.
- **Key Figures**:
  - **John Mahama**: Former President (2012-2017).
- **Ideology**: Social democracy, inclusive governance.
- **Achievements**:
  - Infrastructure expansion.
  - National Health Insurance Scheme.
- **Recent Performance**:
  - **2012**: Won presidency and majority.
  - **2020**: Narrow losses in presidency and Parliament.

## 3. POLITICAL TIMELINE

### Governments Since Independence

| Period        | Leader                     | Government Type         |
|---------------|----------------------------|-------------------------|
| 1957-1966     | Kwame Nkrumah              | First Republic (CPP)    |
| 1966-1969     | Military Junta             | National Liberation     |
| 1969-1972     | Kofi Abrefa Busia          | Second Republic         |
| 1981-1992     | Jerry John Rawlings        | PNDC Military Govt.     |
| 1992-Present  | Multiple Leaders           | Fourth Republic         |

### Major Events

- **1966-02-24**: Nkrumah's government overthrown.
- **1981-12-31**: Rawlings establishes PNDC.
- **1992**: Return to constitutional rule.

### Recent Election Results

- **2020 Presidential**:
  - **NPP**: Nana Akufo-Addo - 51.3%.
  - **NDC**: John Mahama - 47.4%.
- **Parliament**:
  - **NPP**: 137 seats.
  - **NDC**: 137 seats.

### Government Structure

- **Presidential Term Limit**: Two four-year terms.
- **Parliamentary Terms**: Four years, no term limits.
- **Branches**:
  - **Executive**: President and ministers.
  - **Legislature**: Unicameral Parliament.
  - **Judiciary**: Independent Supreme Court.

## 4. CURRENT POLITICAL LANDSCAPE

### Key Figures

- **President**: Nana Akufo-Addo (NPP).
- **Vice President**: Dr. Mahamudu Bawumia.
- **Opposition Leader**: John Mahama (NDC).
- **Speaker of Parliament**: Alban Bagbin (NDC).

### Parliamentary Composition

- **Total Seats**: 275.
- **NPP**: 137 seats.
- **NDC**: 137 seats.
- **Independent**: 1 seat (aligns with NPP).

## 5. ECONOMIC INDICATORS

### GDP Growth (Past 5 Years)

| Year | Growth Rate (%) |
|------|-----------------|
| 2017 | 8.1             |
| 2018 | 6.3             |
| 2019 | 6.5             |
| 2020 | 0.9             |
| 2021 | 5.4             |

### Inflation Rates

- **2020**: 9.9%.
- **2021**: 9.8%.
- **2022**: Increased due to global factors.

### Economic Challenges

- **Debt**: Public debt at ~76.6% of GDP (2021).
- **Fiscal Deficit**: Expanded due to COVID-19.
- **Currency**: Depreciation of the Ghanaian Cedi.
- **Unemployment**: High youth unemployment rates.

### Key Sectors

- **Agriculture**: Cocoa, timber.
- **Mining**: Gold, oil.
- **Services**: Banking, tourism.
- **Manufacturing**: Emerging sector.

### Foreign Investment

- **FDI Inflows (2020)**: ~$2.65 billion.
- **Major Investors**: China, UK, USA.

## 6. POLICY CHALLENGES

### National Issues

1. **Economic Stability**: Inflation and debt management.
2. **Employment**: Youth job creation.
3. **Healthcare**: Infrastructure and access.
4. **Education**: Quality and resources.
5. **Infrastructure**: Roads, energy, digitalization.

### Infrastructure Status

- **Roads**: Ongoing improvements.
- **Energy**: Increased capacity; stability issues.
- **Digital**: National addressing system implemented.

### Education and Healthcare

- **Education**:
  - Free Senior High School since 2017.
  - Challenges: Overcrowding, teacher training.
- **Healthcare**:
  - National Health Insurance Scheme.
  - Issues: Funding, rural access.

### Environmental Concerns

- **Illegal Mining**: Water pollution.
- **Deforestation**: From logging and farming.
- **Climate Change**: Affects agriculture.

## 7. FOREIGN RELATIONS

### International Partnerships

- **ECOWAS**: Active member.
- **African Union**: Founding member.
- **United Nations**: Peacekeeping contributions.

### Regional Role

- **Diplomacy**: Mediator in conflicts.
- **Trade**: Promotes intra-African trade.
- **AfCFTA**: Hosts the Secretariat.

### Trade Agreements

- **AfCFTA**: Continental free trade.
- **EU Agreement**: Interim Economic Partnership.

### Diplomatic Missions

- **Global Embassies**: Extensive network.
- **Foreign Missions**: Over 60 in Ghana.

## 8. VOTING PROCESS

### Procedure Steps

1. **Arrival**: At assigned polling station.
2. **Verification**: Present Voter ID.
3. **Biometric Check**: Fingerprint scan.
4. **Ballot Issuance**: Receive ballots.
5. **Voting**: Mark choices privately.
6. **Casting**: Deposit ballots.
7. **Ink Marking**: Finger marked.
8. **Departure**: Exit polling station.

### Required Documentation

- **Voter ID Card**: Primary ID.
- **Alternate ID**: National ID or passport (if accepted).

### Polling Operations

- **Staff**: Presiding officer and assistants.
- **Observers**: Party agents, accredited monitors.
- **Security**: Police presence.

### Vote Counting

- **On-site Counting**: Immediate after polls close.
- **Transparency**: Open to observers.
- **Result Transmission**: Sent to constituency centers.

### Results Announcement

- **Collation**: Constituency and national levels.
- **Declaration**: By EC Chairperson.
- **Timeframe**: Within 72 hours.

---

**Note**: Information is accurate as of 2023-10-01. For updates, refer to official sources like the Electoral Commission of Ghana.

[End of general information]





"""

    rag_prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", """Question: {question}

Please provide a clear and concise answer based on the above information.
Retrieved Context:
{context}


""")
    ])

    rag_chain = rag_prompt | get_llm() | StrOutputParser()
        

    # RAG generation
    generation = rag_chain.invoke({"context": documents, "question": question})
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
    retrieval_grader = grade_prompt | get_llm().with_structured_output(GradeDocuments)
        
    # Score each doc
    filtered_docs = []
    for d in documents:
        score = retrieval_grader.invoke(
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
    question_rewriter = re_write_prompt | get_llm() | StrOutputParser()
        
    # Re-write question
    better_question = question_rewriter.invoke({"question": question})
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
    class RouteQuery(BaseModel):
        """Route a user query to the most relevant datasource."""
        
        relevant: Literal["yes", "no"] = Field(
            ...,
            description="Given a user question choose if it is relevant in any way to the 2024 Ghana elections.",
        )





 
    system = """
You are an expert at determining if a question is relevant to the 2024 Ghana elections.

Instructions:
- If the question is in any way related to Ghana or its elections, decide 'yes'.
- If the question is not related to Ghana or its elections, decide 'no'.

Examples:
1. Question: "What are the main policies of the New Patriotic Party?"
   Decision: yes

2. Question: "Tell me about the weather in Canada."
   Decision: no

3. Question: "Hey:)?"
   Decision: yes

Respond with 'yes' or 'no' accordingly.
"""

    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),

            ("human", "Question: What are the main policies of the New Patriotic Party?\nDecision:"),
            ("assistant", "yes"),

            ("human", "Question: Tell me about the weather in Canada.\nDecision:"),
            ("assistant", "no"), 

            ("human", "Question: Who won the last election in Ghana?\nDecision:"),
            ("assistant", "yes"),

            ("human", "Question: How to cook Italian pasta?\nDecision:"),
            ("assistant", "no"),

            ("human", "Question: When is the 2024 election date?\nDecision:"),
            ("assistant", "yes"),



            ("human", "Question: hey\nDecision:"),
            ("assistant", "yes"),


            ("human", "Question: hey, what are you here for?\nDecision:"),
            ("assistant", "yes"),

            ("human", "Question: rgasdgfccdc45646..0§&/\nDecision:"),
            ("assistant", "no"),

            ("human", "Question: test\nDecision:"), 
            ("assistant", "no"),
            ("human", "Question: {question}\nDecision:")
        ]
    )




    question_router = route_prompt | get_llm().with_structured_output(RouteQuery)
        
    source = question_router.invoke({"question": question})
    logging.info(source)
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
    system = """You are a grader assessing whether an answer addresses / resolves a question. Give a binary score 'yes' or 'no'. Yes' means that the answer resolves the question."""
    answer_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
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
    if grade == "yes":
        logging.info("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        # Check question-answering
        logging.info("---GRADE GENERATION vs QUESTION---")
        score = answer_grader.invoke({"question": question, "generation": generation})
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