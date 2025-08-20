"""
Customer Management SDK - subscriber/customer object, lifecycle states, events.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.exceptions import CustomerError
from ..models.customers import Customer, CustomerState, CustomerType
from ..services.customer_service import CustomerService


class CustomerManagementSDK:
    """Small, composable SDK for customer lifecycle management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = CustomerService()

    async def create_customer(
        self,
        customer_number: str,
        display_name: str,
        customer_type: str = "residential",
        organization_id: Optional[str] = None,
        primary_contact_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a new customer."""
        customer = await self._service.create_customer(
            tenant_id=self.tenant_id,
            customer_number=customer_number,
            display_name=display_name,
            customer_type=CustomerType(customer_type),
            organization_id=UUID(organization_id) if organization_id else None,
            primary_contact_id=UUID(primary_contact_id) if primary_contact_id else None,
            **kwargs
        )

        # Emit customer.created event
        await self._emit_customer_event("customer.created", customer)

        return {
            "customer_id": str(customer.id),
            "customer_number": customer.customer_number,
            "display_name": customer.display_name,
            "customer_type": customer.customer_type.value,
            "state": customer.state.value,
            "created_at": customer.created_at.isoformat(),
        }

    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer by ID."""
        customer = await self._service.get_customer(UUID(customer_id))
        if not customer or customer.tenant_id != self.tenant_id:
            return None

        return {
            "customer_id": str(customer.id),
            "customer_number": customer.customer_number,
            "display_name": customer.display_name,
            "customer_type": customer.customer_type.value,
            "customer_segment": customer.customer_segment.value,
            "state": customer.state.value,
            "state_changed_at": customer.state_changed_at.isoformat(),
            "organization_id": str(customer.organization_id) if customer.organization_id else None,
            "primary_contact_id": str(customer.primary_contact_id) if customer.primary_contact_id else None,
            "billing_contact_id": str(customer.billing_contact_id) if customer.billing_contact_id else None,
            "prospect_date": customer.prospect_date.isoformat() if customer.prospect_date else None,
            "activation_date": customer.activation_date.isoformat() if customer.activation_date else None,
            "churn_date": customer.churn_date.isoformat() if customer.churn_date else None,
            "monthly_recurring_revenue": customer.monthly_recurring_revenue,
            "lifetime_value": customer.lifetime_value,
            "created_at": customer.created_at.isoformat(),
            "updated_at": customer.updated_at.isoformat(),
            "tags": customer.tags,
            "custom_fields": customer.custom_fields,
        }

    async def get_customer_by_number(self, customer_number: str) -> Optional[Dict[str, Any]]:
        """Get customer by customer number."""
        customer = await self._service.get_customer_by_number(customer_number)
        if not customer or customer.tenant_id != self.tenant_id:
            return None

        return await self.get_customer(str(customer.id))

    async def update_customer(self, customer_id: str, **updates) -> Dict[str, Any]:
        """Update customer."""
        customer = await self._service.update_customer(UUID(customer_id), **updates)
        if customer.tenant_id != self.tenant_id:
            raise CustomerError("Customer not found in tenant")

        # Emit customer.updated event
        await self._emit_customer_event("customer.updated", customer)

        return await self.get_customer(customer_id)

    async def transition_to_prospect(self, customer_id: str, changed_by: Optional[str] = None) -> Dict[str, Any]:
        """Transition customer to prospect state."""
        return await self._transition_customer_state(
            customer_id, CustomerState.PROSPECT, changed_by, "customer.prospect"
        )

    async def activate_customer(self, customer_id: str, changed_by: Optional[str] = None) -> Dict[str, Any]:
        """Activate customer (prospect → active)."""
        return await self._transition_customer_state(
            customer_id, CustomerState.ACTIVE, changed_by, "customer.activated"
        )

    async def suspend_customer(self, customer_id: str, changed_by: Optional[str] = None) -> Dict[str, Any]:
        """Suspend customer."""
        return await self._transition_customer_state(
            customer_id, CustomerState.SUSPENDED, changed_by, "customer.suspended"
        )

    async def churn_customer(self, customer_id: str, changed_by: Optional[str] = None) -> Dict[str, Any]:
        """Mark customer as churned."""
        return await self._transition_customer_state(
            customer_id, CustomerState.CHURNED, changed_by, "customer.churned"
        )

    async def cancel_customer(self, customer_id: str, changed_by: Optional[str] = None) -> Dict[str, Any]:
        """Cancel customer."""
        return await self._transition_customer_state(
            customer_id, CustomerState.CANCELLED, changed_by, "customer.cancelled"
        )

    async def list_customers(
        self,
        state: Optional[str] = None,
        customer_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List customers with optional filters."""
        customers = await self._service.list_customers(
            tenant_id=self.tenant_id,
            state=CustomerState(state) if state else None,
            customer_type=CustomerType(customer_type) if customer_type else None,
            limit=limit,
            offset=offset
        )

        return [
            {
                "customer_id": str(customer.id),
                "customer_number": customer.customer_number,
                "display_name": customer.display_name,
                "customer_type": customer.customer_type.value,
                "state": customer.state.value,
                "state_changed_at": customer.state_changed_at.isoformat(),
                "created_at": customer.created_at.isoformat(),
            }
            for customer in customers
        ]

    async def get_active_customers(self) -> List[Dict[str, Any]]:
        """Get all active customers."""
        return await self.list_customers(state="active")

    async def get_prospects(self) -> List[Dict[str, Any]]:
        """Get all prospect customers."""
        return await self.list_customers(state="prospect")

    async def get_churned_customers(self) -> List[Dict[str, Any]]:
        """Get all churned customers."""
        return await self.list_customers(state="churned")

    async def _transition_customer_state(
        self,
        customer_id: str,
        new_state: CustomerState,
        changed_by: Optional[str],
        event_name: str
    ) -> Dict[str, Any]:
        """Internal method to transition customer state and emit event."""
        customer = await self._service.transition_customer_state(
            UUID(customer_id),
            new_state,
            UUID(changed_by) if changed_by else None
        )

        if customer.tenant_id != self.tenant_id:
            raise CustomerError("Customer not found in tenant")

        # Emit state transition event
        await self._emit_customer_event(event_name, customer)

        return await self.get_customer(customer_id)

    async def _emit_customer_event(self, event_name: str, customer: Customer) -> None:
        """Emit customer lifecycle event."""
        # In a real implementation, this would publish to an event bus
        # For now, we'll just log the event
        event_data = {
            "event": event_name,
            "customer_id": str(customer.id),
            "tenant_id": customer.tenant_id,
            "customer_number": customer.customer_number,
            "state": customer.state.value,
            "timestamp": customer.updated_at.isoformat(),
        }

        # TODO: Integrate with DotMac Core Events for actual event publishing
        print(f"Customer Event: {event_data}")  # Placeholder for event emission
