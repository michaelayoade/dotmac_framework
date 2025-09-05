"""
Exception classes for the DotMac Container Provisioning Service.
"""

from typing import Any, Optional
from uuid import UUID


class ProvisioningError(Exception):
    """Base exception for container provisioning errors."""

    def __init__(
        self,
        message: str,
        isp_id: Optional[UUID] = None,
        stage: Optional[str] = None,
        rollback_completed: bool = False,
        context: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.isp_id = isp_id
        self.stage = stage
        self.rollback_completed = rollback_completed
        self.context = context or {}

    def __str__(self) -> str:
        parts = [super().__str__()]

        if self.isp_id:
            parts.append(f"ISP ID: {self.isp_id}")
        if self.stage:
            parts.append(f"Stage: {self.stage}")
        if self.rollback_completed:
            parts.append("Rollback: Completed")

        return " | ".join(parts)


class ValidationError(ProvisioningError):
    """Exception raised when container validation fails."""

    def __init__(
        self,
        message: str,
        validation_type: str,
        failed_checks: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.validation_type = validation_type
        self.failed_checks = failed_checks or []


class RollbackError(ProvisioningError):
    """Exception raised when rollback operations fail."""

    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        partial_rollback: bool = False,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.original_error = original_error
        self.partial_rollback = partial_rollback


class ResourceCalculationError(ProvisioningError):
    """Exception raised when resource calculation fails."""

    def __init__(
        self,
        message: str,
        customer_count: Optional[int] = None,
        requested_resources: Optional[dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.customer_count = customer_count
        self.requested_resources = requested_resources


class TemplateError(ProvisioningError):
    """Exception raised when container template operations fail."""

    def __init__(
        self,
        message: str,
        template_name: Optional[str] = None,
        template_version: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.template_name = template_name
        self.template_version = template_version


class InfrastructureError(ProvisioningError):
    """Exception raised when infrastructure provisioning fails."""

    def __init__(
        self,
        message: str,
        infrastructure_type: str,  # kubernetes, docker, etc.
        resource_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.infrastructure_type = infrastructure_type
        self.resource_name = resource_name


class TimeoutError(ProvisioningError):
    """Exception raised when provisioning operations timeout."""

    def __init__(self, message: str, timeout_seconds: int, operation: str, **kwargs):
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.operation = operation


class ConfigurationError(ProvisioningError):
    """Exception raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.config_value = config_value


class DeploymentError(ProvisioningError):
    """Exception raised during container deployment phase."""

    def __init__(
        self,
        message: str,
        deployment_phase: str,
        container_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.deployment_phase = deployment_phase
        self.container_id = container_id


class HealthCheckError(ValidationError):
    """Exception raised when health checks fail during provisioning."""

    def __init__(
        self,
        message: str,
        health_check_type: str,
        endpoint: Optional[str] = None,
        expected_status: Optional[int] = None,
        actual_status: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message, validation_type=health_check_type, **kwargs)
        self.health_check_type = health_check_type
        self.endpoint = endpoint
        self.expected_status = expected_status
        self.actual_status = actual_status
