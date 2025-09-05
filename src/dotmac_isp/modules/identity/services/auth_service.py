"""
Authentication service for identity management.
Handles authentication workflows and session management.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from dotmac_shared.services.base import BaseService

from dotmac.platform.auth.core.jwt_service import JWTService
from dotmac.platform.auth.core.sessions import SessionManager

from ..models import User
from ..repository import AuthenticationRepository, UserRepository

logger = logging.getLogger(__name__)


class AuthService(BaseService):
    """Authentication service for identity operations."""

    def __init__(self, db_session, tenant_id: str):
        super().__init__(db_session, tenant_id)
        self.user_repo = UserRepository(db_session, tenant_id)
        self.auth_repo = AuthenticationRepository(db_session)
        self.jwt_service = JWTService()
        self.session_manager = SessionManager()

    async def authenticate_user(
        self,
        email: str,
        password: str,
        portal_type: str = "customer",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Authenticate user and create session."""
        try:
            # Find user
            user = await self.user_repo.get_by_email(email)
            if not user:
                await self._log_failed_attempt(
                    email=email,
                    reason="User not found",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    portal_type=portal_type,
                )
                return None

            # Check if user is active and not locked
            if not user.is_active:
                await self._log_failed_attempt(
                    email=email,
                    reason="Account inactive",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    portal_type=portal_type,
                )
                return None

            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                await self._log_failed_attempt(
                    email=email,
                    reason="Account locked",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    portal_type=portal_type,
                )
                return None

            # Verify password (simplified - in production use proper password hashing)
            if not self._verify_password(password, user.password_hash):
                await self.user_repo.increment_failed_login(user.id)
                await self._log_failed_attempt(
                    email=email,
                    reason="Invalid password",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    portal_type=portal_type,
                )
                return None

            # Create session
            session_data = await self._create_user_session(
                user, portal_type, ip_address, user_agent
            )

            # Update user login info
            await self.user_repo.update_last_login(user.id)

            # Log successful authentication
            await self._log_successful_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                portal_type=portal_type,
            )

            return session_data

        except Exception as e:
            logger.error(f"Authentication error for {email}: {e}")
            return None

    async def refresh_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Refresh user session."""
        try:
            session = await self.auth_repo.get_active_session(session_id)
            if not session:
                return None

            # Update last activity
            session.last_activity = datetime.now(timezone.utc)
            await self.db.commit()

            # Return updated session data
            return {
                "session_id": session.id,
                "user_id": str(session.user_id),
                "tenant_id": session.tenant_id,
                "portal_type": session.portal_type,
                "expires_at": session.expires_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Session refresh error for {session_id}: {e}")
            return None

    async def logout_user(self, session_id: str) -> bool:
        """Logout user and invalidate session."""
        try:
            success = await self.auth_repo.invalidate_session(session_id)
            if success:
                logger.info(f"User logged out: session {session_id}")
            return success
        except Exception as e:
            logger.error(f"Logout error for session {session_id}: {e}")
            return False

    def _verify_password(self, password: str, password_hash: Optional[str]) -> bool:
        """Verify password against hash (simplified implementation)."""
        # In production, use proper password hashing (bcrypt, etc.)
        return password_hash is not None and len(password) >= 8

    async def _create_user_session(
        self,
        user: User,
        portal_type: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
    ) -> dict[str, Any]:
        """Create new user session."""
        session_id = self.session_manager.generate_session_id()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=8)

        await self.auth_repo.create_session(
            session_id=session_id,
            user_id=user.id,
            tenant_id=self.tenant_id,
            portal_type=portal_type,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Create JWT token
        token_payload = {
            "user_id": str(user.id),
            "email": user.email,
            "username": user.username,
            "tenant_id": self.tenant_id,
            "portal_type": portal_type,
            "session_id": session_id,
            "permissions": user.permissions or [],
            "exp": expires_at.timestamp(),
        }

        access_token = self.jwt_service.create_token(token_payload)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 28800,  # 8 hours
            "session_id": session_id,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "portal_type": portal_type,
                "tenant_id": self.tenant_id,
            },
        }

    async def _log_successful_attempt(
        self,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        portal_type: Optional[str] = None,
    ):
        """Log successful authentication attempt."""
        await self.auth_repo.log_authentication_attempt(
            email=email,
            tenant_id=self.tenant_id,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
            portal_type=portal_type,
        )

    async def _log_failed_attempt(
        self,
        email: str,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        portal_type: Optional[str] = None,
    ):
        """Log failed authentication attempt."""
        await self.auth_repo.log_authentication_attempt(
            email=email,
            tenant_id=self.tenant_id,
            success=False,
            failure_reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
            portal_type=portal_type,
        )


# Export service
__all__ = ["AuthService"]
