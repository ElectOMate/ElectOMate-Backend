import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from em_backend.config import settings, weaviate_async_client
from em_backend.custom_answers import custom_answers_router
from em_backend.query import query_router
from em_backend.realtime import realtime_router
from em_backend.statics.party_answers import load_party_answers
from em_backend.transcription import transcription_router
from em_backend.upload import upload_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_party_answers()
    await weaviate_async_client.connect()
    yield
    await weaviate_async_client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(query_router.router)
app.include_router(realtime_router.router)
app.include_router(upload_router.router)
app.include_router(transcription_router.router)
app.include_router(custom_answers_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def read_root():
    logging.debug("GET request received at root...")
    return {"health": "Ok"}
