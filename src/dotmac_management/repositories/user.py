"""
User repository for authentication and user management.
Updated to use consolidated DRY patterns from dotmac_shared.
"""

from datetime import timezone
from typing import Optional
from uuid import UUID

from dotmac_shared.repositories import AsyncBaseRepository
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User, UserInvitation, UserSession


class UserRepository(AsyncBaseRepository[User]):
    """Repository for user operations using consolidated DRY patterns."""

    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, User, tenant_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.get_by_field("email", email)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self.get_by_field("username", username)

    async def get_active_users(self, tenant_id: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> list[User]:
        """Get active users, optionally filtered by tenant."""
        filters = {"is_active": True}
        if tenant_id:
            filters["tenant_id"] = tenant_id

        return await self.list(skip=skip, limit=limit, filters=filters, order_by="created_at")

    async def get_users_by_role(
        self,
        role: str,
        tenant_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """Get users by role."""
        filters = {"role": role, "is_active": True}
        if tenant_id:
            filters["tenant_id"] = tenant_id

        return await self.list(skip=skip, limit=limit, filters=filters, order_by="created_at")

    async def update_last_login(self, user_id: UUID) -> bool:
        """Update user's last login timestamp."""
        from datetime import datetime

        return (
            await self.update(
                user_id,
                {
                    "last_login": datetime.now(timezone.utc),
                    "login_count": User.login_count + 1,
                    "failed_login_attempts": 0,
                    "locked_until": None,
                },
            )
            is not None
        )

    async def increment_failed_login(self, user_id: UUID) -> bool:
        """Increment failed login attempts."""
        return await self.update(user_id, {"failed_login_attempts": User.failed_login_attempts + 1}) is not None

    async def lock_user(self, user_id: UUID, duration_minutes: int = 30) -> bool:
        """Lock user account."""
        from datetime import datetime, timedelta

        return (
            await self.update(
                user_id,
                {
                    "locked_until": datetime.now(timezone.utc) + timedelta(minutes=duration_minutes),
                    "failed_login_attempts": User.failed_login_attempts + 1,
                },
            )
            is not None
        )

    async def unlock_user(self, user_id: UUID) -> bool:
        """Unlock user account."""
        return await self.update(user_id, {"locked_until": None, "failed_login_attempts": 0}) is not None


class UserSessionRepository(AsyncBaseRepository[UserSession]):
    """Repository for user session operations."""

    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, UserSession, tenant_id)

    async def get_by_token(self, session_token: str) -> Optional[UserSession]:
        """Get session by token."""
        return await self.get_by_field("session_token", session_token)

    async def get_active_sessions(self, user_id: UUID) -> list[UserSession]:
        """Get active sessions for user."""
        return await self.list(filters={"user_id": user_id, "is_active": True}, order_by="-last_activity")

    async def revoke_all_sessions(self, user_id: UUID) -> int:
        """Revoke all sessions for a user."""
        from sqlalchemy import update

        query = (
            update(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_active is True)
            .values(is_active=False)
        )
        result = await self.db.execute(query)
        return result.rowcount

    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        from datetime import datetime

        from sqlalchemy import delete

        query = delete(UserSession).where(UserSession.expires_at < datetime.now(timezone.utc))
        result = await self.db.execute(query)
        return result.rowcount


class UserInvitationRepository(AsyncBaseRepository[UserInvitation]):
    """Repository for user invitation operations."""

    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, UserInvitation, tenant_id)

    async def get_by_token(self, invitation_token: str) -> Optional[UserInvitation]:
        """Get invitation by token."""
        return await self.get_by_field("invitation_token", invitation_token)

    async def get_pending_invitations(self, tenant_id: Optional[UUID] = None) -> list[UserInvitation]:
        """Get pending invitations."""
        filters = {"is_accepted": False}
        if tenant_id:
            filters["tenant_id"] = tenant_id

        return await self.list(filters=filters, order_by="-created_at")

    async def get_invitations_by_email(self, email: str) -> list[UserInvitation]:
        """Get invitations by email."""
        return await self.list(filters={"email": email}, order_by="-created_at")

    async def accept_invitation(self, invitation_id: UUID, user_id: UUID) -> bool:
        """Accept an invitation."""
        from datetime import datetime

        return (
            await self.update(
                invitation_id,
                {
                    "is_accepted": True,
                    "accepted_at": datetime.now(timezone.utc),
                    "accepted_by": user_id,
                },
            )
            is not None
        )

    async def cleanup_expired_invitations(self) -> int:
        """Remove expired invitations."""
        from datetime import datetime

        from sqlalchemy import delete

        query = (
            delete(UserInvitation)
            .where(UserInvitation.expires_at < datetime.now(timezone.utc))
            .where(UserInvitation.is_accepted is False)
        )
        result = await self.db.execute(query)
        return result.rowcount
