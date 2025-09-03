"""
Pytest configuration and fixtures for dotmac.secrets tests
"""
import pytest
import os
import asyncio
from typing import Generator


def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "requires_openbao: marks tests as requiring OpenBao/Vault server"
    )
    config.addinivalue_line(
        "markers", "requires_redis: marks tests as requiring Redis server"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def clean_environment():
    """Clean environment variables before each test"""
    # Store original values
    original_env = {}
    secrets_env_vars = [
        "OPENBAO_URL", "OPENBAO_TOKEN", "VAULT_ADDR", "VAULT_TOKEN",
        "JWT_PRIVATE_KEY", "JWT_PUBLIC_KEY", "JWT_ALGORITHM",
        "DATABASE_URL", "DATABASE_HOST", "DATABASE_PORT",
        "DATABASE_USER", "DATABASE_PASSWORD", "DATABASE_NAME",
        "SERVICE_SIGNING_SECRET", "ENCRYPTION_KEY", "WEBHOOK_SECRET",
        "SECRETS_PROVIDER", "SECRETS_CACHE_TYPE", "ENVIRONMENT",
        "EXPLICIT_ALLOW_ENV_SECRETS"
    ]
    
    for var in secrets_env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_env.items():
        os.environ[var] = value


@pytest.fixture
def mock_openbao_env():
    """Set up mock OpenBao environment variables"""
    env_vars = {
        "OPENBAO_URL": "https://vault.example.com",
        "OPENBAO_TOKEN": "mock-token-123",
        "OPENBAO_MOUNT": "secret",
        "SECRETS_PROVIDER": "openbao"
    }
    
    with patch_env_vars(env_vars):
        yield env_vars


@pytest.fixture
def mock_env_provider_env():
    """Set up mock environment provider variables"""
    env_vars = {
        "SECRETS_PROVIDER": "env",
        "ENVIRONMENT": "development",
        "EXPLICIT_ALLOW_ENV_SECRETS": "true",
        "JWT_PRIVATE_KEY": "test-jwt-private-key",
        "JWT_PUBLIC_KEY": "test-jwt-public-key",
        "JWT_ALGORITHM": "RS256",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/testdb",
        "SERVICE_SIGNING_SECRET": "service-secret-123",
        "ENCRYPTION_KEY": "encryption-key-123456789012345678901234567890",
        "WEBHOOK_SECRET": "webhook-secret-123"
    }
    
    with patch_env_vars(env_vars):
        yield env_vars


@pytest.fixture
def production_env():
    """Set up production environment"""
    env_vars = {
        "ENVIRONMENT": "production"
    }
    
    with patch_env_vars(env_vars):
        yield env_vars


class patch_env_vars:
    """Context manager for patching environment variables"""
    
    def __init__(self, env_vars: dict):
        self.env_vars = env_vars
        self.original_values = {}
    
    def __enter__(self):
        # Store original values and set new ones
        for key, value in self.env_vars.items():
            if key in os.environ:
                self.original_values[key] = os.environ[key]
            os.environ[key] = value
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original values
        for key in self.env_vars:
            if key in self.original_values:
                os.environ[key] = self.original_values[key]
            elif key in os.environ:
                del os.environ[key]


# Helper functions for tests
def create_mock_jwt_keypair():
    """Create mock JWT keypair data"""
    return {
        "private_pem": """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKB
UdUqjdFiWnNW4sOtOhb10FrNFHhRTMThV4iLOjhF8y8e4KlPj8eGZvF2EQ...
-----END PRIVATE KEY-----""",
        "public_pem": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1L7VLPHCgVHVKo3R
YlpzVuLDrToW9dBazRR4UUzE4VeIizo4RfMvHuCpT4/Hhmb...
-----END PUBLIC KEY-----""",
        "algorithm": "RS256",
        "kid": "test-key-id"
    }


def create_mock_database_credentials():
    """Create mock database credentials"""
    return {
        "host": "db.example.com",
        "port": 5432,
        "username": "dbuser",
        "password": "secure-password-123!@#",
        "database": "production_db",
        "driver": "postgresql"
    }


# Skip markers for optional dependencies
def skip_if_no_redis():
    """Skip test if Redis is not available"""
    try:
        import redis.asyncio as redis
        # Try to connect
        client = redis.from_url("redis://localhost:6379", socket_connect_timeout=1)
        # This will be closed automatically
        return False
    except Exception:
        return True


def skip_if_no_openbao():
    """Skip test if OpenBao/Vault is not available"""
    openbao_url = os.getenv("TEST_OPENBAO_URL")
    openbao_token = os.getenv("TEST_OPENBAO_TOKEN")
    return not (openbao_url and openbao_token)


# Add pytest markers based on environment
pytest.mark.skipif(skip_if_no_redis(), reason="Redis server not available")(
    pytest.mark.requires_redis
)

pytest.mark.skipif(skip_if_no_openbao(), reason="OpenBao/Vault server not available")(
    pytest.mark.requires_openbao
)