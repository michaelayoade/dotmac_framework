"""
Standardized input validation schemas using Pydantic v2.
Provides reusable validation patterns for consistent API input validation.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class TenantCreateRequest(BaseModel):
    """Tenant creation validation schema."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Tenant name (alphanumeric, underscore, hyphen only)"
    )
    domain: str = Field(
        ..., 
        pattern=r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        description="Valid domain name"
    )
    contact_email: EmailStr = Field(..., description="Primary contact email")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v.lower() in ['admin', 'root', 'system', 'api', 'www']:
            raise ValueError('Reserved tenant name')
        return v
    
    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if v.startswith('.') or v.endswith('.'):
            raise ValueError('Domain cannot start or end with dot')
        return v.lower()


class UserCreateRequest(BaseModel):
    """User creation validation schema."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        pattern=r'^[a-zA-Z0-9_-]+$'
    )
    email: EmailStr
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="Password must be 8-128 characters"
    )
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain number')
        return v


class BillingCreateRequest(BaseModel):
    """Billing record creation validation."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    customer_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]{10,50}$')
    amount: float = Field(..., gt=0, le=1000000, description="Amount in cents")
    currency: str = Field(..., pattern=r'^[A-Z]{3}$', description="ISO currency code")
    description: str = Field(..., min_length=1, max_length=500)
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 1000000:
            raise ValueError('Amount too large')
        return round(v, 2)


class ServicePlanRequest(BaseModel):
    """Service plan validation."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    plan_name: str = Field(..., min_length=1, max_length=100)
    bandwidth_mbps: int = Field(..., ge=1, le=10000)
    data_limit_gb: Optional[int] = Field(None, ge=1, le=100000)
    price_monthly: float = Field(..., gt=0, le=10000)
    
    @field_validator('plan_name')
    @classmethod
    def validate_plan_name(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9\s_-]+$', v):
            raise ValueError('Plan name contains invalid characters')
        return v.strip()


class DeviceCreateRequest(BaseModel):
    """Network device creation validation."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    device_name: str = Field(..., min_length=1, max_length=100)
    mac_address: str = Field(
        ..., 
        pattern=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
        description="Valid MAC address format"
    )
    ip_address: str = Field(
        ...,
        pattern=r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$',
        description="Valid IPv4 address"
    )
    device_type: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')
    
    @field_validator('mac_address')
    @classmethod
    def validate_mac_address(cls, v: str) -> str:
        # Normalize MAC address format
        mac = v.upper().replace('-', ':')
        if not re.match(r'^([0-9A-F]{2}:){5}[0-9A-F]{2}$', mac):
            raise ValueError('Invalid MAC address format')
        return mac
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v: str) -> str:
        parts = v.split('.')
        for part in parts:
            if not 0 <= int(part) <= 255:
                raise ValueError('Invalid IP address range')
        return v


class TicketCreateRequest(BaseModel):
    """Support ticket creation validation."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    priority: str = Field(..., pattern=r'^(low|medium|high|critical)$')
    category: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')
    customer_id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]{10,50}$')
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        valid_priorities = ['low', 'medium', 'high', 'critical']
        if v.lower() not in valid_priorities:
            raise ValueError(f'Priority must be one of: {valid_priorities}')
        return v.lower()


class ApiKeyCreateRequest(BaseModel):
    """API key creation validation."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    key_name: str = Field(..., min_length=3, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    permissions: list[str] = Field(..., min_length=1, max_length=20)
    expires_days: Optional[int] = Field(None, ge=1, le=365)
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v: list[str]) -> list[str]:
        valid_permissions = [
            'read', 'write', 'delete', 'admin', 
            'billing', 'users', 'devices', 'tickets'
        ]
        for perm in v:
            if perm not in valid_permissions:
                raise ValueError(f'Invalid permission: {perm}')
        return list(set(v))  # Remove duplicates


class IpamSubnetRequest(BaseModel):
    """IPAM subnet validation."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    cidr: str = Field(
        ..., 
        pattern=r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$',
        description="CIDR notation (e.g., 192.168.1.0/24)"
    )
    description: str = Field(..., min_length=1, max_length=200)
    vlan_id: Optional[int] = Field(None, ge=1, le=4095)
    
    @field_validator('cidr')
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        ip, prefix = v.split('/')
        prefix_len = int(prefix)
        
        # Validate IP
        parts = ip.split('.')
        for part in parts:
            if not 0 <= int(part) <= 255:
                raise ValueError('Invalid IP address in CIDR')
        
        # Validate prefix
        if not 8 <= prefix_len <= 30:
            raise ValueError('CIDR prefix must be between 8 and 30')
            
        return v


class PortalConfigRequest(BaseModel):
    """Portal configuration validation."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    portal_name: str = Field(..., min_length=3, max_length=100)
    redirect_url: str = Field(..., pattern=r'^https?:\/\/[^\s]+$')
    session_timeout: int = Field(..., ge=300, le=86400)  # 5 minutes to 24 hours
    max_devices: int = Field(..., ge=1, le=100)
    
    @field_validator('redirect_url')
    @classmethod
    def validate_redirect_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


# Common validation mixins
class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    
    page: int = Field(default=1, ge=1, le=1000)
    size: int = Field(default=20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class SearchParams(BaseModel):
    """Standard search parameters."""
    
    query: Optional[str] = Field(None, min_length=1, max_length=200)
    sort_by: Optional[str] = Field(None, pattern=r'^[a-zA-Z_]+$')
    sort_order: Optional[str] = Field('asc', pattern=r'^(asc|desc)$')
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Remove potential injection characters
        cleaned = re.sub(r'[<>"\';]', '', v)
        return cleaned if cleaned else None


# Export all validation schemas
__all__ = [
    'TenantCreateRequest',
    'UserCreateRequest', 
    'BillingCreateRequest',
    'ServicePlanRequest',
    'DeviceCreateRequest',
    'TicketCreateRequest',
    'ApiKeyCreateRequest',
    'IpamSubnetRequest',
    'PortalConfigRequest',
    'PaginationParams',
    'SearchParams',
]