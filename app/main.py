from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import json
import logging

from .config import weaviate_async_client, settings
from .query import query_router
from .realtime import realtime_router
from .upload import upload_router
from .Bingsearch import Bingsearch_router
from .transcription import transcription_router
from .askallparties import askallparties_router
from .api2 import router as api2_router
from .custom_answer_evaluation import custom_answer_evaluation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await weaviate_async_client.connect()
    yield
    # Shutdown
    await weaviate_async_client.close()


app = FastAPI(lifespan=lifespan)

app.include_router(query_router.router)
app.include_router(realtime_router.router)
app.include_router(upload_router.router)
app.include_router(Bingsearch_router.router)
app.include_router(transcription_router.router)
app.include_router(askallparties_router.router)
app.include_router(api2_router.router)
app.include_router(custom_answer_evaluation.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def read_root():
    logging.debug("GET request received at root...")
    return {"health": "Ok"}

@app.on_event("startup")
async def startup_event():
    for route in app.routes:
        logger.info(f"Registered route: {route.path} with methods: {route.methods}")

@app.on_event("shutdown")
async def shutdown_event():
    # Add your shutdown logic here
    pass


