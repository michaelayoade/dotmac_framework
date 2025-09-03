"""
Tests for SecretsManager core functionality
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch

from dotmac.secrets import (
    SecretsManager,
    EnvironmentProvider,
    InMemoryCache,
    SecretKind,
    SecretNotFoundError,
    SecretValidationError,
    create_default_validator,
)
from dotmac.secrets.observability import LoggingObservabilityHook


class TestSecretsManager:
    """Test SecretsManager core functionality"""
    
    @pytest.fixture
    def mock_provider(self):
        """Create mock provider"""
        provider = AsyncMock()
        provider.health_check = AsyncMock(return_value=True)
        return provider
    
    @pytest.fixture
    def cache(self):
        """Create in-memory cache"""
        return InMemoryCache(default_ttl=300)
    
    @pytest.fixture
    def validator(self):
        """Create validator"""
        return create_default_validator()
    
    @pytest.fixture
    def observability_hook(self):
        """Create observability hook"""
        return LoggingObservabilityHook()
    
    @pytest.fixture
    async def manager(self, mock_provider, cache, validator, observability_hook):
        """Create SecretsManager instance"""
        mgr = SecretsManager(
            provider=mock_provider,
            cache=cache,
            validator=validator,
            observability_hook=observability_hook
        )
        yield mgr
        await mgr.close()
    
    @pytest.mark.asyncio
    async def test_get_jwt_keypair_asymmetric(self, manager, mock_provider):
        """Test getting asymmetric JWT keypair"""
        # Mock provider response
        mock_provider.get_secret.return_value = {
            "private_pem": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG...\n-----END PRIVATE KEY-----",
            "public_pem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG...\n-----END PUBLIC KEY-----",
            "algorithm": "RS256",
            "kid": "test-key-id"
        }
        
        keypair = await manager.get_jwt_keypair("test-app", "test-key-id")
        
        assert keypair.algorithm == "RS256"
        assert keypair.kid == "test-key-id"
        assert keypair.private_pem.startswith("-----BEGIN PRIVATE KEY-----")
        assert keypair.public_pem.startswith("-----BEGIN PUBLIC KEY-----")
        
        mock_provider.get_secret.assert_called_once_with("jwt/test-app/keypair/test-key-id")
    
    @pytest.mark.asyncio
    async def test_get_jwt_keypair_symmetric(self, manager, mock_provider):
        """Test getting symmetric JWT keypair"""
        mock_provider.get_secret.return_value = {
            "secret": "super-secret-symmetric-key-12345",
            "algorithm": "HS256",
            "kid": "symmetric-key"
        }
        
        keypair = await manager.get_jwt_keypair("test-app")
        
        assert keypair.algorithm == "HS256"
        assert keypair.kid == "default"  # Default kid when not specified
        assert keypair.private_pem == "super-secret-symmetric-key-12345"
        assert keypair.public_pem == ""
        
        mock_provider.get_secret.assert_called_once_with("jwt/test-app/keypair")
    
    @pytest.mark.asyncio
    async def test_get_symmetric_secret(self, manager, mock_provider):
        """Test getting symmetric secret"""
        mock_provider.get_secret.return_value = {
            "secret": "this-is-a-very-long-symmetric-secret-key-12345"
        }
        
        secret = await manager.get_symmetric_secret("test-secret", min_length=32)
        
        assert secret == "this-is-a-very-long-symmetric-secret-key-12345"
        assert len(secret) >= 32
        
        mock_provider.get_secret.assert_called_once_with("secrets/symmetric/test-secret")
    
    @pytest.mark.asyncio
    async def test_get_symmetric_secret_too_short(self, manager, mock_provider):
        """Test symmetric secret validation failure"""
        mock_provider.get_secret.return_value = {
            "secret": "short"
        }
        
        with pytest.raises(SecretValidationError) as exc_info:
            await manager.get_symmetric_secret("test-secret", min_length=32)
        
        assert "too short" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_get_database_credentials(self, manager, mock_provider):
        """Test getting database credentials"""
        mock_provider.get_secret.return_value = {
            "host": "localhost",
            "port": 5432,
            "username": "testuser",
            "password": "testpass123!@#",
            "database": "testdb",
            "driver": "postgresql"
        }
        
        creds = await manager.get_database_credentials("testdb")
        
        assert creds.host == "localhost"
        assert creds.port == 5432
        assert creds.username == "testuser"
        assert creds.password == "testpass123!@#"
        assert creds.database == "testdb"
        assert creds.driver == "postgresql"
        assert creds.connection_url == "postgresql://testuser:testpass123!@#@localhost:5432/testdb"
        
        mock_provider.get_secret.assert_called_once_with("databases/testdb")
    
    @pytest.mark.asyncio
    async def test_get_service_signing_secret(self, manager, mock_provider):
        """Test getting service signing secret"""
        mock_provider.get_secret.return_value = {
            "secret": "service-signing-secret-key-12345"
        }
        
        secret = await manager.get_service_signing_secret("auth-service")
        
        assert secret == "service-signing-secret-key-12345"
        mock_provider.get_secret.assert_called_once_with("service-signing/auth-service")
    
    @pytest.mark.asyncio
    async def test_get_encryption_key_string(self, manager, mock_provider):
        """Test getting encryption key as string"""
        mock_provider.get_secret.return_value = {
            "key": "this-is-a-32-byte-encryption-key"
        }
        
        key = await manager.get_encryption_key("test-key", min_length=32)
        
        assert key == "this-is-a-32-byte-encryption-key"
        mock_provider.get_secret.assert_called_once_with("encryption-keys/test-key")
    
    @pytest.mark.asyncio
    async def test_get_webhook_signing_secret(self, manager, mock_provider):
        """Test getting webhook signing secret"""
        mock_provider.get_secret.return_value = {
            "secret": "webhook-secret-key-123456789"
        }
        
        secret = await manager.get_webhook_signing_secret("github-webhook")
        
        assert secret == "webhook-secret-key-123456789"
        mock_provider.get_secret.assert_called_once_with("webhooks/github-webhook")
    
    @pytest.mark.asyncio
    async def test_get_custom_secret(self, manager, mock_provider):
        """Test getting custom secret"""
        mock_provider.get_secret.return_value = {
            "api_key": "custom-api-key-123",
            "endpoint": "https://api.example.com",
            "timeout": 30
        }
        
        secret = await manager.get_custom_secret("external/api-service")
        
        assert secret == {
            "api_key": "custom-api-key-123",
            "endpoint": "https://api.example.com",
            "timeout": 30
        }
        mock_provider.get_secret.assert_called_once_with("external/api-service")
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, manager, mock_provider):
        """Test secret caching behavior"""
        mock_provider.get_secret.return_value = {
            "secret": "cached-secret-value"
        }
        
        # First call should hit provider
        secret1 = await manager.get_symmetric_secret("cached-secret")
        assert mock_provider.get_secret.call_count == 1
        
        # Second call should hit cache
        secret2 = await manager.get_symmetric_secret("cached-secret")
        assert mock_provider.get_secret.call_count == 1  # Still 1
        
        assert secret1 == secret2
    
    @pytest.mark.asyncio
    async def test_negative_caching(self, manager, mock_provider):
        """Test negative caching behavior"""
        mock_provider.get_secret.side_effect = SecretNotFoundError("Not found")
        
        # First call should hit provider and fail
        with pytest.raises(SecretNotFoundError):
            await manager.get_symmetric_secret("nonexistent")
        assert mock_provider.get_secret.call_count == 1
        
        # Second call should hit negative cache
        with pytest.raises(SecretNotFoundError):
            await manager.get_symmetric_secret("nonexistent")
        assert mock_provider.get_secret.call_count == 1  # Still 1
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, manager, mock_provider):
        """Test cache invalidation"""
        mock_provider.get_secret.return_value = {
            "secret": "original-value"
        }
        
        # Get secret to cache it
        secret1 = await manager.get_symmetric_secret("test-secret")
        assert secret1 == "original-value"
        
        # Update mock response
        mock_provider.get_secret.return_value = {
            "secret": "updated-value"
        }
        
        # Should still return cached value
        secret2 = await manager.get_symmetric_secret("test-secret")
        assert secret2 == "original-value"
        
        # Invalidate cache
        await manager.invalidate_cache("secrets/symmetric/test-secret")
        
        # Should now get updated value
        secret3 = await manager.get_symmetric_secret("test-secret")
        assert secret3 == "updated-value"
    
    @pytest.mark.asyncio
    async def test_health_check(self, manager, mock_provider, cache):
        """Test health check functionality"""
        mock_provider.health_check.return_value = True
        
        health = await manager.health_check()
        
        assert health["manager"] == "healthy"
        assert health["provider"] == "healthy"
        assert health["cache"] == "healthy"
        assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_get_stats(self, manager, mock_provider, observability_hook):
        """Test statistics collection"""
        mock_provider.get_secret.return_value = {"secret": "test"}
        
        # Perform some operations
        await manager.get_symmetric_secret("test1")
        
        try:
            await manager.get_symmetric_secret("nonexistent")
        except SecretNotFoundError:
            pass
        
        stats = await manager.get_stats()
        
        assert "cache_hits" in stats or "cache_misses" in stats
        assert "provider_calls" in stats
        assert "cache" in stats
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_provider, cache, validator):
        """Test using SecretsManager as async context manager"""
        async with SecretsManager(
            provider=mock_provider,
            cache=cache,
            validator=validator
        ) as manager:
            mock_provider.get_secret.return_value = {"secret": "test"}
            secret = await manager.get_symmetric_secret("test")
            assert secret == "test"
        
        # Manager should be closed after context exit
        # Cache should be closed
        assert cache._cleanup_task.done() or cache._cleanup_task.cancelled()