"""
Enhanced logging with OpenTelemetry trace correlation for SigNoz.
Maintains existing structured logging while adding trace context.
"""

import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from opentelemetry import trace, baggage
from opentelemetry.trace.span import INVALID_SPAN


class OTelTraceContextFilter(logging.Filter, timezone):
    """Inject OpenTelemetry trace context into log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace_id, span_id, and baggage to log record."""
        span = trace.get_current_span()
        
        if span is not None and span.get_span_context().is_valid:
            span_context = span.get_span_context()
            record.trace_id = format(span_context.trace_id, "032x")
            record.span_id = format(span_context.span_id, "016x")
            
            # Add trace flags
            record.trace_flags = span_context.trace_flags
        else:
            record.trace_id = ""
            record.span_id = ""
            record.trace_flags = ""
        
        # Add baggage context (tenant_id, request_id, etc.)
        current_baggage = baggage.get_all()
        for key, value in current_baggage.items():
            if key in ["tenant.id", "request.id", "user.id"]:
                setattr(record, key.replace(".", "_"), value)
        
        # Set defaults if not present
        if not hasattr(record, "tenant_id"):
            record.tenant_id = ""
        if not hasattr(record, "request_id"):
            record.request_id = ""
        if not hasattr(record, "user_id"):
            record.user_id = ""
            
        return True


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter that maintains DotMac's structured logging format
    while adding OpenTelemetry correlation fields.
    """
    
    def __init__(self, include_trace: bool = True):
        super().__init__()
        self.include_trace = include_trace
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log structure
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add trace context if available and enabled
        if self.include_trace:
            if hasattr(record, "trace_id") and record.trace_id:
                log_entry["trace_id"] = record.trace_id
                log_entry["span_id"] = record.span_id
            
            # Add baggage context
            if hasattr(record, "tenant_id") and record.tenant_id:
                log_entry["tenant_id"] = record.tenant_id
            if hasattr(record, "request_id") and record.request_id:
                log_entry["request_id"] = record.request_id
            if hasattr(record, "user_id") and record.user_id:
                log_entry["user_id"] = record.user_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add any extra fields from the log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname", 
                "filename", "module", "lineno", "funcName", "created", 
                "msecs", "relativeCreated", "thread", "threadName", 
                "processName", "process", "getMessage", "exc_info", 
                "exc_text", "stack_info", "trace_id", "span_id", 
                "tenant_id", "request_id", "user_id", "trace_flags"
            } and not key.startswith("_"):
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str)


class DotMacLogger:
    """
    Enhanced logger for DotMac with OpenTelemetry integration.
    Provides structured logging with trace correlation.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def _add_span_event(self, level: str, message: str, **kwargs):
        """Add log event to current span."""
        span = trace.get_current_span()
        if span.is_recording():
            attributes = {
                "log.severity": level,
                "log.message": message,
            }
            # Add any additional context
            for key, value in kwargs.items():
                if isinstance(value, (str, int, float, bool)):
                    attributes[f"log.{key}"] = value
            
            span.add_event("log", attributes)
    
    def info(self, message: str, **kwargs):
        """Log info message with trace correlation."""
        self._add_span_event("INFO", message, **kwargs)
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with trace correlation."""
        self._add_span_event("WARNING", message, **kwargs)
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with trace correlation."""
        self._add_span_event("ERROR", message, **kwargs)
        
        # Mark span as error
        span = trace.get_current_span()
        if span.is_recording():
            span.set_status(trace.Status(trace.StatusCode.ERROR, message))
        
        self.logger.error(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with trace correlation."""
        self._add_span_event("DEBUG", message, **kwargs)
        self.logger.debug(message, extra=kwargs)


def setup_logging(
    log_level: str = "INFO",
    enable_trace_correlation: bool = True,
    use_json_format: bool = True
):
    """
    Setup enhanced logging with OpenTelemetry trace correlation.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_trace_correlation: Whether to include trace context
        use_json_format: Whether to use structured JSON format
    """
    # Remove existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    if use_json_format:
        # Use structured JSON formatter
        formatter = StructuredFormatter(include_trace=enable_trace_correlation)
    else:
        # Use simple text format with trace context
        if enable_trace_correlation:
            format_string = (
                "%(asctime)s %(levelname)s %(name)s "
                "trace_id=%(trace_id)s span_id=%(span_id)s "
                "tenant_id=%(tenant_id)s %(message)s"
            )
        else:
            format_string = "%(asctime)s %(levelname)s %(name)s %(message)s"
        
        formatter = logging.Formatter(format_string)
    
    console_handler.setFormatter(formatter)
    
    # Add trace context filter if enabled
    if enable_trace_correlation:
        console_handler.addFilter(OTelTraceContextFilter())
    
    # Configure root logger
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    
    # Configure third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    # Create DotMac framework logger
    framework_logger = logging.getLogger("dotmac")
    framework_logger.info(
        "Logging setup complete",
        log_level=log_level,
        trace_correlation=enable_trace_correlation,
        json_format=use_json_format
    )


def get_logger(name: str) -> DotMacLogger:
    """Get enhanced DotMac logger instance."""
    return DotMacLogger(name)


# Pre-configured loggers for common components
audit_logger = get_logger("dotmac.audit")
security_logger = get_logger("dotmac.security")
performance_logger = get_logger("dotmac.performance")
business_logger = get_logger("dotmac.business")