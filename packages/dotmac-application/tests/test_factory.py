"""
Test application factory functionality.

Tests factory functions for creating FastAPI applications with proper configuration,
endpoints, and deployment contexts.
"""
import pytest
from fastapi import FastAPI
from dotmac.application import (
    create_app,
    create_management_platform_app,
    create_isp_framework_app,
    PlatformConfig,
    TenantConfig,
    DeploymentContext,
    DeploymentMode,
)


class TestApplicationFactory:
    """Test application factory functions."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description"
        )
        
        app = create_app(config)
        
        assert isinstance(app, FastAPI)
        assert app.title == "Test Platform"
        assert app.description == "Test platform description"

    def test_create_management_platform_app_returns_fastapi_instance(self):
        """Test that create_management_platform_app returns a FastAPI instance."""
        app = create_management_platform_app()
        
        assert isinstance(app, FastAPI)
        assert app.title == "DotMac Management Platform"
        assert "management" in app.description.lower()

    def test_create_isp_framework_app_returns_fastapi_instance(self):
        """Test that create_isp_framework_app returns a FastAPI instance."""
        tenant_config = TenantConfig(
            tenant_id="test-tenant",
            deployment_context=DeploymentContext(
                mode=DeploymentMode.TENANT_CONTAINER,
                tenant_id="test-tenant"
            )
        )
        
        app = create_isp_framework_app(tenant_config=tenant_config)
        
        assert isinstance(app, FastAPI)
        assert "isp" in app.title.lower() or "tenant" in app.title.lower()

    def test_health_endpoints_exist(self):
        """Test that health endpoints are automatically registered."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description"
        )
        
        app = create_app(config)
        
        # Get all routes from the app
        routes = [route.path for route in app.routes]
        
        # Assert health endpoints exist
        assert "/health" in routes
        assert "/health/live" in routes
        assert "/health/ready" in routes
        assert "/health/startup" in routes

    def test_root_endpoint_exists(self):
        """Test that root endpoint is automatically registered."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description"
        )
        
        app = create_app(config)
        
        # Get all routes from the app
        routes = [route.path for route in app.routes]
        
        # Assert root endpoint exists
        assert "/" in routes

    def test_favicon_endpoint_exists(self):
        """Test that favicon endpoint is automatically registered."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description"
        )
        
        app = create_app(config)
        
        # Get all routes from the app
        routes = [route.path for route in app.routes]
        
        # Assert favicon endpoint exists
        assert "/favicon.ico" in routes

    def test_deployment_context_affects_app_configuration(self):
        """Test that deployment context affects application configuration."""
        # Test tenant container mode
        tenant_config = TenantConfig(
            tenant_id="test-tenant",
            deployment_context=DeploymentContext(
                mode=DeploymentMode.TENANT_CONTAINER,
                tenant_id="test-tenant"
            )
        )
        
        tenant_app = create_isp_framework_app(tenant_config=tenant_config)
        
        # Tenant container apps should disable docs for security
        assert tenant_app.docs_url is None
        assert tenant_app.redoc_url is None
        
        # Test management platform mode
        management_app = create_management_platform_app()
        
        # Management platform should have docs enabled
        assert management_app.docs_url is not None
        assert management_app.redoc_url is not None

    def test_custom_configuration_applied(self):
        """Test that custom configuration is properly applied."""
        config = PlatformConfig(
            platform_name="custom_platform",
            title="Custom Platform Title",
            description="Custom platform description",
            version="2.1.0"
        )
        
        app = create_app(config)
        
        assert app.title == "Custom Platform Title"
        assert app.description == "Custom platform description"
        assert app.version == "2.1.0"

    def test_app_factory_with_minimal_config(self):
        """Test app factory with minimal configuration."""
        config = PlatformConfig(
            platform_name="minimal",
            title="Minimal Platform",
            description="Minimal description"
        )
        
        app = create_app(config)
        
        assert isinstance(app, FastAPI)
        assert app.title == "Minimal Platform"
        assert len([route for route in app.routes]) >= 5  # At least standard endpoints