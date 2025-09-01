"""
Partner branding models for whitelabeling support.
Extends existing partner system with DRY compliance.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, ConfigDict, field_validator

from .base import BaseModel as DBBaseModel


class PartnerBrandConfig(DBBaseModel):
    """
    Whitelabel branding configuration for partners.
    Extends existing partner system with branding capabilities.
    """
    __tablename__ = "partner_brand_configs"
    
    # Link to existing partner
    partner_id = Column(UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, unique=True)
    partner = relationship("Partner", back_populates="brand_config")
    
    # Brand Identity
    brand_name = Column(String(200), nullable=False)
    tagline = Column(String(300), nullable=True)
    logo_url = Column(String(500), nullable=True)
    logo_dark_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)
    
    # Color Scheme (hex colors)
    primary_color = Column(String(7), default="#3b82f6")      # Blue
    secondary_color = Column(String(7), default="#22c55e")    # Green
    accent_color = Column(String(7), default="#f97316")       # Orange
    background_color = Column(String(7), default="#ffffff")   # White
    text_color = Column(String(7), default="#1f2937")         # Dark gray
    
    # Typography
    font_family = Column(String(100), default="Inter, sans-serif")
    font_url = Column(String(500), nullable=True)  # Google Fonts URL
    
    # Domain Configuration (leverages existing container system)
    custom_domain = Column(String(200), nullable=True, unique=True)
    ssl_enabled = Column(Boolean, default=True)
    domain_verified = Column(Boolean, default=False)
    
    # Contact Information (overrides default platform contact)
    support_email = Column(String(255), nullable=True)
    support_phone = Column(String(50), nullable=True)
    support_url = Column(String(500), nullable=True)
    
    # Legal/Footer Information
    company_legal_name = Column(String(300), nullable=True)
    privacy_policy_url = Column(String(500), nullable=True)
    terms_of_service_url = Column(String(500), nullable=True)
    address = Column(String(500), nullable=True)
    
    # Social Media Links
    website_url = Column(String(500), nullable=True)
    facebook_url = Column(String(500), nullable=True)
    twitter_url = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    
    # Advanced Configuration (JSON for flexibility)
    brand_config = Column(JSON, default=lambda: {
        "email_templates": {},
        "custom_css": "",
        "portal_settings": {},
        "feature_flags": {}
    })
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Auto-generated brand assets
    generated_assets = Column(JSON, default=lambda: {
        "color_palette": {},
        "css_variables": {},
        "theme_preview": ""
    })


# Pydantic Models for API
class BrandConfigBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    brand_name: str = Field(..., min_length=1, max_length=200)
    tagline: Optional[str] = Field(None, max_length=300)
    logo_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    favicon_url: Optional[str] = None
    
    # Colors with validation
    primary_color: str = Field(default="#3b82f6", pattern=r'^#[0-9A-Fa-f]{6}$')
    secondary_color: str = Field(default="#22c55e", pattern=r'^#[0-9A-Fa-f]{6}$')
    accent_color: str = Field(default="#f97316", pattern=r'^#[0-9A-Fa-f]{6}$')
    background_color: str = Field(default="#ffffff", pattern=r'^#[0-9A-Fa-f]{6}$')
    text_color: str = Field(default="#1f2937", pattern=r'^#[0-9A-Fa-f]{6}$')
    
    font_family: str = Field(default="Inter, sans-serif", max_length=100)
    font_url: Optional[str] = None
    
    custom_domain: Optional[str] = Field(None, max_length=200)
    ssl_enabled: bool = True
    
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    support_url: Optional[str] = None
    
    company_legal_name: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    terms_of_service_url: Optional[str] = None
    address: Optional[str] = None
    
    website_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    brand_config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator('custom_domain')
    @classmethod
    def validate_domain(cls, v):
        if v:
            # Basic domain validation
            import re
            domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
            if not re.match(domain_pattern, v):
                raise ValueError('Invalid domain format')
        return v


class BrandConfigCreate(BrandConfigBase):
    partner_id: UUID


class BrandConfigUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    brand_name: Optional[str] = None
    tagline: Optional[str] = None
    logo_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    favicon_url: Optional[str] = None
    
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    
    font_family: Optional[str] = None
    font_url: Optional[str] = None
    
    custom_domain: Optional[str] = None
    ssl_enabled: Optional[bool] = None
    
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    support_url: Optional[str] = None
    
    company_legal_name: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    terms_of_service_url: Optional[str] = None
    address: Optional[str] = None
    
    website_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    
    brand_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class BrandConfigResponse(BrandConfigBase):
    id: UUID
    partner_id: UUID
    domain_verified: bool
    generated_assets: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    # Include partner info for convenience
    partner: Optional[Dict[str, Any]] = None


class WhitelabelTheme(BaseModel):
    """Generated theme configuration for frontend consumption."""
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
    
    brand: Dict[str, str]
    colors: Dict[str, str]
    typography: Dict[str, str]
    domain: Dict[str, Any]
    contact: Dict[str, str]
    legal: Dict[str, str]
    social: Dict[str, str]
    css_variables: Dict[str, str]
    custom_css: Optional[str] = None