"""
Channel configuration and status models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ChannelStatus(str, Enum):
    """Channel operational status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class ChannelConfig(BaseModel):
    """Channel configuration model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str

    # Channel identification
    channel_type: str = Field(..., min_length=1)  # email, sms, whatsapp, etc.
    plugin_id: str = Field(..., min_length=1)

    # Configuration
    enabled: bool = True
    name: str = Field(..., min_length=1)
    description: Optional[str] = None

    # Plugin configuration
    configuration: dict[str, Any] = Field(default_factory=dict)

    # Rate limiting
    rate_limits: dict[str, int] = Field(default_factory=dict)

    # Message settings
    default_sender: Optional[str] = None
    default_template_id: Optional[str] = None

    # Routing
    priority: int = Field(default=10, ge=1, le=100)
    is_fallback: bool = False

    # Health monitoring
    health_check_enabled: bool = True
    health_check_interval_seconds: int = Field(default=300, ge=60)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Additional data
    extra_data: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class ChannelStatusInfo(BaseModel):
    """Channel status information."""

    channel: str
    plugin_id: str
    status: ChannelStatus

    # Health information
    health_check: Optional[dict[str, Any]] = None
    last_health_check: Optional[datetime] = None

    # Performance metrics
    messages_sent_today: int = 0
    success_rate_24h: Optional[float] = None
    avg_response_time_ms: Optional[float] = None

    # Error information
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    error_count_24h: int = 0

    # Rate limiting status
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset_at: Optional[datetime] = None

    # Connection status
    connected: bool = False
    connection_established_at: Optional[datetime] = None

    # Additional data
    extra_data: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class ChannelCapabilities(BaseModel):
    """Channel capabilities and features."""

    channel_type: str
    plugin_id: str

    # Message types
    supports_text: bool = True
    supports_html: bool = False
    supports_attachments: bool = False
    supports_templates: bool = False

    # Features
    supports_delivery_confirmation: bool = False
    supports_read_receipts: bool = False
    supports_replies: bool = False
    supports_threading: bool = False

    # Limits
    max_message_length: Optional[int] = None
    max_attachment_size_mb: Optional[int] = None
    max_attachments_per_message: Optional[int] = None

    # Supported content types
    supported_attachment_types: list[str] = Field(default_factory=list)

    # Rate limits
    messages_per_second: Optional[int] = None
    messages_per_minute: Optional[int] = None
    messages_per_hour: Optional[int] = None
    messages_per_day: Optional[int] = None

    # Regional support
    supported_countries: list[str] = Field(default_factory=list)
    supported_languages: list[str] = Field(default_factory=list)

    # Cost information
    cost_per_message: Optional[float] = None
    currency: str = "USD"

    model_config = ConfigDict(populate_by_name=True)


class ChannelMetrics(BaseModel):
    """Channel performance metrics."""

    channel: str
    plugin_id: str
    period_start: datetime
    period_end: datetime

    # Volume metrics
    messages_sent: int = 0
    messages_delivered: int = 0
    messages_failed: int = 0
    messages_bounced: int = 0

    # Performance metrics
    avg_send_time_ms: Optional[float] = None
    avg_delivery_time_ms: Optional[float] = None
    success_rate: float = 0.0

    # Error breakdown
    error_breakdown: dict[str, int] = Field(default_factory=dict)

    # Cost metrics
    total_cost: Optional[float] = None
    cost_per_message: Optional[float] = None

    # Rate limiting
    rate_limit_hits: int = 0
    rate_limit_delays_ms: int = 0

    # Uptime
    uptime_percentage: float = 100.0
    downtime_minutes: int = 0

    @property
    def success_rate(self) -> float:
        if self.messages_sent == 0:
            return 0.0
        return (self.messages_delivered / self.messages_sent) * 100


class ChannelAlert(BaseModel):
    """Channel alert configuration."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    channel: str

    # Alert conditions
    alert_type: str = Field(..., min_length=1)  # error_rate, downtime, rate_limit, etc.
    threshold: float
    comparison: str = "greater_than"  # greater_than, less_than, equals

    # Alert settings
    enabled: bool = True
    alert_after_minutes: int = Field(default=5, ge=1)
    cooldown_minutes: int = Field(default=30, ge=1)

    # Notification settings
    notification_channels: list[str] = Field(default_factory=list)
    notification_recipients: list[str] = Field(default_factory=list)

    # Message template
    alert_title: str = "Channel Alert: {channel}"
    alert_message: str = "Channel {channel} has triggered alert: {alert_type}"

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True)
