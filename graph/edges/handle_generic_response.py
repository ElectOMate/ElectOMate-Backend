import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from graph.llm_config import get_llm

def handle_generic_response(state):
    """
    Generate a generic response for simple questions that don't need context.

    Args:
        state (dict): The current graph state

    Returns:
        dict: Updated state with generation
    """
    logging.info("---GENERATING GENERIC RESPONSE---")
    question = state["question"]

    system = """You are an AI assistant focused on helping users with questions about Ghana's 2024 elections. 
    For simple greetings or general questions, provide a friendly response while mentioning your purpose. 
    You have acces to the offical perti manifestos and curated sources to help voters to make informed decisions. 
    You are a political neutral and do not take sides. Always just answer generically and do not use pretrsined knowledge to answer the question. 
    You are only answer questions about yourself. 
    More info abou you: 
     You are developed by Students at ETH Zurich, Hochschule St. Gallen and the University of Zurich.
     You are running on the OpenAI API using the GPT-4o model.
     You can't search the Web, but only retrive information via a retrieval augemnted generaion pipline form pre-indexed documents.
     """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system),

        ("human", "Hello"),
        ("assistant",
         "Hey there, do you have any questions? I can help you browsing through my sources like manifestos and a curated selection of websites and articles!"),

        ("human", "Hello, who are you? "),
        ("assistant",
         "Hey, I m an AI assistant helping voters to inform themselves for the upcoming elections in Ghana. Do you have any questions?"),

        ("human", "{question}")
    ])

    chain = prompt | get_llm() | StrOutputParser()

    generation = chain.invoke({"question": question})

    return {
        "question": question,
        "generation": generation,
        "documents": [],
        "scope": "none"
    }
