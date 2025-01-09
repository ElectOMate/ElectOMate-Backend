from backend.models import SupportedCountries, Question, Response, UserAnswer, CustomAnswerEvaluationRequest
from backend.responses import DEFAULT_RESPONSE
from backend.clients import AzureOpenAIClientManager, WeaviateClientManager
from backend.rag import RAG
from backend.custom_answer_evaluation import get_random_party_scores

from fastapi import FastAPI, Depends, HTTPException,  File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from typing import Annotated, List
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
import markdown
from backend.bing_litellm import router as ai_router
from backend.audio_transcription import router as audio_router



class Settings(BaseSettings):
    weaviate_http_host: str
    weaviate_grcp_host: str
    weaviate_user_api_key: str
    azure_openai_api_key: str
    azure_endpoint: str
    chat_deployement: str
    openai_api_version: str
    embedding_deployement: str

    # Add these if you truly need them:
    google_api_key: str
    litellm_api_key: str
    bing_api_key: str
    litellm_api_base_url: str

    azure_openai_api_key_stt: str
    azure_openai_endpoint_stt: str
    openai_api_key: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
app = FastAPI()

app.include_router(audio_router)

app.include_router(ai_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000","https://electomate.com", "http://localhost:5173", "http://127.0.0.1:5173", "https://electomate.com/Germany" ],  # Replace with your domain(s)
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
    question_body: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[
        AzureOpenAIClientManager, Depends(get_azure_openai_client)
    ],
) -> Response:
    logging.info(f"POST request received at /chat/{country_code}/...")

    # Extract question from json request body
    question: str = question_body.question
    if question is not None:
        logging.debug(f"POST body found with question '{question}'.")
    else:
        return DEFAULT_RESPONSE("Germany")
        
    # Initiate RAG
    rag = RAG()

    # Return the full response
    return {"r": rag.invoke(question, weaviate_client, openai_client)}



@app.post("/custom_answer_evaluation")
async def custom_answer_evaluation(user_answers: List[UserAnswer]):
    # At this point, user_answers is a Python list of UserAnswer objects.
    # You can do whatever custom logic/evaluation you need here:
    for answer in user_answers:
        # For example, just print them out (or store them, score them, etc.)
        print(f"users_answer={answer.users_answer}, custom_answer={answer.custom_answer}")
    

    custom_answers_results = get_random_party_scores(user_answers)



    #custom_answers = {"custom_answers": [answer.custom_answer for answer in user_answers]}
    return custom_answers_results



