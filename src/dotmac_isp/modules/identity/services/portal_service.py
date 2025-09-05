"""
Portal management service for identity operations.
Handles portal access and permissions.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from dotmac_shared.services.base import BaseService

from ..models import PortalAccess
from ..repository import UserRepository

logger = logging.getLogger(__name__)


class PortalService(BaseService):
    """Portal access management service."""

    def __init__(self, db_session, tenant_id: str):
        super().__init__(db_session, tenant_id)
        self.user_repo = UserRepository(db_session, tenant_id)

    async def create_portal_access(
        self,
        user_id: UUID,
        portal_type: str,
        access_data: dict[str, Any],
        created_by: str,
    ) -> Optional[dict[str, Any]]:
        """Create portal access for user."""
        try:
            # Verify user exists
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                logger.warning(
                    f"Portal access creation failed: user {user_id} not found"
                )
                return None

            # Create portal access
            portal_access = PortalAccess(
                tenant_id=self.tenant_id,
                user_id=user_id,
                portal_type=portal_type,
                access_level=access_data.get("access_level", "standard"),
                is_enabled=access_data.get("is_enabled", True),
                allowed_features=access_data.get("allowed_features", []),
                denied_features=access_data.get("denied_features", []),
                max_concurrent_sessions=access_data.get("max_concurrent_sessions", 3),
                session_timeout_minutes=access_data.get("session_timeout_minutes", 480),
                require_mfa=access_data.get("require_mfa", False),
                allowed_ip_ranges=access_data.get("allowed_ip_ranges", []),
            )

            self.db.add(portal_access)
            await self.db.commit()
            await self.db.refresh(portal_access)

            logger.info(
                f"Created {portal_type} portal access for user {user_id} by {created_by}"
            )

            return {
                "id": str(portal_access.id),
                "user_id": str(portal_access.user_id),
                "portal_type": portal_access.portal_type,
                "access_level": portal_access.access_level,
                "is_enabled": portal_access.is_enabled,
                "allowed_features": portal_access.allowed_features,
                "denied_features": portal_access.denied_features,
                "created_at": portal_access.created_at.isoformat(),
                "tenant_id": portal_access.tenant_id,
            }

        except Exception as e:
            logger.error(f"Error creating portal access: {e}")
            await self.db.rollback()
            return None

    async def get_user_portal_access(
        self, user_id: UUID, portal_type: str
    ) -> Optional[dict[str, Any]]:
        """Get user's portal access."""
        try:
            # Query for portal access
            from sqlalchemy import and_, select

            stmt = select(PortalAccess).where(
                and_(
                    PortalAccess.tenant_id == self.tenant_id,
                    PortalAccess.user_id == user_id,
                    PortalAccess.portal_type == portal_type,
                )
            )

            result = await self.db.execute(stmt)
            portal_access = result.scalar_one_or_none()

            if not portal_access:
                return None

            return {
                "id": str(portal_access.id),
                "user_id": str(portal_access.user_id),
                "portal_type": portal_access.portal_type,
                "access_level": portal_access.access_level,
                "is_enabled": portal_access.is_enabled,
                "allowed_features": portal_access.allowed_features,
                "denied_features": portal_access.denied_features,
                "max_concurrent_sessions": portal_access.max_concurrent_sessions,
                "session_timeout_minutes": portal_access.session_timeout_minutes,
                "require_mfa": portal_access.require_mfa,
                "last_access": portal_access.last_access.isoformat()
                if portal_access.last_access
                else None,
                "tenant_id": portal_access.tenant_id,
            }
        except Exception as e:
            logger.error(f"Error getting portal access for user {user_id}: {e}")
            return None

    async def update_portal_access(
        self,
        user_id: UUID,
        portal_type: str,
        access_data: dict[str, Any],
        updated_by: str,
    ) -> Optional[dict[str, Any]]:
        """Update user's portal access."""
        try:
            # Find existing portal access
            from sqlalchemy import and_, select

            stmt = select(PortalAccess).where(
                and_(
                    PortalAccess.tenant_id == self.tenant_id,
                    PortalAccess.user_id == user_id,
                    PortalAccess.portal_type == portal_type,
                )
            )

            result = await self.db.execute(stmt)
            portal_access = result.scalar_one_or_none()

            if not portal_access:
                return None

            # Update fields
            if "access_level" in access_data:
                portal_access.access_level = access_data["access_level"]
            if "is_enabled" in access_data:
                portal_access.is_enabled = access_data["is_enabled"]
            if "allowed_features" in access_data:
                portal_access.allowed_features = access_data["allowed_features"]
            if "denied_features" in access_data:
                portal_access.denied_features = access_data["denied_features"]
            if "max_concurrent_sessions" in access_data:
                portal_access.max_concurrent_sessions = access_data[
                    "max_concurrent_sessions"
                ]
            if "session_timeout_minutes" in access_data:
                portal_access.session_timeout_minutes = access_data[
                    "session_timeout_minutes"
                ]
            if "require_mfa" in access_data:
                portal_access.require_mfa = access_data["require_mfa"]
            if "allowed_ip_ranges" in access_data:
                portal_access.allowed_ip_ranges = access_data["allowed_ip_ranges"]

            await self.db.commit()
            await self.db.refresh(portal_access)

            logger.info(
                f"Updated {portal_type} portal access for user {user_id} by {updated_by}"
            )

            return {
                "id": str(portal_access.id),
                "user_id": str(portal_access.user_id),
                "portal_type": portal_access.portal_type,
                "access_level": portal_access.access_level,
                "is_enabled": portal_access.is_enabled,
                "updated_at": portal_access.updated_at.isoformat(),
                "tenant_id": portal_access.tenant_id,
            }

        except Exception as e:
            logger.error(f"Error updating portal access: {e}")
            await self.db.rollback()
            return None

    async def check_portal_access(
        self, user_id: UUID, portal_type: str, feature: Optional[str] = None
    ) -> bool:
        """Check if user has portal access."""
        try:
            portal_access = await self.get_user_portal_access(user_id, portal_type)

            if not portal_access or not portal_access["is_enabled"]:
                return False

            # Check specific feature access if provided
            if feature:
                denied_features = portal_access.get("denied_features", [])
                if feature in denied_features:
                    return False

                allowed_features = portal_access.get("allowed_features", [])
                if allowed_features and feature not in allowed_features:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking portal access: {e}")
            return False

    async def list_portal_users(self, portal_type: str) -> list[dict[str, Any]]:
        """List users with access to specific portal."""
        try:
            from sqlalchemy import and_, select
            from sqlalchemy.orm import selectinload

            stmt = (
                select(PortalAccess)
                .where(
                    and_(
                        PortalAccess.tenant_id == self.tenant_id,
                        PortalAccess.portal_type == portal_type,
                        PortalAccess.is_enabled is True,
                    )
                )
                .options(selectinload(PortalAccess.user))
            )

            result = await self.db.execute(stmt)
            portal_accesses = result.scalars().all()

            return [
                {
                    "user_id": str(access.user_id),
                    "username": access.user.username if access.user else None,
                    "email": access.user.email if access.user else None,
                    "access_level": access.access_level,
                    "last_access": access.last_access.isoformat()
                    if access.last_access
                    else None,
                    "total_logins": access.total_logins,
                }
                for access in portal_accesses
            ]

        except Exception as e:
            logger.error(f"Error listing {portal_type} portal users: {e}")
            return []


# Export service
__all__ = ["PortalService"]
