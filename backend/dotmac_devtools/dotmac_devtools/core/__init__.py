"""
Core module for DotMac Developer Tools.

Provides configuration management, exception handling, and core utilities.
"""

from .config import DevToolsConfig, load_config, save_config, validate_environment
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    CertificateError,
    ConfigurationError,
    DevToolsError,
    EnvironmentError,
    GenerationError,
    NetworkError,
    PolicyError,
    PortalError,
    SDKGenerationError,
    SecurityError,
    ServiceScaffoldingError,
    TemplateError,
    ValidationError,
)

__all__ = [
    # Configuration
    'DevToolsConfig',
    'load_config',
    'save_config',
    'validate_environment',
    # Exceptions
    'DevToolsError',
    'ConfigurationError',
    'TemplateError',
    'GenerationError',
    'ValidationError',
    'PortalError',
    'SecurityError',
    'SDKGenerationError',
    'ServiceScaffoldingError',
    'EnvironmentError',
    'NetworkError',
    'AuthenticationError',
    'AuthorizationError',
    'CertificateError',
    'PolicyError',
]
