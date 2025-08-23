"""
User and authentication models.
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Text
from .base import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class UserRole:
    """User role constants."""
    MASTER_ADMIN = "master_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_USER = "tenant_user"
    RESELLER = "reseller"
    SUPPORT = "support"


class User(BaseModel):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    # Basic user information
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # User status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Role and permissions
    role = Column(String(50), nullable=False, index=True)  # master_admin, tenant_admin, etc.
    
    # Tenant association (None for master admins)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    
    # Authentication metadata
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    
    # Profile information
    phone = Column(String(20), nullable=True)
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="en", nullable=False)
    
    # Security settings
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(32), nullable=True)
    password_changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Notification preferences
    email_notifications = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    created_deployments = relationship("Deployment", back_populates="created_by_user")
    
    def __repr__(self) -> str:
        return f"<User(email='{self.email}', role='{self.role}')>"
    
    @property
    def is_master_admin(self) -> bool:
        """Check if user is master admin."""
        return self.role == "master_admin"
    
    @property
    def is_tenant_admin(self) -> bool:
        """Check if user is tenant admin."""
        return self.role == "tenant_admin"
    
    @property
    def is_locked(self) -> bool:
        """Check if user account is locked."""
        return self.locked_until and self.locked_until > datetime.utcnow()
    
    def lock_account(self, duration_minutes: int = 30) -> None:
        """Lock user account for specified duration."""
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.failed_login_attempts += 1
    
    def unlock_account(self) -> None:
        """Unlock user account."""
        self.locked_until = None
        self.failed_login_attempts = 0
    
    def record_login(self) -> None:
        """Record successful login."""
        self.last_login = datetime.utcnow()
        self.login_count += 1
        self.failed_login_attempts = 0
        self.locked_until = None


class UserSession(BaseModel):
    """User session tracking."""
    
    __tablename__ = "user_sessions"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    device_fingerprint = Column(String(255), nullable=True)
    
    # Session status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="sessions")
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def extend_session(self, minutes: int = 60) -> None:
        """Extend session expiry."""
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        self.last_activity = datetime.utcnow()
    
    def revoke(self) -> None:
        """Revoke the session."""
        self.is_active = False


class UserInvitation(BaseModel):
    """User invitation for tenant access."""
    
    __tablename__ = "user_invitations"
    
    # Invitation details
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    
    # Invitation metadata
    invitation_token = Column(String(255), unique=True, nullable=False, index=True)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    
    # Status tracking
    is_accepted = Column(Boolean, default=False, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    accepted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant")
    invited_by_user = relationship("User", foreign_keys=[invited_by])
    accepted_by_user = relationship("User", foreign_keys=[accepted_by])
    
    @property
    def is_expired(self) -> bool:
        """Check if invitation is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if invitation is valid for acceptance."""
        return not self.is_accepted and not self.is_expired and self.is_active