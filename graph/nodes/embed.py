import logging
import os
from openai import AzureOpenAI

def embed(state):
    logging.info("---EMBED---")
    question = state["question"]
    
    openai_client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2023-05-15",
    )
    response = openai_client.embeddings.create(
        input=question,
        model=os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
    )
    embedding = response.data[0].embedding
    return {"question": question, "question_embedding": embedding}