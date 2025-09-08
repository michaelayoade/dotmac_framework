"""
Safe router registry system for deployment-aware applications.
"""

import importlib
import logging
from typing import Any, Optional

from fastapi import APIRouter, FastAPI

from .config import PlatformConfig, RouterConfig

logger = logging.getLogger(__name__)


class SafeRouterLoader:
    """Safe router loading with validation and error handling."""

    def __init__(self, platform_config: PlatformConfig):
        self.platform_config = platform_config
        self.loaded_routers: dict[str, APIRouter] = {}
        self.failed_routers: list[str] = []

    def load_router(self, router_config: RouterConfig) -> Optional[APIRouter]:
        """Safely load a router with validation."""
        try:
            # Security validation
            if not self._validate_router_security(router_config):
                logger.warning(f"Security validation failed for router: {router_config.module_path}")
                return None

            if router_config.auto_discover:
                return self._auto_discover_router(router_config)
            else:
                return self._load_single_router(router_config)

        except ImportError as e:
            if router_config.required:
                logger.error(f"Required router failed to load: {router_config.module_path} - {e}")
                raise
            else:
                logger.debug(f"Optional router not available: {router_config.module_path} - {e}")
                self.failed_routers.append(router_config.module_path)
                return None
        except Exception as e:
            logger.error(f"Unexpected error loading router {router_config.module_path}: {e}")
            if router_config.required:
                raise
            return None

    def _validate_router_security(self, router_config: RouterConfig) -> bool:
        """Validate router module path for security."""
        # Only allow trusted namespaces
        trusted_namespaces = [
            "dotmac_isp.",
            "dotmac_management.",
            "dotmac_shared.",
            "api.",
            "core.",
        ]

        if not any(router_config.module_path.startswith(ns) for ns in trusted_namespaces):
            return False

        # Prevent path traversal attempts
        if ".." in router_config.module_path or "/" in router_config.module_path:
            return False

        return True

    def _load_single_router(self, router_config: RouterConfig) -> Optional[APIRouter]:
        """Load a single router from module path."""
        module = importlib.import_module(router_config.module_path)

        # Try common router attribute names
        router_attrs = [
            "router",
            "api_router",
            f'{router_config.module_path.split(".")[-1]}_router',
        ]

        for attr_name in router_attrs:
            router = getattr(module, attr_name, None)
            if isinstance(router, APIRouter):
                self.loaded_routers[router_config.module_path] = router
                return router

        logger.warning(f"No valid router found in {router_config.module_path}")
        return None

    def _auto_discover_router(self, router_config: RouterConfig) -> Optional[list[APIRouter]]:
        """Auto-discover routers in a module namespace."""
        try:
            base_module = importlib.import_module(router_config.module_path)
            discovered_routers = []

            # Get module directory
            if hasattr(base_module, "__path__"):
                import pkgutil

                for _, module_name, _ in pkgutil.iter_modules(base_module.__path__):
                    try:
                        full_module_path = f"{router_config.module_path}.{module_name}"

                        # Skip private modules
                        if module_name.startswith("_"):
                            continue

                        sub_router_config = RouterConfig(
                            module_path=full_module_path,
                            prefix=router_config.prefix,
                            required=False,
                            tags=router_config.tags,
                        )

                        router = self._load_single_router(sub_router_config)
                        if router:
                            discovered_routers.append(router)

                    except Exception as e:
                        logger.debug(f"Failed to load auto-discovered router {full_module_path}: {e}")

            return discovered_routers if discovered_routers else None

        except Exception as e:
            logger.error(f"Auto-discovery failed for {router_config.module_path}: {e}")
            return None


class RouterRegistry:
    """Central router registration system."""

    def __init__(self, platform_config: PlatformConfig):
        self.platform_config = platform_config
        self.loader = SafeRouterLoader(platform_config)
        self.registered_routes: list[str] = []
        self.registration_stats = {
            "total_attempted": 0,
            "successfully_registered": 0,
            "failed_registrations": 0,
            "auto_discovered": 0,
        }

    def register_all_routers(self, app: FastAPI) -> dict[str, Any]:
        """Register all configured routers."""
        logger.info(f"Starting router registration for {self.platform_config.platform_name}")

        for router_config in self.platform_config.routers:
            self._register_router(app, router_config)

        # Register standard endpoints
        self._register_standard_endpoints(app)

        logger.info(f"Router registration complete. Stats: {self.registration_stats}")
        return self.registration_stats

    def _register_router(self, app: FastAPI, router_config: RouterConfig):
        """Register a single router configuration."""
        self.registration_stats["total_attempted"] += 1

        if router_config.auto_discover:
            self._register_auto_discovered_routers(app, router_config)
        else:
            self._register_single_router(app, router_config)

    def _register_single_router(self, app: FastAPI, router_config: RouterConfig):
        """Register a single router."""
        router = self.loader.load_router(router_config)

        if router:
            # Apply router configuration
            include_kwargs = {
                "router": router,
                "prefix": router_config.prefix,
            }

            if router_config.tags:
                include_kwargs["tags"] = router_config.tags

            app.include_router(**include_kwargs)

            self.registered_routes.append(f"{router_config.prefix} ({router_config.module_path})")
            self.registration_stats["successfully_registered"] += 1

            logger.info(f"Registered router: {router_config.module_path} at {router_config.prefix}")
        else:
            self.registration_stats["failed_registrations"] += 1

    def _register_auto_discovered_routers(self, app: FastAPI, router_config: RouterConfig):
        """Register auto-discovered routers."""
        routers = self.loader.load_router(router_config)

        if routers:
            for _i, router in enumerate(routers):
                # Generate prefix for auto-discovered routers
                router_prefix = f"{router_config.prefix}/{router.prefix}" if router.prefix else router_config.prefix

                include_kwargs = {
                    "router": router,
                    "prefix": router_prefix,
                }

                if router_config.tags:
                    include_kwargs["tags"] = router_config.tags

                app.include_router(**include_kwargs)

                self.registered_routes.append(f"{router_prefix} (auto-discovered)")
                self.registration_stats["successfully_registered"] += 1
                self.registration_stats["auto_discovered"] += 1

                logger.info(f"Auto-registered router at {router_prefix}")

    def _register_standard_endpoints(self, app: FastAPI):
        """Register standard endpoints that all platforms need."""
        # These are registered by the lifecycle manager
        # This method is for any additional standard endpoints
        pass

    def get_registration_report(self) -> dict[str, Any]:
        """Get detailed registration report."""
        return {
            "platform": self.platform_config.platform_name,
            "stats": self.registration_stats,
            "registered_routes": self.registered_routes,
            "failed_routers": self.loader.failed_routers,
            "total_routers_configured": len(self.platform_config.routers),
        }
