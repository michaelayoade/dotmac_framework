"""
Tests for EnvironmentProvider functionality
"""
import os
import pytest
from unittest.mock import patch

from dotmac.secrets import (
    EnvironmentProvider,
    Environment,
    SecretNotFoundError,
)


class TestEnvironmentProvider:
    """Test EnvironmentProvider functionality"""
    
    @pytest.fixture
    def env_provider(self):
        """Create environment provider for testing"""
        return EnvironmentProvider(
            environment=Environment.DEVELOPMENT,
            allow_production=True
        )
    
    def test_production_safety_check(self):
        """Test production safety checks"""
        # Should raise error in production without explicit allow
        with pytest.raises(ValueError) as exc_info:
            EnvironmentProvider(
                environment=Environment.PRODUCTION,
                allow_production=False
            )
        assert "disabled in production" in str(exc_info.value)
        
        # Should work with explicit allow
        provider = EnvironmentProvider(
            environment=Environment.PRODUCTION,
            allow_production=True
        )
        assert provider.environment == Environment.PRODUCTION
    
    @patch.dict(os.environ, {"EXPLICIT_ALLOW_ENV_SECRETS": "true"})
    def test_production_env_override(self):
        """Test production override via environment variable"""
        provider = EnvironmentProvider(
            environment=Environment.PRODUCTION,
            allow_production=False
        )
        assert provider.environment == Environment.PRODUCTION
    
    @pytest.mark.asyncio
    async def test_get_jwt_secret_asymmetric(self, env_provider):
        """Test getting JWT asymmetric keypair from environment"""
        with patch.dict(os.environ, {
            "JWT_PRIVATE_KEY_TESTAPP": "-----BEGIN PRIVATE KEY-----\ntest-private\n-----END PRIVATE KEY-----",
            "JWT_PUBLIC_KEY_TESTAPP": "-----BEGIN PUBLIC KEY-----\ntest-public\n-----END PUBLIC KEY-----",
            "JWT_ALGORITHM_TESTAPP": "RS256"
        }):
            secret = await env_provider.get_secret("jwt/testapp/keypair")
            
            assert secret["private_pem"] == "-----BEGIN PRIVATE KEY-----\ntest-private\n-----END PRIVATE KEY-----"
            assert secret["public_pem"] == "-----BEGIN PUBLIC KEY-----\ntest-public\n-----END PUBLIC KEY-----"
            assert secret["algorithm"] == "RS256"
            assert secret["kid"] == "default"
    
    @pytest.mark.asyncio
    async def test_get_jwt_secret_symmetric(self, env_provider):
        """Test getting JWT symmetric secret from environment"""
        with patch.dict(os.environ, {
            "JWT_PRIVATE_KEY": "symmetric-secret-key",
            "JWT_ALGORITHM": "HS256"
        }):
            secret = await env_provider.get_secret("jwt/default/keypair")
            
            assert secret["secret"] == "symmetric-secret-key"
            assert secret["algorithm"] == "HS256"
            assert secret["kid"] == "default"
    
    @pytest.mark.asyncio
    async def test_get_database_secret_url(self, env_provider):
        """Test getting database credentials from DATABASE_URL"""
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://user:pass@host:5432/dbname"
        }):
            secret = await env_provider.get_secret("databases/default")
            
            assert secret["host"] == "host"
            assert secret["port"] == 5432
            assert secret["username"] == "user"
            assert secret["password"] == "pass"
            assert secret["database"] == "dbname"
            assert secret["driver"] == "postgresql"
    
    @pytest.mark.asyncio
    async def test_get_database_secret_components(self, env_provider):
        """Test getting database credentials from individual components"""
        with patch.dict(os.environ, {
            "DATABASE_HOST": "localhost",
            "DATABASE_PORT": "3306",
            "DATABASE_USER": "testuser",
            "DATABASE_PASSWORD": "testpass",
            "DATABASE_NAME": "testdb",
            "DATABASE_DRIVER": "mysql"
        }):
            secret = await env_provider.get_secret("databases/default")
            
            assert secret["host"] == "localhost"
            assert secret["port"] == 3306
            assert secret["username"] == "testuser"
            assert secret["password"] == "testpass"
            assert secret["database"] == "testdb"
            assert secret["driver"] == "mysql"
    
    @pytest.mark.asyncio
    async def test_get_database_secret_named(self, env_provider):
        """Test getting named database credentials"""
        with patch.dict(os.environ, {
            "DATABASE_HOST_ANALYTICS": "analytics-host",
            "DATABASE_USER_ANALYTICS": "analytics-user",
            "DATABASE_PASSWORD_ANALYTICS": "analytics-pass",
            "DATABASE_NAME_ANALYTICS": "analytics_db"
        }):
            secret = await env_provider.get_secret("databases/analytics")
            
            assert secret["host"] == "analytics-host"
            assert secret["username"] == "analytics-user"
            assert secret["password"] == "analytics-pass"
            assert secret["database"] == "analytics_db"
    
    @pytest.mark.asyncio
    async def test_get_service_signing_secret(self, env_provider):
        """Test getting service signing secret"""
        with patch.dict(os.environ, {
            "SERVICE_SIGNING_SECRET_AUTH": "auth-service-secret"
        }):
            secret = await env_provider.get_secret("service-signing/auth")
            assert secret["secret"] == "auth-service-secret"
    
    @pytest.mark.asyncio
    async def test_get_encryption_key(self, env_provider):
        """Test getting encryption key"""
        with patch.dict(os.environ, {
            "ENCRYPTION_KEY_DATA": "data-encryption-key-123"
        }):
            secret = await env_provider.get_secret("encryption-keys/data")
            assert secret["key"] == "data-encryption-key-123"
    
    @pytest.mark.asyncio
    async def test_get_webhook_secret(self, env_provider):
        """Test getting webhook secret"""
        with patch.dict(os.environ, {
            "WEBHOOK_SECRET_GITHUB": "github-webhook-secret"
        }):
            secret = await env_provider.get_secret("webhooks/github")
            assert secret["secret"] == "github-webhook-secret"
    
    @pytest.mark.asyncio
    async def test_get_symmetric_secret(self, env_provider):
        """Test getting symmetric secret"""
        with patch.dict(os.environ, {
            "SYMMETRIC_SECRET_API": "api-secret-key"
        }):
            secret = await env_provider.get_secret("secrets/symmetric/api")
            assert secret["secret"] == "api-secret-key"
    
    @pytest.mark.asyncio
    async def test_get_custom_secret(self, env_provider):
        """Test getting custom secret"""
        with patch.dict(os.environ, {
            "EXTERNAL_SERVICE_CONFIG": "custom-config-value"
        }):
            secret = await env_provider.get_secret("external/service/config")
            assert secret["value"] == "custom-config-value"
    
    @pytest.mark.asyncio
    async def test_secret_not_found(self, env_provider):
        """Test handling of missing environment variables"""
        with pytest.raises(SecretNotFoundError):
            await env_provider.get_secret("jwt/nonexistent/keypair")
    
    @pytest.mark.asyncio
    async def test_prefix_support(self):
        """Test environment variable prefix support"""
        provider = EnvironmentProvider(
            prefix="MYAPP",
            environment=Environment.DEVELOPMENT,
            allow_production=True
        )
        
        with patch.dict(os.environ, {
            "MYAPP_JWT_PRIVATE_KEY": "prefixed-secret",
            "JWT_PRIVATE_KEY": "non-prefixed-secret"
        }):
            secret = await provider.get_secret("jwt/default/keypair")
            # Should prefer prefixed version
            assert secret["secret"] == "prefixed-secret"
    
    @pytest.mark.asyncio
    async def test_list_secrets(self, env_provider):
        """Test listing available secrets"""
        with patch.dict(os.environ, {
            "JWT_PRIVATE_KEY": "test-key",
            "DATABASE_URL": "postgresql://user:pass@host/db",
            "SERVICE_SIGNING_SECRET": "service-secret",
            "JWT_PRIVATE_KEY_MANAGEMENT": "mgmt-key"
        }):
            secrets = await env_provider.list_secrets()
            
            assert "jwt/default/keypair" in secrets
            assert "databases/default" in secrets
            assert "service-signing/default" in secrets
            assert "jwt/management/keypair" in secrets
    
    @pytest.mark.asyncio
    async def test_list_secrets_with_prefix(self, env_provider):
        """Test listing secrets with path prefix"""
        with patch.dict(os.environ, {
            "JWT_PRIVATE_KEY": "test-key",
            "DATABASE_URL": "postgresql://user:pass@host/db"
        }):
            secrets = await env_provider.list_secrets("jwt")
            
            # Should only include JWT secrets
            jwt_secrets = [s for s in secrets if s.startswith("jwt")]
            assert len(jwt_secrets) == len(secrets)
    
    @pytest.mark.asyncio
    async def test_health_check(self, env_provider):
        """Test health check functionality"""
        health = await env_provider.health_check()
        assert health is True  # Should always be healthy for env provider
    
    def test_database_url_parsing_complex(self, env_provider):
        """Test parsing complex database URLs"""
        test_cases = [
            (
                "postgresql://user:pass@host:5432/db?sslmode=disable",
                {
                    "host": "host",
                    "port": 5432,
                    "username": "user",
                    "password": "pass",
                    "database": "db",
                    "driver": "postgresql",
                    "ssl_mode": "disable"
                }
            ),
            (
                "mysql://root:secret@mysql-host:3306/app_db",
                {
                    "host": "mysql-host",
                    "port": 3306,
                    "username": "root",
                    "password": "secret",
                    "database": "app_db",
                    "driver": "mysql"
                }
            ),
        ]
        
        for url, expected in test_cases:
            result = env_provider._parse_database_url(url)
            for key, value in expected.items():
                assert result[key] == value