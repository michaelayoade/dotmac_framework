"""
FastAPI dependency injection for dotmac_core_events.

Provides dependency injection for:
- SDK instances (EventBusSDK, SchemaRegistrySDK, OutboxSDK)
- Tenant ID extraction from headers or JWT
- User ID extraction from JWT tokens
- Authorization checks
"""

import os
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..sdks.event_bus import EventBusSDK
from ..sdks.outbox import OutboxSDK
from ..sdks.schema_registry import SchemaRegistrySDK

# Global SDK instances
_event_bus_instance: Optional[EventBusSDK] = None
_schema_registry_instance: Optional[SchemaRegistrySDK] = None
_outbox_instance: Optional[OutboxSDK] = None

# Security scheme
security = HTTPBearer(auto_error=False)

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

def _get_jwt_secret() -> str:
    """Get JWT secret key from environment."""
    if not JWT_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET_KEY environment variable not configured"
        )
    return JWT_SECRET_KEY


def set_event_bus_instance(instance: EventBusSDK) -> None:
    """Set the global EventBusSDK instance."""
    global _event_bus_instance
    _event_bus_instance = instance


def set_schema_registry_instance(instance: SchemaRegistrySDK) -> None:
    """Set the global SchemaRegistrySDK instance."""
    global _schema_registry_instance
    _schema_registry_instance = instance


def set_outbox_instance(instance: OutboxSDK) -> None:
    """Set the global OutboxSDK instance."""
    global _outbox_instance
    _outbox_instance = instance


async def get_event_bus() -> EventBusSDK:
    """Get the EventBusSDK instance."""
    if _event_bus_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EventBusSDK not initialized"
        )
    return _event_bus_instance


async def get_schema_registry() -> Optional[SchemaRegistrySDK]:
    """Get the SchemaRegistrySDK instance."""
    return _schema_registry_instance


async def get_outbox() -> Optional[OutboxSDK]:
    """Get the OutboxSDK instance."""
    return _outbox_instance


async def get_tenant_id(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Extract tenant ID from header or JWT token.

    Args:
        x_tenant_id: Tenant ID from X-Tenant-ID header
        credentials: JWT credentials from Authorization header

    Returns:
        Tenant ID string

    Raises:
        HTTPException: If tenant ID cannot be determined
    """
    # First try header
    if x_tenant_id:
        return x_tenant_id

    # Try JWT token
    if credentials:
        try:
            # Decode JWT with proper signature verification
            secret = _get_jwt_secret()
            payload = jwt.decode(
                credentials.credentials,
                secret,
                algorithms=[JWT_ALGORITHM],
                verify=True
            )
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                return tenant_id
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired JWT token"
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT validation failed"
            )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tenant ID required in X-Tenant-ID header or JWT token"
    )


async def get_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Extract user ID from JWT token.

    Args:
        credentials: JWT credentials from Authorization header

    Returns:
        User ID string if available, None otherwise
    """
    if not credentials:
        return None

    try:
        # Decode JWT with proper signature verification
        secret = _get_jwt_secret()
        payload = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=[JWT_ALGORITHM],
            verify=True
        )
        return payload.get("sub") or payload.get("user_id")
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


async def check_tenant_access(
    tenant_id: str = Depends(get_tenant_id),
    user_id: Optional[str] = Depends(get_user_id)
) -> bool:
    """
    Check if user has access to the specified tenant.

    Args:
        tenant_id: Tenant ID to check access for
        user_id: User ID from JWT token

    Returns:
        True if access is allowed

    Raises:
        HTTPException: If access is denied
    """
    # TODO: Implement actual tenant access checks
    # For now, allow all access if tenant_id is provided
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: invalid tenant"
        )

    return True
