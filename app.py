from backend.models import SupportedCountries, Question, Response, UserAnswer, CustomAnswerEvaluationRequest, PartyResponse, AskAllPartiesResponse
from backend.responses import DEFAULT_RESPONSE
from backend.clients import AzureOpenAIClientManager, WeaviateClientManager
from backend.rag import RAG
from backend.custom_answer_evaluation import get_random_party_scores

from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
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

    # Add these if needed
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
    allow_origins=[
        "http://localhost:8000", "http://127.0.0.1:8000",
        "https://electomate.com", "http://localhost:5173",
        "http://127.0.0.1:5173", "https://electomate.com/Germany"
    ],
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

@app.get("/test")
async def test_endpoint():
    return {"msg": "This is a test endpoint."}

@app.post("/stream/{country_code}")
async def stream(
    country_code: SupportedCountries,
    question: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[AzureOpenAIClientManager, Depends(get_azure_openai_client)],
) -> Response:
    logging.info(f"POST request received at /stream/{country_code}/...")

    question = question.q
    if question is not None:
        logging.debug(f"POST body found with question '{question}'.")
    else: 
        return DEFAULT_RESPONSE("Germany")

    rag = RAG()
    return StreamingResponse(rag.stream(question, weaviate_client, openai_client))






@app.post("/chat/{country_code}")
def chat(
    country_code: SupportedCountries,
    question_body: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[AzureOpenAIClientManager, Depends(get_azure_openai_client)],
) -> Response:
    logging.info(f"POST request received at /chat/{country_code}/...")

    question: str = question_body.question
    if question is not None:
        logging.debug(f"POST body found with question '{question}'.")
    else:
        return DEFAULT_RESPONSE("Germany")
        
    rag = RAG()
    return {"r": rag.invoke(question, weaviate_client, openai_client)}

@app.post("/custom_answer_evaluation")
async def custom_answer_evaluation(user_answers: List[UserAnswer]):
    for answer in user_answers:
        print(f"users_answer={answer.users_answer}, custom_answer={answer.custom_answer}")

    custom_answers_results = get_random_party_scores(user_answers)
    return custom_answers_results






@app.post("/askallparties/{country_code}", response_model=AskAllPartiesResponse)
def askallparties(
    country_code: SupportedCountries,
    question_body: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[AzureOpenAIClientManager, Depends(get_azure_openai_client)],
) -> AskAllPartiesResponse:
    logging.info(f"POST request received at /askallparties/{country_code}/...")

    question: str = question_body.question
    if question is None:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Define the biggest German parties
    parties_info = [
        {"party": "CDU",  "description": "Christian Democratic Union of Germany"},
        {"party": "SPD",  "description": "Social Democratic Party of Germany"},
        {"party": "FDP",  "description": "Free Democratic Party"},
        {"party": "Grüne", "description": "Alliance 90/The Greens"},
        {"party": "Linke", "description": "The Left"},
    ]

    rag = RAG()
    responses = []

    for p in parties_info:
        prefixed_question = f"What would {p['party']} say to this: {question}"
        logging.debug(f"Asking {p['party']}: {prefixed_question}")
        response = rag.invoke(prefixed_question, weaviate_client, openai_client)

        # Split the response into policies (split by ".")
        policies = [s.strip() for s in response.split(".") if s.strip()]

        # Append the structured response
        responses.append(PartyResponse(
            party=p["party"],
            description=p["description"],
            policies=policies
        ))

    # Return the response model
    return AskAllPartiesResponse(responses=responses)