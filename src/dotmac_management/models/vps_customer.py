"""
VPS Customer models for customer-managed server deployments
"""

from enum import Enum

from dotmac.database.base import Base
from dotmac.database.mixins import TimestampMixin, UUIDMixin
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class VPSStatus(str, Enum):
    """VPS customer deployment and operational status"""

    REQUESTED = "requested"  # Initial setup request submitted
    VALIDATING = "validating"  # Validating customer information
    REQUIREMENTS_CHECK = "requirements_check"  # Checking VPS specifications
    CONNECTION_TEST = "connection_test"  # Testing SSH connectivity
    DEPLOYING = "deploying"  # Installing DotMac framework
    CONFIGURING = "configuring"  # Setting up configuration
    TESTING = "testing"  # Running health checks
    READY = "ready"  # Deployment completed successfully
    ACTIVE = "active"  # Customer system active and monitored
    MAINTENANCE = "maintenance"  # Under maintenance
    SUSPENDED = "suspended"  # Temporarily disabled
    FAILED = "failed"  # Deployment failed
    DECOMMISSIONED = "decommissioned"  # Customer terminated service


class SupportTier(str, Enum):
    """Support service tiers"""

    BASIC = "basic"  # Email support, business hours
    PREMIUM = "premium"  # Phone + email, extended hours
    ENTERPRISE = "enterprise"  # Dedicated support, 24/7


class VPSCustomer(Base, TimestampMixin, UUIDMixin):
    """VPS-specific extensions for CustomerTenant with deployment_type = CUSTOMER_VPS

    This model extends the base tenant model with VPS-specific operational data
    that doesn't belong in the main tenant table.
    """

    __tablename__ = "vps_customers"

    # Link to the main tenant record
    tenant_id = Column(Integer, ForeignKey("customer_tenants.id"), nullable=False, unique=True, index=True)
    tenant = relationship("CustomerTenant", backref="vps_config")

    # VPS-specific operational data
    deployment_logs = Column(JSON, default=list)
    deployment_started_at = Column(DateTime)
    deployment_completed_at = Column(DateTime)
    deployment_config = Column(JSON, default=dict)  # Deployment-specific config

    # Support tracking (extends basic tenant support)
    last_support_contact = Column(DateTime)
    support_ticket_count = Column(Integer, default=0)
    satisfaction_score = Column(Integer)  # 1-5 rating

    # VPS-specific billing
    monthly_fee = Column(Integer)  # In cents - VPS-specific fees
    setup_fee_paid = Column(Boolean, default=False)

    # Advanced monitoring
    monitoring_enabled = Column(Boolean, default=True)
    alert_preferences = Column(JSON, default=dict)
    uptime_percentage = Column(String(10))  # e.g., "99.9%"

    # Service level agreement
    sla_level = Column(String(50))  # e.g., "99.9%", "99.95%"
    sla_credits = Column(Integer, default=0)  # SLA violation credits

    def __repr__(self):
        return f"<VPSCustomer(tenant_id='{self.tenant_id}', vps_config_id='{self.id}')>"


class VPSSupportTicket(Base, TimestampMixin, UUIDMixin):
    """Support tickets for VPS customers"""

    __tablename__ = "vps_support_tickets"

    # Ticket identification
    ticket_id = Column(String(50), unique=True, nullable=False, index=True)

    # Customer relationship - directly to tenant for unified support
    tenant_id = Column(Integer, ForeignKey("customer_tenants.id"), nullable=False)
    tenant = relationship("CustomerTenant", backref="vps_support_tickets")

    # Ticket details
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    category = Column(String(50))  # deployment, configuration, performance, billing
    status = Column(String(20), default="open")  # open, in_progress, resolved, closed

    # Assignment and handling
    assigned_to = Column(Integer, ForeignKey("users.id"))
    assignee = relationship("User", foreign_keys=[assigned_to])

    # Customer contact
    customer_contact_name = Column(String(200))
    customer_contact_email = Column(String(255))
    customer_contact_phone = Column(String(50))

    # Resolution tracking
    resolution = Column(Text)
    resolved_at = Column(DateTime)
    customer_satisfaction = Column(Integer)  # 1-5 rating

    # Internal notes and communication
    internal_notes = Column(JSON, default=list)
    customer_communication = Column(JSON, default=list)

    # Escalation
    escalated = Column(Boolean, default=False)
    escalated_at = Column(DateTime)
    escalated_to = Column(Integer, ForeignKey("users.id"))

    def __repr__(self):
        return f"<VPSSupportTicket(ticket_id='{self.ticket_id}', subject='{self.subject}', status='{self.status}')>"


class VPSDeploymentEvent(Base, TimestampMixin, UUIDMixin):
    """Deployment events and logs for VPS customers"""

    __tablename__ = "vps_deployment_events"

    # Event identification
    event_id = Column(String(100), unique=True, nullable=False, index=True)

    # Customer relationship - directly to tenant
    tenant_id = Column(Integer, ForeignKey("customer_tenants.id"), nullable=False)
    tenant = relationship("CustomerTenant", backref="vps_deployment_events")

    # Event details
    event_type = Column(String(100), nullable=False)  # e.g., "ssh_test", "docker_install"
    status = Column(String(20), nullable=False)  # in_progress, success, failed, warning
    message = Column(String(500))

    # Execution details
    step_number = Column(Integer)
    correlation_id = Column(String(100))  # Links related events
    operator = Column(String(100))  # "system" or user email

    # Technical details
    command_executed = Column(Text)
    exit_code = Column(Integer)
    stdout_output = Column(Text)
    stderr_output = Column(Text)
    execution_time_seconds = Column(Integer)

    # Error handling
    error_details = Column(JSON)
    retry_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<VPSDeploymentEvent(event_type='{self.event_type}', status='{self.status}', tenant_id='{self.tenant_id}')>"


class VPSHealthCheck(Base, TimestampMixin, UUIDMixin):
    """Health check records for VPS customers"""

    __tablename__ = "vps_health_checks"

    # Customer relationship - directly to tenant
    tenant_id = Column(Integer, ForeignKey("customer_tenants.id"), nullable=False)
    tenant = relationship("CustomerTenant", backref="vps_health_checks")

    # Check details
    check_type = Column(String(50), nullable=False)  # ssh, http, database, service
    status = Column(String(20), nullable=False)  # healthy, warning, critical, unknown

    # Timing
    check_duration_ms = Column(Integer)
    response_time_ms = Column(Integer)

    # Results
    details = Column(JSON, default=dict)
    error_message = Column(String(500))

    # Check metadata
    check_source = Column(String(50), default="automated")  # automated, manual, alert
    severity = Column(String(20))  # info, warning, error, critical

    def __repr__(self):
        return f"<VPSHealthCheck(type='{self.check_type}', status='{self.status}', tenant_id='{self.tenant_id}')>"
