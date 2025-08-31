"""
Configuration management for the unified monitoring system.

This module provides configuration handling for monitoring services,
including version detection and environment configuration.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel, ConfigDict
    from pydantic_settings import BaseSettings

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = dict
    BaseSettings = dict

# Leverage existing configuration management
try:
    from dotmac_shared.application.config import DeploymentContext, DeploymentMode

    EXISTING_CONFIG_AVAILABLE = True
except ImportError:
    EXISTING_CONFIG_AVAILABLE = False
    DeploymentContext = None
    DeploymentMode = None

try:
    import toml

    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False


class MonitoringConfig:
    """Configuration for monitoring services."""

    def __init__(
        self,
        service_name: str,
        version: Optional[str] = None,
        environment: Optional[str] = None,
        enabled: bool = True,
        custom_labels: Optional[Dict[str, str]] = None,
        deployment_context: Optional[Any] = None,  # DeploymentContext if available
    ):
        """
        Initialize monitoring configuration.

        Args:
            service_name: Name of the service
            version: Service version (auto-detected if None)
            environment: Environment name (auto-detected if None)
            enabled: Whether monitoring is enabled
            custom_labels: Additional labels for metrics
            deployment_context: Existing deployment context to leverage
        """
        self.service_name = service_name
        self.deployment_context = deployment_context

        # Leverage existing deployment context if available
        if EXISTING_CONFIG_AVAILABLE and deployment_context:
            self.version = (
                version
                or getattr(deployment_context, "version", None)
                or self._detect_version()
            )
            self.environment = (
                environment
                or getattr(deployment_context, "environment", None)
                or self._detect_environment()
            )
        else:
            self.version = version or self._detect_version()
            self.environment = environment or self._detect_environment()

        self.enabled = enabled
        self.custom_labels = custom_labels or {}

    def _detect_version(self) -> str:
        """Auto-detect service version from various sources."""
        # Try environment variable first
        version = os.getenv("SERVICE_VERSION")
        if version:
            return version

        # Try to read from pyproject.toml
        if TOML_AVAILABLE:
            version = self._read_version_from_pyproject()
            if version:
                return version

        # Try to read from package metadata
        try:
            import importlib.metadata

            version = importlib.metadata.version("dotmac-framework")
            return version
        except Exception:
            pass

        # Default fallback
        return "unknown"

    def _detect_environment(self) -> str:
        """Auto-detect environment from various sources."""
        # Check common environment variables
        env_vars = [
            "ENVIRONMENT",
            "ENV",
            "DEPLOYMENT_ENV",
            "STAGE",
            "DOTMAC_ENVIRONMENT",
        ]

        for var in env_vars:
            env = os.getenv(var)
            if env:
                return env.lower()

        # Check for common environment indicators
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            return "kubernetes"

        if os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"):
            return "aws"

        if os.path.exists("/.dockerenv"):
            return "docker"

        # Default based on common patterns
        if os.getenv("DEBUG") == "true":
            return "development"

        return "production"

    def _read_version_from_pyproject(self) -> Optional[str]:
        """Try to read version from pyproject.toml."""
        try:
            # Look for pyproject.toml in current directory and parent directories
            current_path = Path.cwd()

            for path in [current_path] + list(current_path.parents):
                pyproject_path = path / "pyproject.toml"
                if pyproject_path.exists():
                    with open(pyproject_path, "r") as f:
                        config = toml.load(f)

                    # Check poetry section first
                    if "tool" in config and "poetry" in config["tool"]:
                        return config["tool"]["poetry"].get("version")

                    # Check project section
                    if "project" in config:
                        return config["project"].get("version")

        except Exception:
            pass

        return None

    def get_service_info(self) -> Dict[str, str]:
        """Get service information for metrics."""
        info = {
            "service": self.service_name,
            "version": self.version,
            "environment": self.environment,
        }

        # Add custom labels
        info.update(self.custom_labels)

        return info

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "service_name": self.service_name,
            "version": self.version,
            "environment": self.environment,
            "enabled": self.enabled,
            "custom_labels": self.custom_labels,
        }


class MonitoringSettings(BaseSettings if PYDANTIC_AVAILABLE else dict):
    """
    Monitoring settings that can be configured via environment variables.

    Environment variables:
    - MONITORING_ENABLED: Enable/disable monitoring (default: true)
    - MONITORING_SERVICE_NAME: Service name for metrics
    - MONITORING_VERSION: Service version
    - MONITORING_ENVIRONMENT: Environment name
    - MONITORING_LABELS: JSON string of additional labels
    """

    if PYDANTIC_AVAILABLE:
        enabled: bool = True
        service_name: str = "dotmac"
        version: Optional[str] = None
        environment: Optional[str] = None
        labels: Dict[str, str] = {}

        model_config = ConfigDict(
            env_prefix="MONITORING_",
            case_sensitive=False
        )

    else:

        def __init__(self, **kwargs):
            self.enabled = kwargs.get("enabled", True)
            self.service_name = kwargs.get("service_name", "dotmac")
            self.version = kwargs.get("version")
            self.environment = kwargs.get("environment")
            self.labels = kwargs.get("labels", {})


def create_monitoring_config(
    service_name: str,
    version: Optional[str] = None,
    environment: Optional[str] = None,
    **kwargs,
) -> MonitoringConfig:
    """
    Factory function to create monitoring configuration.

    Args:
        service_name: Name of the service
        version: Service version (auto-detected if None)
        environment: Environment name (auto-detected if None)
        **kwargs: Additional configuration options

    Returns:
        MonitoringConfig: Configured monitoring settings
    """
    return MonitoringConfig(
        service_name=service_name, version=version, environment=environment, **kwargs
    )


def load_monitoring_settings() -> MonitoringSettings:
    """Load monitoring settings from environment."""
    if PYDANTIC_AVAILABLE:
        return MonitoringSettings()
    else:
        return MonitoringSettings(
            enabled=os.getenv("MONITORING_ENABLED", "true").lower() == "true",
            service_name=os.getenv("MONITORING_SERVICE_NAME", "dotmac"),
            version=os.getenv("MONITORING_VERSION"),
            environment=os.getenv("MONITORING_ENVIRONMENT"),
        )
