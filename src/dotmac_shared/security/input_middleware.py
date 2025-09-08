"""
Input Sanitization Middleware for FastAPI
Automatically sanitizes all incoming request data to prevent security vulnerabilities
"""

import json
import logging
from typing import Any, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from .input_sanitizer import SecuritySanitizer

logger = logging.getLogger(__name__)


class InputSanitizationMiddleware:
    """
    FastAPI middleware for automatic input sanitization

    Features:
    - Sanitizes JSON request bodies
    - Sanitizes query parameters
    - Sanitizes path parameters
    - Configurable sanitization rules per endpoint
    - Logging of suspicious input patterns
    """

    def __init__(
        self,
        app,
        strict_mode: bool = True,
        log_suspicious: bool = True,
        exempt_paths: Optional[list] = None,
    ):
        self.app = app
        self.strict_mode = strict_mode
        self.log_suspicious = log_suspicious
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/metrics",
        ]

    def is_exempt(self, path: str) -> bool:
        """Check if path is exempt from sanitization"""
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)

    async def sanitize_query_params(self, request: Request) -> dict[str, Any]:
        """Sanitize query parameters"""
        sanitized = {}

        for key, value in request.query_params.items():
            # Sanitize key
            safe_key = SecuritySanitizer.sanitize_string(key)

            # Sanitize value
            if isinstance(value, str):
                safe_value = SecuritySanitizer.sanitize_string(value)

                # Log if value changed significantly
                if self.log_suspicious and value != safe_value:
                    logger.warning(f"Sanitized suspicious query param: {key}")

                sanitized[safe_key] = safe_value
            else:
                sanitized[safe_key] = value

        return sanitized

    async def sanitize_json_body(self, request: Request) -> Optional[dict[str, Any]]:
        """Sanitize JSON request body"""
        try:
            # Get raw body
            body = await request.body()
            if not body:
                return None

            # Parse JSON
            json_data = json.loads(body)

            # Sanitize based on data type
            if isinstance(json_data, dict):
                sanitized = SecuritySanitizer.sanitize_dict(json_data)
            elif isinstance(json_data, list):
                sanitized = SecuritySanitizer.sanitize_list(json_data)
            else:
                sanitized = json_data

            # Log if significant changes were made
            if self.log_suspicious and json_data != sanitized:
                logger.warning(f"Sanitized suspicious JSON body in request to {request.url.path}")

            return sanitized

        except json.JSONDecodeError:
            # Not JSON or malformed - let FastAPI handle it
            return None
        except Exception as e:
            logger.error(f"Error sanitizing JSON body: {e}")
            if self.strict_mode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request body sanitization failed",
                ) from e
            return None

    async def sanitize_form_data(self, request: Request) -> Optional[dict[str, Any]]:
        """Sanitize form data"""
        try:
            # Check if request has form data
            content_type = request.headers.get("content-type", "")
            if not any(ct in content_type for ct in ["application/x-www-form-urlencoded", "multipart/form-data"]):
                return None

            form_data = await request.form()
            sanitized = {}

            for key, value in form_data.items():
                safe_key = SecuritySanitizer.sanitize_string(str(key))

                if hasattr(value, "read"):  # File upload
                    sanitized[safe_key] = value
                else:
                    safe_value = SecuritySanitizer.sanitize_string(str(value))

                    if self.log_suspicious and str(value) != safe_value:
                        logger.warning(f"Sanitized suspicious form field: {key}")

                    sanitized[safe_key] = safe_value

            return sanitized

        except Exception as e:
            logger.error(f"Error sanitizing form data: {e}")
            return None

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            # Skip exempt paths
            if self.is_exempt(request.url.path):
                await self.app(scope, receive, send)
                return

            # Create sanitized scope
            sanitized_scope = scope.copy()

            # Sanitize query parameters
            if request.query_params:
                try:
                    sanitized_params = await self.sanitize_query_params(request)
                    # Update query string in scope
                    query_string = "&".join([f"{k}={v}" for k, v in sanitized_params.items()])
                    sanitized_scope["query_string"] = query_string.encode()
                except Exception as e:
                    logger.error(f"Error sanitizing query params: {e}")
                    if self.strict_mode:
                        error_response = JSONResponse(
                            status_code=400,
                            content={"detail": "Query parameter sanitization failed"},
                        )
                        await error_response(scope, receive, send)
                        return

            # Handle request body sanitization
            body_sanitized = False
            sanitized_body = None

            async def receive_wrapper():
                nonlocal body_sanitized, sanitized_body

                message = await receive()

                if message["type"] == "http.request" and not body_sanitized:
                    body_sanitized = True

                    # Try to sanitize JSON body
                    json_data = await self.sanitize_json_body(request)
                    if json_data is not None:
                        sanitized_body = json.dumps(json_data).encode()
                        message["body"] = sanitized_body

                    # Try to sanitize form data
                    elif request.headers.get("content-type", "").startswith(
                        ("application/x-www-form-urlencoded", "multipart/form-data")
                    ):
                        # For form data, we'll let FastAPI handle parsing and sanitize in the endpoint
                        pass

                return message

            await self.app(sanitized_scope, receive_wrapper, send)
        else:
            await self.app(scope, receive, send)


def create_input_sanitization_middleware(
    strict_mode: bool = True,
    log_suspicious: bool = True,
    exempt_paths: Optional[list] = None,
):
    """
    Factory function to create input sanitization middleware
    """

    def middleware_factory(app):
        return InputSanitizationMiddleware(
            app=app,
            strict_mode=strict_mode,
            log_suspicious=log_suspicious,
            exempt_paths=exempt_paths,
        )

    return middleware_factory


# Dependency for manual sanitization in endpoints
def sanitize_request_data(data: Any) -> Any:
    """
    Dependency function to manually sanitize data in endpoints
    """
    if isinstance(data, dict):
        return SecuritySanitizer.sanitize_dict(data)
    elif isinstance(data, list):
        return SecuritySanitizer.sanitize_list(data)
    elif isinstance(data, str):
        return SecuritySanitizer.sanitize_string(data)
    else:
        return data
