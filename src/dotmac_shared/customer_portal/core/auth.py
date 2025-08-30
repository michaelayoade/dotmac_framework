"""
Portal Authentication Manager

Handles authentication for customer portals using existing auth services.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from dotmac_shared.auth import AuthService
from dotmac_shared.monitoring import get_monitoring

from .schemas import PortalSessionData, PortalType

logger = logging.getLogger(__name__)


class PortalAuthenticationManager:
    """
    Authentication manager for customer portals.

    Leverages existing auth service while providing portal-specific functionality.
    """

    def __init__(self, auth_service: AuthService, portal_type: PortalType):
        """Initialize with existing auth service."""
        self.auth_service = auth_service
        self.portal_type = portal_type
        self.monitoring = get_monitoring("portal_auth")

    async def authenticate_customer(
        self,
        credentials: Dict[str, Any],
        portal_context: Dict[str, Any],
        tenant_id: UUID,
    ) -> PortalSessionData:
        """
        Authenticate customer and create portal session.

        Uses existing auth service for validation and creates portal-specific session.
        """
        try:
            # Authenticate using existing auth service
            auth_result = await self.auth_service.authenticate_user(
                email=credentials.get("email"),
                password=credentials.get("password"),
                tenant_id=str(tenant_id),
            )

            if not auth_result.success:
                raise ValueError("Authentication failed")

            # Create portal session
            session = PortalSessionData(
                session_id=UUID(auth_result.session_id),
                customer_id=UUID(auth_result.user_id),
                portal_type=self.portal_type,
                tenant_id=tenant_id,
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
                permissions=auth_result.permissions,
                preferences=portal_context.get("preferences", {}),
                context={
                    "portal_type": self.portal_type.value,
                    "user_agent": portal_context.get("user_agent"),
                    "ip_address": portal_context.get("ip_address"),
                    "tenant_id": str(tenant_id),
                },
            )

            # Record successful authentication
            self.monitoring.record_http_request(
                method="POST",
                endpoint="portal_authenticate",
                status_code=200,
                duration=0.1,
                tenant_id=str(tenant_id),
            )

            return session

        except Exception as e:
            logger.error(f"Portal authentication failed: {e}")

            # Record failed authentication
            self.monitoring.record_error(
                error_type="authentication_failed",
                service="portal_auth",
                tenant_id=str(tenant_id),
            )

            raise

    async def validate_session(self, session_id: UUID) -> Optional[PortalSessionData]:
        """Validate portal session using existing auth service."""
        try:
            # Validate session through auth service
            session_info = await self.auth_service.validate_session(str(session_id))

            if not session_info:
                return None

            # Convert to portal session data
            return PortalSessionData(
                session_id=session_id,
                customer_id=UUID(session_info.user_id),
                portal_type=self.portal_type,
                tenant_id=UUID(session_info.tenant_id),
                created_at=session_info.created_at,
                expires_at=session_info.expires_at,
                permissions=session_info.permissions,
                preferences=session_info.metadata.get("preferences", {}),
                context=session_info.metadata.get("context", {}),
            )

        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return None

    async def refresh_session(
        self, session_id: UUID, tenant_id: UUID
    ) -> Optional[PortalSessionData]:
        """Refresh portal session using existing auth service."""
        try:
            # Refresh through auth service
            refreshed = await self.auth_service.refresh_session(
                session_id=str(session_id), tenant_id=str(tenant_id)
            )

            if not refreshed:
                return None

            # Return updated session data
            return await self.validate_session(session_id)

        except Exception as e:
            logger.error(f"Session refresh failed: {e}")
            return None

    async def logout(self, session_id: UUID, tenant_id: UUID) -> bool:
        """Logout customer using existing auth service."""
        try:
            return await self.auth_service.logout_session(
                session_id=str(session_id), tenant_id=str(tenant_id)
            )
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False
