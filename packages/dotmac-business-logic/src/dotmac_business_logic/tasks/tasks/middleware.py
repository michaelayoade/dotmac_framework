"""
HTTP middleware for idempotency enforcement and background operations.

This module provides FastAPI middleware that automatically handles
idempotency keys and integrates with the BackgroundOperationsManager
to prevent duplicate operations.
"""

import logging
from typing import Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .manager import BackgroundOperationsManager
from .models import OperationStatus

logger = logging.getLogger(__name__)


class BackgroundOperationsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for handling idempotency and background operations.

    This middleware:
    - Processes Idempotency-Key headers
    - Returns cached results for completed operations
    - Returns 202 status for in-progress operations
    - Sets up request state for handlers to complete operations
    """

    def __init__(
        self,
        app: FastAPI,
        manager: BackgroundOperationsManager,
        exempt_paths: Optional[set[str]] = None,
        idempotency_header: str = "Idempotency-Key",
        cache_hit_header: str = "X-Cache-Hit",
        idempotency_response_header: str = "X-Idempotency-Key",
    ) -> None:
        """
        Initialize the middleware.

        Args:
            app: FastAPI application
            manager: BackgroundOperationsManager instance
            exempt_paths: Paths to exempt from idempotency processing
            idempotency_header: Name of the idempotency header
            cache_hit_header: Name of the cache hit response header
            idempotency_response_header: Name of the idempotency response header
        """
        super().__init__(app)
        self.manager = manager
        self.idempotency_header = idempotency_header
        self.cache_hit_header = cache_hit_header
        self.idempotency_response_header = idempotency_response_header

        # Default exempt paths
        if exempt_paths is None:
            exempt_paths = {
                "/docs",
                "/redoc",
                "/openapi.json",
                "/health",
                "/metrics",
                "/favicon.ico",
            }
        self.exempt_paths = exempt_paths

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and handle idempotency."""
        # Skip processing for exempt paths
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # Only process if idempotency key is present
        idempotency_key = request.headers.get(self.idempotency_header)
        if not idempotency_key:
            return await call_next(request)

        logger.debug(f"Processing idempotency key: {idempotency_key}")

        try:
            # Check if operation already exists
            existing_key = await self.manager.check_idempotency(idempotency_key)

            if existing_key:
                return await self._handle_existing_operation(existing_key, request)
            else:
                return await self._handle_new_operation(
                    idempotency_key, request, call_next
                )

        except Exception as e:
            logger.error(f"Error processing idempotency key {idempotency_key}: {e}")
            # Fall back to normal processing
            return await call_next(request)

    async def _handle_existing_operation(
        self, idempotency_key_obj, request: Request
    ) -> Response:
        """Handle request for existing operation."""
        status = idempotency_key_obj.status

        if status == OperationStatus.COMPLETED:
            # Return cached result
            logger.debug(f"Returning cached result for {idempotency_key_obj.key}")

            response_data = idempotency_key_obj.result or {"status": "completed"}
            response = JSONResponse(content=response_data, status_code=200)
            response.headers[self.cache_hit_header] = "true"
            response.headers[self.idempotency_response_header] = idempotency_key_obj.key
            return response

        elif status == OperationStatus.FAILED:
            # Return error result
            logger.debug(f"Returning error result for {idempotency_key_obj.key}")

            response_data = {
                "status": "failed",
                "error": idempotency_key_obj.error or "Operation failed",
            }
            response = JSONResponse(
                content=response_data,
                status_code=400,  # Or appropriate error status
            )
            response.headers[self.cache_hit_header] = "true"
            response.headers[self.idempotency_response_header] = idempotency_key_obj.key
            return response

        elif status in [OperationStatus.PENDING, OperationStatus.IN_PROGRESS]:
            # Return 202 Accepted for in-progress operation
            logger.debug(f"Operation {idempotency_key_obj.key} is {status}")

            response_data = {
                "status": status.value,
                "message": "Operation is being processed",
            }
            response = JSONResponse(content=response_data, status_code=202)
            response.headers[self.idempotency_response_header] = idempotency_key_obj.key
            return response

        else:
            # Unknown status - treat as new operation
            logger.warning(f"Unknown status {status} for {idempotency_key_obj.key}")
            return await self._process_as_new_operation(
                idempotency_key_obj.key, request
            )

    async def _handle_new_operation(
        self, idempotency_key: str, request: Request, call_next
    ) -> Response:
        """Handle request for new operation."""
        # Set idempotency key in request state for handlers
        request.state.idempotency_key = idempotency_key
        request.state.operation_result = None

        # Mark operation as in progress
        await self._mark_operation_in_progress(idempotency_key, request)

        # Process the request
        response = await call_next(request)

        # Check if handler set a result
        if (
            hasattr(request.state, "operation_result")
            and request.state.operation_result
        ):
            # Complete the idempotent operation
            await self.manager.complete_idempotent_operation(
                idempotency_key, request.state.operation_result
            )
            logger.debug(f"Completed idempotent operation: {idempotency_key}")

        # Add idempotency key to response headers
        response.headers[self.idempotency_response_header] = idempotency_key

        return response

    async def _process_as_new_operation(
        self, idempotency_key: str, request: Request
    ) -> Response:
        """Process request as new operation when existing key has unknown status."""
        # This should ideally not happen, but handle it gracefully
        request.state.idempotency_key = idempotency_key
        request.state.operation_result = None

        # Return a generic response
        response_data = {
            "status": "processing",
            "message": "Operation is being processed",
        }
        response = JSONResponse(content=response_data, status_code=202)
        response.headers[self.idempotency_response_header] = idempotency_key

        return response

    async def _mark_operation_in_progress(
        self, idempotency_key: str, request: Request
    ) -> None:
        """Mark operation as in progress."""
        try:
            # Try to extract tenant and user info from request
            # This is application-specific - you might need to customize this
            tenant_id = self._extract_tenant_id(request)
            user_id = self._extract_user_id(request)
            operation_type = f"{request.method}_{request.url.path}"

            # Create idempotency key if it doesn't exist
            existing_key = await self.manager.check_idempotency(idempotency_key)
            if not existing_key:
                await self.manager.create_idempotency_key(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    operation_type=operation_type,
                    key=idempotency_key,
                )

            # Update status to in progress
            current_data = await self.manager.storage.get_idempotency(idempotency_key)
            if current_data:
                current_data["status"] = OperationStatus.IN_PROGRESS.value

                # Calculate remaining TTL
                from datetime import datetime

                expires_at = datetime.fromisoformat(current_data["expires_at"])
                now = datetime.now(expires_at.tzinfo)
                remaining_ttl = int((expires_at - now).total_seconds())

                if remaining_ttl > 0:
                    await self.manager.storage.set_idempotency(
                        idempotency_key, current_data, remaining_ttl
                    )

        except Exception as e:
            logger.warning(f"Could not mark operation as in progress: {e}")

    def _extract_tenant_id(self, request: Request) -> str:
        """
        Extract tenant ID from request.

        This is application-specific. Override this method or customize
        based on how your application identifies tenants.
        """
        # Try common sources for tenant ID

        # From headers
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # From auth context (if available)
        if hasattr(request.state, "tenant_id"):
            return request.state.tenant_id

        # From path parameters
        if hasattr(request, "path_params"):
            tenant_id = request.path_params.get("tenant_id")
            if tenant_id:
                return tenant_id

        # Default fallback
        return "default"

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request.

        This is application-specific. Override this method or customize
        based on how your application identifies users.
        """
        # Try common sources for user ID

        # From headers
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id

        # From auth context (if available)
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # From JWT or other auth mechanisms
        if hasattr(request.state, "user"):
            user = request.state.user
            if hasattr(user, "id"):
                return str(user.id)
            elif isinstance(user, dict):
                return user.get("id") or user.get("sub")

        # From path parameters
        if hasattr(request, "path_params"):
            user_id = request.path_params.get("user_id")
            if user_id:
                return user_id

        return None

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from idempotency processing."""
        # Exact match
        if path in self.exempt_paths:
            return True

        # Pattern matching for common API paths
        exempt_patterns = [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi",
        ]

        for pattern in exempt_patterns:
            if path.startswith(pattern):
                return True

        return False


def add_background_operations_middleware(
    app: FastAPI,
    manager: Optional[BackgroundOperationsManager] = None,
    **middleware_kwargs,
) -> BackgroundOperationsManager:
    """
    Add background operations middleware to FastAPI app.

    Args:
        app: FastAPI application
        manager: BackgroundOperationsManager instance (created if None)
        **middleware_kwargs: Additional middleware configuration

    Returns:
        BackgroundOperationsManager instance
    """
    if manager is None:
        manager = BackgroundOperationsManager()

    # Add middleware
    app.add_middleware(
        BackgroundOperationsMiddleware, manager=manager, **middleware_kwargs
    )

    logger.info("Added BackgroundOperationsMiddleware to FastAPI app")
    return manager


# Helper functions for handlers


def set_operation_result(request: Request, result: dict) -> None:
    """
    Set the result for an idempotent operation.

    Call this from your route handlers to set the result that will
    be cached and returned for subsequent requests with the same
    idempotency key.

    Args:
        request: FastAPI request object
        result: Operation result to cache
    """
    if hasattr(request.state, "idempotency_key"):
        request.state.operation_result = result


def get_idempotency_key(request: Request) -> Optional[str]:
    """
    Get the idempotency key from request state.

    Args:
        request: FastAPI request object

    Returns:
        Idempotency key if present, None otherwise
    """
    return getattr(request.state, "idempotency_key", None)


def is_idempotent_request(request: Request) -> bool:
    """
    Check if request is idempotent (has idempotency key).

    Args:
        request: FastAPI request object

    Returns:
        True if request has idempotency key, False otherwise
    """
    return (
        hasattr(request.state, "idempotency_key")
        and request.state.idempotency_key is not None
    )
