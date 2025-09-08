"""
Centralized logging configuration for DotMac Framework
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional


class DotMacFormatter(logging.Formatter):
    """Custom formatter for DotMac Framework logs"""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record):
        # Add service context if available
        if hasattr(record, "service_name"):
            record.name = f"{record.service_name}.{record.name}"

        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            original_msg = record.getMessage()
            record.msg = f"[{record.correlation_id}] {original_msg}"
            record.args = None

        return super().format(record)


def get_logger(name: str, service_name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance with DotMac Framework formatting

    Args:
        name: Logger name (typically __name__)
        service_name: Service name for context (e.g., 'isp-service')

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Add service context to all log records from this logger
    if service_name:
        # Create a filter to add service_name to all records
        def add_service_name(record):
            record.service_name = service_name
            return True

        logger.addFilter(add_service_name)

    return logger


def setup_logging(
    level: str = "INFO",
    service_name: Optional[str] = None,
    enable_json: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Setup centralized logging configuration

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Service name for log context
        enable_json: Enable JSON structured logging
        log_file: Optional log file path
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set root level
    root_logger.setLevel(numeric_level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if enable_json:
        # JSON formatter for structured logging (e.g., in production)
        import json

        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                if service_name:
                    log_entry["service"] = service_name

                if hasattr(record, "correlation_id"):
                    log_entry["correlation_id"] = record.correlation_id

                if hasattr(record, "user_id"):
                    log_entry["user_id"] = record.user_id

                return json.dumps(log_entry)

        console_handler.setFormatter(JSONFormatter())
    else:
        # Human-readable formatter
        console_handler.setFormatter(DotMacFormatter())

    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)

        if enable_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(DotMacFormatter())

        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Log the setup completion
    logger = get_logger(__name__, service_name)
    logger.info(f"Logging configured: level={level}, service={service_name}, json={enable_json}")


# Convenience function for adding correlation ID to logs
def with_correlation_id(logger: logging.Logger, correlation_id: str):
    """
    Create a logger adapter that adds correlation ID to all log messages

    Args:
        logger: Base logger instance
        correlation_id: Correlation ID to add to logs

    Returns:
        LoggerAdapter with correlation ID context
    """

    class CorrelationAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            # Add correlation_id to the log record
            if "extra" not in kwargs:
                kwargs["extra"] = {}
            kwargs["extra"]["correlation_id"] = correlation_id
            return msg, kwargs

    return CorrelationAdapter(logger, {})


# Environment-based logging setup
def setup_environment_logging():
    """Setup logging based on environment variables"""
    level = os.getenv("LOG_LEVEL", "INFO")
    service_name = os.getenv("SERVICE_NAME")
    enable_json = os.getenv("LOG_FORMAT", "").lower() == "json"
    log_file = os.getenv("LOG_FILE")

    setup_logging(
        level=level,
        service_name=service_name,
        enable_json=enable_json,
        log_file=log_file,
    )
