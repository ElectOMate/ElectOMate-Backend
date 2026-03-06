"""Provides tracing utilities for FastAPI applications."""

import logging
import os
from typing import Any

from fastapi import FastAPI
from starlette_context import context
from starlette_context.header_keys import HeaderKeys

from em_backend.api.middleware import API_LOGGER_NAME

_logger = logging.getLogger(API_LOGGER_NAME)


def add_obervability(app: FastAPI) -> None:
    """Setup Jaeger tracing on the application."""
    # Force-disable httpx and grpc auto-instrumentation. configure_azure_monitor
    # auto-instruments all detected libraries; httpx/grpc patching breaks
    # Weaviate's internal gRPC connections (DEADLINE_EXCEEDED).
    os.environ["OTEL_PYTHON_DISABLED_INSTRUMENTATIONS"] = (
        "httpx,grpc,grpc_client,grpc_server,grpcio,aiohttp,urllib3,urllib"
    )
    _logger.info(
        "Observability: disabled instrumentations=%s",
        os.environ["OTEL_PYTHON_DISABLED_INSTRUMENTATIONS"],
    )

    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry.instrumentation.fastapi import (
        FastAPIInstrumentor,
    )
    from opentelemetry.trace import Span

    # === Setup Tracing === #

    configure_azure_monitor(logger_name=API_LOGGER_NAME)
    _logger.info("Observability: Azure Monitor configured")

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

    # NOTE: HTTPXClientInstrumentor was removed because it globally patches
    # httpx, which breaks the Weaviate client's internal HTTP/gRPC operations
    # and causes DEADLINE_EXCEEDED errors on hybrid search queries.
