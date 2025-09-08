"""
Tests for Providers system.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from dotmac.application.providers import (
    Providers,
    DatabaseProvider,
    AuthProvider,
    TenantProvider,
    MockDatabaseProvider,
    MockAuthProvider,
    MockTenantProvider,
)


class TestProviders:
    """Test Providers configuration and management."""
    
    def test_providers_initialization(self):
        """Test basic Providers initialization."""
        providers = Providers()
        
        assert providers.database is None
        assert providers.auth is None
        assert providers.tenant is None
        assert providers.cache is None
        assert providers.integrations is None
        assert providers.observability is None
        assert isinstance(providers.config, dict)
    
    def test_providers_with_explicit_providers(self):
        """Test Providers with explicit provider instances."""
        mock_db = MockDatabaseProvider()
        mock_auth = MockAuthProvider()
        mock_tenant = MockTenantProvider()
        
        providers = Providers(
            database=mock_db,
            auth=mock_auth,
            tenant=mock_tenant,
        )
        
        assert providers.database == mock_db
        assert providers.auth == mock_auth
        assert providers.tenant == mock_tenant
    
    def test_from_env_default_providers(self):
        """Test creating providers with default (mock) implementations."""
        providers = Providers.from_env(platform=False)
        
        assert isinstance(providers.database, MockDatabaseProvider)
        assert isinstance(providers.auth, MockAuthProvider)
        assert isinstance(providers.tenant, MockTenantProvider)
    
    @patch('dotmac.application.providers.logger')
    def test_from_env_platform_providers_not_available(self, mock_logger):
        """Test platform provider loading when platform modules aren't available."""
        providers = Providers.from_env(platform=True)
        
        # Should log warnings for missing platform providers
        warning_calls = [call for call in mock_logger.warning.call_args_list]
        assert len(warning_calls) >= 3  # At least db, auth, tenant warnings
    
    def test_validate_required_providers_success(self):
        """Test provider validation with required providers present."""
        providers = Providers(
            database=MockDatabaseProvider(),
            auth=MockAuthProvider(),
        )
        
        # Should not raise any exception
        providers.validate_required_providers()
    
    def test_validate_required_providers_missing_database(self):
        """Test provider validation with missing database provider."""
        providers = Providers(auth=MockAuthProvider())
        
        with pytest.raises(RuntimeError) as exc_info:
            providers.validate_required_providers()
        
        assert "Database provider is required" in str(exc_info.value)
    
    def test_validate_required_providers_missing_auth(self):
        """Test provider validation with missing auth provider."""
        providers = Providers(database=MockDatabaseProvider())
        
        with pytest.raises(RuntimeError) as exc_info:
            providers.validate_required_providers()
        
        assert "Auth provider is required" in str(exc_info.value)
    
    def test_validate_required_providers_missing_both(self):
        """Test provider validation with missing required providers."""
        providers = Providers()
        
        with pytest.raises(RuntimeError) as exc_info:
            providers.validate_required_providers()
        
        error_message = str(exc_info.value)
        assert "Database provider is required" in error_message
        assert "Auth provider is required" in error_message


class TestMockProviders:
    """Test mock provider implementations."""
    
    @pytest.mark.asyncio
    async def test_mock_database_provider(self):
        """Test MockDatabaseProvider functionality."""
        provider = MockDatabaseProvider()
        
        # Test get_session
        session = await provider.get_session()
        assert session is not None
        
        # Test session methods
        result = await session.execute("SELECT 1")
        assert result == {"result": "mock"}
        
        await session.commit()
        await session.rollback()
        
        # Test close_session
        await provider.close_session(session)
    
    @pytest.mark.asyncio
    async def test_mock_auth_provider(self):
        """Test MockAuthProvider functionality."""
        provider = MockAuthProvider()
        
        # Test get_current_user
        user = await provider.get_current_user("test_token")
        expected_user = {
            "user_id": 1,
            "email": "test@example.com", 
            "is_active": True,
            "is_admin": False,
        }
        assert user == expected_user
        
        # Test validate_token
        assert await provider.validate_token("valid_token") is True
        assert await provider.validate_token("invalid_token") is False
    
    @pytest.mark.asyncio
    async def test_mock_tenant_provider(self):
        """Test MockTenantProvider functionality."""
        provider = MockTenantProvider()
        
        # Test get_current_tenant
        tenant = await provider.get_current_tenant("user1")
        assert tenant == "tenant_123"
        
        # Test validate_tenant_access
        access = await provider.validate_tenant_access("user1", "tenant_123")
        assert access is True
        
        access = await provider.validate_tenant_access("user1", "other_tenant")
        assert access is True  # Mock always returns True


class TestProviderProtocols:
    """Test provider protocol compliance."""
    
    def test_database_provider_protocol(self):
        """Test DatabaseProvider protocol compliance."""
        provider = MockDatabaseProvider()
        assert isinstance(provider, DatabaseProvider)
    
    def test_auth_provider_protocol(self):
        """Test AuthProvider protocol compliance."""
        provider = MockAuthProvider()
        assert isinstance(provider, AuthProvider)
    
    def test_tenant_provider_protocol(self):
        """Test TenantProvider protocol compliance."""
        provider = MockTenantProvider()
        assert isinstance(provider, TenantProvider)


class TestProviderIntegration:
    """Test provider integration scenarios."""
    
    def test_providers_with_config(self):
        """Test providers with custom configuration."""
        config = {
            "database_url": "sqlite:///test.db",
            "auth_secret": "test_secret",
            "tenant_mode": "multi",
        }
        
        providers = Providers(
            database=MockDatabaseProvider(),
            auth=MockAuthProvider(),
            config=config,
        )
        
        assert providers.config == config
        assert providers.config["database_url"] == "sqlite:///test.db"
    
    @patch('dotmac.application.providers.logger')
    def test_provider_loading_logs(self, mock_logger):
        """Test that provider loading generates appropriate logs."""
        # Test with platform=False (should load defaults)
        Providers.from_env(platform=False)
        
        # Should log that default providers were loaded
        mock_logger.info.assert_called_with("✅ Default providers loaded")
        
        # Test with platform=True (should attempt platform loading)
        mock_logger.reset_mock()
        Providers.from_env(platform=True)
        
        # Should log loading platform providers
        mock_logger.info.assert_any_call("Loading platform service providers...")


if __name__ == "__main__":
    pytest.main([__file__])