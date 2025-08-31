"""
Pydantic schemas for Partner API.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class PartnerBase(BaseModel):
    company_name: str = Field(..., max_length=100)
    partner_code: str = Field(..., max_length=20)
    contact_name: str = Field(..., max_length=100)
    contact_email: EmailStr
    contact_phone: str = Field(..., max_length=20)
    territory: str = Field(..., max_length=100)
    tier: str = Field("bronze")
    status: str = Field("active")


class PartnerCreate(PartnerBase):
    pass


class PartnerUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    territory: Optional[str] = None
    tier: Optional[str] = None
    status: Optional[str] = None


class PartnerResponse(BaseModel):
    id: UUID
    company_name: str
    partner_code: str
    contact_name: str
    contact_email: EmailStr
    contact_phone: str
    territory: str
    tier: str
    status: str

    model_config = ConfigDict(
        from_attributes=True
    )

class PaginatedPartners(BaseModel):
    items: List[PartnerResponse]
    total: int
    page: int
    size: int


class TierUpdateRequest(BaseModel):
    tier: str


class SuspendRequest(BaseModel):
    reason: Optional[str] = None

