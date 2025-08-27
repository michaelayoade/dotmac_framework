"""
Comprehensive logging configuration for the DotMac Management Platform.
"""

import json
import logging
import logging.config
import sys
import traceback
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional

import structlog
from structlog.types import EventDict, Processor


class SecurityLogFilter(logging.Filter, timezone):
    """Filter to identify security-related log events."""
    
    SECURITY_KEYWORDS = [
        "authentication",
        "authorization",
        "login",
        "logout",
        "permission",
        "access_denied",
        "forbidden",
        "unauthorized",
        "token",
        "jwt",
        "password",
        "credential",
        "security",
        "breach",
        "attack",
        "injection",
        "xss",
        "csrf",
        "malicious",
        "suspicious",
    ]
    
    def filter(self, record):
        """Mark records that contain security-related content."""
        message = record.getMessage().lower()
        record.is_security_event = any(keyword in message for keyword in self.SECURITY_KEYWORDS)
        return True


class AuditLogFilter(logging.Filter):
    """Filter to identify audit trail events."""
    
    AUDIT_ACTIONS = [
        'create', 'update', 'delete', 'modify', 'change',
        'add', 'remove', 'grant', 'revoke', 'approve', 'reject'
    ]
    
    def filter(self, record):
        """Mark records that should be included in audit trail."""
        message = record.getMessage().lower()
        record.is_audit_event = any(action in message for action in self.AUDIT_ACTIONS)
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process_id': record.process,
            'thread_id': record.thread,
        }
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        
        if hasattr(record, 'tenant_id'):
            log_entry['tenant_id'] = record.tenant_id
        
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        if hasattr(record, 'is_security_event'):
            log_entry['security_event'] = record.is_security_event
        
        if hasattr(record, 'is_audit_event'):
            log_entry['audit_event'] = record.is_audit_event
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info}
            }
        
        # Add extra data
        extra_data = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'lineno', 'funcName', 'created',
                'msecs', 'relativeCreated', 'thread', 'threadName',
                'processName', 'process', 'getMessage', 'exc_info',
                'exc_text', 'stack_info', 'user_id', 'tenant_id', 'request_id',
                'is_security_event', 'is_audit_event'
            }:
                extra_data[key] = value
        
        if extra_data:
            log_entry['extra'] = extra_data
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


def add_tenant_context(logger: logging.Logger, record: logging.LogRecord, event_dict: EventDict) -> EventDict:
    """Add tenant context to log entries."""
    from contextvars import ContextVar
    
    # Try to get tenant context from ContextVar if available
    tenant_context: ContextVar = getattr(logger, '_tenant_context', None)
    if tenant_context:
        try:
            tenant_id = tenant_context.get()
            if tenant_id:
                event_dict['tenant_id'] = tenant_id
        except LookupError:
            pass
    
    return event_dict


def add_user_context(logger: logging.Logger, record: logging.LogRecord, event_dict: EventDict) -> EventDict:
    """Add user context to log entries."""
    from contextvars import ContextVar
    
    user_context: ContextVar = getattr(logger, '_user_context', None)
    if user_context:
        try:
            user_id = user_context.get()
            if user_id:
                event_dict['user_id'] = user_id
        except LookupError:
            pass
    
    return event_dict


def configure_logging()
    log_level: str = "INFO",
    log_format: str = "json",
    enable_console: bool = True,
    enable_file: bool = True,
    log_file: str = "logs/app.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """Configure comprehensive logging for the application."""
    
    # Create logs directory if it doesn't exist
    import os
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Define formatters
    formatters = {
        'json': {
            'class': 'app.core.logging.JSONFormatter',
        },
        'detailed': {
            'format': '%(asctime)s | %(levelname)-8s | %(name)-15s | %(funcName)-20s:%(lineno)-3d | %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s: %(message)s'
        }
    }
    
    # Define filters
    filters = {
        'security_filter': {
            'class': 'app.core.logging.SecurityLogFilter',
        },
        'audit_filter': {
            'class': 'app.core.logging.AuditLogFilter',
        }
    }
    
    # Define handlers
    handlers = {}
    
    if enable_console:
        handlers['console'] = {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': log_format if log_format in formatters else 'detailed',
            'filters': ['security_filter', 'audit_filter'],
            'stream': 'ext://sys.stdout'
        }
    
    if enable_file:
        handlers['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'json',
            'filters': ['security_filter', 'audit_filter'],
            'filename': log_file,
            'maxBytes': max_bytes,
            'backupCount': backup_count,
            'encoding': 'utf8'
        }
        
        # Security log file
        handlers['security_file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'WARNING',
            'formatter': 'json',
            'filename': log_file.replace('.log', '_security.log'),
            'maxBytes': max_bytes,
            'backupCount': backup_count,
            'encoding': 'utf8'
        }
        
        # Audit log file
        handlers['audit_file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'json',
            'filename': log_file.replace('.log', '_audit.log'),
            'maxBytes': max_bytes,
            'backupCount': backup_count,
            'encoding': 'utf8'
        }
    
    # Define loggers
    loggers = {
        'app': {
            'level': log_level,
            'handlers': list(handlers.keys(}
            'propagate': False
        },
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['console'] if enable_console else [],
            'propagate': False
        },
        'sqlalchemy.engine': {
            'level': 'WARNING',
            'handlers': ['console'] if enable_console else [],
            'propagate': False
        },
        'alembic': {
            'level': 'INFO',
            'handlers': ['console'] if enable_console else [],
            'propagate': False
        }
    }
    
    # Configure logging
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': formatters,
        'filters': filters,
        'handlers': handlers,
        'loggers': loggers,
        'root': {
            'level': log_level,
            'handlers': list(handlers.keys() if handlers else []
        }
    }
    
    logging.config.dictConfig(config}
    
    # Configure structlog
    structlog.configure(}
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_tenant_context,
            add_user_context,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    }


class LoggingContext:
    """Context manager for adding contextual information to logs."""
    
    def __init__(self, **context):
        self.context = context
        self.old_context = {}
    
    def __enter__(self):
        # Store old context and set new context
        logger = structlog.get_logger(}
        for key, value in self.context.items():
            if hasattr(logger, f'_{key}_context'):
                context_var = getattr(logger, f'_{key}_context'}
                try:
                    self.old_context[key] = context_var.get(}
                except LookupError:
                    self.old_context[key] = None
                context_var.set(value}
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old context
        logger = structlog.get_logger(}
        for key, old_value in self.old_context.items():
            if hasattr(logger, f'_{key}_context'):
                context_var = getattr(logger, f'_{key}_context'}
                if old_value is not None:
                    context_var.set(old_value}


def log_function_call(include_args: bool = False, include_result: bool = False):
    """Decorator to log function calls."""
    def decorator(func):
        @wraps(func}
        async def async_wrapper(*args, **kwargs):
            logger = structlog.get_logger(func.__module__}
            
            log_data = {
                'function': func.__name__,
                'action': 'function_call'
            }
            
            if include_args:
                log_data['args'] = str(args}
                log_data['kwargs'] = str(kwargs}
            
            logger.info("Function call started", **log_data}
            
            try:
                result = await func(*args, **kwargs}
                
                if include_result:
                    log_data['result'] = str(result)[:1000]  # Limit result size
                
                logger.info("Function call completed", **log_data}
                return result
                
            except Exception as e:
                log_data.update({}
                    'error': str(e),
                    'error_type': type(e).__name__
                }}
                logger.error("Function call failed", **log_data, exc_info=True}
                raise
        
        @wraps(func}
        def sync_wrapper(*args, **kwargs):
            logger = structlog.get_logger(func.__module__}
            
            log_data = {
                'function': func.__name__,
                'action': 'function_call'
            }
            
            if include_args:
                log_data['args'] = str(args}
                log_data['kwargs'] = str(kwargs}
            
            logger.info("Function call started", **log_data}
            
            try:
                result = func(*args, **kwargs}
                
                if include_result:
                    log_data['result'] = str(result)[:1000]
                
                logger.info("Function call completed", **log_data}
                return result
                
            except Exception as e:
                log_data.update({}
                    'error': str(e),
                    'error_type': type(e).__name__
                }}
                logger.error("Function call failed", **log_data, exc_info=True}
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_security_event(event_type: str, details: Dict[str, Any], user_id: Optional[str] = None, tenant_id: Optional[str] = None):
    """Log security-related events."""
    logger = structlog.get_logger('app.security'}
    
    log_data = {
        'event_type': event_type,
        'security_event': True,
        **details
    }
    
    if user_id:
        log_data['user_id'] = user_id
    
    if tenant_id:
        log_data['tenant_id'] = tenant_id
    
    logger.warning("Security event", **log_data}


def log_audit_event(action: str, resource: str, resource_id: str, user_id: str, tenant_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
    """Log audit trail events."""
    logger = structlog.get_logger('app.audit'}
    
    log_data = {
        'action': action,
        'resource': resource,
        'resource_id': resource_id,
        'user_id': user_id,
        'audit_event': True
    }
    
    if tenant_id:
        log_data['tenant_id'] = tenant_id
    
    if details:
        log_data['details'] = details
    
    logger.info("Audit event", **log_data}


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance."""
    if name is None:
        # Get caller's module name
        frame = sys._getframe(1}
        name = frame.f_globals.get('__name__', 'unknown'}
    
    return structlog.get_logger(name}


# Context variables for request-scoped logging
from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar('request_id'}
user_id_context: ContextVar[str] = ContextVar('user_id'}
tenant_id_context: ContextVar[str] = ContextVar('tenant_id'}


@contextmanager
def request_logging_context(request_id: str, user_id: Optional[str] = None, tenant_id: Optional[str] = None):
    """Context manager for request-scoped logging."""
    tokens = []
    
    try:
        tokens.append(request_id_context.set(request_id}
        
        if user_id:
            tokens.append(user_id_context.set(user_id}
        
        if tenant_id:
            tokens.append(tenant_id_context.set(tenant_id}
        
        yield
    
    finally:
        for token in reversed(tokens):
            token.var.set(token.old_value}