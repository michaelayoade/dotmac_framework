"""
Comprehensive unit tests for the OpenBao/Vault secrets policy system.

Tests cover:
- Environment-specific enforcement
- Secret type policies
- OpenBao client integration
- Fallback mechanisms
- Error handling and validation
"""

import os
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from dotmac.secrets import (
    Environment,
    HardenedSecretsManager,
    OpenBaoClient,
    SecretAuditLog,
    SecretMetadata,
    SecretPolicy,
    SecretsEnvironmentError,
    SecretsRetrievalError,
    SecretsValidationError,
    SecretType,
)


class TestEnvironment:
    """Test Environment enum."""

    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.TESTING == "testing"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"

    def test_environment_string_conversion(self):
        """Test environment string conversion."""
        assert str(Environment.PRODUCTION) == "production"
        assert Environment("production") == Environment.PRODUCTION


class TestSecretType:
    """Test SecretType enum."""

    def test_secret_type_values(self):
        """Test secret type enum values."""
        assert SecretType.JWT_SECRET == "jwt_secret"
        assert SecretType.DATABASE_CREDENTIAL == "database_credential"
        assert SecretType.API_KEY == "api_key"
        assert SecretType.ENCRYPTION_KEY == "encryption_key"
        assert SecretType.OAUTH_SECRET == "oauth_secret"
        assert SecretType.WEBHOOK_SECRET == "webhook_secret"


class TestSecretPolicy:
    """Test SecretPolicy dataclass."""

    def test_default_policy(self):
        """Test default secret policy."""
        policy = SecretPolicy(SecretType.JWT_SECRET)
        assert policy.secret_type == SecretType.JWT_SECRET
        assert policy.requires_vault_in_production is True
        assert policy.allows_env_fallback_in_dev is True
        assert policy.min_rotation_days == 90
        assert policy.max_age_days == 365

    def test_custom_policy(self):
        """Test custom secret policy configuration."""
        policy = SecretPolicy(
            secret_type=SecretType.DATABASE_CREDENTIAL,
            requires_vault_in_production=True,
            allows_env_fallback_in_dev=False,
            min_rotation_days=30,
            max_age_days=180,
            encryption_required=True
        )
        assert policy.secret_type == SecretType.DATABASE_CREDENTIAL
        assert policy.requires_vault_in_production is True
        assert policy.allows_env_fallback_in_dev is False
        assert policy.min_rotation_days == 30
        assert policy.max_age_days == 180
        assert policy.encryption_required is True


class TestOpenBaoClient:
    """Test OpenBao client."""

    @pytest.fixture
    def mock_vault_url(self):
        return "http://vault.test:8200"

    @pytest.fixture
    def mock_token(self):
        return "test-vault-token-123"

    @pytest.fixture
    def client(self, mock_vault_url, mock_token):
        return OpenBaoClient(vault_url=mock_vault_url, token=mock_token)

    def test_client_initialization(self, client, mock_vault_url, mock_token):
        """Test OpenBao client initialization."""
        assert client.vault_url == mock_vault_url
        assert client.token == mock_token
        assert client.timeout == 30
        assert client.max_retries == 3

    def test_client_custom_config(self):
        """Test OpenBao client with custom configuration."""
        client = OpenBaoClient(
            vault_url="https://vault.prod:8200",
            token="prod-token",
            timeout=60,
            max_retries=5
        )
        assert client.vault_url == "https://vault.prod:8200"
        assert client.timeout == 60
        assert client.max_retries == 5

    @pytest.mark.asyncio
    async def test_get_secret_success(self, client):
        """Test successful secret retrieval."""
        mock_response = {
            "data": {
                "data": {
                    "secret_value": "test-jwt-secret-value"
                },
                "metadata": {
                    "version": 1,
                    "created_time": "2024-01-01T00:00:00Z"
                }
            }
        }

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            result = await client.get_secret("secret/test", "test_key")
            assert result == "test-jwt-secret-value"

    @pytest.mark.asyncio
    async def test_get_secret_not_found(self, client):
        """Test secret not found handling."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value.status_code = 404

            with pytest.raises(SecretsRetrievalError, match="Secret not found"):
                await client.get_secret("secret/nonexistent", "test_key")

    @pytest.mark.asyncio
    async def test_get_secret_network_error(self, client):
        """Test network error handling."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            with pytest.raises(SecretsRetrievalError, match="Failed to retrieve secret"):
                await client.get_secret("secret/test", "test_key")

    @pytest.mark.asyncio
    async def test_store_secret_success(self, client):
        """Test successful secret storage."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 200

            await client.store_secret("secret/test", "test_key", "test_value")
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        mock_response = {"sealed": False, "standby": False}

        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response

            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check failure."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value.status_code = 503

            result = await client.health_check()
            assert result is False


class TestHardenedSecretsManager:
    """Test HardenedSecretsManager."""

    @pytest.fixture
    def mock_vault_client(self):
        client = Mock(spec=OpenBaoClient)
        client.get_secret = AsyncMock()
        client.store_secret = AsyncMock()
        client.health_check = AsyncMock(return_value=True)
        return client

    def test_production_requires_vault(self):
        """Test that production environment requires vault client."""
        with pytest.raises(SecretsEnvironmentError, match="OpenBao/Vault client required in production"):
            HardenedSecretsManager(Environment.PRODUCTION, None)

    def test_development_allows_no_vault(self):
        """Test that development environment allows no vault client."""
        manager = HardenedSecretsManager(Environment.DEVELOPMENT, None)
        assert manager.environment == Environment.DEVELOPMENT
        assert manager.vault_client is None

    def test_staging_requires_vault(self, mock_vault_client):
        """Test that staging environment requires vault client."""
        with pytest.raises(SecretsEnvironmentError):
            HardenedSecretsManager(Environment.STAGING, None)

        # Should work with vault client
        manager = HardenedSecretsManager(Environment.STAGING, mock_vault_client)
        assert manager.environment == Environment.STAGING

    @pytest.mark.asyncio
    async def test_get_secret_production_with_vault(self, mock_vault_client):
        """Test secret retrieval in production with vault."""
        mock_vault_client.get_secret.return_value = "prod-jwt-secret"

        manager = HardenedSecretsManager(Environment.PRODUCTION, mock_vault_client)

        result = await manager.get_secret(
            SecretType.JWT_SECRET, "auth", "jwt_secret_key"
        )

        assert result == "prod-jwt-secret"
        mock_vault_client.get_secret.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_secret_development_fallback(self):
        """Test secret retrieval in development with env fallback."""
        with patch.dict(os.environ, {'AUTH_JWT_SECRET_KEY': 'dev-jwt-secret'}):
            manager = HardenedSecretsManager(Environment.DEVELOPMENT, None)

            result = await manager.get_secret(
                SecretType.JWT_SECRET, "auth", "jwt_secret_key"
            )

            assert result == "dev-jwt-secret"

    @pytest.mark.asyncio
    async def test_get_secret_development_no_fallback(self):
        """Test secret retrieval failure in development without fallback."""
        manager = HardenedSecretsManager(Environment.DEVELOPMENT, None)

        with pytest.raises(SecretsRetrievalError, match="Secret not found"):
            await manager.get_secret(
                SecretType.JWT_SECRET, "nonexistent", "missing_key"
            )

    @pytest.mark.asyncio
    async def test_get_secret_with_tenant_id(self, mock_vault_client):
        """Test secret retrieval with tenant ID."""
        tenant_id = uuid4()
        mock_vault_client.get_secret.return_value = "tenant-specific-secret"

        manager = HardenedSecretsManager(Environment.PRODUCTION, mock_vault_client)

        result = await manager.get_secret(
            SecretType.API_KEY, "billing", "stripe_key", tenant_id
        )

        assert result == "tenant-specific-secret"
        # Verify tenant-specific path was used
        call_args = mock_vault_client.get_secret.call_args
        assert str(tenant_id) in call_args[0][0]  # Path should contain tenant ID

    @pytest.mark.asyncio
    async def test_store_secret_production_only(self, mock_vault_client):
        """Test that secret storage only works in production environments."""
        manager = HardenedSecretsManager(Environment.PRODUCTION, mock_vault_client)

        await manager.store_secret(
            SecretType.JWT_SECRET, "auth", "jwt_key", "new-secret-value"
        )

        mock_vault_client.store_secret.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_secret_development_blocked(self):
        """Test that secret storage is blocked in development."""
        manager = HardenedSecretsManager(Environment.DEVELOPMENT, None)

        with pytest.raises(SecretsEnvironmentError, match="Secret storage not allowed"):
            await manager.store_secret(
                SecretType.JWT_SECRET, "auth", "jwt_key", "new-secret"
            )

    def test_validate_secret_strength_weak(self):
        """Test secret strength validation for weak secrets."""
        manager = HardenedSecretsManager(Environment.DEVELOPMENT, None)

        weak_secrets = ["123", "password", "abc", "test"]
        for weak_secret in weak_secrets:
            with pytest.raises(SecretsValidationError, match="Secret does not meet strength requirements"):
                manager.validate_secret_strength(weak_secret, SecretType.JWT_SECRET)

    def test_validate_secret_strength_strong(self):
        """Test secret strength validation for strong secrets."""
        manager = HardenedSecretsManager(Environment.DEVELOPMENT, None)

        strong_secret = "StrongSecret123!@#"
        # Should not raise exception
        manager.validate_secret_strength(strong_secret, SecretType.JWT_SECRET)

    @pytest.mark.asyncio
    async def test_rotate_secret(self, mock_vault_client):
        """Test secret rotation functionality."""
        # Mock current secret retrieval
        mock_vault_client.get_secret.return_value = "old-secret-value"

        manager = HardenedSecretsManager(Environment.PRODUCTION, mock_vault_client)

        with patch('secrets.token_urlsafe', return_value='new-secure-token'):
            new_secret = await manager.rotate_secret(
                SecretType.JWT_SECRET, "auth", "jwt_key"
            )

            assert new_secret == "new-secure-token"
            mock_vault_client.store_secret.assert_called_once()

    def test_get_secret_policies(self):
        """Test getting secret policies."""
        manager = HardenedSecretsManager(Environment.PRODUCTION, Mock())

        policies = manager.get_secret_policies()

        assert SecretType.JWT_SECRET in policies
        assert SecretType.DATABASE_CREDENTIAL in policies
        assert policies[SecretType.JWT_SECRET].requires_vault_in_production is True

    @pytest.mark.asyncio
    async def test_audit_secret_access(self, mock_vault_client):
        """Test secret access auditing."""
        manager = HardenedSecretsManager(Environment.PRODUCTION, mock_vault_client)
        mock_vault_client.get_secret.return_value = "test-secret"

        # Mock the audit log storage
        with patch.object(manager, '_store_audit_log') as mock_audit:
            await manager.get_secret(SecretType.JWT_SECRET, "auth", "jwt_key")

            mock_audit.assert_called_once()
            audit_log = mock_audit.call_args[0][0]
            assert isinstance(audit_log, SecretAuditLog)
            assert audit_log.secret_type == SecretType.JWT_SECRET


class TestSecretMetadata:
    """Test SecretMetadata model."""

    def test_metadata_creation(self):
        """Test secret metadata creation."""
        metadata = SecretMetadata(
            secret_type=SecretType.JWT_SECRET,
            path="secret/auth/jwt_key",
            version=1,
            created_at="2024-01-01T00:00:00Z",
            last_accessed=None,
            rotation_scheduled=False
        )

        assert metadata.secret_type == SecretType.JWT_SECRET
        assert metadata.version == 1
        assert metadata.rotation_scheduled is False


class TestSecretAuditLog:
    """Test SecretAuditLog model."""

    def test_audit_log_creation(self):
        """Test audit log creation."""
        tenant_id = uuid4()

        audit_log = SecretAuditLog(
            secret_type=SecretType.API_KEY,
            action="RETRIEVE",
            path="secret/billing/stripe_key",
            tenant_id=tenant_id,
            environment=Environment.PRODUCTION,
            success=True,
            error_message=None
        )

        assert audit_log.secret_type == SecretType.API_KEY
        assert audit_log.action == "RETRIEVE"
        assert audit_log.tenant_id == tenant_id
        assert audit_log.success is True


class TestIntegrationScenarios:
    """Test integration scenarios and error handling."""

    @pytest.mark.asyncio
    async def test_vault_connection_failure_fallback(self):
        """Test fallback behavior when vault is unavailable in development."""
        # Mock a failing vault client
        mock_vault_client = Mock(spec=OpenBaoClient)
        mock_vault_client.get_secret = AsyncMock(side_effect=SecretsRetrievalError("Vault unreachable"))

        manager = HardenedSecretsManager(Environment.DEVELOPMENT, mock_vault_client)

        # Should fall back to environment variable
        with patch.dict(os.environ, {'AUTH_JWT_SECRET_KEY': 'fallback-secret'}):
            result = await manager.get_secret(
                SecretType.JWT_SECRET, "auth", "jwt_secret_key"
            )
            assert result == "fallback-secret"

    @pytest.mark.asyncio
    async def test_production_vault_failure_no_fallback(self):
        """Test that production failures don't fall back to env vars."""
        mock_vault_client = Mock(spec=OpenBaoClient)
        mock_vault_client.get_secret = AsyncMock(side_effect=SecretsRetrievalError("Vault error"))

        manager = HardenedSecretsManager(Environment.PRODUCTION, mock_vault_client)

        with patch.dict(os.environ, {'AUTH_JWT_SECRET_KEY': 'should-not-use-this'}):
            with pytest.raises(SecretsRetrievalError):
                await manager.get_secret(
                    SecretType.JWT_SECRET, "auth", "jwt_secret_key"
                )

    @pytest.mark.asyncio
    async def test_multi_tenant_secret_isolation(self, mock_vault_client):
        """Test that tenant secrets are properly isolated."""
        tenant1 = uuid4()
        tenant2 = uuid4()

        mock_vault_client.get_secret.side_effect = lambda path, key: f"secret-for-{path.split('/')[-2]}"

        manager = HardenedSecretsManager(Environment.PRODUCTION, mock_vault_client)

        secret1 = await manager.get_secret(SecretType.API_KEY, "billing", "key", tenant1)
        secret2 = await manager.get_secret(SecretType.API_KEY, "billing", "key", tenant2)

        # Secrets should be different (isolated by tenant)
        assert secret1 != secret2
        assert str(tenant1) in secret1 or str(tenant2) in secret2


@pytest.mark.asyncio
async def test_secrets_manager_comprehensive_workflow():
    """Test a comprehensive workflow with the secrets manager."""
    # Create a mock vault client
    vault_client = Mock(spec=OpenBaoClient)
    vault_client.health_check = AsyncMock(return_value=True)
    vault_client.get_secret = AsyncMock(return_value="production-jwt-secret")
    vault_client.store_secret = AsyncMock()

    # Create manager for production environment
    manager = HardenedSecretsManager(Environment.PRODUCTION, vault_client)

    # Test health check
    health = await manager.health_check()
    assert health is True

    # Test secret retrieval
    secret = await manager.get_secret(SecretType.JWT_SECRET, "auth", "jwt_key")
    assert secret == "production-jwt-secret"

    # Test secret validation
    manager.validate_secret_strength("VeryStrongSecret123!@#", SecretType.JWT_SECRET)

    # Test policy retrieval
    policies = manager.get_secret_policies()
    assert SecretType.JWT_SECRET in policies
