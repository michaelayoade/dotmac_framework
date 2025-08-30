"""
Base schemas for Identity SDK.

These are minimal schemas that can be extended by modules
without creating circular imports.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    """Base schema for creating customers."""

    customer_number: str = Field(..., max_length=50)
    customer_type: str = Field("residential", max_length=20)
    account_status: str = Field("active", max_length=20)
    service_address_required: bool = True
    billing_same_as_service: bool = True
    credit_limit: Optional[str] = Field(None, max_length=20)
    payment_terms: Optional[str] = Field("net_30", max_length=50)
    installation_date: Optional[datetime] = None
    communication_preferences: Optional[str] = Field("email", max_length=50)
    marketing_opt_in: bool = False


class CustomerUpdate(BaseModel):
    """Base schema for updating customers."""

    customer_number: Optional[str] = Field(None, max_length=50)
    customer_type: Optional[str] = Field(None, max_length=20)
    account_status: Optional[str] = Field(None, max_length=20)
    service_address_required: Optional[bool] = None
    billing_same_as_service: Optional[bool] = None
    credit_limit: Optional[str] = Field(None, max_length=20)
    payment_terms: Optional[str] = Field(None, max_length=50)
    installation_date: Optional[datetime] = None
    communication_preferences: Optional[str] = Field(None, max_length=50)
    marketing_opt_in: Optional[bool] = None


class CustomerResponse(BaseModel):
    """Base schema for customer responses."""

    customer_id: UUID
    customer_number: str
    customer_type: str
    account_status: str
    service_address_required: bool
    billing_same_as_service: bool
    credit_limit: Optional[str]
    payment_terms: Optional[str]
    installation_date: Optional[datetime]
    communication_preferences: Optional[str]
    marketing_opt_in: bool
    created_at: datetime
    updated_at: datetime


class CustomerListFilters(BaseModel):
    """Base schema for filtering customer lists."""

    customer_type: Optional[str] = None
    account_status: Optional[str] = None
    marketing_opt_in: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
