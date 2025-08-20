"""
In-memory customer service for customer lifecycle management.
"""

from datetime import datetime
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from typing import Dict, List, Optional
from uuid import UUID

from ..core.exceptions import CustomerError, CustomerNotFoundError
from ..models.customers import Customer, CustomerState, CustomerType


class CustomerService:
    """In-memory service for customer operations."""

    def __init__(self):
        self._customers: Dict[UUID, Customer] = {}
        self._customer_number_index: Dict[str, UUID] = {}
        self._organization_customers: Dict[UUID, List[UUID]] = {}

    async def create_customer(
        self,
        tenant_id: str,
        customer_number: str,
        display_name: str,
        customer_type: CustomerType = CustomerType.RESIDENTIAL,
        **kwargs
    ) -> Customer:
        """Create a new customer."""
        if customer_number in self._customer_number_index:
            raise CustomerError(f"Customer number already exists: {customer_number}")

        customer = Customer(
            tenant_id=tenant_id,
            customer_number=customer_number,
            display_name=display_name,
            customer_type=customer_type,
            prospect_date=utc_now(),
            **kwargs
        )

        self._customers[customer.id] = customer
        self._customer_number_index[customer_number] = customer.id

        # Index by organization if provided
        if customer.organization_id:
            if customer.organization_id not in self._organization_customers:
                self._organization_customers[customer.organization_id] = []
            self._organization_customers[customer.organization_id].append(customer.id)

        return customer

    async def get_customer(self, customer_id: UUID) -> Optional[Customer]:
        """Get customer by ID."""
        return self._customers.get(customer_id)

    async def get_customer_by_number(self, customer_number: str) -> Optional[Customer]:
        """Get customer by customer number."""
        customer_id = self._customer_number_index.get(customer_number)
        if customer_id:
            return self._customers.get(customer_id)
        return None

    async def update_customer(self, customer_id: UUID, **updates) -> Customer:
        """Update customer."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise CustomerNotFoundError(str(customer_id))

        # Handle customer number updates
        if "customer_number" in updates and updates["customer_number"] != customer.customer_number:
            if updates["customer_number"] in self._customer_number_index:
                raise CustomerError(f"Customer number already exists: {updates['customer_number']}")
            del self._customer_number_index[customer.customer_number]
            self._customer_number_index[updates["customer_number"]] = customer_id

        # Update customer fields
        for key, value in updates.items():
            if hasattr(customer, key):
                setattr(customer, key, value)

        customer.updated_at = utc_now()
        return customer

    async def transition_customer_state(
        self,
        customer_id: UUID,
        new_state: CustomerState,
        changed_by: Optional[UUID] = None
    ) -> Customer:
        """Transition customer to new state."""
        customer = self._customers.get(customer_id)
        if not customer:
            raise CustomerNotFoundError(str(customer_id))

        customer.transition_to_state(new_state, changed_by)
        return customer

    async def activate_customer(self, customer_id: UUID, changed_by: Optional[UUID] = None) -> Customer:
        """Activate customer."""
        return await self.transition_customer_state(customer_id, CustomerState.ACTIVE, changed_by)

    async def suspend_customer(self, customer_id: UUID, changed_by: Optional[UUID] = None) -> Customer:
        """Suspend customer."""
        return await self.transition_customer_state(customer_id, CustomerState.SUSPENDED, changed_by)

    async def churn_customer(self, customer_id: UUID, changed_by: Optional[UUID] = None) -> Customer:
        """Mark customer as churned."""
        return await self.transition_customer_state(customer_id, CustomerState.CHURNED, changed_by)

    async def list_customers(
        self,
        tenant_id: str,
        state: Optional[CustomerState] = None,
        customer_type: Optional[CustomerType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Customer]:
        """List customers with optional filters."""
        customers = [
            customer for customer in self._customers.values()
            if customer.tenant_id == tenant_id
        ]

        if state:
            customers = [c for c in customers if c.state == state]

        if customer_type:
            customers = [c for c in customers if c.customer_type == customer_type]

        return customers[offset:offset + limit]

    async def get_customers_by_organization(self, organization_id: UUID) -> List[Customer]:
        """Get customers for an organization."""
        customer_ids = self._organization_customers.get(organization_id, [])
        return [self._customers[cid] for cid in customer_ids if cid in self._customers]
