"""Exception classes for Kubernetes orchestration service."""


class OrchestrationError(Exception):
    """Base exception for Kubernetes orchestration errors."""
    pass


class DeploymentNotFoundError(OrchestrationError):
    """Raised when a tenant deployment is not found."""
    pass


class ResourceLimitExceededError(OrchestrationError):
    """Raised when resource limits would be exceeded."""
    pass


class DeploymentFailedError(OrchestrationError):
    """Raised when a deployment operation fails."""
    pass


class ScalingError(OrchestrationError):
    """Raised when scaling operations fail."""
    pass


class TemplateProcessingError(OrchestrationError):
    """Raised when template processing fails."""
    pass


class KubernetesConnectionError(OrchestrationError):
    """Raised when connection to Kubernetes cluster fails."""
    pass


class TenantResourceError(OrchestrationError):
    """Raised when tenant-specific resource operations fail."""
    pass