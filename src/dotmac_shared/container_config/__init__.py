"""
DotMac Container Configuration Service

A comprehensive configuration management service for multi-tenant ISP container deployments.
Handles per-container configuration injection, environment-specific settings, and secure secret management.
"""

from .core.config_generator import ConfigurationGenerator
from .core.feature_flags import FeatureFlagManager
from .core.secret_manager import SecretManager
from .core.template_engine import TemplateEngine
from .core.validators import ConfigurationValidator, ValidationResult
from .schemas.config_schemas import (
    DatabaseConfig,
    ExternalServiceConfig,
    FeatureFlagConfig,
    ISPConfiguration,
    ServiceConfig,
)
from .schemas.feature_schemas import FeatureDefinition, FeatureFlag, PlanFeatures
from .schemas.tenant_schemas import EnvironmentType, SubscriptionPlan, TenantInfo

__version__ = "0.1.0"
__author__ = "DotMac Framework Team"
__email__ = "support@dotmac-framework.com"
__license__ = "MIT"
__description__ = "Container configuration management service for multi-tenant ISP deployments"

# Main exports for easy importing
__all__ = [
    # Core components
    "ConfigurationGenerator",
    "TemplateEngine",
    "SecretManager",
    "FeatureFlagManager",
    "ConfigurationValidator",
    "ValidationResult",
    # Configuration schemas
    "ISPConfiguration",
    "DatabaseConfig",
    "ServiceConfig",
    "ExternalServiceConfig",
    "FeatureFlagConfig",
    # Tenant schemas
    "TenantInfo",
    "SubscriptionPlan",
    "EnvironmentType",
    # Feature schemas
    "FeatureDefinition",
    "FeatureFlag",
    "PlanFeatures",
]

# Package metadata
__package_info__ = {
    "name": "dotmac-container-config",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "author_email": __email__,
    "license": __license__,
    "url": "https://github.com/dotmac-framework/container-config",
    "keywords": ["configuration", "templates", "multi-tenant", "isp", "containers"],
    "classifiers": [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
}


def get_version() -> str:
    """Get the package version."""
    return __version__


def get_package_info() -> dict:
    """Get complete package information."""
    return __package_info__.copy()
