import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from em_backend.core.logging import setup_logging
from em_backend.custom_answers import custom_answers_router
from em_backend.middleware.logging import LoggingMiddleware
from em_backend.query import query_router
from em_backend.realtime import realtime_router
from em_backend.routers import v2
from em_backend.transcription import transcription_router
from em_backend.upload import upload_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    setup_logging()
    # load_party_answers()
    # await weaviate_async_client.connect()
    yield
    # await weaviate_async_client.close()


app = FastAPI(lifespan=lifespan)

# The logging middleware
app.add_middleware(LoggingMiddleware, app)

app.include_router(query_router.router)
app.include_router(realtime_router.router)
app.include_router(upload_router.router)
app.include_router(transcription_router.router)
app.include_router(custom_answers_router.router)
app.include_router(v2.v2_router)


@app.get("/health")
async def read_root() -> dict[str, str]:
    logging.debug("GET request received at root...")
    return {"health": "Ok"}
