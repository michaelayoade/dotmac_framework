"""Structured logging configuration for DotMac ISP Framework."""

import json
import logging
import logging.config
import sys
from datetime import datetime, timezone
from typing import Any, Dict
import traceback


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add custom fields from record
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    level: str = "INFO", json_logging: bool = True, log_file: str = None
) -> None:
    """Setup structured logging configuration."""

    # Configure formatters
    formatters = {
        "json": {
            "()": JSONFormatter,
        },
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    }

    # Configure handlers
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if json_logging else "standard",
            "stream": "ext://sys.stdout",
        }
    }

    # Add file handler if specified
    if log_file:
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json" if json_logging else "standard",
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        }

    # Configure root logger
    root_config = {"level": level, "handlers": list(handlers.keys())}

    # Configure specific loggers
    loggers = {
        "dotmac_isp": {
            "level": level,
            "handlers": list(handlers.keys()),
            "propagate": False,
        },
        "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.error": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
    }

    # Apply configuration
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "root": root_config,
        "loggers": loggers,
    }

    logging.config.dictConfig(logging_config)


def get_request_logger(
    request_id: str = None, tenant_id: str = None
) -> logging.LoggerAdapter:
    """Get a logger adapter with request context."""
    logger = logging.getLogger("dotmac_isp.request")

    # Add context information
    extra = {}
    if request_id:
        extra["request_id"] = request_id
    if tenant_id:
        extra["tenant_id"] = tenant_id

    return logging.LoggerAdapter(logger, extra)


def log_api_call(
    method: str,
    path: str,
    status_code: int,
    response_time: float,
    request_id: str = None,
    tenant_id: str = None,
    user_id: str = None,
    client_ip: str = None,
) -> None:
    """Log API call with structured data."""
    logger = logging.getLogger("dotmac_isp.api")

    logger.info(
        "API call completed",
        extra={
            "request_id": request_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "client_ip": client_ip,
            "method": method,
            "path": path,
            "status_code": status_code,
            "response_time_ms": round(response_time * 1000, 2),
            "event_type": "api_call",
        },
    )


def log_business_event(
    event_type: str,
    event_data: Dict[str, Any],
    tenant_id: str = None,
    user_id: str = None,
) -> None:
    """Log business events with structured data."""
    logger = logging.getLogger("dotmac_isp.business")

    logger.info(
        f"Business event: {event_type}",
        extra={
            "event_type": event_type,
            "event_data": event_data,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "category": "business_event",
        },
    )
