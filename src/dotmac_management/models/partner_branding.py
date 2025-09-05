"""
Partner branding models for whitelabeling support.
Extends existing partner system with DRY compliance.
"""

import re
import urllib.parse
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import JSON, Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from dotmac_shared.validation.common_validators import CommonValidators

from .base import BaseModel as DBBaseModel


class PartnerBrandConfig(DBBaseModel):
    """
    Whitelabel branding configuration for partners.
    Extends existing partner system with branding capabilities.
    """

    __tablename__ = "partner_brand_configs"

    # Link to existing partner
    partner_id = Column(
        UUID(as_uuid=True), ForeignKey("partners.id"), nullable=False, unique=True
    )
    partner = relationship("Partner", back_populates="brand_config")

    # Brand Identity
    brand_name = Column(String(200), nullable=False)
    tagline = Column(String(300), nullable=True)
    logo_url = Column(String(500), nullable=True)
    logo_dark_url = Column(String(500), nullable=True)
    favicon_url = Column(String(500), nullable=True)

    # Color Scheme (hex colors)
    primary_color = Column(String(7), default="#3b82f6")  # Blue
    secondary_color = Column(String(7), default="#22c55e")  # Green
    accent_color = Column(String(7), default="#f97316")  # Orange
    background_color = Column(String(7), default="#ffffff")  # White
    text_color = Column(String(7), default="#1f2937")  # Dark gray

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
    brand_config = Column(
        JSON,
        default=lambda: {
            "email_templates": {},
            "custom_css": "",
            "portal_settings": {},
            "feature_flags": {},
        },
    )

    # Status
    is_active = Column(Boolean, default=True)

    # Auto-generated brand assets
    generated_assets = Column(
        JSON,
        default=lambda: {"color_palette": {}, "css_variables": {}, "theme_preview": ""},
    )


# Pydantic Models for API
class BrandConfigBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    brand_name: str = Field(..., min_length=1, max_length=200)
    tagline: Optional[str] = Field(None, max_length=300)
    logo_url: Optional[str] = Field(None, max_length=500)
    logo_dark_url: Optional[str] = Field(None, max_length=500)
    favicon_url: Optional[str] = Field(None, max_length=500)

    # Colors with validation
    primary_color: str = Field(default="#3b82f6", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field(default="#22c55e", pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: str = Field(default="#f97316", pattern=r"^#[0-9A-Fa-f]{6}$")
    background_color: str = Field(default="#ffffff", pattern=r"^#[0-9A-Fa-f]{6}$")
    text_color: str = Field(default="#1f2937", pattern=r"^#[0-9A-Fa-f]{6}$")

    font_family: str = Field(default="Inter, sans-serif", max_length=100)
    font_url: Optional[str] = None

    custom_domain: Optional[str] = Field(None, max_length=200)
    ssl_enabled: bool = True

    support_email: Optional[str] = Field(None, max_length=255)
    support_phone: Optional[str] = Field(None, max_length=50)
    support_url: Optional[str] = Field(None, max_length=500)

    company_legal_name: Optional[str] = Field(None, max_length=300)
    privacy_policy_url: Optional[str] = Field(None, max_length=500)
    terms_of_service_url: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=500)

    website_url: Optional[str] = Field(None, max_length=500)
    facebook_url: Optional[str] = Field(None, max_length=500)
    twitter_url: Optional[str] = Field(None, max_length=500)
    linkedin_url: Optional[str] = Field(None, max_length=500)

    brand_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("brand_name")
    @classmethod
    def validate_brand_name(cls, v: str) -> str:
        """Validate brand name with sanitization"""
        return CommonValidators.validate_required_string(v, "Brand name", 2, 200)

    @field_validator("tagline")
    @classmethod
    def validate_tagline(cls, v: Optional[str]) -> Optional[str]:
        """Validate tagline with sanitization"""
        if v is None:
            return None

        clean_tagline = v.strip()
        if len(clean_tagline) == 0:
            return None

        if len(clean_tagline) > 300:
            raise ValueError("Tagline must be less than 300 characters")

        # Basic content validation - no HTML or scripts
        if "<" in clean_tagline or ">" in clean_tagline:
            raise ValueError("Tagline cannot contain HTML tags")

        return clean_tagline

    @field_validator(
        "logo_url",
        "logo_dark_url",
        "favicon_url",
        "support_url",
        "privacy_policy_url",
        "terms_of_service_url",
        "website_url",
        "facebook_url",
        "twitter_url",
        "linkedin_url",
    )
    @classmethod
    def validate_url_fields(cls, v: Optional[str], info) -> Optional[str]:
        """Validate URL fields with security checks"""
        if v is None:
            return None

        clean_url = v.strip()
        if len(clean_url) == 0:
            return None

        # URL length validation
        if len(clean_url) > 500:
            raise ValueError(f"{info.field_name} URL must be less than 500 characters")

        # Basic URL format validation
        try:
            parsed = urllib.parse.urlparse(clean_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(
                    f"{info.field_name} must be a valid URL with scheme and domain"
                )

            # Security: only allow http/https schemes
            if parsed.scheme not in ["http", "https"]:
                raise ValueError(f"{info.field_name} must use http or https protocol")

            # Security: prevent localhost/private IPs for public-facing URLs
            netloc = parsed.netloc.lower()
            if any(blocked in netloc for blocked in ["localhost", "127.0.0.1", "::1"]):
                raise ValueError(f"{info.field_name} cannot use localhost URLs")

            # Validate domain-specific URLs
            field_name = info.field_name
            if field_name == "facebook_url" and "facebook.com" not in netloc:
                raise ValueError("Facebook URL must be from facebook.com domain")
            elif field_name == "twitter_url" and not any(
                domain in netloc for domain in ["twitter.com", "x.com"]
            ):
                raise ValueError("Twitter URL must be from twitter.com or x.com domain")
            elif field_name == "linkedin_url" and "linkedin.com" not in netloc:
                raise ValueError("LinkedIn URL must be from linkedin.com domain")

            return clean_url

        except Exception as e:
            raise ValueError(f"{info.field_name} must be a valid URL: {str(e)}") from e

    @field_validator(
        "primary_color",
        "secondary_color",
        "accent_color",
        "background_color",
        "text_color",
    )
    @classmethod
    def validate_hex_colors(cls, v: str, info) -> str:
        """Validate hex color codes with accessibility checks"""
        if not v:
            # Use field-specific defaults
            defaults = {
                "primary_color": "#3b82f6",
                "secondary_color": "#22c55e",
                "accent_color": "#f97316",
                "background_color": "#ffffff",
                "text_color": "#1f2937",
            }
            return defaults.get(info.field_name, "#000000")

        clean_color = v.strip().lower()

        # Hex color validation
        if not re.match(r"^#[0-9a-f]{6}$", clean_color):
            raise ValueError(
                f"{info.field_name} must be a valid 6-digit hex color (e.g., #ff0000)"
            )

        # Basic accessibility check - prevent pure black/white extremes for text
        if info.field_name == "text_color":
            if clean_color in ["#000000", "#ffffff"]:
                raise ValueError(
                    "Text color should not be pure black or white for accessibility"
                )

        return clean_color

    @field_validator("font_family")
    @classmethod
    def validate_font_family(cls, v: str) -> str:
        """Validate font family with security checks"""
        if not v:
            return "Inter, sans-serif"

        clean_font = v.strip()

        # Length validation
        if len(clean_font) > 100:
            raise ValueError("Font family must be less than 100 characters")

        # Security: prevent CSS injection
        dangerous_chars = ["<", ">", "{", "}", ";", "(", ")"]
        if any(char in clean_font for char in dangerous_chars):
            raise ValueError("Font family contains invalid characters")

        # Basic format validation (allow letters, numbers, spaces, commas, hyphens)
        if not re.match(r'^[a-zA-Z0-9\s,\-\'"]+$', clean_font):
            raise ValueError("Font family contains invalid characters")

        return clean_font

    @field_validator("custom_domain")
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        """Enhanced domain validation with security checks"""
        if v is None:
            return None

        clean_domain = v.strip().lower()
        if len(clean_domain) == 0:
            return None

        # Length validation
        if len(clean_domain) > 200:
            raise ValueError("Domain must be less than 200 characters")

        # Enhanced domain validation
        domain_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        if not re.match(domain_pattern, clean_domain):
            raise ValueError("Invalid domain format")

        # Security checks
        if any(
            blocked in clean_domain for blocked in ["localhost", "127.0.0.1", "::1"]
        ):
            raise ValueError("Cannot use localhost or private IP addresses")

        # Must have at least one dot (no top-level domains)
        if "." not in clean_domain:
            raise ValueError("Domain must include a top-level domain")

        # Prevent common typos/issues
        if clean_domain.startswith(".") or clean_domain.endswith("."):
            raise ValueError("Domain cannot start or end with a period")

        return clean_domain

    @field_validator("support_email")
    @classmethod
    def validate_support_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate support email"""
        if v is None:
            return None

        clean_email = v.strip().lower()
        if len(clean_email) == 0:
            return None

        # Basic email validation
        if "@" not in clean_email or "." not in clean_email:
            raise ValueError("Support email must be a valid email address")

        # Length validation
        if len(clean_email) > 255:
            raise ValueError("Support email must be less than 255 characters")

        # Basic format validation
        if not re.match(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", clean_email
        ):
            raise ValueError("Support email format is invalid")

        return clean_email

    @field_validator("support_phone")
    @classmethod
    def validate_support_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate support phone number"""
        return CommonValidators.validate_phone(v)

    @field_validator("company_legal_name")
    @classmethod
    def validate_company_legal_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate company legal name"""
        if v is None:
            return None

        clean_name = v.strip()
        if len(clean_name) == 0:
            return None

        if len(clean_name) > 300:
            raise ValueError("Company legal name must be less than 300 characters")

        # Basic content validation
        if "<" in clean_name or ">" in clean_name:
            raise ValueError("Company legal name cannot contain HTML tags")

        return clean_name

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate physical address"""
        if v is None:
            return None

        clean_address = v.strip()
        if len(clean_address) == 0:
            return None

        if len(clean_address) > 500:
            raise ValueError("Address must be less than 500 characters")

        # Basic content validation
        if "<" in clean_address or ">" in clean_address:
            raise ValueError("Address cannot contain HTML tags")

        return clean_address

    @field_validator("brand_config")
    @classmethod
    def validate_brand_config(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate brand configuration structure with security checks"""
        if not isinstance(v, dict):
            raise ValueError("Brand config must be a dictionary")

        # Validate custom CSS if present
        if "custom_css" in v:
            css = v["custom_css"]
            if css and isinstance(css, str):
                # Length limit for CSS
                if len(css) > 50000:  # 50KB limit
                    raise ValueError("Custom CSS must be less than 50KB")

                # Security: prevent dangerous CSS
                dangerous_patterns = [
                    "javascript:",
                    "data:",
                    "vbscript:",
                    "expression(",
                    "@import",
                    "behavior:",
                    "-moz-binding",
                ]

                css_lower = css.lower()
                for pattern in dangerous_patterns:
                    if pattern in css_lower:
                        raise ValueError(
                            f"Custom CSS contains dangerous pattern: {pattern}"
                        )

        # Validate feature flags
        if "feature_flags" in v:
            flags = v["feature_flags"]
            if not isinstance(flags, dict):
                raise ValueError("Feature flags must be a dictionary")

            # Validate boolean values
            for key, value in flags.items():
                if not isinstance(value, bool):
                    raise ValueError(f"Feature flag {key} must be a boolean value")

        # Validate portal settings
        if "portal_settings" in v:
            settings = v["portal_settings"]
            if not isinstance(settings, dict):
                raise ValueError("Portal settings must be a dictionary")

        return v


class BrandConfigCreate(BrandConfigBase):
    partner_id: UUID


class BrandConfigUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    brand_name: Optional[str] = Field(None, min_length=1, max_length=200)
    tagline: Optional[str] = Field(None, max_length=300)
    logo_url: Optional[str] = Field(None, max_length=500)
    logo_dark_url: Optional[str] = Field(None, max_length=500)
    favicon_url: Optional[str] = Field(None, max_length=500)

    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    background_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    text_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")

    font_family: Optional[str] = Field(None, max_length=100)
    font_url: Optional[str] = Field(None, max_length=500)

    custom_domain: Optional[str] = Field(None, max_length=200)
    ssl_enabled: Optional[bool] = None

    support_email: Optional[str] = Field(None, max_length=255)
    support_phone: Optional[str] = Field(None, max_length=50)
    support_url: Optional[str] = Field(None, max_length=500)

    company_legal_name: Optional[str] = Field(None, max_length=300)
    privacy_policy_url: Optional[str] = Field(None, max_length=500)
    terms_of_service_url: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = Field(None, max_length=500)

    website_url: Optional[str] = Field(None, max_length=500)
    facebook_url: Optional[str] = Field(None, max_length=500)
    twitter_url: Optional[str] = Field(None, max_length=500)
    linkedin_url: Optional[str] = Field(None, max_length=500)

    brand_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None

    # Apply same validators as base class for non-None values
    validate_brand_name = field_validator("brand_name")(
        BrandConfigBase.validate_brand_name.__func__
    )
    validate_tagline = field_validator("tagline")(
        BrandConfigBase.validate_tagline.__func__
    )
    validate_url_fields = field_validator(
        "logo_url",
        "logo_dark_url",
        "favicon_url",
        "support_url",
        "privacy_policy_url",
        "terms_of_service_url",
        "website_url",
        "facebook_url",
        "twitter_url",
        "linkedin_url",
    )(BrandConfigBase.validate_url_fields.__func__)
    validate_hex_colors = field_validator(
        "primary_color",
        "secondary_color",
        "accent_color",
        "background_color",
        "text_color",
    )(BrandConfigBase.validate_hex_colors.__func__)
    validate_font_family = field_validator("font_family")(
        BrandConfigBase.validate_font_family.__func__
    )
    validate_domain = field_validator("custom_domain")(
        BrandConfigBase.validate_domain.__func__
    )
    validate_support_email = field_validator("support_email")(
        BrandConfigBase.validate_support_email.__func__
    )
    validate_support_phone = field_validator("support_phone")(
        BrandConfigBase.validate_support_phone.__func__
    )
    validate_company_legal_name = field_validator("company_legal_name")(
        BrandConfigBase.validate_company_legal_name.__func__
    )
    validate_address = field_validator("address")(
        BrandConfigBase.validate_address.__func__
    )
    validate_brand_config = field_validator("brand_config")(
        BrandConfigBase.validate_brand_config.__func__
    )


class BrandConfigResponse(BrandConfigBase):
    id: UUID
    partner_id: UUID
    domain_verified: bool
    generated_assets: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    # Include partner info for convenience
    partner: Optional[dict[str, Any]] = None


class WhitelabelTheme(BaseModel):
    """Generated theme configuration for frontend consumption."""

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    brand: dict[str, str]
    colors: dict[str, str]
    typography: dict[str, str]
    domain: dict[str, Any]
    contact: dict[str, str]
    legal: dict[str, str]
    social: dict[str, str]
    css_variables: dict[str, str]
    custom_css: Optional[str] = None
