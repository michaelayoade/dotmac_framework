"""
Consolidated Base Service Architecture

Provides unified service patterns consolidating functionality from:
- dotmac_shared/services/base_service.py
- dotmac_isp/shared/base_service.py
- dotmac_management/shared/base_service.py
- And other base service implementations

This module establishes the single source of truth for service architecture.
"""

from .base_service import BaseManagementService, BaseService
from .exceptions import ServiceConfigurationError, ServiceDependencyError, ServiceError, ServiceNotFoundError
from .service_factory import ServiceBuilder, ServiceFactory
from .service_registry import ServiceRegistry, ServiceRegistryBuilder

__all__ = [
    "BaseService",
    "BaseManagementService",
    "ServiceFactory",
    "ServiceBuilder",
    "ServiceRegistry",
    "ServiceRegistryBuilder",
    "ServiceError",
    "ServiceNotFoundError",
    "ServiceConfigurationError",
    "ServiceDependencyError",
]
