import asyncio
import signal
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from structlog.stdlib import get_logger

from em_backend.api.exceptions import add_exception_handlers
from em_backend.api.middleware import add_middleware
from em_backend.api.observability import add_obervability
from em_backend.api.routers import v2
from em_backend.core.config import settings
from em_backend.core.logging import setup_logging

logger = get_logger(__name__)

# Track active document processing tasks so SIGTERM waits for them
active_document_tasks: set[asyncio.Task] = set()  # noqa: RUF012

GRACEFUL_SHUTDOWN_TIMEOUT = 600  # 10 min max wait for background tasks


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    setup_logging()

    # Install SIGTERM handler that waits for active document tasks
    loop = asyncio.get_running_loop()
    original_handler = signal.getsignal(signal.SIGTERM)

    def _graceful_sigterm(signum: int, frame: object) -> None:
        if active_document_tasks:
            logger.info(
                f"SIGTERM received — waiting for {len(active_document_tasks)} "
                f"active document task(s) to finish (up to {GRACEFUL_SHUTDOWN_TIMEOUT}s)"
            )
            # Schedule the wait as a coroutine on the event loop
            loop.create_task(_wait_for_tasks_then_shutdown(original_handler, signum, frame))
        else:
            logger.info("SIGTERM received — no active document tasks, shutting down immediately")
            if callable(original_handler):
                original_handler(signum, frame)

    signal.signal(signal.SIGTERM, _graceful_sigterm)

    yield


async def _wait_for_tasks_then_shutdown(
    original_handler: object, signum: int, frame: object
) -> None:
    """Wait for active document processing tasks, then re-raise SIGTERM."""
    if active_document_tasks:
        try:
            await asyncio.wait(active_document_tasks, timeout=GRACEFUL_SHUTDOWN_TIMEOUT)
            remaining = [t for t in active_document_tasks if not t.done()]
            if remaining:
                logger.warning(
                    f"Graceful shutdown timeout — {len(remaining)} task(s) still running, "
                    "cancelling"
                )
                for t in remaining:
                    t.cancel()
            else:
                logger.info("All document tasks completed — proceeding with shutdown")
        except Exception as e:
            logger.error(f"Error during graceful shutdown wait: {e}")
    # Re-raise original SIGTERM behavior
    if callable(original_handler):
        original_handler(signum, frame)


app = FastAPI(lifespan=lifespan)

add_middleware(app)
add_exception_handlers(app)
if settings.env == "prod":
    add_obervability(app)

app.include_router(v2.v2_router)


@app.get("/health")
async def read_root() -> dict[str, str]:
    return {"health": "Ok"}
