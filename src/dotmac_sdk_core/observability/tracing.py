"""Tracing components for HTTP client."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotmac_shared.api.exception_handlers import standard_exception_handler

logger = logging.getLogger(__name__)


@dataclass
class SpanAttributes:
    """HTTP span attributes."""

    method: str
    url: str
    status_code: Optional[int] = None
    user_agent: Optional[str] = None
    tenant_id: Optional[str] = None


def trace_http_request(func):
    """Decorator for tracing HTTP requests."""

    def wrapper(*args, **kwargs):
        # Basic tracing placeholder - would integrate with OpenTelemetry
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"HTTP request completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"HTTP request failed after {duration:.3f}s: {e}")
            raise

    return wrapper


class TraceableHTTPClient:
    """HTTP client with tracing capabilities."""

    def __init__(self, base_client, tracer=None):
        self.base_client = base_client
        self.tracer = tracer

    async def request(self, *args, **kwargs):
        """Make traced HTTP request."""
        return await self.base_client.request(*args, **kwargs)
