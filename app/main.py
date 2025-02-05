from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import logging
import json

from .config import weaviate_async_client, settings
from .query import query_router
from .realtime import realtime_router
from .upload import upload_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await weaviate_async_client.connect()
    yield
    await weaviate_async_client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(query_router.router)
app.include_router(realtime_router.router)
if settings.prod is False:
    app.include_router(upload_router.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=json.loads(settings.allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def read_root():
    logging.debug("GET request received at root...")
    return {"health": "Ok"}
