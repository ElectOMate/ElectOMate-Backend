import uvicorn
import asyncio
import base64
import io
import time
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Annotated, List, Dict, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
import markdown
import httpx

# Importing from backend
from backend.models import SupportedCountries, Question, Response, UserAnswer, CustomAnswerEvaluationRequest, PartyResponse, AskAllPartiesResponse
from backend.responses import DEFAULT_RESPONSE
from backend.clients import AzureOpenAIClientManager, WeaviateClientManager
from backend.rag import RAG
from backend.custom_answer_evaluation import get_random_party_scores
from backend.bing_litellm import router as ai_router
from backend.audio_transcription import router as audio_router

# <-- TTS if needed
from backend.azure_tts import generate_speech

# Browser-based code if needed
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
from browser_use.controller.service import Controller
from browser_use.agent.service import Agent
from langchain_openai import ChatOpenAI
from playwright.async_api import Page


class TTSRequest(BaseModel):
    text: str

# ------------------------------
# NEW Pydantic model for function-calling
# ------------------------------
class ChatFunctionCallRequest(BaseModel):
    country_code: str
    question_body: Question  # e.g. "question": "User's RAG query"

# Global browser references (if you're using them)
global_browser = None
global_context = None
global_agent = None

class Settings(BaseSettings):
    weaviate_http_host: str
    weaviate_grcp_host: str
    weaviate_user_api_key: str
    azure_openai_api_key: str
    azure_endpoint: str
    chat_deployement: str
    openai_api_version: str
    embedding_deployement: str

    # Additional possible secrets
    google_api_key: str
    litellm_api_key: str
    bing_api_key: str
    litellm_api_base_url: str

    azure_openai_api_key_stt: str
    azure_openai_endpoint_stt: str
    openai_api_key: str

    azure_speech_key: str
    azure_speech_region: str

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings = Settings()
app = FastAPI()

# Include additional routers if needed
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

# ------------------------------
# Dependencies for Weaviate & Azure
# ------------------------------
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

# ------------------------------
# Example streaming route
# ------------------------------
@app.post("/stream/{country_code}")
async def stream(
    country_code: SupportedCountries,
    question: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[AzureOpenAIClientManager, Depends(get_azure_openai_client)],
) -> Response:
    logging.info(f"POST request received at /stream/{country_code}/...")
    question_str = question.q
    if question_str is None:
        return DEFAULT_RESPONSE("Germany")

    rag = RAG()
    return StreamingResponse(rag.stream(question_str, weaviate_client, openai_client))

# ------------------------------
# Existing /chat route
# ------------------------------
@app.post("/chat/{country_code}")
def chat(
    country_code: SupportedCountries,
    question_body: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[AzureOpenAIClientManager, Depends(get_azure_openai_client)],
) -> Response:
    logging.info(f"POST request received at /chat/{country_code}/...")
    question: str = question_body.question
    if question is None:
        return DEFAULT_RESPONSE("Germany")

    rag = RAG()
    return {"r": rag.invoke(question, weaviate_client, openai_client)}

# ------------------------------
# Evaluate custom user answers
# ------------------------------
@app.post("/custom_answer_evaluation")
async def custom_answer_evaluation(user_answers: List[UserAnswer]):
    print(f"user_answers={user_answers}")
    for answer in user_answers:
        print(f"users_answer={answer.users_answer}, custom_answer={answer.custom_answer}")
    custom_answers_results = get_random_party_scores(user_answers)
    return custom_answers_results

# ------------------------------
# Example multi-party question route
# ------------------------------
@app.post("/askallparties/{country_code}", response_model=AskAllPartiesResponse)
async def askallparties(
    country_code: SupportedCountries,
    question_body: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[AzureOpenAIClientManager, Depends(get_azure_openai_client)],
) -> AskAllPartiesResponse:
    logging.info(f"POST request received at /askallparties/{country_code}/...")
    question: str = question_body.question
    selected_parties: Dict[str, bool] = question_body.selected_parties

    if not question:
        logging.error("Received an empty question.")
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    logging.info("Preparing to query parties' responses.")
    rag = RAG()
    tasks = []
    responses = []
    for party, isSelected in selected_parties.items():
        if isSelected:
            prefixed_question = f"What would {party} say to this: {question}"
            logging.debug(f"Querying RAG for party: {party} with question: {prefixed_question}")
            response = rag.invoke(prefixed_question, weaviate_client, openai_client)

            policies = [s.strip() for s in response.split(".") if s.strip()]
            logging.debug(f"Received policies for {party}: {policies}")
            responses.append(PartyResponse(
                party=party,
                policies=policies
            ))

    logging.info(f"responses={responses}")
    logging.info("Successfully gathered responses from selected parties.")
    return AskAllPartiesResponse(responses=responses)












# ------------------------------
# Azure TTS endpoint (Optional)
# ------------------------------
@app.post("/tts")
async def tts_endpoint(request: TTSRequest):
    """
    Receive text from the frontend, generate TTS audio using azure_tts.generate_speech,
    and return the audio as a streaming response.
    """
    logging.info(f"TTS request for text: '{request.text}'")
    audio_bytes = generate_speech(request.text)  # from azure_tts.py

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="Speech synthesis failed or returned empty audio."
        )

    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")

# ------------------------------
# Route to get ephemeral token for Realtime
# ------------------------------
# File: Backend (app.py)
@app.get("/session")
async def get_session():
    """
    Backend route to fetch an ephemeral key from OpenAI Realtime API.
    """
    DEFAULT_INSTRUCTIONS = """
    You are the AI voice assistant for a voting advice application focusing on the upcoming national general elections.
    Your role is to provide accurate, unbiased information about political parties and their positions.
    When asked about any political topic, policy, or party stance, you MUST use the fetchRagData function 
    to retrieve verified information from our database.
    Never rely on your pre-trained knowledge - always use the RAG system for political information.
    If a query isn't about German politics or elections, politely explain that you can only discuss German political topics. Your creators are named "ElectOMate" in german it is pronounced "Elektomait".
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "voice": "verse",
                "instructions": DEFAULT_INSTRUCTIONS,
                "tools": [
                    {
                        "type": "function",
                        "name": "fetchRagData",
                        "description": "Retrieves verified political information from our RAG system",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "country_code": {
                                    "type": "string",
                                    "description": "The country code (e.g., 'de' for Germany)",
                                    "enum": ["DE"]  # Only allow German queries for now
                                },
                                "question_body": {
                                    "type": "object",
                                    "properties": {
                                        "question": {
                                            "type": "string",
                                            "description": "The political question to look up"
                                        }
                                    },
                                    "required": ["question"]
                                }
                            },
                            "required": ["country_code", "question_body"]
                        }
                    }
                ]
            }
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch session: {response.text}"
            )

        data = response.json()
        return {"client_secret": data["client_secret"]}

# ------------------------------
# NEW: function-calling route
# ------------------------------
@app.post("/function/fetch-rag-data")
def fetch_rag_data(
    payload: ChatFunctionCallRequest,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[AzureOpenAIClientManager, Depends(get_azure_openai_client)]
):
    """
    This route is called internally by your function-calling logic (via real-time).
    It just delegates to the RAG pipeline used in /chat/{country_code}.
    """
    country_code = payload.country_code
    question_obj = payload.question_body
    if not question_obj.question:
        raise HTTPException(status_code=400, detail="No question provided.")

    rag = RAG()
    response_data = rag.invoke(question_obj.question, weaviate_client, openai_client)
    return {"r": response_data}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)