"""
Unified Portal ID Generation Service.

This package consolidates all portal ID generation logic across platforms,
eliminating duplication and providing consistent, configurable ID generation.

Replaces:
- dotmac_isp.modules.identity.portal_id_generator
- dotmac_isp.modules.portal_management.service._generate_portal_id
- dotmac_isp.modules.portal_management.models._generate_portal_id
- dotmac_isp.modules.identity.repository._generate_portal_id

Usage:
    # Simple usage with defaults
    portal_id = generate_portal_id()

    # Async with collision checking
    from dotmac_shared.portal_id.adapters import ISPPortalIdCollisionChecker
    collision_checker = ISPPortalIdCollisionChecker(db_session, tenant_id)
    portal_id = await generate_portal_id_async(collision_checker=collision_checker)

    # Custom configuration
    service = PortalIdServiceFactory.create_custom_service(
        pattern=PortalIdPattern.ALPHANUMERIC_CLEAN,
        length=10,
        prefix="ISP-"
    )
    portal_id = service.generate_portal_id_sync()
"""

from .adapters import ISPPortalIdCollisionChecker, ManagementPortalIdCollisionChecker
from .core.service import (
    PortalIdCollisionChecker,
    PortalIdConfig,
    PortalIdPattern,
    PortalIdServiceFactory,
    UnifiedPortalIdService,
    generate_portal_id,
    generate_portal_id_async,
    get_portal_id_service,
    reload_global_services,
)

__all__ = [
    # Core service classes
    "UnifiedPortalIdService",
    "PortalIdServiceFactory",
    "PortalIdPattern",
    "PortalIdConfig",
    "PortalIdCollisionChecker",
    # Convenience functions
    "generate_portal_id",
    "generate_portal_id_async",
    "get_portal_id_service",
    "reload_global_services",
    # Platform adapters
    "ISPPortalIdCollisionChecker",
    "ManagementPortalIdCollisionChecker",
]
