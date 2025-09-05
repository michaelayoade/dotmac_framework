"""
Middleware manager for coordinating multiple middleware components.
"""

import logging

from fastapi import Request, Response

from .base_middleware import BaseMiddleware

logger = logging.getLogger(__name__)


class MiddlewareManager:
    """Manages and coordinates multiple middleware components."""

    def __init__(self):
        """Initialize middleware manager."""
        self.middleware_stack: list[BaseMiddleware] = []
        self.middleware_registry: dict[str, type[BaseMiddleware]] = {}

    def register_middleware(self, name: str, middleware_class: type[BaseMiddleware]):
        """Register a middleware class."""
        self.middleware_registry[name] = middleware_class
        logger.debug(f"Registered middleware: {name}")

    def add_middleware(self, middleware: BaseMiddleware):
        """Add middleware to the processing stack."""
        if middleware.is_enabled():
            self.middleware_stack.append(middleware)
            logger.debug(f"Added middleware: {middleware.__class__.__name__}")

    def create_and_add_middleware(self, name: str, config: dict | None = None):
        """Create and add middleware by name."""
        if name not in self.middleware_registry:
            raise ValueError(f"Unknown middleware: {name}")

        middleware_class = self.middleware_registry[name]
        middleware = middleware_class(config)
        self.add_middleware(middleware)

    async def process_request(self, request: Request) -> Request | None:
        """Process request through all middleware."""
        current_request = request

        for middleware in self.middleware_stack:
            try:
                result = await middleware.process_request(current_request)
                if result is None:
                    # Middleware short-circuited the request
                    return None
                current_request = result
            except Exception as e:
                logger.error(
                    f"Error in middleware {middleware.__class__.__name__}: {e}"
                )
                raise

        return current_request

    async def process_response(self, request: Request, response: Response) -> Response:
        """Process response through all middleware (in reverse order)."""
        current_response = response

        # Process in reverse order for response
        for middleware in reversed(self.middleware_stack):
            try:
                current_response = await middleware.process_response(
                    request, current_response
                )
            except Exception as e:
                logger.error(
                    f"Error in middleware {middleware.__class__.__name__}: {e}"
                )
                raise

        return current_response

    def get_middleware_count(self) -> int:
        """Get count of active middleware."""
        return len(self.middleware_stack)

    def list_middleware(self) -> list[str]:
        """List names of active middleware."""
        return [m.__class__.__name__ for m in self.middleware_stack]
