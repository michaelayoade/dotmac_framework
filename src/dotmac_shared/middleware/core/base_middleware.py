"""
Base middleware class for DotMac applications.
"""

from abc import ABC, abstractmethod
from typing import Any

from fastapi import Request, Response


class BaseMiddleware(ABC):
    """Base class for all DotMac middleware components."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize middleware with optional configuration."""
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

    @abstractmethod
    async def process_request(self, request: Request) -> Request | None:
        """Process incoming request. Return None to short-circuit."""
        pass

    @abstractmethod
    async def process_response(self, request: Request, response: Response) -> Response:
        """Process outgoing response."""
        pass

    def is_enabled(self) -> bool:
        """Check if middleware is enabled."""
        return self.enabled

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
