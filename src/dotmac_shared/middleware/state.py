"""
Request State Manager for DotMac Framework.

Provides standardized request state handling to eliminate duplication
in state management across middleware components.
"""

import logging
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import Request

from ..utils.datetime_utils import format_iso

logger = logging.getLogger(__name__)


@dataclass
class TenantContext:
    """Tenant context information."""

    tenant_id: str
    source: str  # gateway_header, container_context, jwt_token, subdomain
    validated: bool = False
    gateway_validated: bool = False
    isolation_level: str = "shared"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserContext:
    """User context information."""

    user_id: str
    username: str | None = None
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    session_id: str | None = None
    is_authenticated: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class APIVersionContext:
    """API version context information."""

    version: str
    status: str = "current"  # current, supported, deprecated, sunset
    sunset_date: str | None = None
    replacement_version: str | None = None
    deprecation_warnings: list[str] = field(default_factory=list)


@dataclass
class OperationContext:
    """Background operation context."""

    idempotency_key: str | None = None
    operation_id: str | None = None
    saga_id: str | None = None
    correlation_id: str | None = None
    retry_count: int = 0
    operation_type: str | None = None


@dataclass
class SecurityContext:
    """Security context information."""

    client_ip: str | None = None
    user_agent: str | None = None
    origin: str | None = None
    csrf_token: str | None = None
    rate_limit_key: str | None = None
    security_level: str = "standard"
    suspicious_activity: bool = False


@dataclass
class RequestMetadata:
    """Request metadata and tracking."""

    request_id: str = field(default_factory=lambda: str(uuid4()))
    start_time: str = field(default_factory=format_iso)
    path: str | None = None
    method: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    processing_stages: list[str] = field(default_factory=list)


@dataclass
class RequestState:
    """Standardized request state container.

    This consolidates all request state into a single, well-typed object
    that can be easily managed across middleware components.
    """

    # Core contexts
    tenant_context: TenantContext | None = None
    user_context: UserContext | None = None
    api_version_context: APIVersionContext | None = None
    operation_context: OperationContext | None = None
    security_context: SecurityContext | None = None

    # Metadata
    metadata: RequestMetadata = field(default_factory=RequestMetadata)

    # Custom data for extensions
    custom_data: dict[str, Any] = field(default_factory=dict)

    # Legacy compatibility properties
    @property
    def tenant_id(self) -> str | None:
        """Legacy tenant_id property."""
        return self.tenant_context.tenant_id if self.tenant_context else None

    @property
    def user_id(self) -> str | None:
        """Legacy user_id property."""
        return self.user_context.user_id if self.user_context else None

    @property
    def api_version(self) -> str | None:
        """Legacy api_version property."""
        return self.api_version_context.version if self.api_version_context else None

    @property
    def idempotency_key(self) -> str | None:
        """Legacy idempotency_key property."""
        return self.operation_context.idempotency_key if self.operation_context else None


class RequestStateManager:
    """Manager for request state operations."""

    @staticmethod
    def create_from_request(request: Request) -> RequestState:
        """Create RequestState from FastAPI request.

        Args:
            request: FastAPI request object

        Returns:
            RequestState populated from request
        """
        state = RequestState()

        # Populate metadata from request
        state.metadata.path = str(request.url.path)
        state.metadata.method = request.method

        # Extract headers for security context
        state.security_context = SecurityContext(
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            origin=request.headers.get("Origin"),
            csrf_token=request.headers.get("X-CSRF-Token"),
        )

        return state

    @staticmethod
    def set_on_request(request: Request, state: RequestState):
        """Set RequestState on FastAPI request.

        Args:
            request: FastAPI request object
            state: RequestState to set
        """
        # Set the complete state object
        request.state.dotmac_state = state

        # Set legacy compatibility attributes
        if state.tenant_context:
            request.state.tenant_id = state.tenant_context.tenant_id
            request.state.tenant_context = state.tenant_context

        if state.user_context:
            request.state.user_id = state.user_context.user_id
            request.state.user_context = state.user_context

        if state.api_version_context:
            request.state.api_version = state.api_version_context.version
            request.state.version_info = state.api_version_context

        if state.operation_context:
            request.state.idempotency_key = state.operation_context.idempotency_key
            request.state.operation_context = state.operation_context

        if state.security_context:
            request.state.client_ip = state.security_context.client_ip
            request.state.security_context = state.security_context

        # Set metadata
        request.state.request_id = state.metadata.request_id
        request.state.metadata = state.metadata

    @staticmethod
    def get_from_request(request: Request) -> RequestState:
        """Get RequestState from FastAPI request.

        Args:
            request: FastAPI request object

        Returns:
            RequestState from request, or new empty state
        """
        # Try to get complete state first
        state = getattr(request.state, "dotmac_state", None)
        if state:
            return state

        # Create from legacy attributes if available
        state = RequestState()

        # Legacy tenant context
        if hasattr(request.state, "tenant_context"):
            state.tenant_context = request.state.tenant_context
        elif hasattr(request.state, "tenant_id"):
            state.tenant_context = TenantContext(tenant_id=request.state.tenant_id, source="legacy")

        # Legacy user context
        if hasattr(request.state, "user_context"):
            state.user_context = request.state.user_context
        elif hasattr(request.state, "user_id"):
            state.user_context = UserContext(user_id=request.state.user_id)

        # Legacy API version
        if hasattr(request.state, "version_info"):
            version_info = request.state.version_info
            state.api_version_context = APIVersionContext(
                version=version_info.version,
                status=getattr(version_info, "status", "current"),
            )
        elif hasattr(request.state, "api_version"):
            state.api_version_context = APIVersionContext(version=request.state.api_version)

        # Legacy operation context
        if hasattr(request.state, "operation_context"):
            state.operation_context = request.state.operation_context
        elif hasattr(request.state, "idempotency_key"):
            state.operation_context = OperationContext(idempotency_key=request.state.idempotency_key)

        # Metadata
        if hasattr(request.state, "request_id"):
            state.metadata.request_id = request.state.request_id

        return state

    @staticmethod
    def update_tenant_context(request: Request, tenant_id: str, source: str = "unknown", **kwargs):
        """Update tenant context in request state.

        Args:
            request: FastAPI request
            tenant_id: Tenant ID
            source: Source of tenant information
            **kwargs: Additional tenant context fields
        """
        state = RequestStateManager.get_from_request(request)

        if not state.tenant_context:
            state.tenant_context = TenantContext(tenant_id=tenant_id, source=source)
        else:
            state.tenant_context.tenant_id = tenant_id
            state.tenant_context.source = source

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(state.tenant_context, key):
                setattr(state.tenant_context, key, value)

        RequestStateManager.set_on_request(request, state)

    @staticmethod
    def update_user_context(request: Request, user_id: str, **kwargs):
        """Update user context in request state.

        Args:
            request: FastAPI request
            user_id: User ID
            **kwargs: Additional user context fields
        """
        state = RequestStateManager.get_from_request(request)

        if not state.user_context:
            state.user_context = UserContext(user_id=user_id)
        else:
            state.user_context.user_id = user_id

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(state.user_context, key):
                setattr(state.user_context, key, value)

        RequestStateManager.set_on_request(request, state)

    @staticmethod
    def update_api_version_context(request: Request, version: str, **kwargs):
        """Update API version context in request state.

        Args:
            request: FastAPI request
            version: API version
            **kwargs: Additional version context fields
        """
        state = RequestStateManager.get_from_request(request)

        if not state.api_version_context:
            state.api_version_context = APIVersionContext(version=version)
        else:
            state.api_version_context.version = version

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(state.api_version_context, key):
                setattr(state.api_version_context, key, value)

        RequestStateManager.set_on_request(request, state)

    @staticmethod
    def update_operation_context(request: Request, **kwargs):
        """Update operation context in request state.

        Args:
            request: FastAPI request
            **kwargs: Operation context fields
        """
        state = RequestStateManager.get_from_request(request)

        if not state.operation_context:
            state.operation_context = OperationContext()

        # Update fields
        for key, value in kwargs.items():
            if hasattr(state.operation_context, key):
                setattr(state.operation_context, key, value)

        RequestStateManager.set_on_request(request, state)

    @staticmethod
    def add_processing_stage(request: Request, stage: str):
        """Add processing stage to request metadata.

        Args:
            request: FastAPI request
            stage: Processing stage name
        """
        state = RequestStateManager.get_from_request(request)
        state.metadata.processing_stages.append(stage)
        RequestStateManager.set_on_request(request, state)

    @staticmethod
    def get_state_dict(request: Request) -> dict[str, Any]:
        """Get request state as dictionary.

        Args:
            request: FastAPI request

        Returns:
            Dictionary representation of request state
        """
        state = RequestStateManager.get_from_request(request)
        return asdict(state)

    @staticmethod
    def validate_state(
        request: Request,
        require_tenant: bool = False,
        require_user: bool = False,
        require_version: bool = False,
    ) -> list[str]:
        """Validate request state completeness.

        Args:
            request: FastAPI request
            require_tenant: Whether tenant context is required
            require_user: Whether user context is required
            require_version: Whether API version is required

        Returns:
            List of validation errors (empty if valid)
        """
        state = RequestStateManager.get_from_request(request)
        errors = []

        if require_tenant and not state.tenant_context:
            errors.append("Tenant context required but missing")

        if require_user and not state.user_context:
            errors.append("User context required but missing")

        if require_version and not state.api_version_context:
            errors.append("API version context required but missing")

        return errors


# Convenience functions for common operations
def get_tenant_id(request: Request) -> str | None:
    """Get tenant ID from request state."""
    state = RequestStateManager.get_from_request(request)
    return state.tenant_id


def get_user_id(request: Request) -> str | None:
    """Get user ID from request state."""
    state = RequestStateManager.get_from_request(request)
    return state.user_id


def get_api_version(request: Request) -> str | None:
    """Get API version from request state."""
    state = RequestStateManager.get_from_request(request)
    return state.api_version


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    state = RequestStateManager.get_from_request(request)
    return state.metadata.request_id
