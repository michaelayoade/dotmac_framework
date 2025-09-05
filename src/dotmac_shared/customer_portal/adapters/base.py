"""
Base adapter interface for customer portals.

Defines the contract that platform-specific adapters must implement.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from ..core.schemas import ServiceSummary, ServiceUsageData, UsageSummary


class CustomerPortalAdapter(ABC):
    """
    Abstract base class for platform-specific customer portal adapters.

    This defines the interface that ISP and Management platform adapters
    must implement to integrate with the unified portal service.
    """

    def __init__(self, tenant_id: UUID):
        """Initialize adapter with tenant context."""
        self.tenant_id = tenant_id

    @abstractmethod
    async def get_customer_info(self, customer_id: UUID) -> dict[str, Any]:
        """
        Get basic customer information from the platform.

        Should return a dictionary with at minimum:
        - account_number: str
        - status: str
        - created_at: datetime
        - platform_specific fields
        """
        pass

    @abstractmethod
    async def get_customer_services(self, customer_id: UUID) -> list[ServiceSummary]:
        """
        Get customer's services from the platform.

        Returns standardized service summaries regardless of platform.
        """
        pass

    @abstractmethod
    async def get_platform_data(self, customer_id: UUID) -> dict[str, Any]:
        """
        Get platform-specific data for the customer.

        This allows each platform to include custom data in the dashboard
        without affecting the core portal service logic.
        """
        pass

    @abstractmethod
    async def update_customer_custom_fields(
        self, customer_id: UUID, custom_fields: dict[str, Any]
    ) -> bool:
        """
        Update platform-specific custom fields for the customer.
        """
        pass

    @abstractmethod
    async def get_service_usage(
        self,
        customer_id: UUID,
        service_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ServiceUsageData:
        """
        Get usage data for a specific service.

        This may not be applicable for all platforms (e.g., Management platform
        customers may not have usage tracking).
        """
        pass

    # Optional methods that platforms can override

    async def get_usage_summary(self, customer_id: UUID) -> Optional[UsageSummary]:
        """
        Get overall usage summary for the customer.

        Default implementation returns None. ISP adapter should override this.
        """
        return None

    async def validate_customer_access(
        self, customer_id: UUID, requesting_user_id: UUID
    ) -> bool:
        """
        Validate that the requesting user can access this customer's data.

        Default implementation allows access if user_id matches customer_id.
        Platforms can override for more complex access control.
        """
        return customer_id == requesting_user_id

    async def get_available_actions(self, customer_id: UUID) -> list[str]:
        """
        Get available actions for the customer in this platform.

        Returns a list of action names that the customer can perform.
        """
        return ["update_profile", "view_billing", "create_ticket", "view_services"]

    async def can_perform_action(self, customer_id: UUID, action: str) -> bool:
        """
        Check if customer can perform a specific action.
        """
        available_actions = await self.get_available_actions(customer_id)
        return action in available_actions
