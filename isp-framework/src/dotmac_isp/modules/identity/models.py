"""Identity models - Users, customers, roles, and authentication."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Boolean, Text, ForeignKey, Table, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.models import ContactMixin, AddressMixin


class UserRole(enum.Enum):
    """User role enumeration."""

    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    MANAGER = "manager"
    TECHNICIAN = "technician"
    SUPPORT = "support"
    SALES = "sales"
    CUSTOMER = "customer"


class CustomerType(enum.Enum):
    """Customer type enumeration."""

    RESIDENTIAL = "residential"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class AccountStatus(enum.Enum):
    """Account status enumeration."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    CANCELLED = "cancelled"


# Association table for user-role many-to-many relationship
user_roles = Table(
    "user_roles",
    TenantModel.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    extend_existing=True,
)


class User(TenantModel, ContactMixin):
    """User model for system authentication and access."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)

    # Authentication fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(String(10), default="0", nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Profile fields
    avatar_url = Column(String(500), nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="en", nullable=False)

    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    # customer = relationship("Customer", back_populates="primary_user", uselist=False)  # Keep disabled for now
    # created_tickets = relationship("Ticket", foreign_keys="Ticket.created_by", back_populates="creator")  # Keep disabled
    # assigned_tickets = relationship("Ticket", foreign_keys="Ticket.assigned_to", back_populates="assignee")  # Keep disabled

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False


class Role(TenantModel):
    """Role model for permission management."""

    __tablename__ = "roles"
    __table_args__ = {"extend_existing": True}

    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(Text, nullable=True)  # JSON string of permissions
    is_system_role = Column(Boolean, default=False, nullable=False)

    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")


class Customer(TenantModel):
    """Customer model for ISP service subscribers."""

    __tablename__ = "customers"
    __table_args__ = {"extend_existing": True}

    # Core customer fields (match migration exactly)
    customer_number = Column(String(50), nullable=False)
    display_name = Column(String(200), nullable=False)
    customer_type = Column(String(20), nullable=False)
    account_status = Column(String(20), nullable=False, default="pending")

    # Contact information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company_name = Column(String(200), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Address information
    street_address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    # Business fields
    credit_limit = Column(String(20), nullable=False, default="0.00")
    payment_terms = Column(String(50), nullable=False, default="net_30")
    installation_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Portal integration
    portal_id = Column(String(20), nullable=True)

    # Relationships
    primary_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Relationships - using string names to avoid circular imports
    primary_user = relationship("User", foreign_keys=[primary_user_id], uselist=False)
    invoices = relationship("Invoice", back_populates="customer")
    services = relationship("ServiceInstance", back_populates="customer")
    tickets = relationship("Ticket", back_populates="customer")
    # Note: These cross-module relationships are defined as forward references
    # They will be configured when the related modules are imported


class AuthToken(TenantModel):
    """Authentication token model for session management."""

    __tablename__ = "auth_tokens"
    __table_args__ = {"extend_existing": True}

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    token_type = Column(
        String(50), default="access", nullable=False
    )  # access, refresh, reset
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Additional metadata
    device_info = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Relationships
    # user = relationship("User")  # Disabled to fix registry conflicts

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not revoked and not expired)."""
        return not self.is_revoked and not self.is_expired


class LoginAttempt(TenantModel):
    """Login attempt tracking for security."""

    __tablename__ = "login_attempts"
    __table_args__ = {"extend_existing": True}

    username = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(255), nullable=True)

    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # user = relationship("User")  # Disabled to fix registry conflicts
