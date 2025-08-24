"""
Configuration hot-reloading system for security-critical updates.
Enables runtime configuration updates without service interruption.
"""

import os
import json
import logging
import asyncio
import threading
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
from pathlib import Path
import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import signal

from dotmac_isp.core.management_platform_client import get_management_client
from dotmac_isp.core.config.handlers import create_configuration_handler_chain, ReloadContext, ReloadStatus as HandlerReloadStatus

logger = logging.getLogger(__name__)


class ReloadTrigger(str, Enum):
    """Configuration reload triggers."""

    FILE_CHANGE = "file_change"
    SIGNAL = "signal"
    API_REQUEST = "api_request"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    EMERGENCY = "emergency"


class ReloadStatus(str, Enum):
    """Status of configuration reload."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"


class ConfigScope(str, Enum):
    """Scope of configuration changes."""

    GLOBAL = "global"
    SERVICE = "service"
    FEATURE = "feature"
    SECURITY = "security"
    ENVIRONMENT = "environment"


class ReloadEvent(BaseModel):
    """Configuration reload event."""

    event_id: str
    trigger: ReloadTrigger
    scope: ConfigScope
    status: ReloadStatus
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Change details
    config_paths: List[str]
    changed_keys: List[str]
    old_values_hash: Dict[str, str] = Field(default_factory=dict)
    new_values_hash: Dict[str, str] = Field(default_factory=dict)

    # Validation
    validation_passed: bool = False
    validation_errors: List[str] = Field(default_factory=list)

    # Rollback information
    rollback_data: Optional[Dict[str, Any]] = None
    rollback_required: bool = False

    # Performance metrics
    reload_duration_ms: Optional[float] = None
    affected_services: List[str] = Field(default_factory=list)

    # Metadata
    triggered_by: str = "system"
    emergency_mode: bool = False
    error_message: Optional[str] = None


class ConfigurationHotReload:
    """
    Configuration hot-reloading system for runtime updates.
    Provides safe, validated configuration updates without service restart.
    """

    def __init__(
        self,
        config_paths: List[str],
        reload_callback: Optional[Callable] = None,
        validation_callback: Optional[Callable] = None,
        rollback_enabled: bool = True,
        emergency_rollback_timeout: int = 30,
    ):
        """
        Initialize configuration hot-reload system.

        Args:
            config_paths: Paths to configuration files to monitor
            reload_callback: Callback function for configuration updates
            validation_callback: Callback function for configuration validation
            rollback_enabled: Enable automatic rollback on failure
            emergency_rollback_timeout: Timeout for emergency rollback (seconds)
        """
        self.config_paths = [Path(p) for p in config_paths]
        self.reload_callback = reload_callback
        self.validation_callback = validation_callback
        self.rollback_enabled = rollback_enabled
        self.emergency_rollback_timeout = emergency_rollback_timeout

        # State management
        self.current_config: Dict[str, Any] = {}
        self.config_checksums: Dict[str, str] = {}
        self.reload_history: List[ReloadEvent] = []
        self.reload_callbacks: Dict[str, List[Callable]] = {}

        # File watching
        self.file_observer: Optional[Observer] = None
        self.file_handler: Optional["ConfigFileHandler"] = None

        # Threading
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._lock = threading.RLock()
        self._reload_in_progress = False

        # Emergency state
        self._emergency_mode = False
        self._emergency_config: Optional[Dict[str, Any]] = None

        # Reload statistics
        self.reload_stats = {
            "total_reloads": 0,
            "successful_reloads": 0,
            "failed_reloads": 0,
            "rollbacks": 0,
            "last_reload": None,
            "average_reload_time": 0.0,
        }

        # Initialize
        self._load_initial_config()
        self._setup_signal_handlers()

    def _load_initial_config(self):
        """Load initial configuration from files."""
        try:
            for config_path in self.config_paths:
                if config_path.exists():
                    with open(config_path, "r") as f:
                        if config_path.suffix == ".json":
                            config_data = json.load(f)
                        else:
                            # Assume it's a .env file
                            config_data = self._parse_env_file(config_path)

                    self.current_config[str(config_path)] = config_data
                    self.config_checksums[str(config_path)] = self._calculate_checksum(
                        config_data
                    )

            logger.info(
                f"Initial configuration loaded from {len(self.config_paths)} files"
            )

        except Exception as e:
            logger.error(f"Failed to load initial configuration: {e}")

    def _parse_env_file(self, file_path: Path) -> Dict[str, str]:
        """Parse environment file into dictionary."""
        config = {}
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip().strip("\"'")
        return config

    def _calculate_checksum(self, config_data: Dict[str, Any]) -> str:
        """Calculate checksum for configuration data."""
        config_str = json.dumps(config_data, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def _setup_signal_handlers(self):
        """Setup signal handlers for emergency operations."""
        try:
            # SIGUSR1 for configuration reload
            signal.signal(signal.SIGUSR1, self._signal_reload_handler)

            # SIGUSR2 for emergency rollback
            signal.signal(signal.SIGUSR2, self._signal_emergency_rollback)

            logger.info("Signal handlers configured for hot-reload")

        except Exception as e:
            logger.warning(f"Failed to setup signal handlers: {e}")

    def _signal_reload_handler(self, signum, frame):
        """Handle reload signal."""
        logger.info("Received reload signal (SIGUSR1)")
        asyncio.create_task(
            self.trigger_reload(ReloadTrigger.SIGNAL, triggered_by="signal")
        )

    def _signal_emergency_rollback(self, signum, frame):
        """Handle emergency rollback signal."""
        logger.warning("Received emergency rollback signal (SIGUSR2)")
        asyncio.create_task(self.emergency_rollback())

    def start_file_watching(self):
        """Start watching configuration files for changes."""
        if self.file_observer:
            return  # Already watching

        try:
            self.file_handler = ConfigFileHandler(self)
            self.file_observer = Observer()

            # Watch all config file directories
            watched_dirs = set()
            for config_path in self.config_paths:
                parent_dir = config_path.parent
                if parent_dir not in watched_dirs:
                    self.file_observer.schedule(
                        self.file_handler, str(parent_dir), recursive=False
                    )
                    watched_dirs.add(parent_dir)

            self.file_observer.start()
            logger.info(f"File watching started for {len(watched_dirs)} directories")

        except Exception as e:
            logger.error(f"Failed to start file watching: {e}")

    def stop_file_watching(self):
        """Stop watching configuration files."""
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            self.file_observer = None
            logger.info("File watching stopped")

    def register_reload_callback(self, scope: str, callback: Callable):
        """
        Register a callback for configuration reloads.

        Args:
            scope: Scope of configuration changes to watch
            callback: Function to call on configuration reload
        """
        if scope not in self.reload_callbacks:
            self.reload_callbacks[scope] = []
        self.reload_callbacks[scope].append(callback)
        logger.info(f"Reload callback registered for scope: {scope}")

    async def trigger_reload(
        self,
        trigger: ReloadTrigger = ReloadTrigger.MANUAL,
        config_paths: Optional[List[str]] = None,
        scope: ConfigScope = ConfigScope.GLOBAL,
        triggered_by: str = "system",
        emergency: bool = False,
    ) -> str:
        """
        Trigger a configuration reload.

        Args:
            trigger: What triggered the reload
            config_paths: Specific paths to reload (None for all)
            scope: Scope of the reload
            triggered_by: Who triggered the reload
            emergency: Emergency mode reload

        Returns:
            Event ID for tracking
        """
        with self._lock:
            if self._reload_in_progress and not emergency:
                raise RuntimeError("Reload already in progress")

            # Generate event
            event_id = f"reload-{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}"

            reload_event = ReloadEvent(
                event_id=event_id,
                trigger=trigger,
                scope=scope,
                status=ReloadStatus.PENDING,
                started_at=datetime.utcnow(),
                config_paths=config_paths or [str(p) for p in self.config_paths],
                triggered_by=triggered_by,
                emergency_mode=emergency,
            )

            self.reload_history.append(reload_event)

            # Submit reload job
            future = self.executor.submit(self._perform_reload, reload_event)

            logger.info(
                f"Configuration reload triggered: {event_id} (trigger: {trigger})"
            )
            return event_id

    def _perform_reload(self, reload_event: ReloadEvent):
        """
        Perform the actual configuration reload.
        
        REFACTORED: Replaced 22-complexity method with Chain of Responsibility pattern.
        Now uses ConfigurationHandlerChain for processing (Complexity: 3).
        """
        start_time = time.time()

        try:
            with self._lock:
                self._reload_in_progress = True
                reload_event.status = ReloadStatus.IN_PROGRESS

            # Step 1: Process configurations using handler chain (Complexity: 1)
            config_paths = [Path(path) for path in reload_event.config_paths]
            handler_chain = create_configuration_handler_chain()
            
            # Get tenant ID for multi-tenant support
            tenant_id = getattr(reload_event, 'tenant_id', None) or os.getenv('ISP_TENANT_ID')
            
            context = handler_chain.process_configurations(
                config_paths=config_paths,
                original_config=self.current_config,
                tenant_id=tenant_id
            )
            
            # Step 2: Handle processing results (Complexity: 1)
            if context.has_errors():
                reload_event.status = ReloadStatus.FAILED
                reload_event.error_message = "; ".join(context.errors)
                reload_event.validation_errors = context.errors
                logger.error(f"Configuration processing failed for {reload_event.event_id}: {context.errors}")
                
                if self.rollback_enabled:
                    await self._perform_rollback(reload_event)
                return
            
            # Update reload event with handler chain results
            reload_event.changed_keys = context.changed_keys
            reload_event.validation_passed = not context.has_errors()
            reload_event.validation_errors = context.warnings  # Warnings become validation notes
            
            if not context.has_changes():
                reload_event.status = ReloadStatus.COMPLETED
                reload_event.completed_at = datetime.utcnow()
                logger.info(f"No configuration changes detected for {reload_event.event_id}")
                return
                
            # Calculate hash changes for audit trail
            for changed_key in context.changed_keys:
                if ':' in changed_key:
                    source, key = changed_key.split(':', 1)
                    old_value = str(context.original_config.get(source, {}).get(key, ""))
                    new_value = str(context.new_config.get(key, ""))
                    
                    reload_event.old_values_hash[changed_key] = hashlib.sha256(old_value.encode()).hexdigest()
                    reload_event.new_values_hash[changed_key] = hashlib.sha256(new_value.encode()).hexdigest()

            # Step 3: Apply validated configuration (Complexity: 1)
            # Cross-platform validation with Management Platform
            try:
                await self._validate_with_management_platform(context.new_config, reload_event)
            except Exception as e:
                logger.warning(f"Management Platform validation failed (continuing): {e}")
                # Don't fail the reload if Management Platform validation fails

            # Store rollback data
            if self.rollback_enabled:
                reload_event.rollback_data = self.current_config.copy()

            # Apply new configuration (convert to expected format)
            config_by_path = {}
            for path in config_paths:
                if path.exists():
                    config_by_path[str(path)] = context.new_config
            
            await self._apply_configuration(config_by_path, reload_event)

            # Update current state
            self.current_config.update(config_by_path)
            for config_path_str, config_data in config_by_path.items():
                self.config_checksums[config_path_str] = self._calculate_checksum(config_data)

            # Update statistics
            end_time = time.time()
            reload_event.reload_duration_ms = (end_time - start_time) * 1000
            reload_event.status = ReloadStatus.COMPLETED
            reload_event.completed_at = datetime.utcnow()

            self._update_reload_stats(reload_event)

            # Report successful config application to Management Platform
            await self._report_config_application(reload_event, success=True)

            logger.info(
                f"Configuration reload completed: {reload_event.event_id} "
                f"({len(context.changed_keys)} changes, {reload_event.reload_duration_ms:.2f}ms)"
            )

        except Exception as e:
            reload_event.status = ReloadStatus.FAILED
            reload_event.error_message = str(e)
            reload_event.completed_at = datetime.utcnow()

            logger.error(
                f"Configuration reload failed for {reload_event.event_id}: {e}"
            )

            # Report failed config application to Management Platform
            await self._report_config_application(
                reload_event, success=False, errors=[str(e)]
            )

            # Attempt rollback
            if self.rollback_enabled and reload_event.rollback_data:
                try:
                    await self._perform_rollback(reload_event)
                except Exception as rollback_error:
                    logger.critical(
                        f"Rollback failed for {reload_event.event_id}: {rollback_error}"
                    )
                    self._emergency_mode = True

        finally:
            with self._lock:
                self._reload_in_progress = False

    async def _validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate new configuration."""
        if self.validation_callback:
            if asyncio.iscoroutinefunction(self.validation_callback):
                return await self.validation_callback(config)
            else:
                return self.validation_callback(config)

        # Default validation - just check structure
        return {"valid": True, "errors": []}

    async def _apply_configuration(
        self, config: Dict[str, Any], reload_event: ReloadEvent
    ):
        """Apply new configuration."""
        # Call registered callbacks
        for scope, callbacks in self.reload_callbacks.items():
            if scope == reload_event.scope.value or scope == "global":
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(config, reload_event)
                        else:
                            callback(config, reload_event)
                    except Exception as e:
                        logger.warning(f"Reload callback failed for scope {scope}: {e}")

        # Call main reload callback if set
        if self.reload_callback:
            try:
                if asyncio.iscoroutinefunction(self.reload_callback):
                    await self.reload_callback(config, reload_event)
                else:
                    self.reload_callback(config, reload_event)
            except Exception as e:
                raise RuntimeError(f"Main reload callback failed: {e}")

    async def _perform_rollback(self, reload_event: ReloadEvent):
        """Perform configuration rollback."""
        try:
            if not reload_event.rollback_data:
                raise ValueError("No rollback data available")

            logger.warning(f"Performing rollback for {reload_event.event_id}")

            # Apply rollback configuration
            await self._apply_configuration(reload_event.rollback_data, reload_event)

            # Restore state
            self.current_config = reload_event.rollback_data.copy()
            for config_path_str, config_data in self.current_config.items():
                self.config_checksums[config_path_str] = self._calculate_checksum(
                    config_data
                )

            reload_event.status = ReloadStatus.ROLLED_BACK
            reload_event.rollback_required = True

            self.reload_stats["rollbacks"] += 1

            logger.info(f"Rollback completed for {reload_event.event_id}")

        except Exception as e:
            logger.critical(f"Rollback failed for {reload_event.event_id}: {e}")
            reload_event.status = ReloadStatus.FAILED
            raise

    async def emergency_rollback(self):
        """Perform emergency rollback to last known good configuration."""
        logger.critical("Performing emergency rollback")

        self._emergency_mode = True

        try:
            # Find last successful reload
            last_good_event = None
            for event in reversed(self.reload_history):
                if event.status == ReloadStatus.COMPLETED and event.rollback_data:
                    last_good_event = event
                    break

            if last_good_event:
                await self._perform_rollback(last_good_event)
                logger.info("Emergency rollback completed")
            else:
                logger.critical("No good configuration found for emergency rollback")

                # Use emergency config if available
                if self._emergency_config:
                    self.current_config = self._emergency_config.copy()
                    logger.info("Emergency configuration activated")

        except Exception as e:
            logger.critical(f"Emergency rollback failed: {e}")

        finally:
            self._emergency_mode = False

    def _update_reload_stats(self, reload_event: ReloadEvent):
        """Update reload statistics."""
        self.reload_stats["total_reloads"] += 1

        if reload_event.status == ReloadStatus.COMPLETED:
            self.reload_stats["successful_reloads"] += 1
        else:
            self.reload_stats["failed_reloads"] += 1

        self.reload_stats["last_reload"] = reload_event.completed_at

        # Update average reload time
        if reload_event.reload_duration_ms:
            current_avg = self.reload_stats["average_reload_time"]
            total_reloads = self.reload_stats["total_reloads"]
            self.reload_stats["average_reload_time"] = (
                current_avg * (total_reloads - 1) + reload_event.reload_duration_ms
            ) / total_reloads

    def get_reload_status(self, event_id: str) -> Optional[ReloadEvent]:
        """Get status of a specific reload event."""
        for event in self.reload_history:
            if event.event_id == event_id:
                return event
        return None

    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.current_config.copy()

    def get_reload_stats(self) -> Dict[str, Any]:
        """Get reload statistics."""
        return self.reload_stats.copy()

    def is_emergency_mode(self) -> bool:
        """Check if system is in emergency mode."""
        return self._emergency_mode

    def set_emergency_config(self, config: Dict[str, Any]):
        """Set emergency fallback configuration."""
        self._emergency_config = config.copy()
        logger.info("Emergency configuration set")

    async def _validate_with_management_platform(
        self, config: Dict[str, Any], reload_event: ReloadEvent
    ):
        """Validate configuration with Management Platform."""
        try:
            # Get tenant ID from environment
            tenant_id = os.getenv("ISP_TENANT_ID")
            if not tenant_id:
                logger.warning(
                    "No tenant ID configured - skipping Management Platform validation"
                )
                return

            management_client = await get_management_client()

            # Prepare config data for validation
            flat_config = {}
            for config_path, config_data in config.items():
                if isinstance(config_data, dict):
                    flat_config.update(config_data)
                else:
                    flat_config[config_path] = config_data

            # Validate with Management Platform
            validation_result = await management_client.validate_configuration(
                config_data=flat_config, config_version=reload_event.event_id
            )

            if not validation_result.is_valid:
                logger.warning(
                    f"Management Platform validation warnings: {validation_result.validation_errors}"
                )
                reload_event.validation_errors.extend(
                    validation_result.validation_errors
                )

            if validation_result.warnings:
                logger.info(
                    f"Management Platform validation warnings: {validation_result.warnings}"
                )

        except Exception as e:
            logger.error(f"Error validating with Management Platform: {e}")
            # Don't fail the reload for Management Platform validation errors

    async def _report_config_application(
        self,
        reload_event: ReloadEvent,
        success: bool,
        errors: Optional[List[str]] = None,
    ):
        """Report configuration application result to Management Platform."""
        try:
            tenant_id = os.getenv("ISP_TENANT_ID")
            if not tenant_id:
                return

            management_client = await get_management_client()

            await management_client.report_configuration_applied(
                config_version=reload_event.event_id,
                success=success,
                errors=errors or [],
            )

            logger.debug(
                f"Reported config application to Management Platform: {reload_event.event_id}"
            )

        except Exception as e:
            logger.warning(
                f"Failed to report config application to Management Platform: {e}"
            )

    async def sync_with_management_platform(self) -> bool:
        """Sync configuration with Management Platform and trigger reload if needed."""
        try:
            tenant_id = os.getenv("ISP_TENANT_ID")
            if not tenant_id:
                logger.warning(
                    "No tenant ID configured - cannot sync with Management Platform"
                )
                return False

            management_client = await get_management_client()

            # Get current configuration from Management Platform
            remote_config = await management_client.get_tenant_configuration()

            if not remote_config:
                logger.warning("No configuration received from Management Platform")
                return False

            # Check if remote config is different from current
            current_config_hash = self._calculate_checksum(self.current_config)
            remote_config_hash = self._calculate_checksum(remote_config)

            if current_config_hash != remote_config_hash:
                logger.info("Configuration drift detected - triggering sync reload")

                # Trigger reload with Management Platform config
                event_id = await self.trigger_reload(
                    trigger=ReloadTrigger.API_REQUEST,
                    scope=ConfigScope.GLOBAL,
                    triggered_by="management_platform_sync",
                )

                return True

            logger.debug("Configuration in sync with Management Platform")
            return True

        except Exception as e:
            logger.error(f"Error syncing with Management Platform: {e}")
            return False


class ConfigFileHandler(FileSystemEventHandler):
    """File system event handler for configuration files."""

    def __init__(self, hot_reload: ConfigurationHotReload):
        """  Init   operation."""
        self.hot_reload = hot_reload
        self.last_reload_time = {}
        self.reload_debounce = 1.0  # 1 second debounce

    def on_modified(self, event):
        """On Modified operation."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if this is a monitored config file
        if file_path in self.hot_reload.config_paths:
            # Debounce rapid file changes
            now = time.time()
            last_time = self.last_reload_time.get(str(file_path), 0)

            if now - last_time < self.reload_debounce:
                return

            self.last_reload_time[str(file_path)] = now

            logger.info(f"Configuration file changed: {file_path}")

            # Trigger reload
            asyncio.create_task(
                self.hot_reload.trigger_reload(
                    trigger=ReloadTrigger.FILE_CHANGE,
                    config_paths=[str(file_path)],
                    triggered_by="file_watcher",
                )
            )


# Global hot-reload manager
_config_hotreload: Optional[ConfigurationHotReload] = None


def get_config_hotreload() -> ConfigurationHotReload:
    """Get global configuration hot-reload manager."""
    global _config_hotreload
    if _config_hotreload is None:
        raise RuntimeError("Configuration hot-reload not initialized")
    return _config_hotreload


def init_config_hotreload(
    config_paths: List[str],
    reload_callback: Optional[Callable] = None,
    validation_callback: Optional[Callable] = None,
    rollback_enabled: bool = True,
    emergency_rollback_timeout: int = 30,
) -> ConfigurationHotReload:
    """Initialize global configuration hot-reload manager."""
    global _config_hotreload
    _config_hotreload = ConfigurationHotReload(
        config_paths=config_paths,
        reload_callback=reload_callback,
        validation_callback=validation_callback,
        rollback_enabled=rollback_enabled,
        emergency_rollback_timeout=emergency_rollback_timeout,
    )
    return _config_hotreload
