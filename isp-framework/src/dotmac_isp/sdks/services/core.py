"""Core services SDK module."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ServiceStatus(str, Enum):
    """Service status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PROVISIONING = "provisioning"
    DEPROVISIONING = "deprovisioning"


@dataclass
class ServiceInfo:
    """Service information schema."""

    service_id: str
    service_name: str
    service_type: str
    status: ServiceStatus
    customer_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ServiceCoreSDK:
    """Core services SDK for basic service operations."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id

    async def get_service_info(self, service_id: str) -> ServiceInfo:
        """Get service information."""
        # Mock implementation
        return ServiceInfo(
            service_id=service_id,
            service_name="Mock Service",
            service_type="internet",
            status=ServiceStatus.ACTIVE,
        )

    async def list_services(
        self, customer_id: Optional[str] = None
    ) -> List[ServiceInfo]:
        """List services."""
        # Mock implementation
        return []
