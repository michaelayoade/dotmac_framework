"""
Secure plugin execution sandbox.
"""

import asyncio
import os
import resource
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import structlog

from .models import PluginPermissions, ResourceLimits

logger = structlog.get_logger(__name__)


class PluginSecurityError(Exception):
    """Plugin security related error."""

    pass


class PluginExecutionError(Exception):
    """Plugin execution error."""

    pass


class PluginSandbox:
    """Secure plugin execution sandbox with isolation."""

    def __init__(
        self,
        plugin_id: str,
        tenant_id: Optional[UUID] = None,
        permissions: Optional[PluginPermissions] = None,
        resource_limits: Optional[ResourceLimits] = None,
        enable_monitoring: bool = True,
    ):
        self.plugin_id = plugin_id
        self.tenant_id = tenant_id
        self.permissions = permissions or PluginPermissions.create_default()
        self.resource_limits = resource_limits or ResourceLimits()
        self.enable_monitoring = enable_monitoring

        # Sandbox state
        self._temp_dir: Optional[Path] = None
        self._original_cwd: Optional[Path] = None
        self._execution_stats = {
            "start_time": None,
            "end_time": None,
            "memory_usage": 0,
            "cpu_time": 0.0,
            "network_requests": 0,
        }

    async def __aenter__(self) -> "PluginSandbox":
        """Enter sandbox context."""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit sandbox context with cleanup."""
        await self.cleanup()

    async def setup(self) -> None:
        """Setup sandbox environment."""
        logger.info("Setting up sandbox", plugin_id=self.plugin_id)

        try:
            # Create isolated temporary directory
            self._temp_dir = Path(tempfile.mkdtemp(prefix=f"plugin_{self.plugin_id}_"))
            self._original_cwd = Path.cwd()

            # Change to sandbox directory
            os.chdir(self._temp_dir)

            # Apply resource limits
            self._apply_resource_limits()

            self._execution_stats["start_time"] = datetime.now(timezone.utc)
            logger.info("Sandbox setup complete", plugin_id=self.plugin_id)

        except Exception as e:
            logger.error("Sandbox setup failed", plugin_id=self.plugin_id, error=str(e))
            raise PluginSecurityError(f"Sandbox setup failed: {e}") from e

    async def cleanup(self) -> None:
        """Cleanup sandbox resources."""
        logger.info("Cleaning up sandbox", plugin_id=self.plugin_id)

        try:
            # Record end time
            self._execution_stats["end_time"] = datetime.now(timezone.utc)

            # Return to original directory
            if self._original_cwd:
                os.chdir(self._original_cwd)

            # Remove temporary directory
            if self._temp_dir and self._temp_dir.exists():
                shutil.rmtree(self._temp_dir, ignore_errors=True)

            logger.info("Sandbox cleanup complete", plugin_id=self.plugin_id)

        except Exception as e:
            logger.error("Sandbox cleanup error", plugin_id=self.plugin_id, error=str(e))

    def check_permission(self, category: str, operation: str) -> bool:
        """Check if plugin has permission for operation."""
        has_perm = self.permissions.has_permission(category, operation)

        if not has_perm:
            logger.warning("Permission denied", plugin_id=self.plugin_id, category=category, operation=operation)

        return has_perm

    def get_temp_directory(self) -> Path:
        """Get plugin's temporary directory."""
        if not self._temp_dir:
            raise PluginSecurityError("Sandbox not initialized")
        return self._temp_dir

    async def execute_with_timeout(self, coro_or_func, *args, timeout: Optional[float] = None, **kwargs) -> Any:
        """Execute function/coroutine with timeout and monitoring."""
        timeout = timeout or self.resource_limits.max_execution_time_seconds

        try:
            if asyncio.iscoroutinefunction(coro_or_func):
                result = await asyncio.wait_for(coro_or_func(*args, **kwargs), timeout=timeout)
            else:
                # Run sync function in executor with timeout
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, lambda: coro_or_func(*args, **kwargs)),
                    timeout=timeout,
                )

            return result

        except asyncio.TimeoutError:
            logger.error("Plugin execution timeout", plugin_id=self.plugin_id, timeout=timeout)
            raise PluginExecutionError(f"Plugin execution timeout after {timeout}s")
        except Exception as e:
            logger.error("Plugin execution error", plugin_id=self.plugin_id, error=str(e))
            raise PluginExecutionError(f"Plugin execution failed: {e}") from e

    def _apply_resource_limits(self) -> None:
        """Apply resource limits using system calls."""
        try:
            # Memory limit
            memory_bytes = self.resource_limits.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

            # CPU time limit
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.resource_limits.max_cpu_time_seconds, self.resource_limits.max_cpu_time_seconds),
            )

            # File size limit
            file_size_bytes = self.resource_limits.max_file_size_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_bytes, file_size_bytes))

            logger.info(
                "Applied resource limits",
                plugin_id=self.plugin_id,
                memory_mb=self.resource_limits.max_memory_mb,
                cpu_seconds=self.resource_limits.max_cpu_time_seconds,
            )

        except Exception as e:
            logger.error("Failed to apply resource limits", plugin_id=self.plugin_id, error=str(e))
            raise PluginSecurityError(f"Resource limit setup failed: {e}") from e
