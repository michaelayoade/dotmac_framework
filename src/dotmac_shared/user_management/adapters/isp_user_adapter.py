"""
ISP Platform User Management Adapter.

Integrates the unified user management service with the ISP Framework,
mapping ISP-specific user models (customers, technicians) and providing
ISP-tailored user management functionality.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.user_lifecycle_service import UserLifecycleService
from ..schemas.lifecycle_schemas import (
    UserActivation,
    UserDeactivation,
    UserRegistration,
)
from ..schemas.user_schemas import (
    UserCreate,
    UserProfile,
    UserResponse,
    UserStatus,
    UserSummary,
    UserType,
    UserUpdate,
)
from .base_adapter import BaseUserAdapter

# ISP Framework imports (these would be the actual imports in practice)
try:
    from dotmac_isp.core.celery_app import celery_app
    from dotmac_isp.core.database import get_async_session
    from dotmac_isp.modules.identity.models import Customer
    from dotmac_isp.modules.identity.models import User as ISPUser
    from dotmac_isp.modules.identity.schemas import (
        CustomerCreate,
        CustomerResponse,
        CustomerUpdate,
    )
    from dotmac_isp.modules.identity.schemas import UserCreate as ISPUserCreate
    from dotmac_isp.modules.identity.schemas import UserResponse as ISPUserResponse
    from dotmac_isp.modules.services.models import ServiceInstance, ServiceSubscription
    from dotmac_isp.shared.base_service import BaseTenantService
except ImportError:
    # Fallback types for development/testing
    Customer = Dict[str, Any]
    ISPUser = Dict[str, Any]
    ServiceInstance = Dict[str, Any]
    ServiceSubscription = Dict[str, Any]


class ISPUserAdapter(BaseUserAdapter):
    """
    Adapter that integrates unified user management with ISP Framework.

    Handles ISP-specific user types (customers, technicians, admins) while
    leveraging the unified user management service for core operations.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: Optional[UUID] = None,
        user_service: Optional[UserLifecycleService] = None,
    ):
        """Initialize ISP user adapter."""
        super().__init__(db_session, tenant_id, user_service)
        self.platform_type = "isp_framework"

    # ISP Customer Management
    async def register_customer(
        self,
        customer_data: Dict[str, Any],
        service_instance: Optional[ServiceInstance] = None,
    ) -> UserResponse:
        """
        Register a new ISP customer.

        Creates both a unified user account and ISP-specific customer record.
        """

        # Map ISP customer data to unified user format
        user_registration = self._map_customer_to_user_registration(customer_data)

        # Add ISP-specific context
        user_registration.platform_specific.update(
            {
                "platform": self.platform_type,
                "user_type": "customer",
                "customer_data": customer_data,
                "service_instance_id": (
                    str(service_instance.id) if service_instance else None
                ),
                "registration_source": "isp_customer_portal",
                "requires_service_activation": True,
            }
        )

        # Register user through unified service
        user = await self.user_service.register_user(user_registration)

        # Create ISP-specific customer record
        customer = await self._create_isp_customer_record(
            user, customer_data, service_instance
        )

        # Link customer to service instance if provided
        if service_instance:
            await self._link_customer_to_service(customer, service_instance)

        # Enhance user response with ISP-specific data
        user = await self._enhance_user_with_isp_data(user, customer)

        # Trigger ISP-specific post-registration tasks
        await self._trigger_isp_customer_registration_tasks(user, customer)

        return user

    async def activate_customer(
        self,
        user_id: UUID,
        verification_code: str,
        service_activation_data: Optional[Dict[str, Any]] = None,
    ) -> UserResponse:
        """Activate ISP customer account with optional service activation."""

        # Activate user through unified service
        activation_data = UserActivation(
            user_id=user_id,
            verification_code=verification_code,
            activation_type="email_verification",
            platform_context={
                "platform": self.platform_type,
                "service_activation_data": service_activation_data or {},
                "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            },
        )

        user = await self.user_service.activate_user(activation_data)

        # Perform ISP-specific activation tasks
        if service_activation_data:
            await self._activate_customer_services(user.id, service_activation_data)

        # Update ISP customer record
        await self._update_isp_customer_status(user.id, "active")

        # Trigger post-activation tasks
        await self._trigger_isp_customer_activation_tasks(user)

        return user

    async def update_customer_profile(
        self, user_id: UUID, profile_updates: Dict[str, Any]
    ) -> UserResponse:
        """Update ISP customer profile with ISP-specific data."""

        # Extract ISP-specific profile data
        isp_profile_data = profile_updates.pop("isp_specific", {})
        service_preferences = profile_updates.pop("service_preferences", {})
        billing_preferences = profile_updates.pop("billing_preferences", {})

        # Map to unified profile update
        unified_updates = UserUpdate(
            **profile_updates,
            platform_specific={
                "isp_profile": isp_profile_data,
                "service_preferences": service_preferences,
                "billing_preferences": billing_preferences,
            },
        )

        # Update through unified service
        user = await self.user_service.update_user(user_id, unified_updates)

        # Update ISP customer record
        await self._update_isp_customer_profile(user_id, isp_profile_data)

        return user

    # ISP Technician Management
    async def register_technician(
        self,
        technician_data: Dict[str, Any],
        certifications: Optional[List[Dict[str, Any]]] = None,
        territory_assignments: Optional[List[UUID]] = None,
    ) -> UserResponse:
        """Register a new ISP technician."""

        # Map technician data to unified user format
        user_registration = self._map_technician_to_user_registration(
            technician_data, certifications, territory_assignments
        )

        # Add ISP technician-specific context
        user_registration.platform_specific.update(
            {
                "platform": self.platform_type,
                "user_type": "technician",
                "technician_data": technician_data,
                "certifications": certifications or [],
                "territory_assignments": [
                    str(t) for t in (territory_assignments or [])
                ],
                "requires_background_check": True,
                "requires_training_completion": True,
            }
        )

        # Register user
        user = await self.user_service.register_user(user_registration)

        # Create ISP technician record
        technician = await self._create_isp_technician_record(
            user, technician_data, certifications, territory_assignments
        )

        # Enhance user response
        user = await self._enhance_user_with_technician_data(user, technician)

        return user

    async def assign_technician_territory(
        self,
        technician_id: UUID,
        territory_ids: List[UUID],
        effective_date: Optional[date] = None,
    ) -> UserResponse:
        """Assign territories to a technician."""

        # Update technician territory assignments
        await self._update_technician_territories(
            technician_id, territory_ids, effective_date
        )

        # Update user platform-specific data
        user = await self.user_service.get_user(technician_id)

        platform_updates = user.platform_specific.copy()
        platform_updates["territory_assignments"] = [str(t) for t in territory_ids]
        platform_updates["territory_assigned_at"] = datetime.utcnow().isoformat()

        updated_user = await self.user_service.update_user(
            technician_id, UserUpdate(platform_specific=platform_updates)
        )

        # Trigger territory assignment tasks
        await self._trigger_territory_assignment_tasks(technician_id, territory_ids)

        return updated_user

    # ISP Service Integration
    async def link_user_to_service(
        self,
        user_id: UUID,
        service_instance_id: UUID,
        relationship_type: str = "primary",
    ) -> bool:
        """Link a user to an ISP service instance."""

        # Create service relationship
        await self._create_user_service_relationship(
            user_id, service_instance_id, relationship_type
        )

        # Update user platform data
        user = await self.user_service.get_user(user_id)
        platform_updates = user.platform_specific.copy()

        service_links = platform_updates.get("service_links", [])
        service_links.append(
            {
                "service_instance_id": str(service_instance_id),
                "relationship_type": relationship_type,
                "linked_at": datetime.utcnow().isoformat(),
            }
        )
        platform_updates["service_links"] = service_links

        await self.user_service.update_user(
            user_id, UserUpdate(platform_specific=platform_updates)
        )

        return True

    async def get_user_services(
        self, user_id: UUID, include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all services associated with a user."""

        # Get service relationships from ISP database
        service_relationships = await self._get_user_service_relationships(
            user_id, include_inactive
        )

        # Enrich with service instance details
        services = []
        for relationship in service_relationships:
            service_instance = await self._get_service_instance(
                relationship["service_instance_id"]
            )

            if service_instance:
                services.append(
                    {
                        **service_instance,
                        "relationship_type": relationship["relationship_type"],
                        "linked_at": relationship["linked_at"],
                    }
                )

        return services

    # User Search and Management
    async def search_customers(
        self, search_params: Dict[str, Any], include_service_info: bool = True
    ) -> Dict[str, Any]:
        """Search ISP customers with service information."""

        # Add ISP-specific filters
        search_params["user_type"] = UserType.CUSTOMER
        search_params["tenant_id"] = self.tenant_id

        # Search through unified service
        search_result = await self.user_service.search_users(search_params)

        # Enhance results with ISP-specific data
        if include_service_info:
            enhanced_users = []
            for user in search_result.users:
                services = await self.get_user_services(user.id)
                enhanced_user = user.model_dump()
                enhanced_user["services"] = services
                enhanced_user["service_count"] = len(services)
                enhanced_users.append(enhanced_user)

            search_result.users = enhanced_users

        return search_result.model_dump()

    # Helper Methods for ISP Integration
    async def _create_isp_customer_record(
        self,
        user: UserResponse,
        customer_data: Dict[str, Any],
        service_instance: Optional[ServiceInstance],
    ):
        """Create ISP-specific customer record."""
        # Implementation would create Customer model instance
        # with relationship to unified User
        pass

    async def _create_isp_technician_record(
        self,
        user: UserResponse,
        technician_data: Dict[str, Any],
        certifications: Optional[List[Dict[str, Any]]],
        territory_assignments: Optional[List[UUID]],
    ):
        """Create ISP-specific technician record."""
        # Implementation would create Technician model instance
        pass

    async def _link_customer_to_service(
        self, customer, service_instance: ServiceInstance
    ):
        """Link customer to service instance."""
        pass

    async def _activate_customer_services(
        self, user_id: UUID, service_activation_data: Dict[str, Any]
    ):
        """Activate customer services after account activation."""
        pass

    async def _trigger_isp_customer_registration_tasks(
        self, user: UserResponse, customer
    ):
        """Trigger ISP-specific tasks after customer registration."""
        if celery_app:
            # Send welcome email with ISP branding
            celery_app.send_task(
                "dotmac_isp.modules.notifications.tasks.send_customer_welcome_email",
                args=[str(user.id), customer.id],
            )

            # Create billing account
            celery_app.send_task(
                "dotmac_isp.modules.billing.tasks.create_customer_billing_account",
                args=[str(user.id), customer.id],
            )

            # Initialize customer portal access
            celery_app.send_task(
                "dotmac_isp.portals.customer.tasks.setup_portal_access",
                args=[str(user.id)],
            )

    def _map_customer_to_user_registration(
        self, customer_data: Dict[str, Any]
    ) -> UserRegistration:
        """Map ISP customer data to unified user registration."""
        return UserRegistration(
            username=customer_data.get("email", "").split("@")[0],
            email=customer_data["email"],
            first_name=customer_data["first_name"],
            last_name=customer_data["last_name"],
            user_type=UserType.CUSTOMER,
            password=customer_data["password"],
            phone=customer_data.get("phone"),
            tenant_id=self.tenant_id,
            registration_source="isp_customer_portal",
        )

    def _map_technician_to_user_registration(
        self,
        technician_data: Dict[str, Any],
        certifications: Optional[List[Dict[str, Any]]],
        territory_assignments: Optional[List[UUID]],
    ) -> UserRegistration:
        """Map ISP technician data to unified user registration."""
        return UserRegistration(
            username=technician_data["employee_id"],
            email=technician_data["email"],
            first_name=technician_data["first_name"],
            last_name=technician_data["last_name"],
            user_type=UserType.TECHNICIAN,
            password=technician_data["password"],
            phone=technician_data.get("phone"),
            tenant_id=self.tenant_id,
            registration_source="isp_admin_portal",
            requires_approval=True,
        )


class ISPUserService(BaseTenantService):
    """
    ISP Framework user service that wraps the unified user management adapter.

    Maintains compatibility with existing ISP Framework patterns while
    leveraging unified user management for core functionality.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[UUID] = None):
        """Initialize ISP user service."""
        super().__init__(db_session, tenant_id)
        self.adapter = ISPUserAdapter(db_session, tenant_id)

    async def register_customer(self, *args, **kwargs):
        """Register customer (delegates to adapter)."""
        return await self.adapter.register_customer(*args, **kwargs)

    async def activate_customer(self, *args, **kwargs):
        """Activate customer (delegates to adapter)."""
        return await self.adapter.activate_customer(*args, **kwargs)

    async def register_technician(self, *args, **kwargs):
        """Register technician (delegates to adapter)."""
        return await self.adapter.register_technician(*args, **kwargs)

    async def search_customers(self, *args, **kwargs):
        """Search customers (delegates to adapter)."""
        return await self.adapter.search_customers(*args, **kwargs)

    async def link_user_to_service(self, *args, **kwargs):
        """Link user to service (delegates to adapter)."""
        return await self.adapter.link_user_to_service(*args, **kwargs)


# Factory functions for easy integration
def create_isp_user_adapter(
    db_session: AsyncSession, tenant_id: Optional[UUID] = None, **config_options
) -> ISPUserAdapter:
    """Create ISP user adapter with standard configuration."""
    return ISPUserAdapter(db_session=db_session, tenant_id=tenant_id)


def create_isp_user_service(
    db_session: AsyncSession, tenant_id: Optional[UUID] = None
) -> ISPUserService:
    """Create ISP user service for framework integration."""
    return ISPUserService(db_session, tenant_id)
