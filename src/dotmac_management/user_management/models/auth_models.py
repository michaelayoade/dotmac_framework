"""
Production-ready authentication models.
Comprehensive security and audit tracking.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from dotmac_management.models.base import BaseModel
from ..schemas.auth_schemas import AuthProvider, SessionType, TokenType


class UserPasswordModel(BaseModel):
    """
    User password management with security features.
    Separate from user model for security isolation.
    """
    
    __tablename__ = "user_passwords_v2"
    
    # === Foreign Key ===
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_v2.id"),
        nullable=False,
        unique=True,
        comment="Reference to user"
    )
    
    # === Password Information ===
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Hashed password"
    )
    salt = Column(
        String(255),
        nullable=True,
        comment="Password salt for additional security"
    )
    algorithm = Column(
        String(50),
        nullable=False,
        default="bcrypt",
        comment="Hashing algorithm used"
    )
    
    # === Security Metadata ===
    password_strength_score = Column(
        Integer,
        nullable=True,
        comment="Password strength score (0-100)"
    )
    is_temporary = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Is this a temporary password"
    )
    must_change = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="User must change password on next login"
    )
    
    # === Expiry Management ===
    expires_at = Column(
        DateTime,
        nullable=True,
        comment="Password expiry timestamp"
    )
    
    # === Password Reset ===
    reset_token = Column(
        String(255),
        nullable=True,
        unique=True,
        comment="Password reset token"
    )
    reset_token_expires = Column(
        DateTime,
        nullable=True,
        comment="Reset token expiry"
    )
    reset_attempts = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of reset attempts"
    )
    
    # === Relationships ===
    user = relationship(
        "UserModel",
        back_populates="passwords"
    )
    
    password_history = relationship(
        "PasswordHistoryModel",
        back_populates="current_password",
        cascade="all, delete-orphan"
    )
    
    # === Indexes ===
    __table_args__ = (
        Index("idx_user_passwords_v2_user_id", "user_id"),
        Index("idx_user_passwords_v2_reset_token", "reset_token"),
        Index("idx_user_passwords_v2_expires_at", "expires_at"),
        {"comment": "User password management with security features"}
    )
    
    # === Computed Properties ===
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if password has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @hybrid_property
    def reset_token_valid(self) -> bool:
        """Check if reset token is still valid."""
        if not self.reset_token or not self.reset_token_expires:
            return False
        return datetime.now(timezone.utc) < self.reset_token_expires
    
    # === Instance Methods ===
    
    def generate_reset_token(self, expires_in_hours: int = 24) -> str:
        """Generate password reset token."""
        token = secrets.token_urlsafe(32)
        self.reset_token = token
        self.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        self.reset_attempts = 0
        return token
    
    def clear_reset_token(self) -> None:
        """Clear password reset token."""
        self.reset_token = None
        self.reset_token_expires = None
        self.reset_attempts = 0
    
    def increment_reset_attempts(self) -> None:
        """Increment reset attempts counter."""
        self.reset_attempts += 1
    
    def set_password_expiry(self, days: int = 90) -> None:
        """Set password expiry date."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    
    def __repr__(self) -> str:
        return f"<UserPasswordModel(user_id={self.user_id}, algorithm='{self.algorithm}')>"


class PasswordHistoryModel(BaseModel):
    """
    Password history for preventing reuse.
    Tracks previous passwords for security.
    """
    
    __tablename__ = "password_history_v2"
    
    # === Foreign Keys ===
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_v2.id"),
        nullable=False,
        comment="Reference to user"
    )
    password_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_passwords_v2.id"),
        nullable=False,
        comment="Reference to current password record"
    )
    
    # === Password Information ===
    password_hash = Column(
        String(255),
        nullable=False,
        comment="Historical password hash"
    )
    algorithm = Column(
        String(50),
        nullable=False,
        comment="Hashing algorithm used"
    )
    
    # === Metadata ===
    created_by = Column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who created this password"
    )
    change_reason = Column(
        String(100),
        nullable=True,
        comment="Reason for password change"
    )
    
    # === Relationships ===
    user = relationship("UserModel")
    current_password = relationship("UserPasswordModel", back_populates="password_history")
    
    # === Indexes ===
    __table_args__ = (
        Index("idx_password_history_v2_user_id", "user_id"),
        Index("idx_password_history_v2_created_at", "created_at"),
        {"comment": "Password history for preventing reuse"}
    )
    
    def __repr__(self) -> str:
        return f"<PasswordHistoryModel(user_id={self.user_id}, created_at={self.created_at})>"


class UserSessionModel(BaseModel):
    """
    User session management with comprehensive tracking.
    """
    
    __tablename__ = "user_sessions_v2"
    
    # === Foreign Key ===
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_v2.id"),
        nullable=False,
        index=True,
        comment="Reference to user"
    )
    
    # === Session Identity ===
    session_token = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Session token"
    )
    refresh_token = Column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Refresh token"
    )
    
    # === Session Type and Provider ===
    session_type = Column(
        SQLEnum(SessionType, name="session_type_enum"),
        nullable=False,
        default=SessionType.WEB,
        comment="Type of session"
    )
    auth_provider = Column(
        SQLEnum(AuthProvider, name="auth_provider_enum"),
        nullable=False,
        default=AuthProvider.LOCAL,
        comment="Authentication provider used"
    )
    
    # === Client Information ===
    client_ip = Column(
        String(45),  # IPv6 support
        nullable=True,
        comment="Client IP address"
    )
    user_agent = Column(
        Text,
        nullable=True,
        comment="Client user agent string"
    )
    device_fingerprint = Column(
        String(255),
        nullable=True,
        comment="Device fingerprint hash"
    )
    
    # === Geographic Information ===
    country = Column(
        String(100),
        nullable=True,
        comment="Login country from IP"
    )
    city = Column(
        String(100),
        nullable=True,
        comment="Login city from IP"
    )
    
    # === Session Status ===
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Session active status"
    )
    expires_at = Column(
        DateTime,
        nullable=False,
        index=True,
        comment="Session expiry timestamp"
    )
    last_activity = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Last activity timestamp"
    )
    
    # === Security Flags ===
    is_suspicious = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Marked as suspicious activity"
    )
    mfa_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="MFA verification completed"
    )
    remember_device = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Device marked as trusted"
    )
    
    # === Termination Information ===
    terminated_at = Column(
        DateTime,
        nullable=True,
        comment="Session termination timestamp"
    )
    termination_reason = Column(
        String(100),
        nullable=True,
        comment="Reason for session termination"
    )
    
    # === Session Metadata ===
    session_metadata = Column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional session metadata"
    )
    
    # === Relationships ===
    user = relationship(
        "UserModel",
        back_populates="sessions"
    )
    
    # === Indexes ===
    __table_args__ = (
        Index("idx_user_sessions_v2_user_active", "user_id", "is_active"),
        Index("idx_user_sessions_v2_expires_at", "expires_at"),
        Index("idx_user_sessions_v2_last_activity", "last_activity"),
        Index("idx_user_sessions_v2_client_ip", "client_ip"),
        {"comment": "User session management with comprehensive tracking"}
    )
    
    # === Computed Properties ===
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    @hybrid_property
    def is_valid(self) -> bool:
        """Check if session is valid and active."""
        return self.is_active and not self.is_expired
    
    @hybrid_property
    def duration_minutes(self) -> Optional[int]:
        """Get session duration in minutes."""
        if not self.terminated_at:
            return None
        return int((self.terminated_at - self.created_at).total_seconds() / 60)
    
    # === Instance Methods ===
    
    def extend_session(self, minutes: int = 60) -> None:
        """Extend session expiry."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        self.last_activity = datetime.now(timezone.utc)
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def terminate(self, reason: str = "logout") -> None:
        """Terminate the session."""
        self.is_active = False
        self.terminated_at = datetime.now(timezone.utc)
        self.termination_reason = reason
    
    def mark_suspicious(self, reason: str = None) -> None:
        """Mark session as suspicious."""
        self.is_suspicious = True
        if reason and self.session_metadata:
            self.session_metadata["suspicious_reason"] = reason
    
    def __repr__(self) -> str:
        return f"<UserSessionModel(id={self.id}, user_id={self.user_id}, type={self.session_type})>"


class UserMFAModel(BaseModel):
    """
    Multi-factor authentication settings per user.
    """
    
    __tablename__ = "user_mfa_v2"
    
    # === Foreign Key ===
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_v2.id"),
        nullable=False,
        index=True,
        comment="Reference to user"
    )
    
    # === MFA Configuration ===
    method = Column(
        String(20),
        nullable=False,
        comment="MFA method (totp, sms, email, etc.)"
    )
    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="MFA method enabled status"
    )
    is_primary = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Is this the primary MFA method"
    )
    
    # === Method-specific Data ===
    secret = Column(
        String(255),
        nullable=True,
        comment="Encrypted secret for TOTP"
    )
    phone_number = Column(
        String(20),
        nullable=True,
        comment="Phone number for SMS MFA"
    )
    email = Column(
        String(255),
        nullable=True,
        comment="Email for email MFA"
    )
    
    # === Backup Codes ===
    backup_codes = Column(
        JSON,
        nullable=True,
        comment="Encrypted backup recovery codes"
    )
    backup_codes_used = Column(
        JSON,
        nullable=True,
        default=list,
        comment="List of used backup codes"
    )
    
    # === Verification Status ===
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="MFA method verified status"
    )
    verified_at = Column(
        DateTime,
        nullable=True,
        comment="Verification timestamp"
    )
    last_used = Column(
        DateTime,
        nullable=True,
        comment="Last time this method was used"
    )
    
    # === Usage Statistics ===
    success_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Successful verification count"
    )
    failure_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Failed verification count"
    )
    
    # === Relationships ===
    user = relationship(
        "UserModel",
        back_populates="mfa_settings"
    )
    
    # === Indexes ===
    __table_args__ = (
        Index("idx_user_mfa_v2_user_method", "user_id", "method"),
        Index("idx_user_mfa_v2_user_enabled", "user_id", "is_enabled"),
        UniqueConstraint("user_id", "method", name="uq_user_mfa_v2_user_method"),
        {"comment": "Multi-factor authentication settings per user"}
    )
    
    # === Instance Methods ===
    
    def record_success(self) -> None:
        """Record successful MFA verification."""
        self.success_count += 1
        self.last_used = datetime.now(timezone.utc)
        # Reset failure count on success
        self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record failed MFA verification."""
        self.failure_count += 1
        
        # Auto-disable if too many failures
        if self.failure_count >= 10:
            self.is_enabled = False
    
    def use_backup_code(self, code: str) -> bool:
        """Mark backup code as used."""
        if not self.backup_codes_used:
            self.backup_codes_used = []
        
        # Check if code already used
        if code in self.backup_codes_used:
            return False
            
        # Add to used codes
        self.backup_codes_used.append(code)
        return True
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate new backup codes."""
        codes = [secrets.token_hex(4).upper() for _ in range(count)]
        # In production, these should be encrypted
        self.backup_codes = codes
        self.backup_codes_used = []
        return codes
    
    def __repr__(self) -> str:
        return f"<UserMFAModel(user_id={self.user_id}, method='{self.method}', enabled={self.is_enabled})>"


class UserApiKeyModel(BaseModel):
    """
    API keys for programmatic access.
    """
    
    __tablename__ = "user_api_keys_v2"
    
    # === Foreign Key ===
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_v2.id"),
        nullable=False,
        index=True,
        comment="Reference to user"
    )
    
    # === Key Information ===
    key_id = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Public key identifier"
    )
    name = Column(
        String(100),
        nullable=False,
        comment="Human-readable key name"
    )
    description = Column(
        Text,
        nullable=True,
        comment="Key description"
    )
    
    # === Key Data ===
    key_hash = Column(
        String(255),
        nullable=False,
        comment="Hashed API key"
    )
    key_prefix = Column(
        String(10),
        nullable=False,
        comment="Key prefix for identification"
    )
    
    # === Permissions and Scope ===
    permissions = Column(
        JSON,
        nullable=True,
        default=list,
        comment="API key permissions"
    )
    scope = Column(
        String(500),
        nullable=True,
        comment="API key scope"
    )
    
    # === Lifecycle ===
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Key active status"
    )
    expires_at = Column(
        DateTime,
        nullable=True,
        comment="Key expiry timestamp"
    )
    
    # === Usage Tracking ===
    last_used = Column(
        DateTime,
        nullable=True,
        comment="Last usage timestamp"
    )
    usage_count = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total usage count"
    )
    
    # === Client Information ===
    last_used_ip = Column(
        String(45),
        nullable=True,
        comment="Last used IP address"
    )
    last_used_user_agent = Column(
        Text,
        nullable=True,
        comment="Last used user agent"
    )
    
    # === Relationships ===
    user = relationship(
        "UserModel",
        back_populates="api_keys"
    )
    
    # === Indexes ===
    __table_args__ = (
        Index("idx_user_api_keys_v2_user_active", "user_id", "is_active"),
        Index("idx_user_api_keys_v2_expires_at", "expires_at"),
        {"comment": "API keys for programmatic access"}
    )
    
    # === Computed Properties ===
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @hybrid_property
    def is_valid(self) -> bool:
        """Check if API key is valid for use."""
        return self.is_active and not self.is_expired
    
    # === Instance Methods ===
    
    def record_usage(self, ip_address: str = None, user_agent: str = None) -> None:
        """Record API key usage."""
        self.usage_count += 1
        self.last_used = datetime.now(timezone.utc)
        self.last_used_ip = ip_address
        self.last_used_user_agent = user_agent
    
    def revoke(self) -> None:
        """Revoke the API key."""
        self.is_active = False
    
    def set_expiry(self, days: int) -> None:
        """Set API key expiry."""
        self.expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    
    @classmethod
    def generate_key_components(cls) -> tuple[str, str, str]:
        """Generate key components (key_id, prefix, full_key)."""
        key_id = secrets.token_urlsafe(16)
        prefix = secrets.token_hex(4).upper()
        secret = secrets.token_urlsafe(32)
        full_key = f"{prefix}_{secret}"
        return key_id, prefix, full_key
    
    def __repr__(self) -> str:
        return f"<UserApiKeyModel(user_id={self.user_id}, key_id='{self.key_id}', name='{self.name}')>"


class AuthAuditModel(BaseModel):
    """
    Comprehensive authentication audit log.
    """
    
    __tablename__ = "auth_audit_v2"
    
    # === User Information ===
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users_v2.id"),
        nullable=True,  # May be null for failed login attempts
        index=True,
        comment="Reference to user (if known)"
    )
    username = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Username attempted (for failed logins)"
    )
    email = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Email attempted (for failed logins)"
    )
    
    # === Event Information ===
    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of authentication event"
    )
    success = Column(
        Boolean,
        nullable=False,
        index=True,
        comment="Whether the event was successful"
    )
    failure_reason = Column(
        String(200),
        nullable=True,
        comment="Reason for failure"
    )
    
    # === Session Information ===
    session_id = Column(
        String(255),
        nullable=True,
        comment="Session ID if applicable"
    )
    auth_provider = Column(
        SQLEnum(AuthProvider, name="auth_provider_enum"),
        nullable=False,
        default=AuthProvider.LOCAL,
        comment="Authentication provider used"
    )
    
    # === Client Information ===
    client_ip = Column(
        String(45),
        nullable=True,
        index=True,
        comment="Client IP address"
    )
    user_agent = Column(
        Text,
        nullable=True,
        comment="Client user agent"
    )
    device_fingerprint = Column(
        String(255),
        nullable=True,
        comment="Device fingerprint"
    )
    
    # === Geographic Information ===
    country = Column(
        String(100),
        nullable=True,
        comment="Country from IP geolocation"
    )
    city = Column(
        String(100),
        nullable=True,
        comment="City from IP geolocation"
    )
    
    # === MFA Information ===
    mfa_method = Column(
        String(20),
        nullable=True,
        comment="MFA method used"
    )
    mfa_success = Column(
        Boolean,
        nullable=True,
        comment="MFA verification success"
    )
    
    # === Risk Assessment ===
    risk_score = Column(
        Integer,
        nullable=True,
        comment="Calculated risk score (0-100)"
    )
    risk_factors = Column(
        JSON,
        nullable=True,
        comment="Risk factors identified"
    )
    
    # === Additional Metadata ===
    event_metadata = Column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional event metadata"
    )
    
    # === Relationships ===
    user = relationship("UserModel", back_populates="audit_events")
    
    # === Indexes ===
    __table_args__ = (
        Index("idx_auth_audit_v2_user_created", "user_id", "created_at"),
        Index("idx_auth_audit_v2_event_success", "event_type", "success"),
        Index("idx_auth_audit_v2_client_ip_created", "client_ip", "created_at"),
        Index("idx_auth_audit_v2_created_at", "created_at"),
        {"comment": "Comprehensive authentication audit log"}
    )
    
    def __repr__(self) -> str:
        return f"<AuthAuditModel(event_type='{self.event_type}', success={self.success}, created_at={self.created_at})>"


__all__ = [
    "UserPasswordModel",
    "PasswordHistoryModel",
    "UserSessionModel", 
    "UserMFAModel",
    "UserApiKeyModel",
    "AuthAuditModel",
]