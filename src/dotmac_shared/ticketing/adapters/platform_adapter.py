"""
Platform adapters for integrating ticketing with Management Platform and ISP Framework.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.models import TicketCategory, TicketPriority, TicketResponse
from ..services.ticket_service import TicketService

logger = logging.getLogger(__name__)


class BasePlatformAdapter(ABC):
    """Base adapter for platform-specific ticketing integration."""

    def __init__(self, ticket_service: TicketService):
        self.ticket_service = ticket_service

    @abstractmethod
    async def get_customer_info(self, tenant_id: str, customer_id: str) -> dict[str, Any]:
        """Get customer information from the platform."""
        pass

    @abstractmethod
    async def get_user_info(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        """Get user/staff information from the platform."""
        pass

    @abstractmethod
    async def send_notification(self, notification_type: str, recipient: str, ticket: TicketResponse, **kwargs) -> bool:
        """Send notification about ticket events."""
        pass


class ManagementPlatformAdapter(BasePlatformAdapter):
    """Adapter for Management Platform integration."""

    def __init__(self, ticket_service: TicketService, management_client=None):
        super().__init__(ticket_service)
        self.management_client = management_client

    async def get_customer_info(self, tenant_id: str, customer_id: str) -> dict[str, Any]:
        """Get customer info from Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.get_customer(tenant_id, customer_id)
            return {"id": customer_id, "name": "Unknown Customer"}
        except Exception as e:
            logger.error(f"Error getting customer info: {e}")
            return {"id": customer_id, "name": "Unknown Customer"}

    async def get_user_info(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        """Get user info from Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.get_user(tenant_id, user_id)
            return {"id": user_id, "name": "Unknown User"}
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {"id": user_id, "name": "Unknown User"}

    async def send_notification(self, notification_type: str, recipient: str, ticket: TicketResponse, **kwargs) -> bool:
        """Send notification via Management Platform."""
        try:
            if self.management_client:
                return await self.management_client.send_notification(
                    notification_type,
                    recipient,
                    {
                        "ticket_number": ticket.ticket_number,
                        "title": ticket.title,
                        "status": ticket.status,
                        "priority": ticket.priority,
                        **kwargs,
                    },
                )
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    async def create_billing_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        invoice_id: str,
        issue_description: str,
    ) -> TicketResponse:
        """Create a billing-related ticket."""
        return await self.ticket_service.create_customer_ticket(
            db,
            tenant_id,
            customer_id,
            title=f"Billing Issue - Invoice {invoice_id}",
            description=issue_description,
            category=TicketCategory.BILLING_INQUIRY,
            priority=TicketPriority.HIGH,
            metadata={"invoice_id": invoice_id, "source": "billing_system"},
        )


class ISPPlatformAdapter(BasePlatformAdapter):
    """Adapter for ISP Framework integration."""

    def __init__(self, ticket_service: TicketService, isp_client=None):
        super().__init__(ticket_service)
        self.isp_client = isp_client

    async def get_customer_info(self, tenant_id: str, customer_id: str) -> dict[str, Any]:
        """Get customer info from ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.get_customer(tenant_id, customer_id)
            return {"id": customer_id, "name": "Unknown Customer"}
        except Exception as e:
            logger.error(f"Error getting customer info: {e}")
            return {"id": customer_id, "name": "Unknown Customer"}

    async def get_user_info(self, tenant_id: str, user_id: str) -> dict[str, Any]:
        """Get technician info from ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.get_technician(tenant_id, user_id)
            return {"id": user_id, "name": "Unknown Technician"}
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {"id": user_id, "name": "Unknown Technician"}

    async def send_notification(self, notification_type: str, recipient: str, ticket: TicketResponse, **kwargs) -> bool:
        """Send notification via ISP Framework."""
        try:
            if self.isp_client:
                return await self.isp_client.send_notification(
                    notification_type,
                    recipient,
                    {
                        "ticket_number": ticket.ticket_number,
                        "title": ticket.title,
                        "status": ticket.status,
                        "priority": ticket.priority,
                        **kwargs,
                    },
                )
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    async def create_network_issue_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        service_id: str,
        issue_description: str,
        network_data: Optional[dict[str, Any]] = None,
    ) -> TicketResponse:
        """Create a network-related ticket."""
        metadata = {"service_id": service_id, "source": "network_monitoring"}
        if network_data:
            metadata.update(network_data)

        return await self.ticket_service.create_customer_ticket(
            db,
            tenant_id,
            customer_id,
            title=f"Network Issue - Service {service_id}",
            description=issue_description,
            category=TicketCategory.NETWORK_ISSUE,
            priority=TicketPriority.URGENT,
            metadata=metadata,
        )

    async def create_service_request_ticket(
        self,
        db: AsyncSession,
        tenant_id: str,
        customer_id: str,
        request_type: str,
        details: str,
    ) -> TicketResponse:
        """Create a service request ticket."""
        return await self.ticket_service.create_customer_ticket(
            db,
            tenant_id,
            customer_id,
            title=f"Service Request - {request_type}",
            description=details,
            category=TicketCategory.SERVICE_REQUEST,
            priority=TicketPriority.NORMAL,
            metadata={"request_type": request_type, "source": "customer_portal"},
        )


class TicketingPlatformAdapter:
    """Main adapter that routes to appropriate platform adapters."""

    def __init__(
        self,
        management_adapter: ManagementPlatformAdapter = None,
        isp_adapter: ISPPlatformAdapter = None,
    ):
        self.management_adapter = management_adapter
        self.isp_adapter = isp_adapter

    def get_adapter(self, platform: str) -> Optional[BasePlatformAdapter]:
        """Get adapter for specific platform."""
        if platform == "management":
            return self.management_adapter
        elif platform == "isp":
            return self.isp_adapter
        return None

    async def create_platform_ticket(
        self,
        platform: str,
        db: AsyncSession,
        tenant_id: str,
        ticket_type: str,
        **kwargs,
    ) -> Optional[TicketResponse]:
        """Create ticket using platform-specific logic."""
        adapter = self.get_adapter(platform)
        if not adapter:
            return None

        if platform == "management" and ticket_type == "billing":
            return await adapter.create_billing_ticket(db, tenant_id, **kwargs)
        elif platform == "isp" and ticket_type == "network":
            return await adapter.create_network_issue_ticket(db, tenant_id, **kwargs)
        elif platform == "isp" and ticket_type == "service_request":
            return await adapter.create_service_request_ticket(db, tenant_id, **kwargs)

        # Fallback to generic ticket creation
        return await adapter.ticket_service.create_customer_ticket(db, tenant_id, **kwargs)
