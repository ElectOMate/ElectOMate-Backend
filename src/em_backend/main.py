from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from em_backend.api.exceptions import add_exception_handlers
from em_backend.api.middleware import add_middleware
from em_backend.api.observability import add_obervability
from em_backend.api.routers import v2
from em_backend.core.config import settings
from em_backend.core.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    setup_logging()
    yield


app = FastAPI(lifespan=lifespan)

add_middleware(app)
add_exception_handlers(app)
if settings.env == "prod":
    add_obervability(app)

app.include_router(v2.v2_router)


@app.get("/health")
async def read_root() -> dict[str, str]:
    return {"health": "Ok"}
