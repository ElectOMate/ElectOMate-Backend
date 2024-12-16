from .models import SupportedCountries, Question, Response
from .responses import DEFAULT_RESPONSE
from .clients import AzureOpenAIClientManager, WeaviateClientManager
from .rag import RAG


from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse

from typing import Annotated
from pydantic_settings import BaseSettings
import logging

class Settings(BaseSettings):
    weaviate_http_host: str
    weaviate_grcp_host: str
    weaviate_user_api_key: str
    azure_api_key: str
    azure_endpoint: str
    openai_api_version: str
    chat_deployement: str
    embedding_deployement: str

settings = Settings()
app = FastAPI()


@app.get("/")
async def read_root():
    logging.info("GET request received at root...")
    return {"Hello": "World"}


async def get_weaviate_client():
    return WeaviateClientManager(
        http_host=settings.weaviate_http_host,
        grcp_host=settings.weaviate_grcp_host,
        user_api_key=settings.weaviate_user_api_key
    )


async def get_azure_openai_client():
    return AzureOpenAIClientManager(
        api_key=settings.azure_api_key,
        endpoint=settings.azure_endpoint,
        chat_deployement=settings.chat_deployement,
        embedding_deployement=settings.embedding_deployement
    )


@app.post("/stream/{country_code}")
async def stream(
    country_code: SupportedCountries,
    question: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[
        AzureOpenAIClientManager, Depends(get_azure_openai_client)
    ],
) -> Response:
    logging.info(f"POST request received at /stream/{country_code}/...")

    # Extract question from json request body
    question = question.q
    if question is not None:
        logging.debug(f"POST body found with question '{question}'.")
    else: 
        return DEFAULT_RESPONSE("Germany")
        
    # Inititate RAG
    rag = RAG()

    # Stream the respones
    return StreamingResponse(rag.stream(question, weaviate_client, openai_client))


@app.post("/chat/{country_code}")
def chat(
    country_code: SupportedCountries,
    question: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[
        AzureOpenAIClientManager, Depends(get_azure_openai_client)
    ],
) -> Response:
    logging.info(f"POST request received at /chat/{country_code}/...")

    # Extract question from json request body
    question = question.q
    if question is not None:
        logging.debug(f"POST body found with question '{question}'.")
    else:
        return DEFAULT_RESPONSE("Germany")
        
    # Initiate RAG
    rag = RAG()

    # Return the full response
    return rag.invoke(question, weaviate_client, openai_client)