import logging
import os
from weaviate import WeaviateClient
from weaviate.classes.init import Auth
from weaviate.config import AdditionalConfig, Timeout
from weaviate.connect import ConnectionParams, ProtocolParams
from langchain_weaviate.vectorstores import WeaviateVectorStore


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
    embedding = state["question_embedding"]
    
    weaviate_client = WeaviateClient(
        connection_params=ConnectionParams(
            http=ProtocolParams(
                host=os.getenv('WEAVIATE_EXTERNAL_IP'),
                port=80,
                secure=False
            ),
            grpc=ProtocolParams(
                host=os.getenv('GRPC_EXTERNAL_IP'),
                port=50051,
                secure=False
            )
        ),
        auth_client_secret=Auth.api_key(api_key=os.getenv('USER_KEY')),
        additional_config=AdditionalConfig(
            timeout=Timeout(init=30, query=60, insert=120)
        )
    )
    retriever = WeaviateVectorStore(weaviate_client, index_name="Document_Chunk").as_retriever()

    # Retrieval
    documents = retriever.invoke(question, vector=embedding)
    return {"documents": documents, "question": question}
