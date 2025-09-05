"""
Integration tests for user management v2 authentication system.
Tests the complete authentication flow including login, MFA, sessions, and API keys.
"""
from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from dotmac_management.user_management.models.user_models import UserModel
from dotmac_management.user_management.schemas.auth_schemas import (
    APIKeyCreateRequestSchema,
    MFASetupRequestSchema,
    MFAType,
    PasswordChangeRequestSchema,
)
from dotmac_management.user_management.schemas.user_schemas import UserCreateSchema, UserType
from dotmac_management.user_management.services.user_service import UserService
from dotmac_shared.database.session import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for testing."""
    async with get_db_session() as session:
        yield session

@pytest.fixture
async def tenant_id() -> UUID:
    """Generate test tenant ID."""
    return uuid4()

@pytest.fixture
async def test_user_data() -> UserCreateSchema:
    """Create test user data."""
    return UserCreateSchema(
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type=UserType.CUSTOMER,
        password="SecurePass123!",
        terms_accepted=True,
        privacy_accepted=True
    )

@pytest.fixture
async def test_user(
    db_session: AsyncSession, 
    tenant_id: UUID, 
    test_user_data: UserCreateSchema
) -> UserModel:
    """Create test user in database."""
    user_service = UserService(db_session, tenant_id)
    user_response = await user_service.create_user(test_user_data)
    
    # Get the actual UserModel from database
    user = await user_service.user_repo.get_by_id(user_response.id)
    return user

class TestAuthenticationFlow:
    """Test complete authentication workflows."""
    
    async def test_successful_login_without_mfa(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test successful login without MFA."""
        auth_service = AuthService(db_session, tenant_id)
        
        # Attempt login
        result = await auth_service.authenticate_user(
            username=test_user.username,
            password="SecurePass123!",
            client_ip="127.0.0.1",
            user_agent="Test Client",
            device_fingerprint="test-device-123"
        )
        
        # Verify successful authentication
        assert result.success is True
        assert result.requires_mfa is False
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.session_id is not None
        assert result.user_id == test_user.id
        assert result.expires_at is not None

    async def test_failed_login_invalid_password(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test failed login with invalid password."""
        auth_service = AuthService(db_session, tenant_id)
        
        result = await auth_service.authenticate_user(
            username=test_user.username,
            password="WrongPassword",
            client_ip="127.0.0.1"
        )
        
        assert result.success is False
        assert result.error_code == "INVALID_CREDENTIALS"
        assert result.access_token is None

    async def test_failed_login_nonexistent_user(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID
    ):
        """Test failed login with nonexistent user."""
        auth_service = AuthService(db_session, tenant_id)
        
        result = await auth_service.authenticate_user(
            username="nonexistent@example.com",
            password="password",
            client_ip="127.0.0.1"
        )
        
        assert result.success is False
        assert result.error_code == "INVALID_CREDENTIALS"

    async def test_login_with_email(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test login using email instead of username."""
        auth_service = AuthService(db_session, tenant_id)
        
        result = await auth_service.authenticate_user(
            username=test_user.email,
            password="SecurePass123!",
            client_ip="127.0.0.1"
        )
        
        assert result.success is True
        assert result.user_id == test_user.id

class TestMFAFlow:
    """Test Multi-Factor Authentication workflows."""
    
    async def test_mfa_setup_and_verification(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test complete MFA setup and verification flow."""
        auth_service = AuthService(db_session, tenant_id)
        
        # Setup MFA
        setup_request = MFASetupRequestSchema(
            mfa_type=MFAType.TOTP,
            device_name="Test Authenticator"
        )
        
        setup_response = await auth_service.setup_mfa(test_user.id, setup_request)
        
        assert setup_response.qr_code is not None
        assert setup_response.manual_entry_key is not None
        assert len(setup_response.backup_codes) == 10
        assert "verify MFA setup" in setup_response.message
        
        # Simulate TOTP code generation (in real scenario, user would use authenticator app)
        import pyotp
        totp = pyotp.TOTP(setup_response.manual_entry_key)
        mfa_code = totp.now()
        
        # Verify MFA setup
        verification_success = await auth_service.verify_mfa_setup(test_user.id, mfa_code)
        assert verification_success is True

    async def test_login_with_mfa_required(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test login flow when MFA is required."""
        auth_service = AuthService(db_session, tenant_id)
        
        # First setup and enable MFA
        setup_request = MFASetupRequestSchema(
            mfa_type=MFAType.TOTP,
            device_name="Test Authenticator"
        )
        setup_response = await auth_service.setup_mfa(test_user.id, setup_request)
        
        import pyotp
        totp = pyotp.TOTP(setup_response.manual_entry_key)
        mfa_code = totp.now()
        await auth_service.verify_mfa_setup(test_user.id, mfa_code)
        
        # Now attempt login - should require MFA
        login_result = await auth_service.authenticate_user(
            username=test_user.username,
            password="SecurePass123!",
            client_ip="127.0.0.1"
        )
        
        assert login_result.success is True
        assert login_result.requires_mfa is True
        assert login_result.temp_token is not None
        assert login_result.access_token is None  # No full access yet
        
        # Complete MFA verification
        new_mfa_code = totp.now()
        final_result = await auth_service.verify_mfa_and_complete_login(
            temp_token=login_result.temp_token,
            mfa_code=new_mfa_code,
            client_ip="127.0.0.1"
        )
        
        assert final_result.success is True
        assert final_result.access_token is not None
        assert final_result.refresh_token is not None

class TestSessionManagement:
    """Test session management functionality."""
    
    async def test_session_creation_and_validation(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test session creation and validation."""
        auth_service = AuthService(db_session, tenant_id)
        
        # Login to create session
        result = await auth_service.authenticate_user(
            username=test_user.username,
            password="SecurePass123!",
            client_ip="127.0.0.1",
            user_agent="Test Client",
            device_fingerprint="test-device-123"
        )
        
        assert result.session_id is not None
        
        # Verify session exists and is active
        session = await auth_service.session_repo.get_active_session(result.session_id)
        assert session is not None
        assert session.user_id == test_user.id
        assert session.client_ip == "127.0.0.1"
        assert session.user_agent == "Test Client"
        assert session.device_fingerprint == "test-device-123"

    async def test_logout_invalidates_session(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test that logout properly invalidates session."""
        auth_service = AuthService(db_session, tenant_id)
        
        # Login
        result = await auth_service.authenticate_user(
            username=test_user.username,
            password="SecurePass123!",
            client_ip="127.0.0.1"
        )
        
        session_id = result.session_id
        
        # Verify session is active
        session = await auth_service.session_repo.get_active_session(session_id)
        assert session is not None
        
        # Logout
        logout_success = await auth_service.logout_user(session_id, "127.0.0.1")
        assert logout_success is True
        
        # Verify session is no longer active
        session = await auth_service.session_repo.get_active_session(session_id)
        assert session is None

    async def test_refresh_token_functionality(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test refresh token generation and usage."""
        auth_service = AuthService(db_session, tenant_id)
        
        # Login
        result = await auth_service.authenticate_user(
            username=test_user.username,
            password="SecurePass123!",
            client_ip="127.0.0.1"
        )
        
        original_refresh_token = result.refresh_token
        assert original_refresh_token is not None
        
        # Use refresh token to get new tokens
        new_tokens = await auth_service.refresh_token(original_refresh_token)
        assert new_tokens is not None
        
        new_access_token, new_refresh_token = new_tokens
        assert new_access_token is not None
        assert new_refresh_token is not None
        assert new_refresh_token != original_refresh_token

class TestPasswordManagement:
    """Test password change functionality."""
    
    async def test_successful_password_change(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test successful password change."""
        auth_service = AuthService(db_session, tenant_id)
        
        # Change password
        change_request = PasswordChangeRequestSchema(
            current_password="SecurePass123!",
            new_password="NewSecurePass456!",
            confirm_password="NewSecurePass456!",
            keep_current_session=False
        )
        
        success = await auth_service.change_password(
            user_id=test_user.id,
            request=change_request,
            client_ip="127.0.0.1"
        )
        
        assert success is True
        
        # Verify old password no longer works
        old_result = await auth_service.authenticate_user(
            username=test_user.username,
            password="SecurePass123!",
            client_ip="127.0.0.1"
        )
        
        assert old_result.success is False
        
        # Verify new password works
        new_result = await auth_service.authenticate_user(
            username=test_user.username,
            password="NewSecurePass456!",
            client_ip="127.0.0.1"
        )
        
        assert new_result.success is True

    async def test_password_change_invalid_current_password(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test password change with invalid current password."""
        auth_service = AuthService(db_session, tenant_id)
        
        change_request = PasswordChangeRequestSchema(
            current_password="WrongPassword",
            new_password="NewSecurePass456!",
            confirm_password="NewSecurePass456!",
            keep_current_session=False
        )
        
        success = await auth_service.change_password(
            user_id=test_user.id,
            request=change_request,
            client_ip="127.0.0.1"
        )
        
        assert success is False

class TestAPIKeyManagement:
    """Test API key creation and management."""
    
    async def test_api_key_creation(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test API key creation."""
        auth_service = AuthService(db_session, tenant_id)
        
        create_request = APIKeyCreateRequestSchema(
            name="Test API Key",
            expires_in_days=30,
            permissions=["read:users", "write:users"]
        )
        
        api_key_response = await auth_service.create_api_key(
            user_id=test_user.id,
            request=create_request
        )
        
        assert api_key_response.id is not None
        assert api_key_response.name == "Test API Key"
        assert api_key_response.key.startswith("dmac_")
        assert api_key_response.expires_at is not None
        assert api_key_response.permissions == ["read:users", "write:users"]

    async def test_api_key_without_expiry(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test API key creation without expiry."""
        auth_service = AuthService(db_session, tenant_id)
        
        create_request = APIKeyCreateRequestSchema(
            name="Permanent API Key",
            permissions=["read:data"]
        )
        
        api_key_response = await auth_service.create_api_key(
            user_id=test_user.id,
            request=create_request
        )
        
        assert api_key_response.expires_at is None

class TestAccountSecurity:
    """Test account security features."""
    
    async def test_account_lockout_after_failed_attempts(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test account lockout after multiple failed login attempts."""
        auth_service = AuthService(db_session, tenant_id)
        
        # Make multiple failed attempts
        for _ in range(6):  # More than max_failed_attempts (5)
            result = await auth_service.authenticate_user(
                username=test_user.username,
                password="WrongPassword",
                client_ip="127.0.0.1"
            )
            assert result.success is False
        
        # Next attempt should be locked
        result = await auth_service.authenticate_user(
            username=test_user.username,
            password="SecurePass123!",  # Even with correct password
            client_ip="127.0.0.1"
        )
        
        assert result.success is False
        assert result.error_code == "ACCOUNT_LOCKED"

    async def test_audit_trail_logging(
        self, 
        db_session: AsyncSession, 
        tenant_id: UUID, 
        test_user: UserModel
    ):
        """Test that authentication events are logged for audit trail."""
        auth_service = AuthService(db_session, tenant_id)
        
        # Perform successful login
        await auth_service.authenticate_user(
            username=test_user.username,
            password="SecurePass123!",
            client_ip="127.0.0.1"
        )
        
        # Check audit logs
        audit_events = await auth_service.audit_repo.get_user_events(
            user_id=test_user.id,
            limit=10
        )
        
        assert len(audit_events) > 0
        
        # Find login success event
        login_events = [e for e in audit_events if e.event_type == "LOGIN_SUCCESS"]
        assert len(login_events) > 0
        
        login_event = login_events[0]
        assert login_event.user_id == test_user.id
        assert login_event.client_ip == "127.0.0.1"

class TestTenantIsolation:
    """Test tenant isolation in authentication."""
    
    async def test_cross_tenant_login_isolation(
        self, 
        db_session: AsyncSession
    ):
        """Test that users from different tenants are isolated."""
        tenant1_id = uuid4()
        tenant2_id = uuid4()
        
        # Create user in tenant 1
        user_service1 = UserService(db_session, tenant1_id)
        user_data = UserCreateSchema(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            user_type=UserType.CUSTOMER,
            password="SecurePass123!",
            terms_accepted=True,
            privacy_accepted=True
        )
        user1 = await user_service1.create_user(user_data)
        
        # Try to authenticate from tenant 2
        auth_service2 = AuthService(db_session, tenant2_id)
        result = await auth_service2.authenticate_user(
            username="testuser",
            password="SecurePass123!",
            client_ip="127.0.0.1"
        )
        
        # Should fail because user belongs to different tenant
        assert result.success is False
        assert result.error_code == "INVALID_CREDENTIALS"