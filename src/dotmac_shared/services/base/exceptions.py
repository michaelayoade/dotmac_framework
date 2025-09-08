"""
Service Layer Exception Definitions

Consolidates service-specific exceptions for consistent error handling
across the entire DotMac framework service layer.
"""

from typing import Any, Optional


class ServiceError(Exception):
    """Base exception for all service layer errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ServiceNotFoundError(ServiceError):
    """Raised when a requested service is not found in the registry."""

    def __init__(self, service_name: str, available_services: Optional[list[str]] = None):
        super().__init__(f"Service '{service_name}' not found")
        self.service_name = service_name
        self.available_services = available_services or []


class ServiceConfigurationError(ServiceError):
    """Raised when a service has invalid configuration."""

    def __init__(self, service_name: str, config_issue: str):
        super().__init__(f"Service '{service_name}' configuration error: {config_issue}")
        self.service_name = service_name
        self.config_issue = config_issue


class ServiceDependencyError(ServiceError):
    """Raised when a service dependency is missing or invalid."""

    def __init__(self, service_name: str, dependency: str, issue: str):
        super().__init__(f"Service '{service_name}' dependency '{dependency}' error: {issue}")
        self.service_name = service_name
        self.dependency = dependency
        self.issue = issue
