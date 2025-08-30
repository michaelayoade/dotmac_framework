"""
Base service classes and interfaces for service lifecycle management.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service status enumeration."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"


@dataclass
class ServiceHealth:
    """Service health information."""

    status: ServiceStatus
    message: str
    details: Dict[str, Any]
    last_check: Optional[float] = None

    def __post_init__(self):
        """Set last_check timestamp if not provided."""
        if self.last_check is None:
            self.last_check = time.time()


class BaseService(ABC):
    """Base class for all business services."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        """__init__ service method."""
        self.name = name
        self.config = config or {}
        self.status = ServiceStatus.UNINITIALIZED
        self._health = ServiceHealth(
            status=ServiceStatus.UNINITIALIZED,
            message="Service not initialized",
            details={},
        )
        self.logger = logging.getLogger(f"service.{name}")
        self.priority = 50  # Default priority for initialization ordering

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the service. Return True if successful."""
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        """Shutdown the service. Return True if successful."""
        pass

    @abstractmethod
    async def health_check(self) -> ServiceHealth:
        """Perform health check. Return health status."""
        pass

    def get_status(self) -> ServiceStatus:
        """Get current service status."""
        return self.status

    def get_health(self) -> ServiceHealth:
        """Get current health information."""
        return self._health

    def is_ready(self) -> bool:
        """Check if service is ready for use."""
        return self.status == ServiceStatus.READY

    def is_healthy(self) -> bool:
        """Check if service is healthy."""
        return self.status in [ServiceStatus.READY, ServiceStatus.INITIALIZING]

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default."""
        return self.config.get(key, default)

    def has_config(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self.config

    async def _set_status(
        self, status: ServiceStatus, message: str = "", details: Dict[str, Any] = None
    ):
        """Update service status and health."""
        self.status = status
        self._health = ServiceHealth(
            status=status, message=message, details=details or {}
        )

        if status == ServiceStatus.ERROR:
            self.logger.error(f"Service {self.name} error: {message}")
        elif status == ServiceStatus.READY:
            self.logger.info(f"Service {self.name} ready: {message}")
        elif status == ServiceStatus.INITIALIZING:
            self.logger.info(f"Service {self.name} initializing: {message}")
        elif status == ServiceStatus.SHUTTING_DOWN:
            self.logger.info(f"Service {self.name} shutting down: {message}")

    def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive service information."""
        return {
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority,
            "ready": self.is_ready(),
            "healthy": self.is_healthy(),
            "health": {
                "status": self._health.status.value,
                "message": self._health.message,
                "last_check": self._health.last_check,
                "details": self._health.details,
            },
            "config_keys": list(self.config.keys()),
        }


class ConfigurableService(BaseService):
    """Base service with configuration validation."""

    def __init__(
        self, name: str, config: Dict[str, Any] = None, required_config: list = None
    ):
        """__init__ service method."""
        super().__init__(name, config)
        self.required_config = required_config or []

    def validate_config(self) -> bool:
        """Validate required configuration is present."""
        missing_keys = []
        invalid_keys = []

        for key in self.required_config:
            if key not in self.config:
                missing_keys.append(key)
            elif self.config[key] is None:
                invalid_keys.append(key)

        if missing_keys or invalid_keys:
            error_details = {}
            if missing_keys:
                error_details["missing_config"] = missing_keys
            if invalid_keys:
                error_details["invalid_config"] = invalid_keys

            self.logger.error(
                f"Service {self.name} configuration validation failed: {error_details}"
            )
            return False

        return True

    def get_required_config_status(self) -> Dict[str, Any]:
        """Get status of required configuration."""
        status = {
            "required_keys": self.required_config,
            "missing": [],
            "invalid": [],
            "valid": [],
        }

        for key in self.required_config:
            if key not in self.config:
                status["missing"].append(key)
            elif self.config[key] is None:
                status["invalid"].append(key)
            else:
                status["valid"].append(key)

        return status

    async def initialize(self) -> bool:
        """Initialize with config validation."""
        await self._set_status(
            ServiceStatus.INITIALIZING, f"Validating configuration for {self.name}"
        )

        if not self.validate_config():
            config_status = self.get_required_config_status()
            await self._set_status(
                ServiceStatus.ERROR,
                f"Configuration validation failed for service {self.name}",
                {"config_validation": config_status},
            )
            return False

        await self._set_status(
            ServiceStatus.INITIALIZING,
            f"Configuration validated, initializing {self.name}",
        )
        return await self._initialize_service()

    @abstractmethod
    async def _initialize_service(self) -> bool:
        """Service-specific initialization logic."""
        pass

    async def health_check(self) -> ServiceHealth:
        """Enhanced health check with configuration validation."""
        # First check configuration
        if not self.validate_config():
            return ServiceHealth(
                status=ServiceStatus.ERROR,
                message=f"Service {self.name} configuration validation failed",
                details={"config_validation": self.get_required_config_status()},
            )

        # Delegate to service-specific health check
        return await self._health_check_service()

    @abstractmethod
    async def _health_check_service(self) -> ServiceHealth:
        """Service-specific health check logic."""
        pass


class StatefulService(ConfigurableService):
    """Base service with state management capabilities."""

    def __init__(
        self, name: str, config: Dict[str, Any] = None, required_config: list = None
    ):
        """__init__ service method."""
        super().__init__(name, config, required_config)
        self._service_state: Dict[str, Any] = {}
        self._initialization_time: Optional[float] = None
        self._last_activity: Optional[float] = None

    def set_state(self, key: str, value: Any):
        """Set service state value."""
        self._service_state[key] = value
        self._last_activity = time.time()

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get service state value."""
        return self._service_state.get(key, default)

    def has_state(self, key: str) -> bool:
        """Check if state key exists."""
        return key in self._service_state

    def clear_state(self):
        """Clear all service state."""
        self._service_state.clear()
        self._last_activity = time.time()

    def get_state_info(self) -> Dict[str, Any]:
        """Get service state information."""
        return {
            "state_keys": list(self._service_state.keys()),
            "initialization_time": self._initialization_time,
            "last_activity": self._last_activity,
            "uptime_seconds": (
                (time.time() - self._initialization_time)
                if self._initialization_time
                else None
            ),
        }

    async def _initialize_service(self) -> bool:
        """Initialize stateful service."""
        self._initialization_time = time.time()
        self._last_activity = time.time()

        return await self._initialize_stateful_service()

    @abstractmethod
    async def _initialize_stateful_service(self) -> bool:
        """Service-specific stateful initialization logic."""
        pass

    async def _health_check_service(self) -> ServiceHealth:
        """Enhanced health check with state information."""
        health = await self._health_check_stateful_service()

        # Add state information to health details
        if health.details is None:
            health.details = {}

        health.details["state_info"] = self.get_state_info()

        return health

    @abstractmethod
    async def _health_check_stateful_service(self) -> ServiceHealth:
        """Service-specific stateful health check logic."""
        pass
