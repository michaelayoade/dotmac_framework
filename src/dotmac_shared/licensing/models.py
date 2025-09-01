"""
License Contract Models
Database models for license management and enforcement
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func

from dotmac_shared.database.base import Base
from dotmac_shared.database.mixins import TimestampMixin, UUIDMixin


class LicenseStatus(str, Enum):
    """License contract status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class LicenseContract(Base, TimestampMixin, UUIDMixin):
    """License contract for ISP instances"""
    
    __tablename__ = "license_contracts"
    
    # Contract identification
    contract_id = Column(String(100), unique=True, nullable=False, index=True)
    subscription_id = Column(String(100), nullable=False, index=True)
    
    # Status and validity
    status = Column(String(20), default=LicenseStatus.ACTIVE, nullable=False, index=True)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    
    # Contract details
    contract_type = Column(String(50), nullable=False)  # starter, professional, enterprise
    contract_hash = Column(String(64), nullable=False)  # Integrity verification
    
    # Resource limits
    max_customers = Column(Integer, nullable=True)
    max_concurrent_users = Column(Integer, nullable=True)
    max_bandwidth_gbps = Column(Integer, nullable=True)
    max_storage_gb = Column(Integer, nullable=True)
    max_api_calls_per_hour = Column(Integer, nullable=True)
    max_network_devices = Column(Integer, nullable=True)
    
    # Feature control
    enabled_features = Column(JSON, default=list)
    disabled_features = Column(JSON, default=list)
    feature_limits = Column(JSON, default=dict)
    
    # Enforcement configuration
    enforcement_mode = Column(String(20), default="strict", nullable=False)  # strict, warning, disabled
    
    # Instance references
    issuer_management_instance = Column(String(100), nullable=False)
    target_isp_instance = Column(String(100), nullable=False, index=True)
    
    # Usage tracking
    current_usage = Column(JSON, default=dict)
    violation_count = Column(Integer, default=0)
    last_violation_at = Column(DateTime, nullable=True)
    
    # Management relationship
    tenant_id = Column(Integer, ForeignKey("customer_tenants.id"), nullable=False, index=True)
    
    @property
    def is_expired(self) -> bool:
        """Check if license has expired"""
        return datetime.utcnow() > self.valid_until
    
    @property
    def days_until_expiry(self) -> int:
        """Days until license expires"""
        delta = self.valid_until - datetime.utcnow()
        return max(0, delta.days)
    
    @property
    def is_active(self) -> bool:
        """Check if license is currently active"""
        return (
            self.status == LicenseStatus.ACTIVE and
            not self.is_expired
        )
    
    def __repr__(self):
        return f"<LicenseContract(contract_id='{self.contract_id}', type='{self.contract_type}', status='{self.status}')>"


class LicenseViolation(Base, TimestampMixin, UUIDMixin):
    """License violation tracking"""
    
    __tablename__ = "license_violations"
    
    # Contract reference
    contract_id = Column(String(100), ForeignKey("license_contracts.contract_id"), nullable=False, index=True)
    
    # Violation details
    violation_type = Column(String(100), nullable=False)  # customer_limit_exceeded, feature_disabled, etc.
    severity = Column(String(20), nullable=False)  # warning, error, critical
    
    # Violation data
    limit_type = Column(String(50), nullable=False)
    limit_value = Column(Integer, nullable=True)
    actual_value = Column(Integer, nullable=True)
    exceeded_by = Column(Integer, nullable=True)
    
    # Context
    violation_context = Column(JSON, nullable=True)
    user_action = Column(String(200), nullable=True)  # What user was trying to do
    endpoint_path = Column(String(200), nullable=True)
    
    # Resolution
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_method = Column(String(100), nullable=True)
    
    # Additional metadata
    tenant_usage_snapshot = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<LicenseViolation(contract_id='{self.contract_id}', type='{self.violation_type}', severity='{self.severity}')>"


class LicenseUsageLog(Base, TimestampMixin):
    """License usage tracking log"""
    
    __tablename__ = "license_usage_logs"
    
    id = Column(Integer, primary_key=True)
    
    # Contract reference
    contract_id = Column(String(100), ForeignKey("license_contracts.contract_id"), nullable=False, index=True)
    
    # Usage period
    log_date = Column(DateTime, nullable=False, index=True)
    log_hour = Column(Integer, nullable=True)  # 0-23 for hourly logs
    
    # Usage metrics
    customer_count = Column(Integer, default=0)
    concurrent_users_peak = Column(Integer, default=0)
    concurrent_users_avg = Column(Integer, default=0)
    api_calls_count = Column(Integer, default=0)
    storage_used_gb = Column(Integer, default=0)
    bandwidth_used_gbps_peak = Column(Integer, default=0)
    network_devices_count = Column(Integer, default=0)
    
    # Feature usage
    features_used = Column(JSON, default=list)
    feature_usage_counts = Column(JSON, default=dict)
    
    # Performance metrics
    response_time_avg_ms = Column(Integer, nullable=True)
    error_rate_percent = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<LicenseUsageLog(contract_id='{self.contract_id}', date='{self.log_date}')>"


class LicenseAlert(Base, TimestampMixin, UUIDMixin):
    """License-related alerts and notifications"""
    
    __tablename__ = "license_alerts"
    
    # Contract reference
    contract_id = Column(String(100), ForeignKey("license_contracts.contract_id"), nullable=False, index=True)
    
    # Alert details
    alert_type = Column(String(100), nullable=False)  # approaching_limit, expired, violation
    severity = Column(String(20), nullable=False)  # info, warning, critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Alert triggers
    trigger_threshold = Column(Integer, nullable=True)  # e.g., 80% for approaching limit
    current_value = Column(Integer, nullable=True)
    limit_value = Column(Integer, nullable=True)
    
    # Alert status
    status = Column(String(20), default="active", nullable=False)  # active, acknowledged, resolved
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Notification tracking
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    webhook_sent = Column(Boolean, default=False)
    webhook_sent_at = Column(DateTime, nullable=True)
    
    # Additional context
    alert_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<LicenseAlert(contract_id='{self.contract_id}', type='{self.alert_type}', severity='{self.severity}')>"