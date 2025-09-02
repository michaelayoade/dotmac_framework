"""
Enhanced database observability with OpenTelemetry integration.
Provides query monitoring, N+1 detection, and performance metrics.
"""

import time
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.orm import Session
from sqlalchemy.sql import ClauseElement
from opentelemetry import trace, metrics

from .otel import db_operation_duration, get_tracer, get_meter
from .logging import get_logger

logger = get_logger("dotmac.database")

# Database metrics
db_meter = get_meter("dotmac-database")

query_counter = db_meter.create_counter(
    "db.queries.total",
    description="Total database queries executed"
)

connection_pool_usage = db_meter.create_histogram(
    "db.connection_pool.usage",
    description="Connection pool usage metrics"
)

slow_query_counter = db_meter.create_counter(
    "db.slow_queries.total",
    description="Total slow database queries"
)

n_plus_one_detector = db_meter.create_counter(
    "db.n_plus_one.detected",
    description="Detected N+1 query patterns"
)


class QueryMonitor:
    """Monitor database queries for performance and N+1 patterns."""
    
    def __init__(self, slow_query_threshold: float = 100.0):
        self.slow_query_threshold = slow_query_threshold  # milliseconds
        self.active_spans: Dict[str, Any] = {}
        self.query_count_per_request: Dict[str, int] = {}
        self.similar_queries: Dict[str, List[str]] = {}
    
    def start_query_span(self, operation: str, statement: str, parameters: Any = None) -> str:
        """Start a span for database query."""
        tracer = get_tracer("dotmac-database")
        
        span = tracer.start_span(
            name=f"db.{operation}",
            attributes={
                "db.system": "postgresql",
                "db.operation": operation,
                "db.statement": self._sanitize_query(statement),
            }
        )
        
        span_id = id(span)
        self.active_spans[span_id] = {
            "span": span,
            "start_time": time.perf_counter(),
            "statement": statement,
            "operation": operation
        }
        
        return span_id
    
    def end_query_span(self, span_id: str, rows_affected: int = 0, error: Exception = None):
        """End database query span with metrics."""
        if span_id not in self.active_spans:
            return
        
        span_data = self.active_spans.pop(span_id)
        span = span_data["span"]
        duration_ms = (time.perf_counter() - span_data["start_time"]) * 1000
        
        try:
            # Set span attributes
            span.set_attribute("db.rows_affected", rows_affected)
            span.set_attribute("db.duration_ms", duration_ms)
            
            if error:
                span.record_exception(error)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(error)))
            
            # Record metrics
            labels = {
                "operation": span_data["operation"],
                "status": "error" if error else "success"
            }
            
            query_counter.add(1, labels)
            db_operation_duration.record(duration_ms, labels)
            
            # Check for slow queries
            if duration_ms > self.slow_query_threshold:
                slow_query_counter.add(1, labels)
                logger.warning(
                    "Slow query detected",
                    duration_ms=duration_ms,
                    operation=span_data["operation"],
                    statement=self._sanitize_query(span_data["statement"])
                )
            
            # Check for potential N+1 patterns
            self._check_n_plus_one_pattern(span_data["statement"], span_data["operation"])
            
        finally:
            span.end()
    
    def _sanitize_query(self, statement: str) -> str:
        """Sanitize SQL statement for logging."""
        if isinstance(statement, ClauseElement):
            statement = str(statement.compile(compile_kwargs={"literal_binds": True}))
        
        # Truncate very long queries
        if len(statement) > 500:
            statement = statement[:500] + "..."
        
        return statement
    
    def _check_n_plus_one_pattern(self, statement: str, operation: str):
        """Simple N+1 query pattern detection."""
        if operation != "SELECT":
            return
        
        # Get current request context (simplified)
        request_id = "current"  # In real implementation, get from context
        
        # Count similar queries in current request
        if request_id not in self.similar_queries:
            self.similar_queries[request_id] = []
        
        # Normalize query for comparison
        normalized = self._normalize_query_for_comparison(statement)
        self.similar_queries[request_id].append(normalized)
        
        # Check for repeated similar queries (potential N+1)
        similar_count = self.similar_queries[request_id].count(normalized)
        if similar_count > 5:  # Threshold for N+1 detection
            n_plus_one_detector.add(1, {"pattern": normalized[:100]})
            logger.warning(
                "Potential N+1 query pattern detected",
                query_pattern=normalized,
                occurrence_count=similar_count,
                request_id=request_id
            )
    
    def _normalize_query_for_comparison(self, statement: str) -> str:
        """Normalize query for N+1 pattern detection."""
        # Remove parameter values and normalize whitespace
        import re
        normalized = re.sub(r'\$\d+|\?|:\w+', '?', str(statement))
        normalized = re.sub(r'\s+', ' ', normalized).strip().upper()
        return normalized


# Global query monitor instance
query_monitor = QueryMonitor()


def setup_database_observability(engine: AsyncEngine, enable_sql_logging: bool = False):
    """
    Setup database observability for SQLAlchemy engine.
    
    Args:
        engine: SQLAlchemy async engine
        enable_sql_logging: Whether to enable detailed SQL logging
    """
    # Get the sync engine for event listening
    sync_engine = engine.sync_engine if hasattr(engine, "sync_engine") else engine
    
    # Setup query monitoring events
    @event.listens_for(sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Track query start."""
        operation = _extract_operation_from_statement(statement)
        span_id = query_monitor.start_query_span(operation, statement, parameters)
        context._span_id = span_id
        
        if enable_sql_logging:
            logger.debug(
                "Executing query",
                operation=operation,
                statement=query_monitor._sanitize_query(statement)
            )
    
    @event.listens_for(sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Track query completion."""
        if hasattr(context, "_span_id"):
            query_monitor.end_query_span(
                context._span_id,
                rows_affected=cursor.rowcount if cursor else 0
            )
    
    @event.listens_for(sync_engine, "handle_error")
    def handle_error(exception_context):
        """Track query errors."""
        if hasattr(exception_context.statement_context, "_span_id"):
            query_monitor.end_query_span(
                exception_context.statement_context._span_id,
                error=exception_context.original_exception
            )
    
    # Setup connection pool monitoring
    @event.listens_for(sync_engine, "connect")
    def on_connect(dbapi_conn, connection_record):
        """Track connection pool usage."""
        pool = sync_engine.pool
        if hasattr(pool, "size") and hasattr(pool, "checked_in"):
            pool_usage = (pool.size() - pool.checked_in()) / pool.size() * 100
            connection_pool_usage.record(pool_usage, {"pool": "main"})
    
    logger.info("Database observability setup complete")


def _extract_operation_from_statement(statement: str) -> str:
    """Extract SQL operation type from statement."""
    statement_str = str(statement).strip().upper()
    
    if statement_str.startswith("SELECT"):
        return "SELECT"
    elif statement_str.startswith("INSERT"):
        return "INSERT"
    elif statement_str.startswith("UPDATE"):
        return "UPDATE"
    elif statement_str.startswith("DELETE"):
        return "DELETE"
    elif statement_str.startswith("CREATE"):
        return "CREATE"
    elif statement_str.startswith("DROP"):
        return "DROP"
    elif statement_str.startswith("ALTER"):
        return "ALTER"
    else:
        return "UNKNOWN"


def traced_db_operation(operation_name: str):
    """
    Decorator to trace database operations with custom metrics.
    
    Args:
        operation_name: Name of the database operation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer("dotmac-database")
            start_time = time.perf_counter()
            
            with tracer.start_as_current_span(f"db.{operation_name}") as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("db.operation.success", True)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
                finally:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    span.set_attribute("db.operation.duration_ms", duration_ms)
                    
                    # Record custom metric
                    db_operation_duration.record(
                        duration_ms,
                        {"operation": operation_name, "function": func.__name__}
                    )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer("dotmac-database")
            start_time = time.perf_counter()
            
            with tracer.start_as_current_span(f"db.{operation_name}") as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("db.operation.success", True)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
                finally:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    span.set_attribute("db.operation.duration_ms", duration_ms)
                    
                    # Record custom metric
                    db_operation_duration.record(
                        duration_ms,
                        {"operation": operation_name, "function": func.__name__}
                    )
        
        # Return appropriate wrapper based on function type
        if hasattr(func, "__code__") and "await" in func.__code__.co_names:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@asynccontextmanager
async def traced_transaction(session: AsyncSession, operation_name: str):
    """
    Context manager for traced database transactions.
    
    Args:
        session: SQLAlchemy async session
        operation_name: Name of the transaction operation
    """
    tracer = get_tracer("dotmac-database")
    start_time = time.perf_counter()
    
    with tracer.start_as_current_span(f"db.transaction.{operation_name}") as span:
        try:
            async with session.begin():
                yield session
                span.set_attribute("db.transaction.committed", True)
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.set_attribute("db.transaction.committed", False)
            raise
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute("db.transaction.duration_ms", duration_ms)
            
            # Record transaction metric
            db_operation_duration.record(
                duration_ms,
                {"operation": "transaction", "name": operation_name}
            )