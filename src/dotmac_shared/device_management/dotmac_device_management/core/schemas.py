"""
Device management schemas for API serialization and validation.

Pydantic schemas for API serialization and validation.
"""

import re
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceCreateRequest(BaseModel):
    """Schema for device creation request."""

    device_id: str = Field(..., description="Unique device identifier")
    hostname: str = Field(..., description="Device hostname")
    device_type: str = Field(default="unknown", description="Device type")
    model: Optional[str] = Field(None, description="Device model")
    vendor: Optional[str] = Field(None, description="Device vendor")
    firmware_version: Optional[str] = Field(None, description="Firmware version")
    ip_address: Optional[str] = Field(None, description="Primary IP address")
    mac_address: Optional[str] = Field(None, description="Primary MAC address")
    site_id: Optional[str] = Field(None, description="Site identifier")
    location: Optional[str] = Field(None, description="Physical location")
    description: Optional[str] = Field(None, description="Device description")
    status: str = Field(default="active", description="Device status")
    properties: dict[str, Any] = Field(
        default_factory=dict, description="Additional properties"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v):
        if not v or not v.strip():
            raise ValueError("device_id cannot be empty")
        # Allow alphanumeric, hyphens, underscores, dots
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("device_id contains invalid characters")
        return v.strip()

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v):
        if not v or not v.strip():
            raise ValueError("hostname cannot be empty")
        # Basic hostname validation
        if not re.match(r"^[a-zA-Z0-9.-]+$", v):
            raise ValueError("Invalid hostname format")
        return v.strip()


class DeviceResponse(BaseModel):
    """Schema for device response."""

    id: str
    tenant_id: str
    device_id: str
    hostname: str
    device_type: str
    model: Optional[str]
    vendor: Optional[str]
    firmware_version: Optional[str]
    ip_address: Optional[str]
    mac_address: Optional[str]
    site_id: Optional[str]
    location: Optional[str]
    description: Optional[str]
    status: str
    properties: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ConfigIntentRequest(BaseModel):
    """Schema for configuration intent request."""

    device_id: str = Field(..., description="Target device identifier")
    intent_type: str = Field(..., description="Type of configuration intent")
    config_data: dict[str, Any] = Field(..., description="Configuration data")
    apply_immediately: bool = Field(
        default=False, description="Apply configuration immediately"
    )
    validate_only: bool = Field(
        default=False, description="Only validate configuration"
    )

    model_config = ConfigDict(from_attributes=True)


class ConfigIntentResponse(BaseModel):
    """Schema for configuration intent response."""

    intent_id: str = Field(..., description="Configuration intent identifier")
    device_id: str = Field(..., description="Target device identifier")
    intent_type: str = Field(..., description="Type of configuration intent")
    status: str = Field(..., description="Intent processing status")
    result: Optional[dict[str, Any]] = Field(None, description="Processing result")
    errors: list[str] = Field(default_factory=list, description="Processing errors")
    warnings: list[str] = Field(default_factory=list, description="Processing warnings")
    applied_at: Optional[datetime] = Field(
        None, description="When configuration was applied"
    )

    model_config = ConfigDict(from_attributes=True)
