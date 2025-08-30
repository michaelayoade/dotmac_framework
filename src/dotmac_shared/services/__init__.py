"""
Shared services module for DotMac framework.
"""

from .service_factory import DeploymentAwareServiceFactory
from .service_registry import ServiceRegistry

__all__ = ["DeploymentAwareServiceFactory", "ServiceRegistry"]
