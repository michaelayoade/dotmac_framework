"""
Reseller API schemas for ISP Framework

Defines request/response models for reseller APIs.
Leverages shared schemas where possible following DRY principles.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator

# Import shared enums for validation
from dotmac_shared.sales.core.reseller_models import (
    ResellerType,
    ResellerStatus,
    ResellerTier,
    CommissionStructure,
    ResellerCertificationStatus
)


# === Base Schemas ===

class ResellerApplicationCreate(BaseModel):
    """Schema for creating new reseller application from website."""
    
    # Company information
    company_name: str = Field(..., min_length=2, max_length=300, description="Company name")
    legal_company_name: Optional[str] = Field(None, max_length=300, description="Legal company name if different")
    website_url: Optional[str] = Field(None, max_length=500, description="Company website URL")
    business_type: Optional[str] = Field(None, max_length=100, description="Type of business entity")
    years_in_business: Optional[int] = Field(None, ge=0, le=100, description="Years in business")
    
    # Primary contact
    contact_name: str = Field(..., min_length=2, max_length=200, description="Primary contact name")
    contact_title: Optional[str] = Field(None, max_length=100, description="Contact job title")
    contact_email: EmailStr = Field(..., description="Primary contact email")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Primary contact phone")
    
    # Business details
    employee_count: Optional[int] = Field(None, ge=1, le=10000, description="Number of employees")
    annual_revenue_range: Optional[str] = Field(None, description="Annual revenue range")
    telecom_experience_years: Optional[int] = Field(None, ge=0, le=50, description="Years of telecom experience")
    business_description: Optional[str] = Field(None, max_length=2000, description="Business description")
    
    # Desired partnership details
    desired_territories: Optional[List[str]] = Field(None, description="List of desired service territories")
    target_customer_segments: Optional[List[str]] = Field(None, description="Target customer segments")
    estimated_monthly_customers: Optional[int] = Field(None, ge=1, le=10000, description="Estimated monthly new customers")
    preferred_commission_structure: Optional[str] = Field(None, description="Preferred commission structure")
    
    @validator('website_url')
    def validate_website_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            v = 'https://' + v
        return v
    
    @validator('annual_revenue_range')
    def validate_revenue_range(cls, v):
        valid_ranges = [
            "under_100k", "100k_500k", "500k_1m", "1m_5m", "5m_10m", "over_10m"
        ]
        if v and v not in valid_ranges:
            raise ValueError(f"Revenue range must be one of: {valid_ranges}")
        return v


class ResellerApplicationResponse(BaseModel):
    """Schema for reseller application response."""
    
    id: UUID
    application_id: str
    application_status: str
    
    # Company info
    company_name: str
    contact_name: str
    contact_email: str
    
    # Application tracking
    submitted_at: datetime
    days_since_submission: int
    can_be_approved: bool
    is_pending_review: bool
    
    class Config:
        from_attributes = True


class ResellerResponse(BaseModel):
    """Schema for reseller response - leveraging existing shared structure."""
    
    id: UUID
    reseller_id: str
    company_name: str
    reseller_type: ResellerType
    reseller_status: ResellerStatus
    reseller_tier: ResellerTier
    
    # Contact information
    primary_contact_name: str
    primary_contact_email: str
    
    # Performance metrics
    total_customers: int
    active_customers: int
    lifetime_sales: Decimal
    ytd_sales: Decimal
    
    # Commission info
    base_commission_rate: Optional[Decimal]
    
    # Portal access
    portal_enabled: bool
    portal_last_login: Optional[datetime]
    
    # Dates
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Export all schemas
__all__ = [
    "ResellerApplicationCreate",
    "ResellerApplicationResponse", 
    "ResellerResponse"
]