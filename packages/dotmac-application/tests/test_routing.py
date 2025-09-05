"""
Test router registration functionality.

Tests router auto-discovery, registration, and configuration based on
PlatformConfig.routers settings.
"""
from unittest.mock import Mock, patch

import pytest
from dotmac.application import (
    PlatformConfig,
    RouterConfig,
    RouterRegistry,
    SafeRouterLoader,
    create_app,
)
from fastapi import APIRouter, FastAPI


class TestRouterRegistration:
    """Test router registration and configuration."""

    def test_explicit_router_registration(self):
        """Test explicit router registration from configuration."""
        # Mock router module
        mock_router = APIRouter()
        mock_router.add_api_route(
            "/test", endpoint=lambda: {"message": "test"}, methods=["GET"]
        )

        with patch("importlib.import_module") as mock_import:
            # Mock the module import
            mock_module = Mock()
            mock_module.router = mock_router
            mock_import.return_value = mock_module

            config = PlatformConfig(
                platform_name="test_platform",
                title="Test Platform",
                description="Test platform description",
                routers=[
                    RouterConfig(
                        module_path="test_app.routers.auth",
                        prefix="/api/v1/auth",
                        required=True,
                        tags=["authentication"],
                    )
                ],
            )

            app = create_app(config)

            # Check that router was registered
            routes = [route.path for route in app.routes]
            assert "/api/v1/auth/test" in routes or any(
                "/test" in route for route in routes
            )

    def test_auto_discovery_router_registration(self):
        """Test auto-discovery router registration."""
        # Mock multiple router modules for auto-discovery
        mock_auth_router = APIRouter()
        mock_auth_router.add_api_route(
            "/login", endpoint=lambda: {"message": "login"}, methods=["POST"]
        )

        mock_users_router = APIRouter()
        mock_users_router.add_api_route(
            "/profile", endpoint=lambda: {"message": "profile"}, methods=["GET"]
        )

        with patch("os.listdir") as mock_listdir, patch(
            "os.path.isfile"
        ) as mock_isfile, patch("importlib.import_module") as mock_import:
            # Mock directory listing
            mock_listdir.return_value = ["auth.py", "users.py", "__init__.py"]
            mock_isfile.return_value = True

            # Mock module imports
            def mock_import_side_effect(module_path):
                if "auth" in module_path:
                    mock_module = Mock()
                    mock_module.router = mock_auth_router
                    return mock_module
                elif "users" in module_path:
                    mock_module = Mock()
                    mock_module.router = mock_users_router
                    return mock_module
                else:
                    raise ImportError(f"No module named '{module_path}'")

            mock_import.side_effect = mock_import_side_effect

            config = PlatformConfig(
                platform_name="test_platform",
                title="Test Platform",
                description="Test platform description",
                routers=[
                    RouterConfig(
                        module_path="test_app.modules",
                        prefix="/api/v1",
                        auto_discover=True,
                        tags=["api"],
                    )
                ],
            )

            app = create_app(config)

            # Check that auto-discovered routers were registered
            routes = [route.path for route in app.routes]
            # Should have both auth and users routes with prefix
            route_paths_str = " ".join(routes)
            assert any("login" in path for path in routes) or "login" in route_paths_str
            assert (
                any("profile" in path for path in routes)
                or "profile" in route_paths_str
            )

    def test_router_config_validation(self):
        """Test router configuration validation."""
        registry = RouterRegistry()

        # Valid configuration should not raise
        valid_config = RouterConfig(
            module_path="dotmac.valid.module", prefix="/api/v1", required=True
        )

        # Should not raise an exception for valid module path
        registry.validate_router_config(valid_config)

        # Invalid configuration should raise
        invalid_config = RouterConfig(
            module_path="../../../etc/passwd",  # Path traversal attempt
            prefix="/api/v1",
            required=True,
        )

        with pytest.raises(ValueError, match="Invalid module path"):
            registry.validate_router_config(invalid_config)

    def test_safe_router_loader_security(self):
        """Test SafeRouterLoader security validation."""
        loader = SafeRouterLoader()

        # Valid module paths should pass
        valid_paths = [
            "dotmac.auth.routes",
            "my_app.routers.users",
            "platform.api.v1.billing",
        ]

        for path in valid_paths:
            assert loader.is_safe_module_path(path)

        # Invalid/dangerous paths should fail
        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "os.system",
            "__import__",
            "..dangerous.module",
            "sys.modules",
        ]

        for path in dangerous_paths:
            assert not loader.is_safe_module_path(path)

    def test_required_router_failure_handling(self):
        """Test handling of required router loading failures."""
        with patch("importlib.import_module") as mock_import:
            # Mock import failure
            mock_import.side_effect = ImportError("Module not found")

            config = PlatformConfig(
                platform_name="test_platform",
                title="Test Platform",
                description="Test platform description",
                routers=[
                    RouterConfig(
                        module_path="nonexistent.module",
                        prefix="/api/v1",
                        required=True,  # Required router should cause failure
                    )
                ],
            )

            # Required router failure should raise exception
            with pytest.raises(ImportError):
                create_app(config)

    def test_optional_router_failure_handling(self):
        """Test handling of optional router loading failures."""
        with patch("importlib.import_module") as mock_import:
            # Mock import failure
            mock_import.side_effect = ImportError("Module not found")

            config = PlatformConfig(
                platform_name="test_platform",
                title="Test Platform",
                description="Test platform description",
                routers=[
                    RouterConfig(
                        module_path="nonexistent.module",
                        prefix="/api/v1",
                        required=False,  # Optional router should not cause failure
                    )
                ],
            )

            # Optional router failure should not prevent app creation
            app = create_app(config)
            assert isinstance(app, FastAPI)

    def test_router_tags_and_prefix_application(self):
        """Test that router tags and prefixes are properly applied."""
        mock_router = APIRouter()
        mock_router.add_api_route(
            "/endpoint", endpoint=lambda: {"message": "test"}, methods=["GET"]
        )

        with patch("importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.router = mock_router
            mock_import.return_value = mock_module

            config = PlatformConfig(
                platform_name="test_platform",
                title="Test Platform",
                description="Test platform description",
                routers=[
                    RouterConfig(
                        module_path="test_app.routers.tagged",
                        prefix="/api/v2/custom",
                        required=True,
                        tags=["custom", "v2"],
                    )
                ],
            )

            app = create_app(config)

            # Check that prefix was applied
            routes = [route.path for route in app.routes]
            prefixed_route_exists = any("/api/v2/custom" in route for route in routes)
            assert prefixed_route_exists

    def test_empty_router_configuration(self):
        """Test app creation with no routers configured."""
        config = PlatformConfig(
            platform_name="test_platform",
            title="Test Platform",
            description="Test platform description",
            routers=[],  # No routers
        )

        app = create_app(config)

        # Should still have standard endpoints
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/health" in routes
