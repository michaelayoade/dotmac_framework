"""
Tenant management models - strategically aligned with migration schema.

This represents the true architectural vision: a container-per-tenant SaaS platform
where each tenant (ISP customer) gets their own isolated container deployment.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class TenantStatus(str, Enum):
    """Tenant lifecycle status - matching migration schema."""
    PENDING = "pending"        # Just created, not yet deployed
    ACTIVE = "active"          # Container deployed and operational
    SUSPENDED = "suspended"    # Temporarily disabled
    CANCELLED = "cancelled"    # Permanently disabled
    MAINTENANCE = "maintenance" # Under maintenance
    FAILED = "failed"          # Deployment failed


class Tenant(BaseModel):
    """
    Core tenant model - each tenant represents an ISP customer
    who will get their own containerized ISP framework deployment.
    
    Matches the migration schema exactly.
    """
    
    __tablename__ = "tenants"
    
    # Basic tenant information (from migration schema lines 48-63)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Contact information (from migration schema)
    contact_email = Column(String(255), nullable=False)
    contact_name = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    
    # Status (from migration schema)
    status = Column(String(50), nullable=False, default="pending")
    
    # Settings as JSON (from migration schema)
    settings = Column(JSON, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Tenant(name='{self.name}', slug='{self.slug}', status='{self.status}')>"
    
    @property
    def is_active(self) -> bool:
        """Check if tenant container is active and operational."""
        return self.status == TenantStatus.ACTIVE.value
    
    @property
    def can_deploy(self) -> bool:
        """Check if tenant can deploy new container instances."""
        return self.status in [TenantStatus.ACTIVE.value, TenantStatus.MAINTENANCE.value]
    
    def get_container_name(self) -> str:
        """Get the Docker container name for this tenant."""
        return f"dotmac-isp-{self.slug}"
    
    def get_container_url(self) -> str:
        """Get the URL where this tenant's ISP framework will be accessible."""
        return f"https://{self.slug}.dotmac-isp.com"


class TenantConfiguration(BaseModel):
    """
    Tenant configuration model - matches migration schema.
    Stores configuration for tenant's ISP framework container.
    """
    
    __tablename__ = "tenant_configurations"
    
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    category = Column(String(100), nullable=False)  # e.g., 'isp_settings', 'billing', 'networking'
    key = Column(String(255), nullable=False)       # e.g., 'company_name', 'default_plan'
    value = Column(JSON, nullable=True)             # The actual configuration value
    is_encrypted = Column(Boolean, nullable=False, default=False)
    
    # Relationship back to tenant
    tenant = relationship("Tenant", back_populates="configurations")
    
    def __repr__(self) -> str:
        return f"<TenantConfiguration(category='{self.category}', key='{self.key}')>"


class TenantInvitation(BaseModel):
    """
    Tenant invitation model - for inviting users to join a tenant's ISP management.
    This is a logical model that may not have a direct table yet.
    """
    
    __tablename__ = "tenant_invitations"
    
    tenant_id = Column(PGUUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    invited_by = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<TenantInvitation(email='{self.email}', role='{self.role}')>"




# Add the relationships to Tenant
Tenant.configurations = relationship("TenantConfiguration", back_populates="tenant", cascade="all, delete-orphan")
Tenant.deployments = relationship("Deployment", back_populates="tenant", cascade="all, delete-orphan")