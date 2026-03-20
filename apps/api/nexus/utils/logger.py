"""Structured logging configuration using structlog."""

import io
import logging
import sys

import structlog


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    # Force UTF-8 output on Windows to prevent cp949 codec errors
    # when log messages contain unicode characters (em dash, etc.)
    log_output = sys.stderr
    if sys.platform == "win32" and hasattr(sys.stderr, "buffer"):
        log_output = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=log_output),
        cache_logger_on_first_use=True,
    )
