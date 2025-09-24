"""Middleware setup module.

This module sets up two important middlewares:
- Context middleware: contextvars are not enough to keep context inside a single request
  in startlette, we use the starlette-context library for that
- Logging middleware: following the [11th factor](https://brandur.org/canonical-log-lines#what-are-they)
  we only emit one log per request, this is the log emission
"""

import logging
from time import perf_counter
from typing import Any
from urllib.parse import quote

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.routing import Mount
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.routing import Match
from starlette.types import ASGIApp, Scope
from starlette_context import plugins
from starlette_context.middleware import RawContextMiddleware

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


def get_route_name(app: ASGIApp, scope: Scope, prefix: str = "") -> str:
    """Generate a descriptive route name for timing metrics."""
    if prefix:
        prefix += "."

    route = next(
        (r for r in app.router.routes if r.matches(scope)[0] == Match.FULL),  # type: ignore
        None,
    )

    if hasattr(route, "endpoint") and hasattr(route, "name"):
        return f"{prefix}{route.endpoint.__module__}.{route.name}"  # type: ignore
    elif isinstance(route, Mount):
        return f"{type(route.app).__name__}<{route.name!r}>"
    else:
        return scope["path"]


def get_path_with_query_string(scope: Scope) -> str:
    """Get the URL with the substitution of query parameters.

    Args:
        scope (Scope): Current context.

    Returns:
        str: URL with query parameters
    """
    if "path" not in scope:
        return "-"
    path_with_query_string = quote(scope["path"])
    if raw_query_string := scope["query_string"]:
        query_string = raw_query_string.decode("ascii")
        path_with_query_string = f"{path_with_query_string}?{query_string}"
    return path_with_query_string


def get_client_addr(scope: Scope) -> str:
    """Get the client's address.

    Args:
        scope (Scope): Current context.

    Returns:
        str: Client's address in the IP:PORT format.
    """
    client = scope.get("client")
    if not client:
        return ""
    ip, port = client
    return f"{ip}:{port}"


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log canonical log lines."""

    def __init__(self, app: ASGIApp, fastapi_app: FastAPI) -> None:
        """Init middleware."""
        super().__init__(app)
        self.fastapi_app = fastapi_app

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Middleware function."""
        # Clear context on request handling
        structlog.contextvars.clear_contextvars()

        # Get some request context
        scope = request.scope
        route_name = get_route_name(self.fastapi_app, request.scope)

        start = perf_counter()
        response = await call_next(request)

        assert start
        elapsed = perf_counter() - start

        # In production, we perform a cannonical log line per request
        # https://brandur.org/canonical-log-lines
        log_kwargs: dict[str, Any] = {
            "level": logging.INFO if response.status_code < 400 else logging.ERROR,
            "event": f"{response.status_code} {scope['method']}"
            "{get_path_with_query_string(scope)}",
            "time": round(elapsed * 1000),
            "status": response.status_code,
            "method": scope["method"],
            "path": scope["path"],
            "query": scope["query_string"].decode(),
            "client_ip": get_client_addr(scope),
            "route": route_name,
        }
        if response.status_code >= 400:
            log_kwargs.update({"level": logging.ERROR})
        else:
            log_kwargs["level"] = logging.INFO
        if scope["path"] not in ("/metrics", "/metrics/", "/health"):
            logger.log(**log_kwargs)

        return response


def add_middleware(app: FastAPI) -> None:
    """Adds middleware for context management request across request."""
    # For some reason, the first added middleware gets executed last
    # https://fastapi.tiangolo.com/tutorial/middleware/#multiple-middleware-execution-order

    # The logging middleware
    app.add_middleware(LoggingMiddleware, app)

    # We add a context middleware for context management accross requests
    app.add_middleware(
        # Raw context middleware works better with streaming responses
        # https://starlette-context.readthedocs.io/en/latest/middleware.html#choosing-the-right-middleware
        RawContextMiddleware,
        plugins=(plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
    )
