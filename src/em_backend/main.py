from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from em_backend.core.logging import setup_logging
from em_backend.middleware.logging import LoggingMiddleware
from em_backend.routers import v2


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    setup_logging()
    yield


app = FastAPI(lifespan=lifespan)

# The logging middleware
app.add_middleware(LoggingMiddleware, app)

app.include_router(v2.v2_router)


@app.get("/health")
async def read_root() -> dict[str, str]:
    return {"health": "Ok"}
