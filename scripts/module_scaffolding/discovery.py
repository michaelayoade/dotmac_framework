"""
Module auto-discovery and registry system.
"""

import asyncio
import importlib
import importlib.util
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

logger = logging.getLogger(__name__)


class ModuleStatus(Enum):
    """Module status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    LOADING = "loading"
    ERROR = "error"


@dataclass
class ModuleInfo:
    """Information about a discovered module."""

    name: str
    path: str
    platform: str
    router_available: bool = False
    service_available: bool = False
    models_available: bool = False
    schemas_available: bool = False
    repository_available: bool = False
    tasks_available: bool = False
    dependencies_available: bool = False
    exceptions_available: bool = False
    router_instance: Any = None
    service_class: Type = None
    last_health_check: Optional[float] = None
    status: ModuleStatus = ModuleStatus.LOADING
    error_message: Optional[str] = None
    additional_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModuleDiscovery:
    """Automatic module discovery system."""

    def __init__(self, framework_root: Optional[Path] = None):
        self.framework_root = framework_root or Path(__file__).parent.parent.parent
        self.src_root = self.framework_root / "src"
        self.discovered_modules: Dict[str, ModuleInfo] = {}

    async def discover_all_modules(self) -> Dict[str, ModuleInfo]:
        """Discover all modules in the framework."""
        logger.info("🔍 Starting module discovery...")

        # Discover ISP Framework modules
        isp_modules = await self._discover_platform_modules("isp")

        # Discover Management Platform modules
        mgmt_modules = await self._discover_platform_modules("management")

        # Combine results
        self.discovered_modules.update(isp_modules)
        self.discovered_modules.update(mgmt_modules)

        logger.info(f"📊 Discovered {len(self.discovered_modules)} modules total")
        return self.discovered_modules

    async def _discover_platform_modules(self, platform: str) -> Dict[str, ModuleInfo]:
        """Discover modules for a specific platform."""
        if platform == "isp":
            modules_dir = self.src_root / "dotmac_isp" / "modules"
            base_package = "dotmac_isp.modules"
        else:
            modules_dir = self.src_root / "dotmac_management" / "modules"
            base_package = "dotmac_management.modules"

        if not modules_dir.exists():
            logger.warning(f"Modules directory not found: {modules_dir}")
            return {}

        modules = {}

        # Use ThreadPoolExecutor for parallel discovery
        with ThreadPoolExecutor(max_workers=4) as executor:
            tasks = []

            for module_dir in modules_dir.iterdir():
                if module_dir.is_dir() and not module_dir.name.startswith("_"):
                    task = executor.submit(
                        self._discover_single_module, module_dir, platform, base_package
                    )
                    tasks.append(task)

            # Wait for all discovery tasks to complete
            for task in tasks:
                try:
                    module_info = task.result()
                    if module_info:
                        modules[module_info.name] = module_info
                except Exception as e:
                    logger.error(f"Error discovering module: {e}")

        return modules

    def _discover_single_module(
        self, module_dir: Path, platform: str, base_package: str
    ) -> Optional[ModuleInfo]:
        """Discover a single module synchronously."""
        try:
            module_name = module_dir.name
            module_info = ModuleInfo(
                name=module_name,
                path=str(module_dir.relative_to(self.framework_root)),
                platform=platform,
            )

            # Check for standard components
            self._check_component_availability(module_dir, module_info)

            # Try to import and validate components
            self._import_module_components(module_info, base_package)

            # Determine module status
            self._determine_module_status(module_info)

            return module_info

        except Exception as e:
            logger.error(f"Error discovering module {module_dir.name}: {e}")
            return None

    def _check_component_availability(self, module_dir: Path, module_info: ModuleInfo):
        """Check which standard components are available."""
        components = {
            "router": "router.py",
            "service": "service.py",
            "models": "models.py",
            "schemas": "schemas.py",
            "repository": "repository.py",
            "tasks": "tasks.py",
            "dependencies": "dependencies.py",
            "exceptions": "exceptions.py",
        }

        for component, filename in components.items():
            component_path = module_dir / filename
            if component_path.exists():
                setattr(module_info, f"{component}_available", True)

        # Find additional files
        for file_path in module_dir.rglob("*.py"):
            if file_path.is_file():
                rel_path = file_path.relative_to(module_dir)
                if (
                    str(rel_path) not in components.values()
                    and str(rel_path) != "__init__.py"
                ):
                    module_info.additional_files.append(str(rel_path))

    def _import_module_components(self, module_info: ModuleInfo, base_package: str):
        """Attempt to import module components."""
        module_package = f"{base_package}.{module_info.name}"

        try:
            # Try to import router
            if module_info.router_available:
                router_module = importlib.import_module(f"{module_package}.router")
                if hasattr(router_module, "router"):
                    module_info.router_instance = router_module.router
                    module_info.metadata["router_prefix"] = getattr(
                        router_module.router, "prefix", f"/{module_info.name}"
                    )
                    module_info.metadata["router_tags"] = getattr(
                        router_module.router, "tags", [module_info.name]
                    )

            # Try to import service class
            if module_info.service_available:
                service_module = importlib.import_module(f"{module_package}.service")
                # Look for service class (convention: ModuleNameService)
                service_class_name = (
                    f"{module_info.name.title().replace('_', '')}Service"
                )
                if hasattr(service_module, service_class_name):
                    module_info.service_class = getattr(
                        service_module, service_class_name
                    )

            # Try to import main module (for metadata)
            try:
                main_module = importlib.import_module(module_package)
                if hasattr(main_module, "__all__"):
                    module_info.metadata["exports"] = main_module.__all__
                if hasattr(main_module, "__doc__"):
                    module_info.metadata["description"] = main_module.__doc__
            except ImportError:
                pass

        except ImportError as e:
            logger.warning(
                f"Could not import components for module {module_info.name}: {e}"
            )
            module_info.error_message = str(e)
        except Exception as e:
            logger.error(f"Unexpected error importing module {module_info.name}: {e}")
            module_info.error_message = str(e)

    def _determine_module_status(self, module_info: ModuleInfo):
        """Determine the overall status of a module."""
        if module_info.error_message:
            module_info.status = ModuleStatus.ERROR
            return

        # Check for core components
        has_core = all(
            [
                module_info.router_available,
                module_info.service_available,
                module_info.models_available,
            ]
        )

        # Check for complete structure
        has_complete = all(
            [
                module_info.router_available,
                module_info.service_available,
                module_info.models_available,
                module_info.schemas_available,
                module_info.repository_available,
            ]
        )

        if has_complete and module_info.router_instance and module_info.service_class:
            module_info.status = ModuleStatus.HEALTHY
        elif has_core and module_info.router_instance:
            module_info.status = ModuleStatus.DEGRADED
        elif module_info.router_available or module_info.service_available:
            module_info.status = ModuleStatus.DEGRADED
        else:
            module_info.status = ModuleStatus.UNAVAILABLE


class ModuleRegistry:
    """Module registry and management system."""

    def __init__(self):
        self.modules: Dict[str, ModuleInfo] = {}
        self.discovery = ModuleDiscovery()
        self._health_check_interval = 300  # 5 minutes
        self._health_check_task = None

    async def initialize(self):
        """Initialize the module registry."""
        logger.info("🚀 Initializing Module Registry...")

        # Discover all modules
        self.modules = await self.discovery.discover_all_modules()

        # Start periodic health checks
        await self._start_health_checks()

        # Log initialization results
        await self._log_initialization_summary()

    async def _start_health_checks(self):
        """Start periodic health checks for modules."""

        async def health_check_loop():
            while True:
                try:
                    await asyncio.sleep(self._health_check_interval)
                    await self.run_health_checks()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in health check loop: {e}")

        self._health_check_task = asyncio.create_task(health_check_loop())

    async def run_health_checks(self):
        """Run health checks on all registered modules."""
        logger.debug("🏥 Running module health checks...")

        for module_name, module_info in self.modules.items():
            try:
                await self._check_module_health(module_info)
            except Exception as e:
                logger.error(f"Health check failed for module {module_name}: {e}")
                module_info.status = ModuleStatus.ERROR
                module_info.error_message = str(e)

    async def _check_module_health(self, module_info: ModuleInfo):
        """Check health of a specific module."""
        import time

        from dotmac_shared.api.exception_handlers import standard_exception_handler

        try:
            # Basic availability check
            if module_info.router_instance:
                # Check if router is still accessible
                if hasattr(module_info.router_instance, "routes"):
                    routes_count = len(module_info.router_instance.routes)
                    module_info.metadata["routes_count"] = routes_count

            # Service health check
            if module_info.service_class:
                # Could instantiate and call health method if available
                pass

            # Update health check timestamp
            module_info.last_health_check = time.time()

            # If we got here without errors, module is still healthy
            if module_info.status == ModuleStatus.ERROR:
                module_info.status = ModuleStatus.HEALTHY
                module_info.error_message = None

        except Exception as e:
            module_info.status = ModuleStatus.ERROR
            module_info.error_message = str(e)

    async def _log_initialization_summary(self):
        """Log summary of module registry initialization."""
        status_counts = {}
        for module in self.modules.values():
            status = module.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        logger.info("📊 Module Registry Summary:")
        logger.info(f"  Total modules: {len(self.modules)}")
        for status, count in status_counts.items():
            logger.info(f"  {status.title()}: {count} modules")

        # Log unhealthy modules
        unhealthy = [
            m
            for m in self.modules.values()
            if m.status in [ModuleStatus.ERROR, ModuleStatus.UNAVAILABLE]
        ]
        if unhealthy:
            logger.warning(f"⚠️  {len(unhealthy)} modules need attention:")
            for module in unhealthy:
                logger.warning(
                    f"    - {module.name} ({module.platform}): {module.status.value}"
                )
                if module.error_message:
                    logger.warning(f"      Error: {module.error_message}")

    def get_module(self, name: str) -> Optional[ModuleInfo]:
        """Get module information by name."""
        return self.modules.get(name)

    def get_modules_by_platform(self, platform: str) -> List[ModuleInfo]:
        """Get all modules for a specific platform."""
        return [m for m in self.modules.values() if m.platform == platform]

    def get_modules_by_status(self, status: ModuleStatus) -> List[ModuleInfo]:
        """Get all modules with a specific status."""
        return [m for m in self.modules.values() if m.status == status]

    def get_healthy_modules(self) -> List[ModuleInfo]:
        """Get all healthy modules."""
        return self.get_modules_by_status(ModuleStatus.HEALTHY)

    def get_available_routers(self) -> Dict[str, Any]:
        """Get all available router instances."""
        return {
            name: module.router_instance
            for name, module in self.modules.items()
            if module.router_instance
            and module.status in [ModuleStatus.HEALTHY, ModuleStatus.DEGRADED]
        }

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get comprehensive registry statistics."""
        stats = {
            "total_modules": len(self.modules),
            "by_platform": {},
            "by_status": {},
            "component_availability": {
                "router": 0,
                "service": 0,
                "models": 0,
                "schemas": 0,
                "repository": 0,
                "tasks": 0,
                "dependencies": 0,
                "exceptions": 0,
            },
            "healthy_routers": len(self.get_available_routers()),
            "last_health_check": max(
                [
                    m.last_health_check
                    for m in self.modules.values()
                    if m.last_health_check
                ],
                default=0,
            ),
        }

        for module in self.modules.values():
            # Count by platform
            platform = module.platform
            stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1

            # Count by status
            status = module.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Count component availability
            for component in stats["component_availability"]:
                if getattr(module, f"{component}_available", False):
                    stats["component_availability"][component] += 1

        return stats

    async def refresh_module(self, module_name: str) -> bool:
        """Refresh a specific module's information."""
        logger.info(f"🔄 Refreshing module: {module_name}")

        try:
            # Rediscover the specific module
            platform = (
                self.modules[module_name].platform
                if module_name in self.modules
                else None
            )

            if not platform:
                logger.error(f"Module {module_name} not found for refresh")
                return False

            # Rediscover platform modules (could be optimized to discover just one)
            updated_modules = await self.discovery._discover_platform_modules(platform)

            if module_name in updated_modules:
                self.modules[module_name] = updated_modules[module_name]
                logger.info(f"✅ Module {module_name} refreshed successfully")
                return True
            else:
                logger.error(f"Module {module_name} not found after refresh")
                return False

        except Exception as e:
            logger.error(f"Error refreshing module {module_name}: {e}")
            return False

    async def shutdown(self):
        """Shutdown the module registry."""
        logger.info("🛑 Shutting down Module Registry...")

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        self.modules.clear()
        logger.info("✅ Module Registry shutdown complete")


# Global registry instance
_global_registry: Optional[ModuleRegistry] = None


async def get_module_registry() -> ModuleRegistry:
    """Get the global module registry instance."""
    global _global_registry

    if _global_registry is None:
        _global_registry = ModuleRegistry()
        await _global_registry.initialize()

    return _global_registry


def get_registry_sync() -> Optional[ModuleRegistry]:
    """Get the global module registry instance synchronously (may return None if not initialized)."""
    return _global_registry
