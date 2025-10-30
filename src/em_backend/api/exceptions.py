"""Exception handlers for the application."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette_context import context


def add_validation_error_handler(app: FastAPI) -> None:
    """Adds a validation handler for logging."""

    
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        """Adds validation errors to logging."""
        context["exc_info"] = exc

        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"name": "ValidationError", "detail": str(exc)},
        )


def add_exception_handlers(app: FastAPI) -> None:
    """Adds exception handlers to the application."""
    add_validation_error_handler(app)
