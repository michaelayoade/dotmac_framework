"""
Tests for authentication models - Validation, serialization, and business logic.
"""
import os
import sys
from datetime import datetime, timedelta

# Adjust path for platform services imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../packages/dotmac-platform-services/src'))

import pytest
from pydantic import ValidationError
from tests.factories.auth_factories import (
    AuthTokenFactory,
    SessionDataFactory,
    UserFactory,
)

from dotmac.auth.models import AuthToken, SessionData, User

# Restore path after imports
sys.path = sys.path[1:]


class TestUserModel:
    """Test suite for User model validation and functionality."""

    def test_user_creation_with_required_fields(self):
        """Test User model creation with only required fields."""
        user = User(
            id="user-123",
            email="test@example.com"
        )

        assert user.id == "user-123"
        assert user.email == "test@example.com"
        assert user.username is None
        assert user.is_active is True
        assert user.tenant_id is None
        assert user.roles == []
        assert user.metadata == {}
        assert user.created_at is None
        assert user.updated_at is None

    def test_user_creation_with_all_fields(self):
        """Test User model creation with all fields populated."""
        created_at = datetime.utcnow()
        updated_at = datetime.utcnow()

        user = User(
            id="user-456",
            email="admin@example.com",
            username="admin",
            is_active=True,
            tenant_id="tenant-789",
            roles=["admin", "user"],
            metadata={"department": "IT"},
            created_at=created_at,
            updated_at=updated_at
        )

        assert user.id == "user-456"
        assert user.email == "admin@example.com"
        assert user.username == "admin"
        assert user.is_active is True
        assert user.tenant_id == "tenant-789"
        assert user.roles == ["admin", "user"]
        assert user.metadata == {"department": "IT"}
        assert user.created_at == created_at
        assert user.updated_at == updated_at

    def test_user_email_validation(self):
        """Test User model email validation."""
        # Valid email should work
        user = User(id="user-1", email="valid@example.com")
        assert user.email == "valid@example.com"

        # Test with empty string - should be caught by pydantic
        with pytest.raises(ValidationError):
            User(id="user-2", email="")

    def test_user_factory_creation(self):
        """Test User creation using factory."""
        user = UserFactory()

        assert user.id is not None
        assert "@" in user.email
        assert user.username is not None
        assert user.is_active is True
        assert user.tenant_id is not None
        assert isinstance(user.roles, list)
        assert isinstance(user.metadata, dict)
        assert isinstance(user.created_at, datetime)

    def test_admin_user_factory(self):
        """Test admin user creation using factory."""
        admin = UserFactory(roles=["admin", "user"])

        assert "admin" in admin.roles
        assert "user" in admin.roles
        assert admin.is_active is True


class TestSessionDataModel:
    """Test suite for SessionData model."""

    def test_session_data_creation(self):
        """Test SessionData model creation."""
        expires_at = datetime.utcnow() + timedelta(hours=1)

        session = SessionData(
            user_id="user-123",
            tenant_id="tenant-456",
            session_id="session-789",
            expires_at=expires_at
        )

        assert session.user_id == "user-123"
        assert session.tenant_id == "tenant-456"
        assert session.session_id == "session-789"
        assert session.expires_at == expires_at
        assert session.metadata == {}

    def test_session_data_factory(self):
        """Test SessionData creation using factory."""
        session = SessionDataFactory()

        assert session.user_id is not None
        assert session.tenant_id is not None
        assert session.session_id is not None
        assert session.expires_at > datetime.utcnow()
        assert isinstance(session.metadata, dict)

    def test_session_expiry_validation(self):
        """Test session expiry logic."""
        # Future expiry should be valid
        future_time = datetime.utcnow() + timedelta(hours=1)
        session = SessionData(
            user_id="user-1",
            session_id="session-1",
            expires_at=future_time
        )
        assert session.expires_at > datetime.utcnow()

        # Past expiry should still be accepted (business logic will handle)
        past_time = datetime.utcnow() - timedelta(hours=1)
        expired_session = SessionData(
            user_id="user-2",
            session_id="session-2",
            expires_at=past_time
        )
        assert expired_session.expires_at < datetime.utcnow()


class TestAuthTokenModel:
    """Test suite for AuthToken model."""

    def test_auth_token_creation(self):
        """Test AuthToken model creation."""
        token = AuthToken(
            token="abc123token",
            token_type="bearer",
            expires_in=3600,
            refresh_token="refresh123",
            scope="read write"
        )

        assert token.token == "abc123token"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600
        assert token.refresh_token == "refresh123"
        assert token.scope == "read write"

    def test_auth_token_defaults(self):
        """Test AuthToken model with default values."""
        token = AuthToken(token="simple_token")

        assert token.token == "simple_token"
        assert token.token_type == "bearer"  # default
        assert token.expires_in is None
        assert token.refresh_token is None
        assert token.scope is None

    def test_auth_token_factory(self):
        """Test AuthToken creation using factory."""
        token = AuthTokenFactory()

        assert token.token is not None
        assert token.token_type == "bearer"
        assert token.expires_in == 3600
        assert token.refresh_token is not None
        assert token.scope == "read write"

    def test_token_validation(self):
        """Test token validation logic."""
        # Non-empty token should be valid
        token = AuthToken(token="valid_token_123")
        assert len(token.token) > 0

        # Empty token should fail validation
        with pytest.raises(ValidationError):
            AuthToken(token="")


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_user_model_dict_conversion(self):
        """Test User model to dict conversion."""
        user = UserFactory()
        user_dict = user.model_dump()

        assert isinstance(user_dict, dict)
        assert user_dict["id"] == user.id
        assert user_dict["email"] == user.email
        assert user_dict["is_active"] == user.is_active

    def test_user_json_serialization(self):
        """Test User model JSON serialization."""
        user = UserFactory()
        json_str = user.model_dump_json()

        assert isinstance(json_str, str)
        assert user.id in json_str
        assert user.email in json_str

    def test_model_from_dict(self):
        """Test creating model from dictionary."""
        user_data = {
            "id": "test-user",
            "email": "test@example.com",
            "username": "testuser",
            "is_active": True,
            "roles": ["user"]
        }

        user = User(**user_data)
        assert user.id == "test-user"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.roles == ["user"]
