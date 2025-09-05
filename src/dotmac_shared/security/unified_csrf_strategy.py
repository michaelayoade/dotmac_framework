"""
Unified CSRF Strategy for DotMac Portals

Provides consistent CSRF protection across SSR (Server-Side Rendered) and API
scenarios for all DotMac portals (Admin, Customer, Management, Reseller, Technician).

Implements double-submit cookie pattern with additional security enhancements.
"""

import hashlib
import json
import secrets as python_secrets  # Avoid conflict with dotmac secrets module
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import structlog
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class CSRFError(Exception):
    """Error raised for CSRF validation failures."""


class CSRFMode(str, Enum):
    """CSRF protection modes for different scenarios."""

    API_ONLY = "api_only"  # Pure API endpoints
    SSR_ONLY = "ssr_only"  # Server-side rendered pages only
    HYBRID = "hybrid"  # Mixed SSR + API (most common)
    DISABLED = "disabled"  # No CSRF protection (dangerous)


class CSRFTokenDelivery(str, Enum):
    """Token delivery methods."""

    HEADER_ONLY = "header_only"  # X-CSRF-Token header only
    COOKIE_ONLY = "cookie_only"  # Cookie only (double-submit pattern)
    BOTH = "both"  # Header + Cookie (most secure)
    META_TAG = "meta_tag"  # HTML meta tag for SSR


@dataclass
class CSRFConfig:
    """Comprehensive CSRF configuration."""

    # Basic settings
    mode: CSRFMode = CSRFMode.HYBRID
    token_delivery: CSRFTokenDelivery = CSRFTokenDelivery.BOTH
    secret_key: Optional[str] = None
    token_lifetime: int = 3600  # 1 hour

    # Path configuration
    excluded_paths: list[str] = None
    api_paths: list[str] = None
    ssr_paths: list[str] = None
    safe_methods: set[str] = None

    # Security settings
    require_referer_check: bool = True
    allowed_origins: list[str] = None
    cookie_secure: bool = True
    cookie_samesite: str = "Strict"
    cookie_httponly: bool = True

    # Portal-specific settings
    portal_name: str = "default"
    enable_debug_logging: bool = False

    def __post_init__(self):
        """Initialize default values."""
        if self.excluded_paths is None:
            self.excluded_paths = ["/health", "/metrics", "/docs", "/openapi.json"]

        if self.api_paths is None:
            self.api_paths = ["/api/", "/graphql"]

        if self.ssr_paths is None:
            self.ssr_paths = ["/", "/dashboard", "/admin", "/portal"]

        if self.safe_methods is None:
            self.safe_methods = {"GET", "HEAD", "OPTIONS", "TRACE"}

        if self.allowed_origins is None:
            self.allowed_origins = []


class CSRFToken:
    """CSRF token with enhanced security features."""

    def __init__(self, secret_key: str, lifetime: int = 3600):
        self.secret_key = secret_key
        self.lifetime = lifetime

    def generate(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        Generate CSRF token with optional session/user binding.

        Args:
            session_id: Session identifier for binding
            user_id: User identifier for binding

        Returns:
            Signed CSRF token
        """
        timestamp = str(int(time.time()))
        random_data = python_secrets.token_hex(16)

        # Optional binding data
        binding_data = ""
        if session_id:
            binding_data += f":session:{session_id}"
        if user_id:
            binding_data += f":user:{user_id}"

        # Create token data
        token_data = f"{timestamp}:{random_data}{binding_data}"

        # Sign with secret key
        signature = self._sign_token_data(token_data)

        return f"{token_data}:{signature}"

    def validate(self, token: str, session_id: Optional[str] = None, user_id: Optional[str] = None) -> bool:
        """
        Validate CSRF token with optional session/user binding check.

        Args:
            token: Token to validate
            session_id: Expected session identifier
            user_id: Expected user identifier

        Returns:
            True if token is valid
        """
        try:
            # Parse token parts
            parts = token.split(":")
            if len(parts) < 3:
                return False

            # Extract basic components
            timestamp_str = parts[0]
            parts[1]
            signature = parts[-1]  # Last part is always signature

            # Reconstruct token data (everything except signature)
            token_data = ":".join(parts[:-1])

            # Validate timestamp
            timestamp = int(timestamp_str)
            if time.time() - timestamp > self.lifetime:
                logger.debug("CSRF token expired")
                return False

            # Validate signature
            expected_signature = self._sign_token_data(token_data)
            if not python_secrets.compare_digest(signature, expected_signature):
                logger.debug("CSRF token signature invalid")
                return False

            # Validate bindings if provided
            if session_id and f":session:{session_id}" not in token_data:
                logger.debug("CSRF token session binding failed")
                return False

            if user_id and f":user:{user_id}" not in token_data:
                logger.debug("CSRF token user binding failed")
                return False

            return True

        except (ValueError, TypeError, IndexError) as e:
            logger.debug(f"CSRF token validation error: {e}")
            return False

    def _sign_token_data(self, token_data: str) -> str:
        """Sign token data with secret key."""
        return hashlib.sha256((token_data + self.secret_key).encode()).hexdigest()


class CSRFValidationContext:
    """Context for CSRF validation with portal-specific information."""

    def __init__(
        self, request: Request, config: CSRFConfig, session_id: Optional[str] = None, user_id: Optional[str] = None
    ):
        self.request = request
        self.config = config
        self.session_id = session_id
        self.user_id = user_id
        self.is_api_request = self._determine_api_request()
        self.is_ssr_request = self._determine_ssr_request()

    def _determine_api_request(self) -> bool:
        """Determine if request is for API endpoint."""
        path = self.request.url.path
        return any(path.startswith(api_path) for api_path in self.config.api_paths)

    def _determine_ssr_request(self) -> bool:
        """Determine if request is for SSR endpoint."""
        path = self.request.url.path
        content_type = self.request.headers.get("Content-Type", "")

        # Check path patterns
        is_ssr_path = any(path.startswith(ssr_path) for ssr_path in self.config.ssr_paths)

        # Check content type for form submissions
        is_form_submission = (
            "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type
        )

        return is_ssr_path or is_form_submission


class UnifiedCSRFMiddleware(BaseHTTPMiddleware):
    """
    Unified CSRF middleware supporting both SSR and API scenarios.

    Provides flexible CSRF protection that adapts to different portal needs
    while maintaining consistent security standards.
    """

    def __init__(self, app, config: CSRFConfig):
        super().__init__(app)
        self.config = config
        self.token_generator = CSRFToken(
            secret_key=config.secret_key or python_secrets.token_hex(32), lifetime=config.token_lifetime
        )

        # Track token usage for debugging
        self._token_stats = {"generated": 0, "validated_success": 0, "validated_failed": 0}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with unified CSRF protection."""

        # Skip CSRF protection if disabled
        if self.config.mode == CSRFMode.DISABLED:
            return await call_next(request)

        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        # Skip safe methods
        if request.method in self.config.safe_methods:
            # Generate and provide token for safe requests
            response = await call_next(request)
            await self._add_csrf_token_to_response(request, response)
            return response

        # Create validation context
        context = CSRFValidationContext(
            request=request,
            config=self.config,
            session_id=self._extract_session_id(request),
            user_id=self._extract_user_id(request),
        )

        # Validate CSRF token
        is_valid = await self._validate_csrf_protection(context)

        if not is_valid:
            self._token_stats["validated_failed"] += 1

            logger.warning(
                "CSRF validation failed",
                portal=self.config.portal_name,
                method=request.method,
                path=request.url.path,
                is_api=context.is_api_request,
                is_ssr=context.is_ssr_request,
                client_ip=request.client.host if request.client else None,
            )

            # Return appropriate error response
            return self._create_csrf_error_response(context)

        self._token_stats["validated_success"] += 1

        # Process request and add new token to response
        response = await call_next(request)
        await self._add_csrf_token_to_response(request, response, context)

        return response

    async def _validate_csrf_protection(self, context: CSRFValidationContext) -> bool:
        """Validate CSRF protection based on request type and configuration."""

        # Extract tokens from request
        header_token = context.request.headers.get("X-CSRF-Token")
        cookie_token = context.request.cookies.get("csrf_token")
        form_token = None

        # Try to get token from form data for SSR requests
        if context.is_ssr_request:
            try:
                form_data = await context.request.form()
                form_token = form_data.get("csrf_token")
            except Exception:
                pass

        # Determine which token to validate based on configuration and request type
        token_to_validate = None

        if context.is_api_request:
            # API requests prefer header tokens
            token_to_validate = header_token

            # Fallback to cookie for double-submit pattern
            if not token_to_validate and self.config.token_delivery in [
                CSRFTokenDelivery.COOKIE_ONLY,
                CSRFTokenDelivery.BOTH,
            ]:
                token_to_validate = cookie_token

        elif context.is_ssr_request:
            # SSR requests prefer form tokens
            token_to_validate = form_token or header_token

            # Double-submit cookie pattern validation
            if (
                self.config.token_delivery in [CSRFTokenDelivery.COOKIE_ONLY, CSRFTokenDelivery.BOTH]
                and cookie_token
                and token_to_validate != cookie_token
            ):
                logger.debug("Double-submit cookie CSRF validation failed")
                return False

        if not token_to_validate:
            logger.debug("No CSRF token found in request")
            return False

        # Validate the token
        is_valid = self.token_generator.validate(
            token=token_to_validate, session_id=context.session_id, user_id=context.user_id
        )

        # Additional referer check if enabled
        if is_valid and self.config.require_referer_check:
            is_valid = self._validate_referer(context.request)

        return is_valid

    async def _add_csrf_token_to_response(
        self, request: Request, response: Response, context: Optional[CSRFValidationContext] = None
    ) -> None:
        """Add CSRF token to response based on configuration."""

        # Generate new token
        session_id = self._extract_session_id(request) if context else None
        user_id = self._extract_user_id(request) if context else None

        new_token = self.token_generator.generate(session_id=session_id, user_id=user_id)

        self._token_stats["generated"] += 1

        # Add token based on delivery method
        if self.config.token_delivery in [CSRFTokenDelivery.HEADER_ONLY, CSRFTokenDelivery.BOTH]:
            response.headers["X-CSRF-Token"] = new_token

        if self.config.token_delivery in [CSRFTokenDelivery.COOKIE_ONLY, CSRFTokenDelivery.BOTH]:
            response.set_cookie(
                key="csrf_token",
                value=new_token,
                max_age=self.config.token_lifetime,
                secure=self.config.cookie_secure,
                httponly=self.config.cookie_httponly,
                samesite=self.config.cookie_samesite,
            )

        # Add meta tag for SSR responses
        if (
            self.config.token_delivery == CSRFTokenDelivery.META_TAG
            and context
            and context.is_ssr_request
            and "text/html" in response.headers.get("content-type", "")
        ):
            # This would require HTML processing - implement based on template engine
            logger.debug("Meta tag CSRF token delivery not implemented")

    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from CSRF protection."""
        return any(path.startswith(excluded) for excluded in self.config.excluded_paths)

    def _extract_session_id(self, request: Request) -> Optional[str]:
        """Extract session ID from request for token binding."""
        # Try multiple sources for session ID
        session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = request.headers.get("X-Session-ID")
        return session_id

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request for token binding."""
        # This would typically come from authentication middleware
        return getattr(request.state, "user_id", None)

    def _validate_referer(self, request: Request) -> bool:
        """Validate referer header against allowed origins."""
        referer = request.headers.get("Referer")
        if not referer:
            logger.debug("No referer header in request")
            return False

        # Check against allowed origins
        if self.config.allowed_origins:
            return any(referer.startswith(origin) for origin in self.config.allowed_origins)

        # Default: same origin check
        host = request.headers.get("Host")
        if host:
            return referer.startswith(f"https://{host}") or referer.startswith(f"http://{host}")

        return False

    def _create_csrf_error_response(self, context: CSRFValidationContext) -> Response:
        """Create appropriate error response based on request type."""

        if context.is_api_request:
            # API requests get JSON error
            return Response(
                content=json.dumps(
                    {
                        "error": "CSRF token validation failed",
                        "error_code": "CSRF_TOKEN_INVALID",
                        "portal": self.config.portal_name,
                    }
                ),
                status_code=status.HTTP_403_FORBIDDEN,
                headers={"Content-Type": "application/json"},
            )

        else:
            # SSR requests get HTML error or redirect
            # This could be customized per portal
            return Response(
                content="""
                <html>
                <head><title>Security Error</title></head>
                <body>
                <h1>Security Validation Failed</h1>
                <p>Your session has expired or the request could not be validated.</p>
                <p><a href="/">Return to Home</a></p>
                </body>
                </html>
                """,
                status_code=status.HTTP_403_FORBIDDEN,
                headers={"Content-Type": "text/html"},
            )

    def get_stats(self) -> dict[str, Any]:
        """Get CSRF middleware statistics."""
        return {
            "config": {
                "mode": self.config.mode.value,
                "portal": self.config.portal_name,
                "token_delivery": self.config.token_delivery.value,
            },
            "stats": self._token_stats.copy(),
        }


# Portal-specific CSRF configurations
def create_admin_portal_csrf_config() -> CSRFConfig:
    """Create CSRF config optimized for Admin Portal."""
    return CSRFConfig(
        mode=CSRFMode.HYBRID,
        token_delivery=CSRFTokenDelivery.BOTH,
        portal_name="admin",
        excluded_paths=["/health", "/metrics", "/api/health"],
        api_paths=["/api/v1/", "/api/admin/"],
        ssr_paths=["/", "/dashboard", "/admin"],
        require_referer_check=True,
        cookie_secure=True,
        cookie_samesite="Strict",
    )


def create_customer_portal_csrf_config() -> CSRFConfig:
    """Create CSRF config optimized for Customer Portal."""
    return CSRFConfig(
        mode=CSRFMode.HYBRID,
        token_delivery=CSRFTokenDelivery.BOTH,
        portal_name="customer",
        excluded_paths=["/health", "/api/public/"],
        api_paths=["/api/v1/", "/api/customer/"],
        ssr_paths=["/", "/portal", "/dashboard", "/billing"],
        require_referer_check=True,
        cookie_secure=True,
        cookie_samesite="Lax",  # Slightly more permissive for customer portal
    )


def create_management_portal_csrf_config() -> CSRFConfig:
    """Create CSRF config optimized for Management Portal."""
    return CSRFConfig(
        mode=CSRFMode.HYBRID,
        token_delivery=CSRFTokenDelivery.BOTH,
        portal_name="management",
        excluded_paths=["/health", "/metrics", "/api/webhooks/"],
        api_paths=["/api/v1/", "/api/management/", "/graphql"],
        ssr_paths=["/", "/management", "/tenants"],
        require_referer_check=True,
        cookie_secure=True,
        cookie_samesite="Strict",
    )


def create_reseller_portal_csrf_config() -> CSRFConfig:
    """Create CSRF config optimized for Reseller Portal."""
    return CSRFConfig(
        mode=CSRFMode.HYBRID,
        token_delivery=CSRFTokenDelivery.BOTH,
        portal_name="reseller",
        excluded_paths=["/health", "/api/public/"],
        api_paths=["/api/v1/", "/api/reseller/"],
        ssr_paths=["/", "/reseller", "/dashboard", "/partners"],
        require_referer_check=True,
        cookie_secure=True,
        cookie_samesite="Lax",
    )


def create_technician_portal_csrf_config() -> CSRFConfig:
    """Create CSRF config optimized for Technician Portal."""
    return CSRFConfig(
        mode=CSRFMode.HYBRID,
        token_delivery=CSRFTokenDelivery.BOTH,
        portal_name="technician",
        excluded_paths=["/health", "/api/offline-sync/"],
        api_paths=["/api/v1/", "/api/technician/"],
        ssr_paths=["/", "/technician", "/work-orders", "/map"],
        require_referer_check=False,  # Technicians may work from various networks
        cookie_secure=True,
        cookie_samesite="Lax",
    )


# Factory function for creating CSRF middleware
def create_csrf_middleware(portal_type: str, custom_config: Optional[CSRFConfig] = None) -> UnifiedCSRFMiddleware:
    """
    Create CSRF middleware for specific portal type.

    Args:
        portal_type: Type of portal (admin, customer, management, reseller, technician)
        custom_config: Optional custom configuration

    Returns:
        Configured UnifiedCSRFMiddleware instance
    """
    if custom_config:
        return UnifiedCSRFMiddleware(app=None, config=custom_config)

    # Use portal-specific defaults
    config_creators = {
        "admin": create_admin_portal_csrf_config,
        "customer": create_customer_portal_csrf_config,
        "management": create_management_portal_csrf_config,
        "reseller": create_reseller_portal_csrf_config,
        "technician": create_technician_portal_csrf_config,
    }

    config_creator = config_creators.get(portal_type)
    if not config_creator:
        raise ValueError(f"Unknown portal type: {portal_type}")

    config = config_creator()
    return UnifiedCSRFMiddleware(app=None, config=config)
class CSRFTokenExpiredError(CSRFError):
    """Raised when CSRF token is expired."""
