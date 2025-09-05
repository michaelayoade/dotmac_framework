"""
Unit tests for UserService.
Tests core user management business logic.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from dotmac_management.user_management.models.user_models import UserModel
from dotmac_management.user_management.schemas.user_schemas import (
    UserCreateSchema,
    UserStatus,
    UserType,
    UserUpdateSchema,
)
from dotmac_management.user_management.services.user_service import UserService
from dotmac_shared.core.exceptions import AuthorizationError, EntityNotFoundError, ValidationError


@pytest.fixture
async def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
async def mock_user_repo():
    """Mock user repository."""
    repo = AsyncMock()
    repo.check_username_available = AsyncMock(return_value=True)
    repo.check_email_available = AsyncMock(return_value=True)
    repo.create_user = AsyncMock()
    repo.get_by_id_or_raise = AsyncMock()
    repo.update = AsyncMock()
    repo.activate_user = AsyncMock()
    repo.search_users = AsyncMock()
    return repo


@pytest.fixture
async def user_service(mock_db_session, mock_user_repo):
    """Create UserService instance with mocked dependencies."""
    service = UserService(mock_db_session, tenant_id=uuid4())
    service.user_repo = mock_user_repo
    service.profile_repo = AsyncMock()
    return service


@pytest.fixture
def sample_user_create():
    """Sample user creation data."""
    return UserCreateSchema(
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type=UserType.CUSTOMER,
        password="SecurePass123!",
        terms_accepted=True,
        privacy_accepted=True,
        timezone="UTC",
        language="en"
    )


@pytest.fixture
def sample_user_model():
    """Sample user model instance."""
    return UserModel(
        id=uuid4(),
        username="testuser",
        email="test@example.com", 
        first_name="Test",
        last_name="User",
        user_type=UserType.CUSTOMER,
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


class TestUserCreation:
    """Test user creation functionality."""
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, sample_user_create, sample_user_model):
        """Test successful user creation."""
        # Arrange
        user_service.user_repo.create_user.return_value = sample_user_model
        
        with patch('dotmac_management.user_management.services.user_service.pwd_context') as mock_pwd:
            mock_pwd.hash.return_value = "hashed_password"
            
            # Act
            result = await user_service.create_user(sample_user_create)
            
            # Assert
            assert result is not None
            assert result.username == "testuser"
            assert result.email == "test@example.com"
            user_service.user_repo.check_username_available.assert_called_once_with("testuser")
            user_service.user_repo.check_email_available.assert_called_once_with("test@example.com")
            user_service.user_repo.create_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, user_service, sample_user_create):
        """Test user creation with duplicate username."""
        # Arrange
        user_service.user_repo.check_username_available.return_value = False
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Username is already taken"):
            await user_service.create_user(sample_user_create)
    
    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, user_service, sample_user_create):
        """Test user creation with duplicate email."""
        # Arrange
        user_service.user_repo.check_email_available.return_value = False
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Email address is already in use"):
            await user_service.create_user(sample_user_create)
    
    @pytest.mark.asyncio
    async def test_create_user_tenant_validation(self, user_service, sample_user_create):
        """Test user creation with tenant access validation."""
        # Arrange
        different_tenant_id = uuid4()
        sample_user_create.tenant_id = different_tenant_id
        
        # Act & Assert
        with pytest.raises(AuthorizationError, match="Cannot create user in different tenant"):
            await user_service.create_user(sample_user_create)


class TestUserRetrieval:
    """Test user retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_service, sample_user_model):
        """Test getting user by ID."""
        # Arrange
        user_id = sample_user_model.id
        user_service.user_repo.get_with_profile.return_value = sample_user_model
        
        # Act
        result = await user_service.get_user(user_id, include_profile=True)
        
        # Assert
        assert result is not None
        assert result.id == user_id
        user_service.user_repo.get_with_profile.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_service):
        """Test getting non-existent user."""
        # Arrange
        user_id = uuid4()
        user_service.user_repo.get_with_profile.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError, match=f"User not found with ID: {user_id}"):
            await user_service.get_user(user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_by_username(self, user_service, sample_user_model):
        """Test getting user by username."""
        # Arrange
        username = "testuser"
        user_service.user_repo.get_by_username.return_value = sample_user_model
        
        # Act
        result = await user_service.get_user_by_username(username)
        
        # Assert
        assert result is not None
        assert result.username == username
        user_service.user_repo.get_by_username.assert_called_once_with(username)
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_service, sample_user_model):
        """Test getting user by email."""
        # Arrange
        email = "test@example.com"
        user_service.user_repo.get_by_email.return_value = sample_user_model
        
        # Act
        result = await user_service.get_user_by_email(email)
        
        # Assert
        assert result is not None
        assert result.email == email
        user_service.user_repo.get_by_email.assert_called_once_with(email)


class TestUserUpdate:
    """Test user update functionality."""
    
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, sample_user_model):
        """Test successful user update."""
        # Arrange
        user_id = sample_user_model.id
        update_data = UserUpdateSchema(
            first_name="Updated",
            last_name="Name"
        )
        user_service.user_repo.get_by_id_or_raise.return_value = sample_user_model
        user_service.user_repo.update.return_value = sample_user_model
        
        # Act
        result = await user_service.update_user(user_id, update_data, user_id)
        
        # Assert
        assert result is not None
        user_service.user_repo.get_by_id_or_raise.assert_called_once_with(user_id)
        user_service.user_repo.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_email_validation(self, user_service, sample_user_model):
        """Test user update with email validation."""
        # Arrange
        user_id = sample_user_model.id
        new_email = "newemail@example.com"
        update_data = UserUpdateSchema(email=new_email)
        
        user_service.user_repo.get_by_id_or_raise.return_value = sample_user_model
        user_service.user_repo.check_email_available.return_value = True
        user_service.user_repo.update.return_value = sample_user_model
        
        # Act
        result = await user_service.update_user(user_id, update_data, user_id)
        
        # Assert
        assert result is not None
        user_service.user_repo.check_email_available.assert_called_once_with(new_email, user_id)
    
    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(self, user_service, sample_user_model):
        """Test user update with duplicate email."""
        # Arrange
        user_id = sample_user_model.id
        update_data = UserUpdateSchema(email="duplicate@example.com")
        
        user_service.user_repo.get_by_id_or_raise.return_value = sample_user_model
        user_service.user_repo.check_email_available.return_value = False
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Email address is already in use"):
            await user_service.update_user(user_id, update_data, user_id)


class TestUserStatusManagement:
    """Test user status management."""
    
    @pytest.mark.asyncio
    async def test_activate_user(self, user_service, sample_user_model):
        """Test user activation."""
        # Arrange
        user_id = sample_user_model.id
        admin_id = uuid4()
        sample_user_model.status = UserStatus.PENDING
        
        user_service.user_repo.get_by_id_or_raise.return_value = sample_user_model
        activated_user = sample_user_model
        activated_user.status = UserStatus.ACTIVE
        user_service.user_repo.activate_user.return_value = activated_user
        
        # Act
        result = await user_service.activate_user(user_id, admin_id)
        
        # Assert
        assert result is not None
        assert result.status == UserStatus.ACTIVE
        user_service.user_repo.activate_user.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_activate_already_active_user(self, user_service, sample_user_model):
        """Test activating already active user."""
        # Arrange
        user_id = sample_user_model.id
        admin_id = uuid4()
        sample_user_model.status = UserStatus.ACTIVE
        
        user_service.user_repo.get_by_id_or_raise.return_value = sample_user_model
        
        # Act & Assert
        from dotmac_shared.core.exceptions import BusinessRuleError
        with pytest.raises(BusinessRuleError, match="User is already active"):
            await user_service.activate_user(user_id, admin_id)
    
    @pytest.mark.asyncio
    async def test_deactivate_user(self, user_service, sample_user_model):
        """Test user deactivation."""
        # Arrange
        user_id = sample_user_model.id
        admin_id = uuid4()
        reason = "Policy violation"
        
        user_service.user_repo.get_by_id_or_raise.return_value = sample_user_model
        deactivated_user = sample_user_model
        deactivated_user.status = UserStatus.INACTIVE
        user_service.user_repo.deactivate_user.return_value = deactivated_user
        
        # Act
        result = await user_service.deactivate_user(user_id, admin_id, reason)
        
        # Assert
        assert result is not None
        user_service.user_repo.deactivate_user.assert_called_once_with(user_id, reason)
    
    @pytest.mark.asyncio
    async def test_suspend_user(self, user_service, sample_user_model):
        """Test user suspension."""
        # Arrange
        user_id = sample_user_model.id
        admin_id = uuid4()
        reason = "Security concern"
        duration = 7
        
        user_service.user_repo.get_by_id_or_raise.return_value = sample_user_model
        suspended_user = sample_user_model
        suspended_user.status = UserStatus.SUSPENDED
        user_service.user_repo.suspend_user.return_value = suspended_user
        
        # Act
        result = await user_service.suspend_user(user_id, admin_id, reason, duration)
        
        # Assert
        assert result is not None
        user_service.user_repo.suspend_user.assert_called_once_with(user_id, reason, admin_id)


class TestUserSearch:
    """Test user search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_users(self, user_service, sample_user_model):
        """Test user search."""
        # Arrange
        from dotmac_management.user_management.schemas.user_schemas import UserSearchSchema
        search_params = UserSearchSchema(
            query="test",
            page=1,
            page_size=20
        )
        
        users = [sample_user_model]
        total_count = 1
        user_service.user_repo.search_users.return_value = (users, total_count)
        
        # Act
        result_users, result_count = await user_service.search_users(search_params)
        
        # Assert
        assert len(result_users) == 1
        assert result_count == 1
        user_service.user_repo.search_users.assert_called_once()


class TestUserValidation:
    """Test user validation methods."""
    
    @pytest.mark.asyncio
    async def test_validate_user_creation_super_admin(self, user_service):
        """Test validation of super admin user creation."""
        # Arrange
        user_data = UserCreateSchema(
            username="admin",
            email="admin@example.com",
            first_name="Admin",
            last_name="User", 
            user_type=UserType.SUPER_ADMIN,
            password="SecurePass123!",
            terms_accepted=True,
            privacy_accepted=True
        )
        
        # Act - This should not raise an exception in the base case
        # In a real implementation, this would check current user permissions
        await user_service._validate_user_creation(user_data)
        
        # Assert - No exception raised
        assert True


class TestBulkOperations:
    """Test bulk user operations."""
    
    @pytest.mark.asyncio
    async def test_bulk_activate_users(self, user_service):
        """Test bulk user activation."""
        # Arrange
        from dotmac_management.user_management.schemas.user_schemas import UserBulkOperationSchema
        user_ids = [uuid4(), uuid4(), uuid4()]
        
        operation_data = UserBulkOperationSchema(
            user_ids=user_ids,
            operation="activate"
        )
        admin_id = uuid4()
        
        # Mock repository responses
        users = [UserModel(id=uid, tenant_id=user_service.tenant_id) for uid in user_ids]
        for i, user_id in enumerate(user_ids):
            user_service.user_repo.get_by_id.return_value = users[i]
        
        user_service.user_repo.bulk_activate_users.return_value = len(user_ids)
        
        # Act
        result = await user_service.bulk_operation(operation_data, admin_id)
        
        # Assert
        assert result["success"] == len(user_ids)
        assert result["failed"] == 0
        user_service.user_repo.bulk_activate_users.assert_called_once_with(user_ids)


class TestUserStatistics:
    """Test user statistics functionality."""
    
    @pytest.mark.asyncio
    async def test_get_user_statistics(self, user_service):
        """Test getting user statistics."""
        # Arrange
        expected_stats = {
            "total_users": 100,
            "active_users": 85,
            "pending_users": 10,
            "locked_users": 3,
            "suspended_users": 2
        }
        user_service.user_repo.get_user_stats.return_value = expected_stats
        
        # Act
        result = await user_service.get_user_statistics()
        
        # Assert
        assert result == expected_stats
        user_service.user_repo.get_user_stats.assert_called_once_with(user_service.tenant_id)
    
    @pytest.mark.asyncio
    async def test_get_recent_users(self, user_service, sample_user_model):
        """Test getting recent users."""
        # Arrange
        limit = 5
        recent_users = [sample_user_model]
        user_service.user_repo.get_recent_users.return_value = recent_users
        
        # Act
        result = await user_service.get_recent_users(limit)
        
        # Assert
        assert len(result) == 1
        user_service.user_repo.get_recent_users.assert_called_once_with(limit, user_service.tenant_id)


class TestErrorHandling:
    """Test error handling in user service."""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, user_service, sample_user_create):
        """Test database error handling."""
        # Arrange
        user_service.user_repo.create_user.side_effect = Exception("Database connection failed")
        
        # Act & Assert
        with pytest.raises(ValidationError):
            await user_service.create_user(sample_user_create)
    
    @pytest.mark.asyncio
    async def test_tenant_access_validation(self, user_service, sample_user_model):
        """Test tenant access validation."""
        # Arrange
        different_tenant_id = uuid4()
        sample_user_model.tenant_id = different_tenant_id
        
        # Act & Assert
        with pytest.raises(AuthorizationError):
            user_service._validate_tenant_access(different_tenant_id, "test operation")


# === Integration Test Markers ===

@pytest.mark.integration
class TestUserServiceIntegration:
    """Integration tests for UserService with real database."""
    
    @pytest.mark.asyncio
    async def test_full_user_lifecycle(self):
        """Test complete user lifecycle from creation to deletion."""
        # This would test with real database connection
        # Implementation would depend on test database setup
        pass