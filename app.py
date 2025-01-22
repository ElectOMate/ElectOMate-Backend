import uvicorn
import asyncio
import base64
import io
import time
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated, List
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
import markdown

# Importing from backend
from backend.models import SupportedCountries, Question, Response, UserAnswer, CustomAnswerEvaluationRequest, PartyResponse, AskAllPartiesResponse
from backend.responses import DEFAULT_RESPONSE
from backend.clients import AzureOpenAIClientManager, WeaviateClientManager
from backend.rag import RAG
from backend.custom_answer_evaluation import get_random_party_scores, get_custom_answers_evaluation
from backend.bing_litellm import router as ai_router
from backend.audio_transcription import router as audio_router

# <-- NEW: import our azure TTS function
from backend.azure_tts import generate_speech

# Importing from browser_use
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
from browser_use.controller.service import Controller
from browser_use.agent.service import Agent
from langchain_openai import ChatOpenAI
from playwright.async_api import Page

class TTSRequest(BaseModel):
    text: str

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

    # Add these if needed
    google_api_key: str
    litellm_api_key: str
    bing_api_key: str
    litellm_api_base_url: str

    azure_openai_api_key_stt: str
    azure_openai_endpoint_stt: str
    openai_api_key: str

    azure_speech_key: str
    azure_speech_region: str

    model_config = SettingsConfigDict(env_file=".env",  extra="allow" )

settings = Settings()

async def lifespan(app: FastAPI):
    global global_browser, global_context

    global_browser = Browser(
        config=BrowserConfig(
            headless=False,
            disable_security=True
        )
    )
    global_context = await global_browser.new_context()
    page = await global_context.get_current_page()
    await page.goto("about:blank")

    yield

    if global_browser:
        await global_browser.close()
        global_browser = None

app = FastAPI(lifespan=lifespan)

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
    if question is None:
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
    if question is None:
        return DEFAULT_RESPONSE("Germany")

    rag = RAG()
    return {"r": rag.invoke(question, weaviate_client, openai_client)}

@app.post("/custom_answer_evaluation")
async def custom_answer_evaluation(
    custom_answer_evaluation_request: CustomAnswerEvaluationRequest,
    openai_client: Annotated[AzureOpenAIClientManager, Depends(get_azure_openai_client)],):
    for question, answer in zip(custom_answer_evaluation_request.questionnaire_questions, custom_answer_evaluation_request.custom_answers):
        print(f"question={question.q}, users_answer={answer.users_answer}, custom_answer={answer.custom_answer}")

    custom_answers_results = await get_custom_answers_evaluation(custom_answer_evaluation_request.questionnaire_questions,
                            custom_answer_evaluation_request.custom_answers, openai_client)
    return custom_answers_results

@app.post("/askallparties/{country_code}", response_model=AskAllPartiesResponse)
async def askallparties(
    country_code: SupportedCountries,
    question_body: Question,
    weaviate_client: Annotated[WeaviateClientManager, Depends(get_weaviate_client)],
    openai_client: Annotated[AzureOpenAIClientManager, Depends(get_azure_openai_client)],
) -> AskAllPartiesResponse:
    logging.info(f"POST request received at /askallparties/{country_code}/...")

    question: str = question_body.question
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    parties_info = [
        {"party": "CDU", "description": "Christian Democratic Union of Germany"},
        {"party": "SPD", "description": "Social Democratic Party of Germany"},
    ]

    rag = RAG()
    tasks = []
    responses = []
    for p in parties_info:
        task = asyncio.create_task(ask_party(p["party"], question, rag, weaviate_client, openai_client))
        tasks.append(task)

    responses = await asyncio.gather(*tasks)

    return AskAllPartiesResponse(responses=responses)

async def ask_party(party: str, question: str, rag: RAG, weaviate_client: WeaviateClientManager, openai_client: AzureOpenAIClientManager):
    prefixed_question = f"What would {party} say to this: {question}"
    response = rag.invoke(prefixed_question, weaviate_client, openai_client)
    policies = [s.strip() for s in response.split(".") if s.strip()]
    return PartyResponse(
        party=party,
        description=party,
        policies=policies
    )

# ------------------------------
# NEW Azure TTS endpoint
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

    # Return the audio as a streaming response
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    global global_agent, global_context
    if not global_agent:
        controller = Controller()
        model = ChatOpenAI(model="gpt-4o")
        global_agent = Agent(
            task="(Empty task, we'll control it with manual instructions)",
            llm=model,
            controller=controller,
            browser_context=global_context
        )

    sending_frames = True

    async def send_frames_loop():
        while sending_frames:
            try:
                page = await global_context.get_current_page()
                screenshot_bytes = await page.screenshot(full_page=False)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                await websocket.send_json({"type": "frame", "data": screenshot_b64})
                await asyncio.sleep(1.0)
            except Exception as e:
                print("Error sending frames:", e)
                break

    frame_task = asyncio.create_task(send_frames_loop())

    try:
        while True:
            msg = await websocket.receive_text()
            if msg.startswith("goto "):
                url = msg.replace("goto ", "").strip()
                page = await global_context.get_current_page()
                await page.goto(url)
            elif msg.startswith("scroll"):
                page = await global_context.get_current_page()
                await page.evaluate("window.scrollBy(0, 400);")
            elif msg.startswith("done"):
                await websocket.send_text("Okay, finishing up!")
                break
            else:
                await websocket.send_text(f"Received unknown instruction: {msg}")

            await websocket.send_text(f"Executed command: {msg}")

    except WebSocketDisconnect:
        print("Client disconnected.")
    finally:
        sending_frames = False
        frame_task.cancel()
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)