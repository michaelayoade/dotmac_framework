"""Authentication repositories for Platform SDK.

This module provides SDK-specific repository abstractions for authentication operations.
It wraps the actual identity module repositories to maintain proper architectural boundaries.
"""

from typing import Any, Optional
from uuid import UUID

from dotmac_isp.modules.identity.models import User
from dotmac_isp.modules.identity.repository import (
    UserRepository as IdentityUserRepository,
)
from dotmac_isp.sdks.core.exceptions import SDKError
from sqlalchemy.orm import Session


class UserRepository:
    """Platform SDK wrapper for user repository operations."""

    def __init__(self, db_session: Session, tenant_id: Optional[UUID] = None):
        """Initialize user repository with database session."""
        self.db = db_session
        self.tenant_id = tenant_id
        self._identity_repo = IdentityUserRepository(db_session, tenant_id) if tenant_id else None

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find user by ID."""
        try:
            if not self._identity_repo:
                raise SDKError("Repository not properly initialized with tenant_id")
            return self._identity_repo.get_by_id(user_id)
        except Exception as e:
            raise SDKError(f"Failed to find user by ID: {str(e)}") from e

    async def find_by_username(self, username: str) -> Optional[User]:
        """Find user by username."""
        try:
            if not self._identity_repo:
                raise SDKError("Repository not properly initialized with tenant_id")
            return self._identity_repo.get_by_username(username)
        except Exception as e:
            raise SDKError(f"Failed to find user by username: {str(e)}") from e

    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""
        try:
            if not self._identity_repo:
                raise SDKError("Repository not properly initialized with tenant_id")
            return self._identity_repo.get_by_email(email)
        except Exception as e:
            raise SDKError(f"Failed to find user by email: {str(e)}") from e

    async def create(self, user_data: dict[str, Any]) -> User:
        """Create new user."""
        try:
            if not self._identity_repo:
                raise SDKError("Repository not properly initialized with tenant_id")
            return self._identity_repo.create(user_data)
        except Exception as e:
            raise SDKError(f"Failed to create user: {str(e)}") from e

    async def update(self, user_id: UUID, user_data: dict[str, Any]) -> Optional[User]:
        """Update existing user."""
        try:
            if not self._identity_repo:
                raise SDKError("Repository not properly initialized with tenant_id")
            return self._identity_repo.update(user_id, user_data)
        except Exception as e:
            raise SDKError(f"Failed to update user: {str(e)}") from e

    async def delete(self, user_id: UUID) -> bool:
        """Delete user by ID."""
        try:
            if not self._identity_repo:
                raise SDKError("Repository not properly initialized with tenant_id")
            return self._identity_repo.delete(user_id)
        except Exception as e:
            raise SDKError(f"Failed to delete user: {str(e)}") from e


class UserSessionRepository:
    """Platform SDK repository for user session operations.

    This is a simplified session repository for SDK purposes.
    In a full implementation, this would connect to a dedicated session store.
    """

    def __init__(self, db_session: Session, tenant_id: Optional[UUID] = None):
        """Initialize session repository."""
        self.db = db_session
        self.tenant_id = tenant_id
        self._sessions: dict[str, dict[str, Any]] = {}  # In-memory for now

    async def create_session(self, user_id: UUID, session_data: dict[str, Any]) -> str:
        """Create new user session."""
        try:
            session_id = f"session_{user_id}_{len(self._sessions)}"
            self._sessions[session_id] = {
                "user_id": user_id,
                "tenant_id": self.tenant_id,
                **session_data,
            }
            return session_id
        except Exception as e:
            raise SDKError(f"Failed to create session: {str(e)}") from e

    async def find_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Find session by ID."""
        return self._sessions.get(session_id)

    async def update_session(self, session_id: str, session_data: dict[str, Any]) -> bool:
        """Update existing session."""
        try:
            if session_id in self._sessions:
                self._sessions[session_id].update(session_data)
                return True
            return False
        except Exception as e:
            raise SDKError(f"Failed to update session: {str(e)}") from e

    async def delete_session(self, session_id: str) -> bool:
        """Delete session by ID."""
        try:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
        except Exception as e:
            raise SDKError(f"Failed to delete session: {str(e)}") from e

    async def find_sessions_by_user(self, user_id: UUID) -> list[dict[str, Any]]:
        """Find all sessions for a user."""
        try:
            return [
                {"session_id": sid, **sdata} for sid, sdata in self._sessions.items() if sdata.get("user_id") == user_id
            ]
        except Exception as e:
            raise SDKError(f"Failed to find user sessions: {str(e)}") from e
