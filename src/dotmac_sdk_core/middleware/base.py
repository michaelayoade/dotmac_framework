"""Base HTTP middleware classes."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class HTTPMiddleware(ABC):
    """Base HTTP middleware class."""

    @abstractmethod
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process outgoing request."""
        pass

    @abstractmethod
    async def process_response(self, response: "HTTPResponse") -> "HTTPResponse":
        """Process incoming response."""
        pass


class RequestMiddleware(HTTPMiddleware):
    """Middleware that only processes requests."""

    async def process_response(self, response: "HTTPResponse") -> "HTTPResponse":
        """Default response processing - no-op."""
        return response


class ResponseMiddleware(HTTPMiddleware):
    """Middleware that only processes responses."""

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Default request processing - no-op."""
        return request_data
