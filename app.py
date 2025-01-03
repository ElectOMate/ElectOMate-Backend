from backend.models import SupportedCountries, Question, Response
from backend.responses import DEFAULT_RESPONSE
from backend.clients import AzureOpenAIClientManager, WeaviateClientManager
from backend.rag import RAG


from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from typing import Annotated
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

class Settings(BaseSettings):
    weaviate_http_host: str
    weaviate_grcp_host: str
    weaviate_user_api_key: str
    azure_openai_api_key: str
    azure_endpoint: str
    chat_deployement: str
    openai_api_version: str
    embedding_deployement: str
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000","https://electomate.com", "http://localhost:5173", "http://127.0.0.1:5173" ],  # Replace with your domain(s)
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    logging.info("GET request received at root...")
    return {"Hello": "World"}


async def get_weaviate_client():
    return WeaviateClientManager(
        http_host=settings.weaviate_http_host,
        grcp_host=settings.weaviate_grcp_host,
        user_api_key=settings.weaviate_user_api_key,
        openai_api_key=settings.azure_openai_api_key
    )


async def get_azure_openai_client():
    return AzureOpenAIClientManager(
        api_key=settings.azure_openai_api_key,
        endpoint=settings.azure_endpoint,
        api_version=settings.openai_api_version,
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
    return {"r": rag.invoke(question, weaviate_client, openai_client)}