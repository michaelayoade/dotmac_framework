"""Notification system models for alerts, templates, and delivery."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin


class NotificationPriority(str, Enum):
    """Notification priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


class NotificationType(str, Enum):
    """Notification types."""

    SYSTEM_ALERT = "system_alert"
    NETWORK_ALERT = "network_alert"
    BILLING_ALERT = "billing_alert"
    SERVICE_ALERT = "service_alert"
    SUPPORT_ALERT = "support_alert"
    MAINTENANCE_ALERT = "maintenance_alert"
    SECURITY_ALERT = "security_alert"
    PROMOTIONAL = "promotional"
    INFORMATIONAL = "informational"

    # Project and Installation notifications
    PROJECT_CREATED = "project_created"
    PROJECT_STARTED = "project_started"
    PROJECT_MILESTONE = "project_milestone"
    PROJECT_COMPLETED = "project_completed"
    PROJECT_DELAYED = "project_delayed"

    # Field Operations notifications
    TECHNICIAN_ASSIGNED = "technician_assigned"
    TECHNICIAN_ENROUTE = "technician_enroute"
    TECHNICIAN_ARRIVED = "technician_arrived"
    INSTALLATION_STARTED = "installation_started"
    INSTALLATION_COMPLETED = "installation_completed"
    APPOINTMENT_SCHEDULED = "appointment_scheduled"
    APPOINTMENT_REMINDER = "appointment_reminder"

    # Sales Integration notifications
    OPPORTUNITY_WON = "opportunity_won"
    CUSTOMER_ONBOARDED = "customer_onboarded"
    WELCOME_CUSTOMER = "welcome_customer"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"
    IN_APP = "in_app"


class NotificationStatus(str, Enum):
    """Notification delivery status."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BOUNCED = "bounced"
    COMPLAINED = "complained"


class DeliveryStatus(str, Enum):
    """Delivery attempt status."""

    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    SKIPPED = "skipped"


class NotificationTemplate(TenantModel, StatusMixin, AuditMixin):
    """Notification template model for reusable message templates."""

    __tablename__ = "notification_templates"

    # Template identification
    template_name = Column(String(255), nullable=False, index=True)
    template_code = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Template configuration
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    priority = Column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.NORMAL,
        nullable=False,
    )

    # Template content
    subject_template = Column(String(500), nullable=True)
    body_template = Column(Text, nullable=False)
    html_template = Column(Text, nullable=True)

    # Channel configuration
    supported_channels = Column(JSON, nullable=False)  # List of supported channels
    default_channel = Column(SQLEnum(NotificationChannel), nullable=False)

    # Template variables
    required_variables = Column(
        JSON, nullable=True
    )  # List of required template variables
    optional_variables = Column(
        JSON, nullable=True
    )  # List of optional template variables

    # Localization
    language = Column(String(10), default="en", nullable=False)

    # Template settings
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_system_template = Column(Boolean, default=False, nullable=False)

    # Rate limiting
    rate_limit_enabled = Column(Boolean, default=False, nullable=False)
    rate_limit_count = Column(Integer, nullable=True)  # Max notifications per period
    rate_limit_period = Column(Integer, nullable=True)  # Period in seconds

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    notifications = relationship("Notification", back_populates="template")
    rules = relationship("NotificationRule", back_populates="template")

    __table_args__ = (
        Index("ix_templates_tenant_code", "tenant_id", "template_code", unique=True),
        Index("ix_templates_type_active", "notification_type", "is_active"),
    )

    def __repr__(self):
        return f"<NotificationTemplate(name='{self.template_name}', type='{self.notification_type}')>"


class NotificationRule(TenantModel, StatusMixin, AuditMixin):
    """Notification rule for automated notification triggers."""

    __tablename__ = "notification_rules"

    # Rule identification
    rule_name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Rule configuration
    event_type = Column(
        String(100), nullable=False, index=True
    )  # What event triggers this
    conditions = Column(JSON, nullable=False)  # Rule conditions

    # Template and channels
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notification_templates.id"),
        nullable=False,
        index=True,
    )
    override_channels = Column(JSON, nullable=True)  # Override template channels

    # Recipients
    recipient_rules = Column(JSON, nullable=False)  # Rules for determining recipients

    # Timing
    delay_seconds = Column(Integer, default=0, nullable=False)  # Delay before sending
    schedule_pattern = Column(
        String(100), nullable=True
    )  # Cron pattern for scheduled notifications

    # Rule state
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, default=0, nullable=False)

    # Throttling
    throttle_enabled = Column(Boolean, default=False, nullable=False)
    throttle_limit = Column(Integer, nullable=True)  # Max triggers per period
    throttle_period = Column(Integer, nullable=True)  # Period in seconds

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    template = relationship("NotificationTemplate", back_populates="rules")

    __table_args__ = (Index("ix_rules_event_active", "event_type", "is_active"),)

    def __repr__(self):
        return f"<NotificationRule(name='{self.rule_name}', event='{self.event_type}')>"


class Notification(TenantModel, AuditMixin):
    """Individual notification instance."""

    __tablename__ = "notifications"

    # Notification identification
    notification_id = Column(String(100), nullable=False, unique=True, index=True)

    # Template and rule reference
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notification_templates.id"),
        nullable=True,
        index=True,
    )
    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notification_rules.id"),
        nullable=True,
        index=True,
    )

    # Notification details
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    priority = Column(
        SQLEnum(NotificationPriority),
        default=NotificationPriority.NORMAL,
        nullable=False,
        index=True,
    )

    # Content
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    html_body = Column(Text, nullable=True)

    # Recipients
    recipient_type = Column(String(50), nullable=False)  # user, customer, team, etc.
    recipient_id = Column(String(100), nullable=True)  # ID of recipient
    recipient_email = Column(String(255), nullable=True)
    recipient_phone = Column(String(20), nullable=True)
    recipient_name = Column(String(255), nullable=True)

    # Delivery configuration
    channels = Column(JSON, nullable=False)  # List of delivery channels to try
    preferred_channel = Column(SQLEnum(NotificationChannel), nullable=True)

    # Status and timing
    status = Column(
        SQLEnum(NotificationStatus),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Source information
    source_system = Column(String(100), nullable=True)  # Which system generated this
    source_event = Column(String(100), nullable=True)  # Which event triggered this
    source_reference_id = Column(
        String(100), nullable=True
    )  # Reference to source object

    # Retry configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Additional data
    notification_metadata = Column(
        JSON, nullable=True
    )  # Additional notification metadata
    variables = Column(JSON, nullable=True)  # Template variables used

    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0, nullable=False)

    # Relationships
    template = relationship("NotificationTemplate", back_populates="notifications")
    rule = relationship("NotificationRule")
    deliveries = relationship(
        "NotificationDelivery",
        back_populates="notification",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_notifications_status_scheduled", "status", "scheduled_at"),
        Index("ix_notifications_recipient", "recipient_type", "recipient_id"),
        Index("ix_notifications_source", "source_system", "source_event"),
    )

    @hybrid_property
    def is_delivered(self) -> bool:
        """Check if notification was successfully delivered."""
        return self.status == NotificationStatus.DELIVERED

    @hybrid_property
    def is_failed(self) -> bool:
        """Check if notification failed to deliver."""
        return self.status == NotificationStatus.FAILED

    def __repr__(self):
        return f"<Notification(id='{self.notification_id}', type='{self.notification_type}', status='{self.status}')>"


class NotificationDelivery(TenantModel):
    """Individual delivery attempt record."""

    __tablename__ = "notification_deliveries"

    notification_id = Column(
        UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False, index=True
    )

    # Delivery details
    channel = Column(SQLEnum(NotificationChannel), nullable=False, index=True)
    status = Column(SQLEnum(DeliveryStatus), nullable=False, index=True)

    # Timing
    attempted_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Delivery details
    delivery_address = Column(
        String(500), nullable=True
    )  # Email, phone, webhook URL, etc.
    provider = Column(String(100), nullable=True)  # Which provider was used
    provider_message_id = Column(String(255), nullable=True)  # Provider's message ID

    # Response details
    response_code = Column(String(50), nullable=True)
    response_message = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Cost tracking
    delivery_cost = Column(Float, nullable=True)  # Cost of this delivery
    cost_currency = Column(String(3), default="USD", nullable=True)

    # Error details
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    # Additional data
    delivery_data = Column(JSON, nullable=True)  # Provider-specific data

    # Relationships
    notification = relationship("Notification", back_populates="deliveries")

    __table_args__ = (
        Index("ix_deliveries_channel_status", "channel", "status"),
        Index("ix_deliveries_attempted", "attempted_at"),
    )

    def __repr__(self):
        return (
            f"<NotificationDelivery(channel='{self.channel}', status='{self.status}')>"
        )


class NotificationPreference(TenantModel, AuditMixin):
    """User notification preferences."""

    __tablename__ = "notification_preferences"

    # User identification
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_type = Column(
        String(50), default="user", nullable=False
    )  # user, customer, admin

    # Preference configuration
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False)

    # Channel preferences
    preferred_channels = Column(
        JSON, nullable=False
    )  # Ordered list of preferred channels
    disabled_channels = Column(JSON, nullable=True)  # Explicitly disabled channels

    # Timing preferences
    quiet_hours_start = Column(String(5), nullable=True)  # HH:MM format
    quiet_hours_end = Column(String(5), nullable=True)  # HH:MM format
    timezone = Column(String(50), default="UTC", nullable=False)

    # Frequency preferences
    digest_enabled = Column(Boolean, default=False, nullable=False)
    digest_frequency = Column(String(20), nullable=True)  # hourly, daily, weekly
    max_frequency = Column(String(50), nullable=True)  # Rate limiting preference

    # Contact information
    email_address = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    push_token = Column(String(500), nullable=True)

    # Additional preferences
    language = Column(String(10), default="en", nullable=False)
    custom_preferences = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_preferences_user_type", "user_id", "notification_type", unique=True),
    )

    def __repr__(self):
        return f"<NotificationPreference(user='{self.user_id}', type='{self.notification_type}', enabled={self.enabled})>"


class NotificationQueue(TenantModel):
    """Notification queue for batch processing."""

    __tablename__ = "notification_queue"

    # Queue configuration
    queue_name = Column(String(100), nullable=False, index=True)
    priority = Column(Integer, default=0, nullable=False, index=True)

    # Notification reference
    notification_id = Column(
        UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False, index=True
    )

    # Queue status
    status = Column(
        String(20), default="queued", nullable=False, index=True
    )  # queued, processing, completed, failed

    # Processing details
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Worker information
    worker_id = Column(String(100), nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    # Error tracking
    last_error = Column(Text, nullable=True)

    # Relationships
    notification = relationship("Notification")

    __table_args__ = (
        Index("ix_queue_status_scheduled", "status", "scheduled_at"),
        Index("ix_queue_priority", "priority", "scheduled_at"),
    )

    def __repr__(self):
        return f"<NotificationQueue(queue='{self.queue_name}', status='{self.status}')>"


class NotificationLog(TenantModel):
    """Notification activity log."""

    __tablename__ = "notification_logs"

    # Log details
    notification_id = Column(
        UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False, index=True
    )
    event_type = Column(
        String(50), nullable=False, index=True
    )  # created, sent, delivered, failed, etc.
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Event details
    description = Column(Text, nullable=True)
    channel = Column(SQLEnum(NotificationChannel), nullable=True)

    # System information
    system_info = Column(JSON, nullable=True)  # System context when event occurred

    # Performance metrics
    processing_time_ms = Column(Integer, nullable=True)
    memory_usage_mb = Column(Float, nullable=True)

    # Relationships
    notification = relationship("Notification")

    __table_args__ = (
        Index("ix_logs_notification_event", "notification_id", "event_type"),
        Index("ix_logs_timestamp", "event_timestamp"),
    )

    def __repr__(self):
        return f"<NotificationLog(notification='{self.notification_id}', event='{self.event_type}')>"
