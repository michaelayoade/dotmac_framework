"""
Structured logging foundation for DotMac Framework
"""

import logging
import sys
from typing import Any

import structlog


def setup_logging(
    level: str = "INFO",
    json_logs: bool = False,
    include_tracing: bool = True,
) -> None:
    """
    Configure structured logging for DotMac applications

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Whether to output JSON formatted logs
        include_tracing: Whether to include tracing information
    """
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]

    if include_tracing:
        processors.append(structlog.processors.dict_tracebacks)

    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        logger_factory=structlog.WriteLoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )


def get_logger(name: str, **context: Any) -> structlog.BoundLogger:
    """
    Get a structured logger with optional context

    Args:
        name: Logger name (typically __name__)
        **context: Additional context to bind to logger

    Returns:
        Structured logger instance
    """
    logger = structlog.get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger


class LoggerMixin:
    """Mixin to add structured logging to classes"""

    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class"""
        return get_logger(
            f"{self.__class__.__module__}.{self.__class__.__name__}",
            class_name=self.__class__.__name__,
        )

    def log_with_context(self, level: str, message: str, **context: Any) -> None:
        """Log message with additional context"""
        getattr(self.logger, level.lower())(message, **context)
