"""
Auth Models - Compatibility Module

Provides User and other models expected by tests.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    """User model for authentication."""

    id: str
    email: str
    username: str | None = None
    is_active: bool = True
    tenant_id: str | None = None
    roles: list[str] = []
    metadata: dict[str, Any] = {}
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SessionData(BaseModel):
    """Session data model."""

    user_id: str
    tenant_id: str | None = None
    session_id: str
    expires_at: datetime
    metadata: dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class AuthToken(BaseModel):
    """Auth token model."""

    token: str
    token_type: str = "bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None

    model_config = ConfigDict(from_attributes=True)


__all__ = ["User", "SessionData", "AuthToken"]
