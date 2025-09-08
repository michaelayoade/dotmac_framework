"""
Tests for authentication models - Validation, serialization, and business logic.
"""
import os
import sys
from datetime import datetime, timedelta

# Adjust path for platform services imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../packages/dotmac-platform-services/src'))

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

        # Empty string is allowed by this model
        user_empty_email = User(id="user-2", email="")
        assert user_empty_email.email == ""

    def test_user_roles_list(self):
        """Test User roles as list."""
        user = User(
            id="user-roles-test",
            email="roles@example.com",
            roles=["admin", "moderator", "user"]
        )

        assert len(user.roles) == 3
        assert "admin" in user.roles
        assert "moderator" in user.roles
        assert "user" in user.roles

    def test_user_metadata_dict(self):
        """Test User metadata as dictionary."""
        metadata = {
            "department": "Engineering",
            "level": "senior",
            "preferences": {"theme": "dark"}
        }

        user = User(
            id="user-metadata-test",
            email="metadata@example.com",
            metadata=metadata
        )

        assert user.metadata["department"] == "Engineering"
        assert user.metadata["level"] == "senior"
        assert user.metadata["preferences"]["theme"] == "dark"


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

    def test_session_data_minimal(self):
        """Test SessionData with minimal required fields."""
        expires_at = datetime.utcnow() + timedelta(minutes=30)

        session = SessionData(
            user_id="user-minimal",
            session_id="session-minimal",
            expires_at=expires_at
        )

        assert session.user_id == "user-minimal"
        assert session.tenant_id is None
        assert session.session_id == "session-minimal"
        assert session.expires_at == expires_at

    def test_session_expiry_future(self):
        """Test session with future expiry."""
        future_time = datetime.utcnow() + timedelta(hours=24)
        session = SessionData(
            user_id="user-future",
            session_id="session-future",
            expires_at=future_time
        )
        assert session.expires_at > datetime.utcnow()

    def test_session_expiry_past(self):
        """Test session with past expiry (should be valid model, business logic handles)."""
        past_time = datetime.utcnow() - timedelta(hours=1)
        session = SessionData(
            user_id="user-expired",
            session_id="session-expired",
            expires_at=past_time
        )
        assert session.expires_at < datetime.utcnow()


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

    def test_auth_token_different_types(self):
        """Test AuthToken with different token types."""
        bearer_token = AuthToken(token="bearer_test", token_type="bearer")
        assert bearer_token.token_type == "bearer"

        api_key_token = AuthToken(token="api_key_test", token_type="api_key")
        assert api_key_token.token_type == "api_key"

    def test_token_validation(self):
        """Test token validation."""
        # Non-empty token should be valid
        token = AuthToken(token="valid_token_123")
        assert len(token.token) > 0

        # Empty token is allowed by this model
        empty_token = AuthToken(token="")
        assert empty_token.token == ""


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_user_model_dict_conversion(self):
        """Test User model to dict conversion."""
        user = User(
            id="serialize-test",
            email="serialize@example.com",
            username="serialize_user",
            roles=["user"]
        )
        user_dict = user.model_dump()

        assert isinstance(user_dict, dict)
        assert user_dict["id"] == "serialize-test"
        assert user_dict["email"] == "serialize@example.com"
        assert user_dict["username"] == "serialize_user"
        assert user_dict["is_active"] is True
        assert user_dict["roles"] == ["user"]

    def test_user_json_serialization(self):
        """Test User model JSON serialization."""
        user = User(
            id="json-test",
            email="json@example.com"
        )
        json_str = user.model_dump_json()

        assert isinstance(json_str, str)
        assert "json-test" in json_str
        assert "json@example.com" in json_str

    def test_model_from_dict(self):
        """Test creating model from dictionary."""
        user_data = {
            "id": "dict-test-user",
            "email": "dict@example.com",
            "username": "dictuser",
            "is_active": True,
            "roles": ["user", "tester"]
        }

        user = User(**user_data)
        assert user.id == "dict-test-user"
        assert user.email == "dict@example.com"
        assert user.username == "dictuser"
        assert user.roles == ["user", "tester"]

    def test_session_data_serialization(self):
        """Test SessionData serialization."""
        expires_at = datetime.utcnow() + timedelta(hours=2)
        session = SessionData(
            user_id="session-serialize-test",
            session_id="session-123",
            expires_at=expires_at,
            metadata={"source": "test"}
        )

        session_dict = session.model_dump()
        assert session_dict["user_id"] == "session-serialize-test"
        assert session_dict["session_id"] == "session-123"
        assert session_dict["metadata"]["source"] == "test"

    def test_auth_token_serialization(self):
        """Test AuthToken serialization."""
        token = AuthToken(
            token="serialize-token-123",
            expires_in=7200,
            scope="read write admin"
        )

        token_dict = token.model_dump()
        assert token_dict["token"] == "serialize-token-123"
        assert token_dict["token_type"] == "bearer"
        assert token_dict["expires_in"] == 7200
        assert token_dict["scope"] == "read write admin"
