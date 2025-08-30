"""
Deployment utilities for DotMac platforms.

This module provides tools for managing tenant container provisioning,
Kubernetes integration, and deployment automation.
"""

from .tenant_provisioning import (
    TenantConfigurationBuilder,
    TenantNamespaceGenerator,
    TenantProvisioningEngine,
    TenantProvisioningRequest,
    TenantProvisioningResult,
    TenantResourceCalculator,
    provisioning_engine,
)

__all__ = [
    "TenantProvisioningRequest",
    "TenantProvisioningResult",
    "TenantResourceCalculator",
    "TenantNamespaceGenerator",
    "TenantConfigurationBuilder",
    "TenantProvisioningEngine",
    "provisioning_engine",
]
