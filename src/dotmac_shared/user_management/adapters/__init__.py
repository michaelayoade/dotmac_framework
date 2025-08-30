"""
User Management Platform Adapters.

Provides platform-specific adapters for integrating the unified user management
service with ISP Framework and Management Platform.
"""

from .base_adapter import BaseUserAdapter
from .isp_user_adapter import (
    ISPUserAdapter,
    ISPUserService,
    create_isp_user_adapter,
    create_isp_user_service,
)
from .management_platform_adapter import (
    ManagementPlatformUserAdapter,
    create_management_user_adapter,
    create_management_user_service,
)

__all__ = [
    # Base adapter
    "BaseUserAdapter",
    # ISP Framework adapter
    "ISPUserAdapter",
    "ISPUserService",
    "create_isp_user_adapter",
    "create_isp_user_service",
    # Management Platform adapter
    "ManagementPlatformUserAdapter",
    "create_management_user_adapter",
    "create_management_user_service",
]
