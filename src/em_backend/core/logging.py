"""Logging configuration and setup for the application.

This module provides structured logging configuration using structlog,
with environment-specific formatters and handlers. It supports both
console-friendly development logging and JSON-formatted production logging.
"""

import logging
import sys
from typing import Any, cast

import orjson
import structlog
from pythonjsonlogger.orjson import OrjsonFormatter

from em_backend.config import settings


def setup_logging_prod() -> None:
    """Configure logging in the production setup.

    The structlog logging and the stdlib logging are fully decoupled.

    ## Structlog

    The structlog setup is meant to be as fast as possible. Serializing with orjson
    and building the static logger class. It renders everything as json to stdout.

    ## Stdlib logging

    The stdlib logging setup is also logging to json (with orjson) to stdout. It is
    using `python-json-logger`.
    """
    # # Opentelemetry is not installed in dev
    # from opentelemetry import trace

    # def add_open_telemetry_spans(
    #     _, __, event_dict: structlog.types.EventDict
    # ) -> MutableMapping[str, Any]:
    #     """Add opentelemetry span ids to event dict."""
    #     span = trace.get_current_span()
    #     if not span.is_recording():
    #         event_dict["span"] = None
    #         return event_dict

    #     ctx = span.get_span_context()
    #     parent = getattr(span, "parent", None)

    #     event_dict["span"] = {
    #         "span_id": format(ctx.span_id, "016x"),
    #         "trace_id": format(ctx.trace_id, "032x"),
    #         "parent_span_id": None if not parent else format(parent.span_id, "016x"),
    #     }

    #     return event_dict

    # Structlog
    structlog.configure_once(
        processors=[
            # You should not use contextvars binding with structlog
            # The starlette execution model does not work properly with it
            # See https://github.com/fastapi/fastapi/discussions/5999
            # Instead, we use startlette-context (https://pypi.org/project/starlette-context/)
            structlog.contextvars.merge_contextvars,
            # add_open_telemetry_spans,
            # Add log level to event dict.
            structlog.processors.add_log_level,
            # If the "exc_info" key in the event dict is either true or a
            # sys.exc_info() tuple, remove "exc_info" and render the exception
            # with traceback into the "exception" key.
            structlog.processors.dict_tracebacks,
            # Add time stamp
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Use orjson for rendering the log entries
            # That is faster that logging with stdlib logging
            structlog.processors.JSONRenderer(serializer=orjson.dumps),
        ],
        # Creating a static class is faster than using processors
        wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
        # Orjson returns a bytes object
        logger_factory=structlog.BytesLoggerFactory(),
    )

    # Stdlib logging
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(OrjsonFormatter())
    logger.addHandler(handler)


def setup_logging_dev(**kwargs: dict) -> None:
    """Configure logging in the development setup.

    Structlog is piped through the stdlib logger.

    ## Structlog

    We use the stdlib logger intergration to our advantage. This allows
    for loggers with names. In addition, as `rich` is in the development
    setup, we will pretty print the stack traces. In addition, we render
    it to console formated strings and pipe it to the stdlib logger.

    ## Stdlib logging

    As simple as it gets.
    """
    # Structlog
    structlog.configure_once(
        processors=[
            # If log level is too low, abort pipeline and throw away log entry.
            structlog.stdlib.filter_by_level,
            # You should not use contextvars binding with structlog
            # The starlette execution model does not work properly with it
            # See https://github.com/fastapi/fastapi/discussions/5999
            # Instead, we use startlette-context (https://pypi.org/project/starlette-context/)
            structlog.contextvars.merge_contextvars,
            # Add the name of the logger to event dict.
            structlog.stdlib.add_logger_name,
            # Add log level to event dict.
            structlog.stdlib.add_log_level,
            # Perform %-style formatting.
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add a timestamp in ISO 8601 format.
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # If the "stack_info" key in the event dict is true, remove it and
            # render the current stack trace in the "stack" key.
            structlog.processors.StackInfoRenderer(),
            # If some value is in bytes, decode it to a Unicode str.
            structlog.processors.UnicodeDecoder(),
            # Add callsite parameters.
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                }
            ),
            # Render it to the console
            structlog.dev.ConsoleRenderer(),
        ],
        # `wrapper_class` is the bound logger that you get back from
        # get_logger(). This one imitates the API of `logging.Logger`.
        wrapper_class=structlog.stdlib.BoundLogger,
        # `logger_factory` is used to create wrapped loggers that are used for
        # OUTPUT. This one returns a `logging.Logger`. The final value (a JSON
        # string) from the final processor (`JSONRenderer`) will be passed to
        # the method of the same name as that you've called on the bound logger.
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Effectively freeze configuration after creating the first bound
        # logger.
        cache_logger_on_first_use=True,
    )

    logging_kwargs: dict[str, Any] = {}

    # If a handler is supplied
    handlers = cast("logging.Handler | None", kwargs.pop("handlers", None))
    if handlers:
        logging_kwargs |= {"handlers": handlers}
    else:
        logging_kwargs |= {"stream": sys.stdout}

    # Setup logging
    logging.basicConfig(format="%(message)s", level=logging.DEBUG, **logging_kwargs)

    # Specific settings to prevent request dumps
    # If you want to log requests, you are probably better of using a proxy like mitmproxy
    # See https://mitmproxy.org/
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("openai._base_client").setLevel(logging.INFO)
    logging.getLogger("langfuse").setLevel(logging.INFO)


def setup_logging(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
    """Logging setup based on environment."""
    if settings.env == "prod":
        setup_logging_prod()
    else:
        from rich.traceback import install  # type: ignore

        install(show_locals=True)
        setup_logging_dev(**kwargs)
