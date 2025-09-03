"""
Safe router registry system for deployment-aware applications.
"""

import importlib
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, FastAPI

from .config import PlatformConfig, RouterConfig

logger = logging.getLogger(__name__)


class SafeRouterLoader:
    """Safe router loading with validation and error handling."""

    def __init__(self, platform_config: PlatformConfig):
        self.platform_config = platform_config
        self.loaded_routers: Dict[str, APIRouter] = {}
        self.failed_routers: List[str] = []

    def load_router(self, router_config: RouterConfig) -> Optional[Union[APIRouter, List[APIRouter]]]:
        """Safely load a router with validation."""
        try:
            # Security validation
            if not self._validate_router_security(router_config):
                logger.warning(
                    f"Security validation failed for router: {router_config.module_path}"
                )
                return None

            if router_config.auto_discover:
                return self._auto_discover_router(router_config)
            else:
                return self._load_single_router(router_config)

        except ImportError as e:
            if router_config.required:
                logger.error(
                    f"Required router failed to load: {router_config.module_path} - {e}"
                )
                raise
            else:
                logger.debug(
                    f"Optional router not available: {router_config.module_path} - {e}"
                )
                self.failed_routers.append(router_config.module_path)
                return None
        except Exception as e:
            logger.error(
                f"Unexpected error loading router {router_config.module_path}: {e}"
            )
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
            "modules.",
            "routers.",
        ]

        if not any(
            router_config.module_path.startswith(ns) for ns in trusted_namespaces
        ):
            return False

        # Prevent path traversal attempts
        if ".." in router_config.module_path or "/" in router_config.module_path:
            return False

        return True

    def _load_single_router(self, router_config: RouterConfig) -> Optional[APIRouter]:
        """Load a single router from module path."""
        try:
            module = importlib.import_module(router_config.module_path)

            # Try common router attribute names
            router_attrs = [
                "router",
                "api_router",
                f'{router_config.module_path.split(".")[-1]}_router',
                "app_router",
            ]

            for attr_name in router_attrs:
                router = getattr(module, attr_name, None)
                if isinstance(router, APIRouter):
                    self.loaded_routers[router_config.module_path] = router
                    return router

            logger.warning(f"No valid router found in {router_config.module_path}")
            return None

        except Exception as e:
            logger.error(f"Error loading single router {router_config.module_path}: {e}")
            raise

    def _auto_discover_router(
        self, router_config: RouterConfig
    ) -> Optional[List[APIRouter]]:
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

                        # Skip private modules and common non-router modules
                        if module_name.startswith("_") or module_name in ["__pycache__", "tests"]:
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
                        logger.debug(
                            f"Failed to load auto-discovered router {full_module_path}: {e}"
                        )

            return discovered_routers if discovered_routers else None

        except Exception as e:
            logger.error(f"Auto-discovery failed for {router_config.module_path}: {e}")
            return None


class RouterRegistry:
    """Central router registration system."""

    def __init__(self, platform_config: PlatformConfig):
        self.platform_config = platform_config
        self.loader = SafeRouterLoader(platform_config)
        self.registered_routers: Dict[str, APIRouter] = {}

    def register_all_routers(self, app: FastAPI) -> Dict[str, Any]:
        """Register all configured routers with the FastAPI app."""
        stats = {
            "total_attempted": len(self.platform_config.routers),
            "successfully_registered": 0,
            "failed_to_load": 0,
            "skipped_optional": 0,
            "auto_discovered": 0,
        }

        logger.info(f"Registering {stats['total_attempted']} router configurations...")

        for router_config in self.platform_config.routers:
            try:
                result = self.loader.load_router(router_config)
                
                if result is None:
                    if router_config.required:
                        stats["failed_to_load"] += 1
                    else:
                        stats["skipped_optional"] += 1
                    continue

                # Handle single router
                if isinstance(result, APIRouter):
                    self._register_single_router(app, result, router_config)
                    stats["successfully_registered"] += 1

                # Handle multiple routers (auto-discovered)
                elif isinstance(result, list):
                    for router in result:
                        if isinstance(router, APIRouter):
                            self._register_single_router(app, router, router_config)
                            stats["auto_discovered"] += 1
                    stats["successfully_registered"] += len(result)

            except Exception as e:
                logger.error(f"Failed to register router {router_config.module_path}: {e}")
                stats["failed_to_load"] += 1
                if router_config.required:
                    raise

        self._log_registration_stats(stats)
        return stats

    def _register_single_router(
        self, app: FastAPI, router: APIRouter, config: RouterConfig
    ):
        """Register a single router with the app."""
        try:
            # Apply router configuration
            include_kwargs = {
                "router": router,
                "prefix": config.prefix,
                "tags": config.tags if config.tags else None,
            }

            # Remove None values
            include_kwargs = {k: v for k, v in include_kwargs.items() if v is not None}

            app.include_router(**include_kwargs)

            # Store for tracking
            router_key = f"{config.module_path}:{config.prefix}"
            self.registered_routers[router_key] = router

            logger.debug(
                f"✅ Registered router: {config.module_path} -> {config.prefix or '/'}"
            )

        except Exception as e:
            logger.error(
                f"Failed to include router {config.module_path}: {e}"
            )
            raise

    def _log_registration_stats(self, stats: Dict[str, Any]):
        """Log router registration statistics."""
        logger.info("Router registration complete:")
        logger.info(f"  ✅ Successfully registered: {stats['successfully_registered']}")
        if stats["auto_discovered"] > 0:
            logger.info(f"  🔍 Auto-discovered: {stats['auto_discovered']}")
        if stats["skipped_optional"] > 0:
            logger.info(f"  ⏭️ Skipped optional: {stats['skipped_optional']}")
        if stats["failed_to_load"] > 0:
            logger.warning(f"  ❌ Failed to load: {stats['failed_to_load']}")

    def get_registered_routers(self) -> Dict[str, APIRouter]:
        """Get all registered routers."""
        return self.registered_routers.copy()

    def get_registration_summary(self) -> Dict[str, Any]:
        """Get summary of router registration."""
        return {
            "total_registered": len(self.registered_routers),
            "failed_routers": self.loader.failed_routers.copy(),
            "router_paths": list(self.registered_routers.keys()),
        }


# Convenience functions
def register_routers(app: FastAPI, config: PlatformConfig) -> Dict[str, Any]:
    """Register routers from configuration."""
    registry = RouterRegistry(config)
    return registry.register_all_routers(app)


def create_router_registry(config: PlatformConfig) -> RouterRegistry:
    """Create a router registry."""
    return RouterRegistry(config)