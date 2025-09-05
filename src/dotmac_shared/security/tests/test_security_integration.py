"""
Comprehensive Security Integration Tests

Tests the complete security implementation including:
- OpenBao secrets policy with environment checks
- Hardened secret factory integration
- Unified CSRF strategy across portals
- Environment-specific security validation
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ...application.config import DeploymentContext, DeploymentMode
from ..environment_security_validator import EnvironmentSecurityValidator, SecuritySeverity, validate_portal_security
from ..hardened_secret_factory import HardenedSecretFactory, initialize_hardened_secrets

# Import security components
from ..secrets_policy import Environment, HardenedSecretsManager, OpenBaoClient, SecretsEnvironmentError, SecretType
from ..unified_csrf_strategy import (
    CSRFConfig,
    CSRFMode,
    CSRFTokenDelivery,
    UnifiedCSRFMiddleware,
    create_admin_portal_csrf_config,
    create_customer_portal_csrf_config,
)


class TestSecretsPolicy:
    """Test OpenBao secrets policy implementation."""

    def test_environment_detection(self):
        """Test environment detection from various sources."""

        # Test explicit environment
        manager = HardenedSecretsManager(Environment.PRODUCTION)
        assert manager.environment == Environment.PRODUCTION

        # Test development default
        manager = HardenedSecretsManager(Environment.DEVELOPMENT)
        assert manager.environment == Environment.DEVELOPMENT

    def test_production_vault_requirement(self):
        """Test that production requires OpenBao/Vault."""

        # Production without vault client should fail
        with pytest.raises(SecretsEnvironmentError):
            HardenedSecretsManager(Environment.PRODUCTION, vault_client=None)

    def test_development_fallback_allowed(self):
        """Test that development allows environment fallback."""

        # Development without vault should work
        manager = HardenedSecretsManager(Environment.DEVELOPMENT, vault_client=None)
        assert manager.fallback_store is not None

    @pytest.mark.asyncio
    async def test_secret_retrieval_with_policy_enforcement(self):
        """Test secret retrieval with policy enforcement."""

        # Mock vault client
        vault_client = Mock(spec=OpenBaoClient)
        vault_client.get_secret = AsyncMock(return_value="test_secret_value")
        vault_client.is_healthy = AsyncMock(return_value=True)

        manager = HardenedSecretsManager(Environment.PRODUCTION, vault_client=vault_client)

        # Test JWT secret retrieval
        secret_value = await manager.get_secret(SecretType.JWT_SECRET, "auth", "jwt_secret_key")

        assert secret_value == "test_secret_value"
        vault_client.get_secret.assert_called_with("auth", "jwt_secret_key")

    @pytest.mark.asyncio
    async def test_secret_storage_validation(self):
        """Test secret storage with policy validation."""

        vault_client = Mock(spec=OpenBaoClient)
        vault_client.put_secret = AsyncMock(return_value=True)
        vault_client.is_healthy = AsyncMock(return_value=True)

        manager = HardenedSecretsManager(Environment.PRODUCTION, vault_client=vault_client)

        # Test storing valid secret
        success = await manager.put_secret(
            SecretType.JWT_SECRET,
            "auth",
            "jwt_secret_key",
            "x" * 64,  # Valid length secret
        )

        assert success

        # Test storing invalid secret (too short)
        with pytest.raises(ValueError):
            await manager.put_secret(
                SecretType.JWT_SECRET,
                "auth",
                "jwt_secret_key",
                "short",  # Too short
            )

    @pytest.mark.asyncio
    async def test_environment_compliance_validation(self):
        """Test environment compliance validation."""

        # Production with healthy vault
        vault_client = Mock(spec=OpenBaoClient)
        vault_client.is_healthy = AsyncMock(return_value=True)

        manager = HardenedSecretsManager(Environment.PRODUCTION, vault_client=vault_client)

        compliance = await manager.validate_environment_compliance()
        assert compliance["compliant"] is True
        assert compliance["environment"] == "production"

        # Production with unhealthy vault
        vault_client.is_healthy = AsyncMock(return_value=False)
        compliance = await manager.validate_environment_compliance()
        assert compliance["compliant"] is False
        assert "Primary OpenBao store unhealthy" in compliance["violations"]


class TestHardenedSecretFactory:
    """Test hardened secret factory integration."""

    @pytest.mark.asyncio
    async def test_factory_initialization(self):
        """Test factory initialization with environment detection."""

        factory = HardenedSecretFactory()

        # Test with development context
        dev_context = DeploymentContext(mode=DeploymentMode.DEVELOPMENT)

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            await factory.initialize(dev_context)
            assert factory._secrets_manager is not None

    @pytest.mark.asyncio
    async def test_jwt_secret_retrieval(self):
        """Test JWT secret retrieval through factory."""

        factory = HardenedSecretFactory()

        # Mock the secrets manager
        mock_manager = AsyncMock()
        mock_manager.get_secret = AsyncMock(return_value="test_jwt_secret")
        mock_manager.environment = Environment.DEVELOPMENT
        factory._secrets_manager = mock_manager

        secret = await factory.get_jwt_secret()
        assert secret == "test_jwt_secret"

        mock_manager.get_secret.assert_called_with(SecretType.JWT_SECRET, "auth", "jwt_secret_key", None)

    @pytest.mark.asyncio
    async def test_database_credentials_retrieval(self):
        """Test database credentials retrieval through factory."""

        factory = HardenedSecretFactory()

        # Mock the secrets manager
        mock_manager = AsyncMock()
        mock_manager.get_secret = AsyncMock(side_effect=["test_db_password", "test_db_user"])
        mock_manager.environment = Environment.DEVELOPMENT
        factory._secrets_manager = mock_manager

        creds = await factory.get_database_credentials("main")

        assert creds["password"] == "test_db_password"
        assert creds["username"] == "test_db_user"

    @pytest.mark.asyncio
    async def test_production_enforcement(self):
        """Test that production requirements are enforced."""

        factory = HardenedSecretFactory()

        # Mock production environment with no vault
        mock_manager = AsyncMock()
        mock_manager.get_secret = AsyncMock(return_value=None)
        mock_manager.environment = Environment.PRODUCTION
        factory._secrets_manager = mock_manager

        # Should raise exception for missing secret in production
        with pytest.raises(SecretsEnvironmentError):
            await factory.get_jwt_secret()


class TestUnifiedCSRFStrategy:
    """Test unified CSRF strategy implementation."""

    def test_csrf_config_creation(self):
        """Test CSRF configuration creation for different portals."""

        # Admin portal config
        admin_config = create_admin_portal_csrf_config()
        assert admin_config.mode == CSRFMode.HYBRID
        assert admin_config.portal_name == "admin"
        assert admin_config.require_referer_check is True
        assert admin_config.cookie_samesite == "Strict"

        # Customer portal config
        customer_config = create_customer_portal_csrf_config()
        assert customer_config.mode == CSRFMode.HYBRID
        assert customer_config.portal_name == "customer"
        assert customer_config.cookie_samesite == "Lax"  # More permissive

    def test_csrf_token_generation(self):
        """Test CSRF token generation and validation."""

        from ..unified_csrf_strategy import CSRFToken

        token_generator = CSRFToken("test_secret_key")

        # Generate token
        token = token_generator.generate()
        assert len(token.split(":")) == 3  # timestamp:random:signature

        # Validate token
        is_valid = token_generator.validate(token)
        assert is_valid is True

        # Test invalid token
        invalid_token = "invalid:token:signature"
        is_valid = token_generator.validate(invalid_token)
        assert is_valid is False

    def test_csrf_token_binding(self):
        """Test CSRF token session/user binding."""

        from ..unified_csrf_strategy import CSRFToken

        token_generator = CSRFToken("test_secret_key")

        # Generate token with binding
        session_id = "session_123"
        user_id = "user_456"

        token = token_generator.generate(session_id=session_id, user_id=user_id)

        # Validate with correct binding
        is_valid = token_generator.validate(token, session_id=session_id, user_id=user_id)
        assert is_valid is True

        # Validate with incorrect binding
        is_valid = token_generator.validate(token, session_id="wrong_session", user_id=user_id)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_csrf_middleware_integration(self):
        """Test CSRF middleware integration."""

        config = create_admin_portal_csrf_config()
        middleware = UnifiedCSRFMiddleware(None, config)

        # Mock request and response
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url.path = "/api/admin/test"
        mock_request.headers = {"X-CSRF-Token": "valid_token"}
        mock_request.cookies = {}
        mock_request.client.host = "127.0.0.1"

        mock_call_next = AsyncMock()
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.set_cookie = Mock()
        mock_call_next.return_value = mock_response

        # Mock token validation
        with patch.object(middleware.token_generator, "validate", return_value=True):
            result = await middleware.dispatch(mock_request, mock_call_next)
            assert result == mock_response


class TestEnvironmentSecurityValidator:
    """Test environment-specific security validation."""

    def test_validator_creation(self):
        """Test security validator creation."""

        validator = EnvironmentSecurityValidator(Environment.PRODUCTION, portal_name="admin")

        assert validator.environment == Environment.PRODUCTION
        assert validator.portal_name == "admin"
        assert validator.requirements["secrets_management"]["vault_required"] is True

    def test_production_requirements(self):
        """Test production security requirements."""

        validator = EnvironmentSecurityValidator(Environment.PRODUCTION)
        reqs = validator.requirements

        # Production should require strict security
        assert reqs["secrets_management"]["vault_required"] is True
        assert reqs["csrf_protection"]["required"] is True
        assert reqs["csrf_protection"]["strict_mode"] is True
        assert reqs["rate_limiting"]["required"] is True
        assert reqs["security_headers"]["required"] is True

    def test_development_requirements(self):
        """Test development security requirements."""

        validator = EnvironmentSecurityValidator(Environment.DEVELOPMENT)
        reqs = validator.requirements

        # Development should be more relaxed
        assert reqs["secrets_management"]["vault_required"] is False
        assert reqs["csrf_protection"]["required"] is False
        assert reqs["rate_limiting"]["required"] is False
        assert reqs["security_headers"]["required"] is False

    @pytest.mark.asyncio
    async def test_comprehensive_security_validation(self):
        """Test comprehensive security validation."""

        validator = EnvironmentSecurityValidator(Environment.DEVELOPMENT, portal_name="test")

        # Mock secrets manager
        mock_secrets_manager = AsyncMock()
        mock_secrets_manager.validate_environment_compliance = AsyncMock(
            return_value={"compliant": True, "violations": [], "store_status": {"primary": {"healthy": True}}}
        )

        # Mock CSRF config
        csrf_config = CSRFConfig(mode=CSRFMode.HYBRID, portal_name="test")

        # Run validation
        result = await validator.validate_comprehensive_security(
            secrets_manager=mock_secrets_manager, csrf_config=csrf_config
        )

        assert result.environment == Environment.DEVELOPMENT
        assert isinstance(result.security_score, float)
        assert result.security_score >= 0.0

    @pytest.mark.asyncio
    async def test_production_compliance_violations(self):
        """Test detection of production compliance violations."""

        validator = EnvironmentSecurityValidator(Environment.PRODUCTION, portal_name="admin")

        # Test without secrets manager (should be violation)
        result = await validator.validate_comprehensive_security()

        critical_violations = result.get_violations_by_severity(SecuritySeverity.CRITICAL)
        assert len(critical_violations) > 0
        assert any("secrets manager" in v.message.lower() for v in critical_violations)

    @pytest.mark.asyncio
    async def test_portal_specific_validation(self):
        """Test portal-specific security validation."""

        # Test different portal types
        portal_types = ["admin", "customer", "management", "reseller", "technician"]

        for portal_type in portal_types:
            result = await validate_portal_security(portal_type=portal_type, environment=Environment.DEVELOPMENT)

            assert result.environment == Environment.DEVELOPMENT
            assert isinstance(result.security_score, float)


class TestSecurityIntegration:
    """Test complete security system integration."""

    @pytest.mark.asyncio
    async def test_full_security_stack_initialization(self):
        """Test full security stack initialization."""

        # Test development environment
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            # Initialize hardened secrets
            deployment_context = DeploymentContext(mode=DeploymentMode.DEVELOPMENT)
            await initialize_hardened_secrets(deployment_context)

            # Create CSRF config
            csrf_config = create_admin_portal_csrf_config()

            # Create security validator
            validator = EnvironmentSecurityValidator(
                Environment.DEVELOPMENT, portal_name="admin", deployment_context=deployment_context
            )

            # Validate security (should pass in development)
            result = await validator.validate_comprehensive_security(csrf_config=csrf_config)

            # Development should be compliant with relaxed requirements
            assert result.compliant is True or result.security_score > 50

    @pytest.mark.asyncio
    async def test_production_security_enforcement(self):
        """Test that production security is properly enforced."""

        # Mock production environment
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            # Test that missing vault causes failures
            validator = EnvironmentSecurityValidator(Environment.PRODUCTION, portal_name="admin")

            result = await validator.validate_comprehensive_security()

            # Should have critical violations in production without proper setup
            assert result.has_critical_violations()
            assert result.security_score < 50

    def test_security_configuration_consistency(self):
        """Test that security configurations are consistent across portals."""

        # All portal CSRF configs should have consistent security features
        configs = [
            create_admin_portal_csrf_config(),
            create_customer_portal_csrf_config(),
        ]

        for config in configs:
            # All should use hybrid mode for flexibility
            assert config.mode == CSRFMode.HYBRID

            # All should use both header and cookie delivery
            assert config.token_delivery == CSRFTokenDelivery.BOTH

            # Token lifetime should be reasonable (between 30 min and 4 hours)
            assert 1800 <= config.token_lifetime <= 14400

    def test_environment_security_tier_consistency(self):
        """Test that security tiers are consistent across environments."""

        environments = [Environment.PRODUCTION, Environment.STAGING, Environment.DEVELOPMENT]

        for env in environments:
            validator = EnvironmentSecurityValidator(env)
            reqs = validator.requirements

            if env == Environment.PRODUCTION:
                # Production should have strictest requirements
                assert reqs["secrets_management"]["vault_required"] is True
                assert reqs["csrf_protection"]["required"] is True
                assert reqs["rate_limiting"]["required"] is True

            elif env == Environment.DEVELOPMENT:
                # Development should be most relaxed
                assert reqs["secrets_management"]["vault_required"] is False
                assert reqs["csrf_protection"]["required"] is False

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Test consistent error handling across security components."""

        # Test secrets policy error handling
        with pytest.raises(SecretsEnvironmentError):
            HardenedSecretsManager(Environment.PRODUCTION, vault_client=None)

        # Test factory error handling
        factory = HardenedSecretFactory()
        factory._secrets_manager = None

        # Should handle uninitialized state gracefully
        try:
            await factory.get_jwt_secret()
        except (SecretsEnvironmentError, ValueError):
            # Expected error types
            pass

    def test_security_documentation_completeness(self):
        """Test that security implementation matches documentation."""

        # This test ensures our implementation aligns with the documented standards

        # Check that all documented secret types are implemented
        documented_secret_types = [
            SecretType.JWT_SECRET,
            SecretType.DATABASE_CREDENTIAL,
            SecretType.API_KEY,
            SecretType.ENCRYPTION_KEY,
        ]

        for secret_type in documented_secret_types:
            # Each type should have a policy
            manager = HardenedSecretsManager(Environment.DEVELOPMENT)
            assert secret_type in manager.DEFAULT_POLICIES

        # Check that all documented CSRF modes are implemented
        documented_csrf_modes = [CSRFMode.API_ONLY, CSRFMode.SSR_ONLY, CSRFMode.HYBRID]

        for mode in documented_csrf_modes:
            # Should be able to create config with each mode
            config = CSRFConfig(mode=mode)
            assert config.mode == mode


# Test fixtures and utilities


@pytest.fixture
def mock_vault_client():
    """Create a mock OpenBao/Vault client."""
    client = Mock(spec=OpenBaoClient)
    client.get_secret = AsyncMock(return_value="mock_secret")
    client.put_secret = AsyncMock(return_value=True)
    client.is_healthy = AsyncMock(return_value=True)
    return client


@pytest.fixture
def development_environment():
    """Set up development environment for tests."""
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
        yield


@pytest.fixture
def production_environment():
    """Set up production environment for tests."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        yield


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
