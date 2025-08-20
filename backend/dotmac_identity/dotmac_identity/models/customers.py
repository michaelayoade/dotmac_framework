"""
Customer models for subscriber/customer lifecycle management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class CustomerState(Enum):
    """Customer lifecycle state enumeration."""
    PROSPECT = "prospect"
    LEAD = "lead"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CHURNED = "churned"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"


class CustomerType(Enum):
    """Customer type enumeration."""
    RESIDENTIAL = "residential"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"


class CustomerSegment(Enum):
    """Customer segment enumeration."""
    HIGH_VALUE = "high_value"
    STANDARD = "standard"
    BUDGET = "budget"
    PREMIUM = "premium"
    VIP = "vip"


@dataclass
class Customer:
    """Customer model for subscriber/customer lifecycle management."""
    id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Basic information
    customer_number: str = ""
    display_name: str = ""

    # Relationships
    organization_id: Optional[UUID] = None
    primary_contact_id: Optional[UUID] = None
    billing_contact_id: Optional[UUID] = None
    technical_contact_id: Optional[UUID] = None

    # Customer classification
    customer_type: CustomerType = CustomerType.RESIDENTIAL
    customer_segment: CustomerSegment = CustomerSegment.STANDARD

    # Lifecycle state
    state: CustomerState = CustomerState.PROSPECT
    state_changed_at: datetime = field(default_factory=utc_now)
    state_changed_by: Optional[UUID] = None

    # Important dates
    prospect_date: Optional[datetime] = None
    activation_date: Optional[datetime] = None
    suspension_date: Optional[datetime] = None
    churn_date: Optional[datetime] = None
    cancellation_date: Optional[datetime] = None

    # Financial information
    monthly_recurring_revenue: Optional[float] = None
    total_contract_value: Optional[float] = None
    lifetime_value: Optional[float] = None

    # Service information
    service_address_id: Optional[UUID] = None
    billing_address_id: Optional[UUID] = None

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional data
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if customer is in active state."""
        return self.state == CustomerState.ACTIVE

    def is_prospect(self) -> bool:
        """Check if customer is a prospect."""
        return self.state in [CustomerState.PROSPECT, CustomerState.LEAD]

    def is_churned(self) -> bool:
        """Check if customer has churned."""
        return self.state in [CustomerState.CHURNED, CustomerState.CANCELLED]

    def get_state_duration(self) -> int:
        """Get duration in current state (days)."""
        return (utc_now() - self.state_changed_at).days

    def transition_to_state(self, new_state: CustomerState, changed_by: Optional[UUID] = None) -> None:
        """Transition customer to new state."""
        old_state = self.state
        self.state = new_state
        self.state_changed_at = utc_now()
        self.state_changed_by = changed_by
        self.updated_at = utc_now()

        # Set specific date fields based on state
        if new_state == CustomerState.ACTIVE and old_state in [CustomerState.PROSPECT, CustomerState.LEAD]:
            self.activation_date = utc_now()
        elif new_state == CustomerState.SUSPENDED:
            self.suspension_date = utc_now()
        elif new_state == CustomerState.CHURNED:
            self.churn_date = utc_now()
        elif new_state == CustomerState.CANCELLED:
            self.cancellation_date = utc_now()
