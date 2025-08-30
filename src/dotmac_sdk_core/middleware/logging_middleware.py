"""Logging middleware for HTTP requests."""

import logging
import time
from typing import Any, Dict

from .base import HTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(HTTPMiddleware):
    """HTTP request/response logging middleware."""

    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log outgoing request."""
        method = request_data.get("method", "UNKNOWN")
        url = request_data.get("url", "unknown")

        logger.log(self.log_level, f"HTTP {method} {url}")

        request_data["_request_start_time"] = time.time()
        return request_data

    async def process_response(self, response: "HTTPResponse") -> "HTTPResponse":
        """Log incoming response."""
        duration = response.request_time or 0.0

        logger.log(
            self.log_level,
            f"HTTP {response.status_code} {response.url} ({duration:.3f}s)",
        )

        return response
