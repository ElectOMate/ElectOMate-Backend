"""Provides tracing utilities for FastAPI applications."""

from typing import Any

from fastapi import FastAPI
from starlette_context import context
from starlette_context.header_keys import HeaderKeys

from em_backend.api.middleware import API_LOGGER_NAME


def add_obervability(app: FastAPI) -> None:
    """Setup Jaeger tracing on the application."""
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry.instrumentation.fastapi import (
        FastAPIInstrumentor,
    )
    from opentelemetry.instrumentation.httpx import (
        HTTPXClientInstrumentor,
    )
    from opentelemetry.trace import Span

    # === Setup Tracing === #

    configure_azure_monitor(logger_name=API_LOGGER_NAME)

    # === Instrumentation === #

    def server_request_hook(span: Span, scope: dict[str, Any]) -> None:
        if span and span.is_recording() and context.exists():
            span.set_attributes(
                {
                    k.value if isinstance(k, HeaderKeys) else k: v
                    for k, v in context.items()
                }
            )

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=r"/health,/metrics,/docs",
        server_request_hook=server_request_hook,
    )

    # Instrument HTTPX
    HTTPXClientInstrumentor().instrument()
