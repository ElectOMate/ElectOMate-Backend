"""Logging configuration and setup for the application.

This module provides structured logging configuration using structlog,
with environment-specific formatters and handlers. It supports both
console-friendly development logging and JSON-formatted production logging.
"""

import json
import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog
from opentelemetry import trace
from pythonjsonlogger.orjson import OrjsonFormatter
from starlette_context import context
from starlette_context.header_keys import HeaderKeys

from em_backend.api.middleware import API_LOGGER_NAME
from em_backend.core.config import settings


class ExtraFormatter(logging.Formatter):
    """
    Custom formatter that pretty-prints structlog's extra fields
    alongside the log message.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(*args, **kwargs)
        standard_attrs = set(
            logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        )
        standard_attrs.add("message")
        standard_attrs.add("asctime")
        standard_attrs.add("color_message")
        self.standard_attrs = standard_attrs

    def format(self, record: logging.LogRecord) -> str:
        # Default log message
        base = super().format(record)

        extras = {
            k: v for k, v in record.__dict__.items() if k not in self.standard_attrs
        }

        if extras:
            return f"{base} | extra={json.dumps(extras, default=str)}"
        return base


def add_startlette_context(
    _: structlog.types.WrappedLogger, __: str, event_dict: structlog.types.EventDict
) -> MutableMapping[str, Any]:
    """Add request context to event dict."""
    if context.exists():
        return {
            **event_dict,
            **{
                # Dirty patch until https://github.com/tomwojcik/starlette-context/pull/192
                k.value if isinstance(k, HeaderKeys) else k: v
                for k, v in context.data.items()
            },
        }
    else:
        return event_dict


def add_open_telemetry_spans(
    _: structlog.types.WrappedLogger, __: str, event_dict: structlog.types.EventDict
) -> MutableMapping[str, Any]:
    """Add opentelemetry span ids to event dict."""
    span = trace.get_current_span()
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span"] = {
        "span_id": format(ctx.span_id, "016x"),
        "trace_id": format(ctx.trace_id, "032x"),
        "parent_span_id": None if not parent else format(parent.span_id, "016x"),
    }

    return event_dict


def setup_logging() -> None:
    if settings.env == "prod":
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.contextvars.merge_contextvars,
            add_startlette_context,
            add_open_telemetry_spans,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.dict_tracebacks,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.render_to_log_kwargs,
        ]
    else:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.contextvars.merge_contextvars,
            add_startlette_context,
            add_open_telemetry_spans,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.render_to_log_kwargs,
        ]

    structlog.configure_once(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger = logging.getLogger()

    # Clear any existing handlers to ensure only our handler is used
    logger.handlers.clear()

    if settings.env == "prod":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(OrjsonFormatter())
        logger.setLevel(logging.WARNING)
        logging.getLogger(API_LOGGER_NAME).setLevel(logging.INFO)
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ExtraFormatter("%(levelname)s [%(name)s] %(message)s"))
        logger.setLevel(logging.INFO)
    logger.addHandler(handler)
