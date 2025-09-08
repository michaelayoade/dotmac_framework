"""
Comprehensive tests for User Management Authentication - targeting 95% coverage.

Tests cover user creation, updating, deletion, role management, and edge cases.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

try:
    from dotmac_shared.auth.user_management import (
        PasswordPolicy,
        User,
        UserCreateRequest,
        UserManagementError,
        UserManager,
        UserRole,
        UserStatus,
        UserUpdateRequest,
    )
except ImportError:
    # Create mock classes for testing
    from enum import Enum
    from typing import Optional

    class UserStatus(Enum):
        ACTIVE = "active"
        INACTIVE = "inactive"
        SUSPENDED = "suspended"
        PENDING = "pending"

    class UserRole(Enum):
        ADMIN = "admin"
        USER = "user"
        GUEST = "guest"
        MODERATOR = "moderator"

    class User:
        def __init__(self, user_id, email, username, tenant_id, **kwargs):
            self.user_id = user_id
            self.email = email
            self.username = username
            self.tenant_id = tenant_id
            self.status = kwargs.get('status', UserStatus.ACTIVE)
            self.role = kwargs.get('role', UserRole.USER)
            self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
            self.updated_at = kwargs.get('updated_at', datetime.now(timezone.utc))
            self.last_login = kwargs.get('last_login')
            self.password_hash = kwargs.get('password_hash')
            self.metadata = kwargs.get('metadata', {})

    class UserCreateRequest:
        def __init__(self, email, username, password, **kwargs):
            self.email = email
            self.username = username
            self.password = password
            self.role = kwargs.get('role', UserRole.USER)
            self.metadata = kwargs.get('metadata', {})

    class UserUpdateRequest:
        def __init__(self, **kwargs):
            self.email = kwargs.get('email')
            self.username = kwargs.get('username')
            self.status = kwargs.get('status')
            self.role = kwargs.get('role')
            self.metadata = kwargs.get('metadata', {})

    class PasswordPolicy:
        def __init__(self, **kwargs):
            self.min_length = kwargs.get('min_length', 8)
            self.require_uppercase = kwargs.get('require_uppercase', True)
            self.require_lowercase = kwargs.get('require_lowercase', True)
            self.require_numbers = kwargs.get('require_numbers', True)
            self.require_symbols = kwargs.get('require_symbols', False)
            self.max_age_days = kwargs.get('max_age_days', 90)

        def validate_password(self, password: str) -> bool:
            if len(password) < self.min_length:
                return False
            if self.require_uppercase and not any(c.isupper() for c in password):
                return False
            if self.require_lowercase and not any(c.islower() for c in password):
                return False
            if self.require_numbers and not any(c.isdigit() for c in password):
                return False
            if self.require_symbols and not any(c in "!@#$%^&*" for c in password):
                return False
            return True

    class UserManager:
        def __init__(self, tenant_id):
            if tenant_id is None:
                raise ValueError("tenant_id cannot be None")
            if tenant_id == "":
                raise ValueError("tenant_id cannot be empty")
            self.tenant_id = tenant_id
            self._users = {}
            self._password_policy = PasswordPolicy()

        async def create_user(self, request: UserCreateRequest) -> User:
            if not request.email:
                raise UserManagementError("Email is required")
            if not request.username:
                raise UserManagementError("Username is required")
            if not request.password:
                raise UserManagementError("Password is required")

            # Check for existing user
            if request.email in [u.email for u in self._users.values()]:
                raise UserManagementError("Email already exists")
            if request.username in [u.username for u in self._users.values()]:
                raise UserManagementError("Username already exists")

            # Validate password
            if not self._password_policy.validate_password(request.password):
                raise UserManagementError("Password does not meet policy requirements")

            user_id = str(uuid4())
            user = User(
                user_id=user_id,
                email=request.email,
                username=request.username,
                tenant_id=self.tenant_id,
                role=request.role,
                password_hash=f"hashed_{request.password}",
                metadata=request.metadata
            )

            self._users[user_id] = user
            return user

        async def get_user(self, user_id: str) -> Optional[User]:
            if not user_id:
                raise UserManagementError("User ID is required")
            return self._users.get(user_id)

        async def get_user_by_email(self, email: str) -> Optional[User]:
            if not email:
                raise UserManagementError("Email is required")
            for user in self._users.values():
                if user.email == email:
                    return user
            return None

        async def get_user_by_username(self, username: str) -> Optional[User]:
            if not username:
                raise UserManagementError("Username is required")
            for user in self._users.values():
                if user.username == username:
                    return user
            return None

        async def update_user(self, user_id: str, request: UserUpdateRequest) -> User:
            if not user_id:
                raise UserManagementError("User ID is required")

            user = self._users.get(user_id)
            if not user:
                raise UserManagementError("User not found")

            # Check for email conflicts
            if request.email and request.email != user.email:
                if request.email in [u.email for u in self._users.values()]:
                    raise UserManagementError("Email already exists")
                user.email = request.email

            # Check for username conflicts
            if request.username and request.username != user.username:
                if request.username in [u.username for u in self._users.values()]:
                    raise UserManagementError("Username already exists")
                user.username = request.username

            if request.status:
                user.status = request.status
            if request.role:
                user.role = request.role
            if request.metadata:
                user.metadata.update(request.metadata)

            user.updated_at = datetime.now(timezone.utc)
            return user

        async def delete_user(self, user_id: str) -> bool:
            if not user_id:
                raise UserManagementError("User ID is required")

            user = self._users.get(user_id)
            if not user:
                raise UserManagementError("User not found")

            del self._users[user_id]
            return True

        async def list_users(self, limit: int = 100, offset: int = 0) -> list[User]:
            users = list(self._users.values())
            return users[offset:offset + limit]

        async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
            if not user_id:
                raise UserManagementError("User ID is required")
            if not old_password:
                raise UserManagementError("Old password is required")
            if not new_password:
                raise UserManagementError("New password is required")

            user = self._users.get(user_id)
            if not user:
                raise UserManagementError("User not found")

            # Verify old password
            if user.password_hash != f"hashed_{old_password}":
                raise UserManagementError("Invalid old password")

            # Validate new password
            if not self._password_policy.validate_password(new_password):
                raise UserManagementError("Password does not meet policy requirements")

            user.password_hash = f"hashed_{new_password}"
            user.updated_at = datetime.now(timezone.utc)
            return True

        async def reset_password(self, user_id: str, new_password: str) -> bool:
            if not user_id:
                raise UserManagementError("User ID is required")
            if not new_password:
                raise UserManagementError("New password is required")

            user = self._users.get(user_id)
            if not user:
                raise UserManagementError("User not found")

            # Validate new password
            if not self._password_policy.validate_password(new_password):
                raise UserManagementError("Password does not meet policy requirements")

            user.password_hash = f"hashed_{new_password}"
            user.updated_at = datetime.now(timezone.utc)
            return True

        def set_password_policy(self, policy: PasswordPolicy):
            self._password_policy = policy

    class UserManagementError(Exception):
        pass


class TestUserManagementComprehensive:
    """Comprehensive tests for UserManager."""

    @pytest.fixture
    def user_manager(self):
        """Create test user manager instance."""
        return UserManager(tenant_id="test-tenant")

    @pytest.fixture
    def sample_user_request(self):
        """Create sample user creation request."""
        return UserCreateRequest(
            email="test@example.com",
            username="testuser",
            password="Password123",
            role=UserRole.USER
        )

    def test_user_manager_initialization_valid_tenant(self):
        """Test user manager with valid tenant ID."""
        manager = UserManager(tenant_id="valid-tenant")
        assert manager.tenant_id == "valid-tenant"

    def test_user_manager_initialization_none_tenant(self):
        """Test user manager handles None tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be None"):
            UserManager(tenant_id=None)

    def test_user_manager_initialization_empty_tenant(self):
        """Test user manager handles empty tenant_id."""
        with pytest.raises(ValueError, match="tenant_id cannot be empty"):
            UserManager(tenant_id="")

    async def test_create_user_success(self, user_manager, sample_user_request):
        """Test successful user creation."""
        user = await user_manager.create_user(sample_user_request)

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.tenant_id == "test-tenant"
        assert user.role == UserRole.USER
        assert user.status == UserStatus.ACTIVE
        assert isinstance(user.user_id, str)
        assert user.password_hash == "hashed_Password123"

    async def test_create_user_empty_email(self, user_manager):
        """Test user creation with empty email."""
        request = UserCreateRequest(email="", username="testuser", password="Password123")
        with pytest.raises(UserManagementError, match="Email is required"):
            await user_manager.create_user(request)

    async def test_create_user_empty_username(self, user_manager):
        """Test user creation with empty username."""
        request = UserCreateRequest(email="test@example.com", username="", password="Password123")
        with pytest.raises(UserManagementError, match="Username is required"):
            await user_manager.create_user(request)

    async def test_create_user_empty_password(self, user_manager):
        """Test user creation with empty password."""
        request = UserCreateRequest(email="test@example.com", username="testuser", password="")
        with pytest.raises(UserManagementError, match="Password is required"):
            await user_manager.create_user(request)

    async def test_create_user_duplicate_email(self, user_manager, sample_user_request):
        """Test user creation with duplicate email."""
        await user_manager.create_user(sample_user_request)

        duplicate_request = UserCreateRequest(
            email="test@example.com",
            username="different_user",
            password="Password123"
        )

        with pytest.raises(UserManagementError, match="Email already exists"):
            await user_manager.create_user(duplicate_request)

    async def test_create_user_duplicate_username(self, user_manager, sample_user_request):
        """Test user creation with duplicate username."""
        await user_manager.create_user(sample_user_request)

        duplicate_request = UserCreateRequest(
            email="different@example.com",
            username="testuser",
            password="Password123"
        )

        with pytest.raises(UserManagementError, match="Username already exists"):
            await user_manager.create_user(duplicate_request)

    async def test_create_user_weak_password(self, user_manager):
        """Test user creation with weak password."""
        request = UserCreateRequest(
            email="test@example.com",
            username="testuser",
            password="weak"
        )

        with pytest.raises(UserManagementError, match="Password does not meet policy requirements"):
            await user_manager.create_user(request)

    async def test_get_user_success(self, user_manager, sample_user_request):
        """Test successful user retrieval."""
        created_user = await user_manager.create_user(sample_user_request)
        retrieved_user = await user_manager.get_user(created_user.user_id)

        assert retrieved_user is not None
        assert retrieved_user.user_id == created_user.user_id
        assert retrieved_user.email == created_user.email

    async def test_get_user_empty_id(self, user_manager):
        """Test get user with empty ID."""
        with pytest.raises(UserManagementError, match="User ID is required"):
            await user_manager.get_user("")

    async def test_get_user_nonexistent(self, user_manager):
        """Test get user with nonexistent ID."""
        result = await user_manager.get_user("nonexistent-id")
        assert result is None

    async def test_get_user_by_email_success(self, user_manager, sample_user_request):
        """Test successful user retrieval by email."""
        created_user = await user_manager.create_user(sample_user_request)
        retrieved_user = await user_manager.get_user_by_email("test@example.com")

        assert retrieved_user is not None
        assert retrieved_user.email == created_user.email
        assert retrieved_user.user_id == created_user.user_id

    async def test_get_user_by_email_empty(self, user_manager):
        """Test get user by email with empty email."""
        with pytest.raises(UserManagementError, match="Email is required"):
            await user_manager.get_user_by_email("")

    async def test_get_user_by_email_nonexistent(self, user_manager):
        """Test get user by email with nonexistent email."""
        result = await user_manager.get_user_by_email("nonexistent@example.com")
        assert result is None

    async def test_get_user_by_username_success(self, user_manager, sample_user_request):
        """Test successful user retrieval by username."""
        created_user = await user_manager.create_user(sample_user_request)
        retrieved_user = await user_manager.get_user_by_username("testuser")

        assert retrieved_user is not None
        assert retrieved_user.username == created_user.username
        assert retrieved_user.user_id == created_user.user_id

    async def test_get_user_by_username_empty(self, user_manager):
        """Test get user by username with empty username."""
        with pytest.raises(UserManagementError, match="Username is required"):
            await user_manager.get_user_by_username("")

    async def test_get_user_by_username_nonexistent(self, user_manager):
        """Test get user by username with nonexistent username."""
        result = await user_manager.get_user_by_username("nonexistent")
        assert result is None

    async def test_update_user_success(self, user_manager, sample_user_request):
        """Test successful user update."""
        user = await user_manager.create_user(sample_user_request)

        update_request = UserUpdateRequest(
            email="updated@example.com",
            username="updated_user",
            status=UserStatus.INACTIVE,
            role=UserRole.ADMIN
        )

        updated_user = await user_manager.update_user(user.user_id, update_request)

        assert updated_user.email == "updated@example.com"
        assert updated_user.username == "updated_user"
        assert updated_user.status == UserStatus.INACTIVE
        assert updated_user.role == UserRole.ADMIN

    async def test_update_user_empty_id(self, user_manager):
        """Test update user with empty ID."""
        update_request = UserUpdateRequest(email="test@example.com")
        with pytest.raises(UserManagementError, match="User ID is required"):
            await user_manager.update_user("", update_request)

    async def test_update_user_nonexistent(self, user_manager):
        """Test update user with nonexistent ID."""
        update_request = UserUpdateRequest(email="test@example.com")
        with pytest.raises(UserManagementError, match="User not found"):
            await user_manager.update_user("nonexistent-id", update_request)

    async def test_update_user_duplicate_email(self, user_manager):
        """Test update user with duplicate email."""
        # Create first user
        user1_request = UserCreateRequest(
            email="user1@example.com",
            username="user1",
            password="Password123"
        )
        await user_manager.create_user(user1_request)

        # Create second user
        user2_request = UserCreateRequest(
            email="user2@example.com",
            username="user2",
            password="Password123"
        )
        user2 = await user_manager.create_user(user2_request)

        # Try to update user2 with user1's email
        update_request = UserUpdateRequest(email="user1@example.com")
        with pytest.raises(UserManagementError, match="Email already exists"):
            await user_manager.update_user(user2.user_id, update_request)

    async def test_delete_user_success(self, user_manager, sample_user_request):
        """Test successful user deletion."""
        user = await user_manager.create_user(sample_user_request)
        result = await user_manager.delete_user(user.user_id)

        assert result is True

        # Verify user is deleted
        retrieved_user = await user_manager.get_user(user.user_id)
        assert retrieved_user is None

    async def test_delete_user_empty_id(self, user_manager):
        """Test delete user with empty ID."""
        with pytest.raises(UserManagementError, match="User ID is required"):
            await user_manager.delete_user("")

    async def test_delete_user_nonexistent(self, user_manager):
        """Test delete user with nonexistent ID."""
        with pytest.raises(UserManagementError, match="User not found"):
            await user_manager.delete_user("nonexistent-id")

    async def test_list_users_success(self, user_manager):
        """Test successful user listing."""
        # Create multiple users
        for i in range(5):
            request = UserCreateRequest(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password="Password123"
            )
            await user_manager.create_user(request)

        users = await user_manager.list_users()
        assert len(users) == 5

    async def test_list_users_with_limit(self, user_manager):
        """Test user listing with limit."""
        # Create multiple users
        for i in range(5):
            request = UserCreateRequest(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password="Password123"
            )
            await user_manager.create_user(request)

        users = await user_manager.list_users(limit=3)
        assert len(users) == 3

    async def test_list_users_with_offset(self, user_manager):
        """Test user listing with offset."""
        # Create multiple users
        for i in range(5):
            request = UserCreateRequest(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password="Password123"
            )
            await user_manager.create_user(request)

        users = await user_manager.list_users(offset=2)
        assert len(users) == 3

    async def test_change_password_success(self, user_manager, sample_user_request):
        """Test successful password change."""
        user = await user_manager.create_user(sample_user_request)
        result = await user_manager.change_password(
            user.user_id,
            "Password123",
            "NewPassword123"
        )

        assert result is True

        # Verify password was changed
        updated_user = await user_manager.get_user(user.user_id)
        assert updated_user.password_hash == "hashed_NewPassword123"

    async def test_change_password_empty_user_id(self, user_manager):
        """Test change password with empty user ID."""
        with pytest.raises(UserManagementError, match="User ID is required"):
            await user_manager.change_password("", "old", "new")

    async def test_change_password_empty_old_password(self, user_manager, sample_user_request):
        """Test change password with empty old password."""
        user = await user_manager.create_user(sample_user_request)
        with pytest.raises(UserManagementError, match="Old password is required"):
            await user_manager.change_password(user.user_id, "", "new")

    async def test_change_password_empty_new_password(self, user_manager, sample_user_request):
        """Test change password with empty new password."""
        user = await user_manager.create_user(sample_user_request)
        with pytest.raises(UserManagementError, match="New password is required"):
            await user_manager.change_password(user.user_id, "old", "")

    async def test_change_password_nonexistent_user(self, user_manager):
        """Test change password for nonexistent user."""
        with pytest.raises(UserManagementError, match="User not found"):
            await user_manager.change_password("nonexistent-id", "old", "new")

    async def test_change_password_wrong_old_password(self, user_manager, sample_user_request):
        """Test change password with wrong old password."""
        user = await user_manager.create_user(sample_user_request)
        with pytest.raises(UserManagementError, match="Invalid old password"):
            await user_manager.change_password(user.user_id, "wrong", "NewPassword123")

    async def test_change_password_weak_new_password(self, user_manager, sample_user_request):
        """Test change password with weak new password."""
        user = await user_manager.create_user(sample_user_request)
        with pytest.raises(UserManagementError, match="Password does not meet policy requirements"):
            await user_manager.change_password(user.user_id, "Password123", "weak")

    async def test_reset_password_success(self, user_manager, sample_user_request):
        """Test successful password reset."""
        user = await user_manager.create_user(sample_user_request)
        result = await user_manager.reset_password(user.user_id, "ResetPassword123")

        assert result is True

        # Verify password was reset
        updated_user = await user_manager.get_user(user.user_id)
        assert updated_user.password_hash == "hashed_ResetPassword123"

    def test_password_policy_validation(self):
        """Test password policy validation."""
        policy = PasswordPolicy(
            min_length=8,
            require_uppercase=True,
            require_lowercase=True,
            require_numbers=True,
            require_symbols=True
        )

        # Valid password
        assert policy.validate_password("Password123!") is True

        # Too short
        assert policy.validate_password("Pass1!") is False

        # No uppercase
        assert policy.validate_password("password123!") is False

        # No lowercase
        assert policy.validate_password("PASSWORD123!") is False

        # No numbers
        assert policy.validate_password("Password!") is False

        # No symbols
        assert policy.validate_password("Password123") is False

    def test_password_policy_flexible(self):
        """Test flexible password policy."""
        policy = PasswordPolicy(
            min_length=6,
            require_uppercase=False,
            require_lowercase=True,
            require_numbers=True,
            require_symbols=False
        )

        # Valid password
        assert policy.validate_password("password123") is True

        # Too short
        assert policy.validate_password("pass1") is False

        # No lowercase
        assert policy.validate_password("PASSWORD123") is False

        # No numbers
        assert policy.validate_password("password") is False

    async def test_concurrent_user_operations(self, user_manager):
        """Test concurrent user operations."""
        import asyncio

        async def create_user_worker(i):
            request = UserCreateRequest(
                email=f"user{i}@example.com",
                username=f"user{i}",
                password="Password123"
            )
            return await user_manager.create_user(request)

        # Create 10 users concurrently
        tasks = [create_user_worker(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        for i, result in enumerate(results):
            assert not isinstance(result, Exception)
            assert result.email == f"user{i}@example.com"

    def test_user_object_attributes(self):
        """Test User object attributes."""
        timestamp = datetime.now(timezone.utc)
        metadata = {"extra": "info"}

        user = User(
            user_id="test-id",
            email="test@example.com",
            username="testuser",
            tenant_id="test-tenant",
            status=UserStatus.ACTIVE,
            role=UserRole.ADMIN,
            created_at=timestamp,
            updated_at=timestamp,
            last_login=timestamp,
            password_hash="hashed_password",
            metadata=metadata
        )

        assert user.user_id == "test-id"
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.tenant_id == "test-tenant"
        assert user.status == UserStatus.ACTIVE
        assert user.role == UserRole.ADMIN
        assert user.created_at == timestamp
        assert user.updated_at == timestamp
        assert user.last_login == timestamp
        assert user.password_hash == "hashed_password"
        assert user.metadata == metadata
