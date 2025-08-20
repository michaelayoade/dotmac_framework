"""
Exception classes for DotMac Developer Tools.
"""


class DevToolsError(Exception):
    """Base exception for DotMac Developer Tools."""
    pass


class ConfigurationError(DevToolsError):
    """Configuration-related errors."""
    pass


class TemplateError(DevToolsError):
    """Template processing errors."""
    pass


class GenerationError(DevToolsError):
    """Code generation errors."""
    pass


class ValidationError(DevToolsError):
    """Validation errors."""
    pass


class PortalError(DevToolsError):
    """Developer portal errors."""
    pass


class SecurityError(DevToolsError):
    """Security and zero-trust errors."""
    pass


class SDKGenerationError(GenerationError):
    """SDK generation specific errors."""
    pass


class ServiceScaffoldingError(GenerationError):
    """Service scaffolding specific errors."""
    pass


class EnvironmentError(DevToolsError):
    """Environment setup and validation errors."""
    pass


class NetworkError(DevToolsError):
    """Network-related errors."""
    pass


class AuthenticationError(SecurityError):
    """Authentication errors."""
    pass


class AuthorizationError(SecurityError):
    """Authorization errors."""
    pass


class CertificateError(SecurityError):
    """Certificate management errors."""
    pass


class PolicyError(SecurityError):
    """Security policy errors."""
    pass
