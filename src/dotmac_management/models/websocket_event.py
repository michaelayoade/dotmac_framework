"""WebSocket Event Models for the Management Platform."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from dotmac.database.base import AuditableMixin, TenantModel


class EventType(str, Enum):
    """WebSocket event types."""

    # System Events
    SYSTEM_NOTIFICATION = "system_notification"
    CONNECTION_STATUS = "connection_status"
    HEARTBEAT = "heartbeat"

    # User Events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_SESSION_UPDATE = "user_session_update"

    # Platform Events
    TENANT_CREATED = "tenant_created"
    TENANT_UPDATED = "tenant_updated"
    TENANT_DEPLOYED = "tenant_deployed"
    TENANT_SUSPENDED = "tenant_suspended"

    # Billing Events
    PAYMENT_PROCESSED = "payment_processed"
    INVOICE_GENERATED = "invoice_generated"
    BILLING_UPDATE = "billing_update"
    PAYMENT_FAILED = "payment_failed"

    # Service Events
    SERVICE_ACTIVATED = "service_activated"
    SERVICE_SUSPENDED = "service_suspended"
    SERVICE_PROVISIONED = "service_provisioned"
    SERVICE_ERROR = "service_error"

    # Network Events
    NETWORK_ALERT = "network_alert"
    DEVICE_STATUS_CHANGE = "device_status_change"
    BANDWIDTH_ALERT = "bandwidth_alert"
    CONNECTION_EVENT = "connection_event"

    # Support Events
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_RESOLVED = "ticket_resolved"

    # File Events
    FILE_UPLOADED = "file_uploaded"
    FILE_DOWNLOADED = "file_downloaded"
    FILE_DELETED = "file_deleted"
    FILE_SHARED = "file_shared"

    # Domain Events
    DOMAIN_ADDED = "domain_added"
    DOMAIN_VERIFIED = "domain_verified"
    DOMAIN_EXPIRED = "domain_expired"
    DNS_UPDATED = "dns_updated"


class EventPriority(str, Enum):
    """Event priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class DeliveryStatus(str, Enum):
    """Event delivery status."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SubscriptionType(str, Enum):
    """WebSocket subscription types."""

    USER_SPECIFIC = "user_specific"
    TENANT_WIDE = "tenant_wide"
    ROLE_BASED = "role_based"
    EVENT_TYPE = "event_type"
    ENTITY_SPECIFIC = "entity_specific"


class WebSocketEvent(TenantModel, AuditableMixin):
    """WebSocket event tracking and delivery."""

    __tablename__ = "websocket_events"

    # Event identification
    event_id = Column(String(100), nullable=False, unique=True, index=True)
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    event_category = Column(
        String(50), nullable=False, index=True
    )  # system, billing, network, etc.

    # Event content
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_data = Column(JSON, nullable=False)
    metadata = Column(JSON, nullable=True)

    # Event properties
    priority = Column(
        SQLEnum(EventPriority), default=EventPriority.NORMAL, nullable=False, index=True
    )
    is_persistent = Column(
        Boolean, default=False, nullable=False
    )  # Store for offline users
    requires_acknowledgment = Column(Boolean, default=False, nullable=False)

    # Targeting
    target_user_id = Column(String(100), nullable=True, index=True)
    target_user_ids = Column(
        JSON, nullable=True
    )  # List of user IDs for multi-user events
    target_roles = Column(JSON, nullable=True)  # List of roles
    broadcast_to_tenant = Column(Boolean, default=False, nullable=False)

    # Delivery tracking
    delivery_status = Column(
        SQLEnum(DeliveryStatus),
        default=DeliveryStatus.PENDING,
        nullable=False,
        index=True,
    )
    delivery_attempts = Column(Integer, default=0, nullable=False)
    max_delivery_attempts = Column(Integer, default=3, nullable=False)
    last_delivery_attempt = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True, index=True)

    # Scheduling
    scheduled_for = Column(DateTime, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)

    # Source information
    source_service = Column(String(100), nullable=True, index=True)
    source_entity_type = Column(String(50), nullable=True, index=True)
    source_entity_id = Column(String(100), nullable=True, index=True)

    # Response tracking
    acknowledged_by = Column(JSON, nullable=True)  # List of user IDs who acknowledged
    acknowledged_at = Column(DateTime, nullable=True)
    response_data = Column(JSON, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Custom fields
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    deliveries = relationship(
        "WebSocketDelivery", back_populates="event", cascade="all, delete-orphan"
    )
    subscriptions = relationship("WebSocketSubscription", back_populates="event")

    __table_args__ = (
        Index("ix_websocket_events_type_priority", "event_type", "priority"),
        Index(
            "ix_websocket_events_delivery_status", "delivery_status", "scheduled_for"
        ),
        Index("ix_websocket_events_tenant_user", "tenant_id", "target_user_id"),
        Index(
            "ix_websocket_events_source",
            "source_service",
            "source_entity_type",
            "source_entity_id",
        ),
        Index("ix_websocket_events_expires", "expires_at"),
        Index("ix_websocket_events_scheduled", "scheduled_for"),
    )

    @hybrid_property
    def is_expired(self):
        """Check if event has expired."""
        return self.expires_at and datetime.now(timezone.utc) > self.expires_at

    @hybrid_property
    def is_due_for_delivery(self):
        """Check if event is due for delivery."""
        if self.scheduled_for:
            return datetime.now(timezone.utc) >= self.scheduled_for
        return True

    @hybrid_property
    def acknowledgment_rate(self):
        """Calculate acknowledgment rate if required."""
        if not self.requires_acknowledgment or not self.acknowledged_by:
            return None

        target_count = 0
        if self.target_user_ids:
            target_count = len(self.target_user_ids)
        elif self.target_user_id:
            target_count = 1

        if target_count > 0:
            return len(self.acknowledged_by) / target_count * 100
        return 0

    def __repr__(self):
        return f"<WebSocketEvent(id='{self.event_id}', type='{self.event_type}', status='{self.delivery_status}')>"


class WebSocketConnection(TenantModel):
    """Active WebSocket connection tracking."""

    __tablename__ = "websocket_connections"

    # Connection identification
    connection_id = Column(String(100), nullable=False, unique=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(100), nullable=True, index=True)

    # Connection details
    client_ip = Column(String(45), nullable=True, index=True)
    user_agent = Column(String(500), nullable=True)
    origin = Column(String(200), nullable=True)

    # Connection lifecycle
    connected_at = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), index=True
    )
    last_ping = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    disconnected_at = Column(DateTime, nullable=True, index=True)

    # Connection properties
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    protocol_version = Column(String(10), default="1.0", nullable=False)
    compression_enabled = Column(Boolean, default=False, nullable=False)

    # Usage statistics
    messages_sent = Column(Integer, default=0, nullable=False)
    messages_received = Column(Integer, default=0, nullable=False)
    bytes_sent = Column(Integer, default=0, nullable=False)
    bytes_received = Column(Integer, default=0, nullable=False)

    # Subscription tracking
    active_subscriptions = Column(JSON, nullable=True)  # List of subscription names

    # Error tracking
    error_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    last_error_at = Column(DateTime, nullable=True)

    # Connection quality
    average_latency_ms = Column(Integer, nullable=True)
    connection_quality_score = Column(Integer, default=100, nullable=False)  # 0-100

    # Custom fields
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    deliveries = relationship("WebSocketDelivery", back_populates="connection")

    __table_args__ = (
        Index("ix_websocket_connections_user", "user_id", "is_active"),
        Index("ix_websocket_connections_tenant_active", "tenant_id", "is_active"),
        Index("ix_websocket_connections_session", "session_id"),
        Index("ix_websocket_connections_activity", "last_activity"),
        Index("ix_websocket_connections_ip", "client_ip"),
    )

    @hybrid_property
    def connection_duration_seconds(self):
        """Get connection duration in seconds."""
        end_time = self.disconnected_at or datetime.now(timezone.utc)
        return (end_time - self.connected_at).total_seconds()

    @hybrid_property
    def is_stale(self):
        """Check if connection appears stale (no activity for 5 minutes)."""
        if not self.last_activity:
            return False
        return (datetime.now(timezone.utc) - self.last_activity).total_seconds() > 300

    def __repr__(self):
        return f"<WebSocketConnection(id='{self.connection_id}', user='{self.user_id}', active={self.is_active})>"


class WebSocketSubscription(TenantModel, AuditableMixin):
    """WebSocket subscription management."""

    __tablename__ = "websocket_subscriptions"

    # Subscription identification
    connection_id = Column(
        String(100),
        ForeignKey("websocket_connections.connection_id"),
        nullable=False,
        index=True,
    )
    subscription_name = Column(String(100), nullable=False, index=True)
    subscription_type = Column(SQLEnum(SubscriptionType), nullable=False, index=True)

    # Subscription target
    user_id = Column(String(100), nullable=False, index=True)
    event_types = Column(JSON, nullable=True)  # List of event types to receive
    entity_filter = Column(JSON, nullable=True)  # Filter criteria

    # Subscription properties
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    priority_filter = Column(SQLEnum(EventPriority), nullable=True, index=True)
    auto_acknowledge = Column(Boolean, default=False, nullable=False)

    # Usage statistics
    events_received = Column(Integer, default=0, nullable=False)
    last_event_received = Column(DateTime, nullable=True)

    # Subscription lifecycle
    subscribed_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    unsubscribed_at = Column(DateTime, nullable=True, index=True)

    # Custom fields
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    connection = relationship("WebSocketConnection", back_populates="deliveries")
    event = relationship("WebSocketEvent", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_websocket_subscriptions_user_type", "user_id", "subscription_type"),
        Index(
            "ix_websocket_subscriptions_connection_name",
            "connection_id",
            "subscription_name",
            unique=True,
        ),
        Index("ix_websocket_subscriptions_active", "is_active", "subscribed_at"),
        Index("ix_websocket_subscriptions_event_types", "event_types"),
    )

    def matches_event(self, event: WebSocketEvent) -> bool:
        """Check if subscription matches an event."""
        # Check event types filter
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Check priority filter
        if self.priority_filter and event.priority < self.priority_filter:
            return False

        # Check entity filter
        if self.entity_filter:
            entity_type = self.entity_filter.get("entity_type")
            entity_id = self.entity_filter.get("entity_id")

            if entity_type and event.source_entity_type != entity_type:
                return False
            if entity_id and event.source_entity_id != entity_id:
                return False

        return True

    def __repr__(self):
        return f"<WebSocketSubscription(connection='{self.connection_id}', name='{self.subscription_name}')>"


class WebSocketDelivery(TenantModel):
    """WebSocket event delivery tracking."""

    __tablename__ = "websocket_deliveries"

    # Delivery identification
    event_id = Column(
        String(100), ForeignKey("websocket_events.event_id"), nullable=False, index=True
    )
    connection_id = Column(
        String(100),
        ForeignKey("websocket_connections.connection_id"),
        nullable=False,
        index=True,
    )
    delivery_id = Column(String(100), nullable=False, unique=True, index=True)

    # Delivery details
    user_id = Column(String(100), nullable=False, index=True)
    attempted_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    delivered_at = Column(DateTime, nullable=True, index=True)
    acknowledged_at = Column(DateTime, nullable=True, index=True)

    # Delivery status
    status = Column(
        SQLEnum(DeliveryStatus),
        default=DeliveryStatus.PENDING,
        nullable=False,
        index=True,
    )
    attempt_count = Column(Integer, default=1, nullable=False)

    # Delivery metrics
    delivery_latency_ms = Column(Integer, nullable=True)
    message_size_bytes = Column(Integer, nullable=True)

    # Error details
    error_code = Column(String(50), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    retry_after = Column(DateTime, nullable=True, index=True)

    # Response tracking
    client_response = Column(JSON, nullable=True)
    response_received_at = Column(DateTime, nullable=True)

    # Custom fields
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    event = relationship("WebSocketEvent", back_populates="deliveries")
    connection = relationship("WebSocketConnection", back_populates="deliveries")

    __table_args__ = (
        Index(
            "ix_websocket_deliveries_event_connection",
            "event_id",
            "connection_id",
            unique=True,
        ),
        Index("ix_websocket_deliveries_user_status", "user_id", "status"),
        Index("ix_websocket_deliveries_attempted", "attempted_at"),
        Index("ix_websocket_deliveries_retry", "retry_after"),
        Index("ix_websocket_deliveries_status_tenant", "status", "tenant_id"),
    )

    @hybrid_property
    def was_successful(self):
        """Check if delivery was successful."""
        return self.status == DeliveryStatus.DELIVERED

    @hybrid_property
    def needs_retry(self):
        """Check if delivery needs retry."""
        return (
            self.status == DeliveryStatus.FAILED
            and self.retry_after
            and datetime.now(timezone.utc) >= self.retry_after
        )

    def __repr__(self):
        return f"<WebSocketDelivery(event='{self.event_id}', connection='{self.connection_id}', status='{self.status}')>"


class WebSocketMetrics(TenantModel):
    """WebSocket usage metrics and analytics."""

    __tablename__ = "websocket_metrics"

    # Metrics identification
    metric_date = Column(DateTime, nullable=False, index=True)
    metric_hour = Column(Integer, nullable=False, index=True)  # 0-23
    user_id = Column(String(100), nullable=True, index=True)

    # Connection metrics
    total_connections = Column(Integer, default=0, nullable=False)
    unique_users = Column(Integer, default=0, nullable=False)
    average_connection_duration_seconds = Column(Integer, default=0, nullable=False)
    total_connection_time_seconds = Column(Integer, default=0, nullable=False)

    # Message metrics
    total_messages_sent = Column(Integer, default=0, nullable=False)
    total_messages_received = Column(Integer, default=0, nullable=False)
    total_bytes_sent = Column(Integer, default=0, nullable=False)
    total_bytes_received = Column(Integer, default=0, nullable=False)

    # Event metrics
    events_by_type = Column(JSON, nullable=True)  # Count by event type
    events_by_priority = Column(JSON, nullable=True)  # Count by priority
    delivery_success_rate = Column(Integer, default=100, nullable=False)  # Percentage
    average_delivery_latency_ms = Column(Integer, default=0, nullable=False)

    # Error metrics
    total_errors = Column(Integer, default=0, nullable=False)
    error_breakdown = Column(JSON, nullable=True)  # Count by error type

    # Performance metrics
    peak_concurrent_connections = Column(Integer, default=0, nullable=False)
    average_latency_ms = Column(Integer, default=0, nullable=False)
    bandwidth_usage_mb = Column(Integer, default=0, nullable=False)

    # Custom fields
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index(
            "ix_websocket_metrics_date_hour", "metric_date", "metric_hour", unique=True
        ),
        Index("ix_websocket_metrics_tenant_date", "tenant_id", "metric_date"),
        Index("ix_websocket_metrics_user_date", "user_id", "metric_date"),
    )

    @hybrid_property
    def total_bandwidth_mb(self):
        """Calculate total bandwidth usage in MB."""
        total_bytes = (self.total_bytes_sent or 0) + (self.total_bytes_received or 0)
        return round(total_bytes / (1024 * 1024), 2)

    @hybrid_property
    def messages_per_connection(self):
        """Calculate average messages per connection."""
        if self.total_connections > 0:
            total_messages = (self.total_messages_sent or 0) + (
                self.total_messages_received or 0
            )
            return round(total_messages / self.total_connections, 2)
        return 0

    def __repr__(self):
        return f"<WebSocketMetrics(date='{self.metric_date}', tenant='{self.tenant_id}', connections={self.total_connections})>"


# Export all models and enums
__all__ = [
    # Enums
    "EventType",
    "EventPriority",
    "DeliveryStatus",
    "SubscriptionType",
    # Models
    "WebSocketEvent",
    "WebSocketConnection",
    "WebSocketSubscription",
    "WebSocketDelivery",
    "WebSocketMetrics",
]
