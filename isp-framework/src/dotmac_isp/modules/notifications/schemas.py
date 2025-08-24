"""Notification system schemas for API requests and responses."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from .models import (
    NotificationPriority,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
    DeliveryStatus,
)


class NotificationTemplateBase(BaseModel):
    """Base schema for notification template."""

    template_name: str = Field(
        ..., min_length=1, max_length=255, description="Template display name"
    )
    template_code: str = Field(
        ..., min_length=1, max_length=100, description="Template code"
    )
    description: Optional[str] = Field(None, description="Template description")
    notification_type: NotificationType = Field(..., description="Notification type")
    priority: NotificationPriority = Field(
        NotificationPriority.NORMAL, description="Default priority"
    )
    subject_template: Optional[str] = Field(
        None, max_length=500, description="Subject template"
    )
    body_template: str = Field(..., description="Message body template")
    html_template: Optional[str] = Field(None, description="HTML template")
    supported_channels: List[NotificationChannel] = Field(
        ..., description="Supported channels"
    )
    default_channel: NotificationChannel = Field(
        ..., description="Default delivery channel"
    )
    required_variables: Optional[List[str]] = Field(
        None, description="Required template variables"
    )
    optional_variables: Optional[List[str]] = Field(
        None, description="Optional template variables"
    )
    language: str = Field("en", description="Template language")
    is_active: bool = Field(True, description="Template active status")
    rate_limit_enabled: bool = Field(False, description="Rate limiting enabled")
    rate_limit_count: Optional[int] = Field(None, description="Rate limit count")
    rate_limit_period: Optional[int] = Field(
        None, description="Rate limit period in seconds"
    )
    tags: Optional[List[str]] = Field(None, description="Template tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class NotificationTemplateCreate(NotificationTemplateBase):
    """Schema for creating notification template."""

    pass


class NotificationTemplateUpdate(BaseModel):
    """Schema for updating notification template."""

    template_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Optional[NotificationPriority] = None
    subject_template: Optional[str] = Field(None, max_length=500)
    body_template: Optional[str] = None
    html_template: Optional[str] = None
    supported_channels: Optional[List[NotificationChannel]] = None
    default_channel: Optional[NotificationChannel] = None
    required_variables: Optional[List[str]] = None
    optional_variables: Optional[List[str]] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    rate_limit_enabled: Optional[bool] = None
    rate_limit_count: Optional[int] = None
    rate_limit_period: Optional[int] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class NotificationTemplateResponse(NotificationTemplateBase):
    """Schema for notification template responses."""

    id: str = Field(..., description="Template ID")
    tenant_id: str = Field(..., description="Tenant ID")
    is_system_template: bool = Field(..., description="System template flag")
    status: str = Field(..., description="Template status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        """Class for Config operations."""
        from_attributes = True


class NotificationRuleBase(BaseModel):
    """Base schema for notification rule."""

    rule_name: str = Field(..., min_length=1, max_length=255, description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    event_type: str = Field(
        ..., min_length=1, max_length=100, description="Triggering event type"
    )
    conditions: Dict[str, Any] = Field(..., description="Rule conditions")
    override_channels: Optional[List[NotificationChannel]] = Field(
        None, description="Channel overrides"
    )
    recipient_rules: Dict[str, Any] = Field(
        ..., description="Recipient determination rules"
    )
    delay_seconds: int = Field(0, ge=0, description="Delay before sending")
    schedule_pattern: Optional[str] = Field(None, description="Cron schedule pattern")
    is_active: bool = Field(True, description="Rule active status")
    throttle_enabled: bool = Field(False, description="Throttling enabled")
    throttle_limit: Optional[int] = Field(None, description="Throttle limit")
    throttle_period: Optional[int] = Field(
        None, description="Throttle period in seconds"
    )
    tags: Optional[List[str]] = Field(None, description="Rule tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom fields")


class NotificationRuleCreate(NotificationRuleBase):
    """Schema for creating notification rule."""

    template_id: str = Field(..., description="Template ID")


class NotificationRuleUpdate(BaseModel):
    """Schema for updating notification rule."""

    rule_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    template_id: Optional[str] = None
    override_channels: Optional[List[NotificationChannel]] = None
    recipient_rules: Optional[Dict[str, Any]] = None
    delay_seconds: Optional[int] = Field(None, ge=0)
    schedule_pattern: Optional[str] = None
    is_active: Optional[bool] = None
    throttle_enabled: Optional[bool] = None
    throttle_limit: Optional[int] = None
    throttle_period: Optional[int] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class NotificationRuleResponse(NotificationRuleBase):
    """Schema for notification rule responses."""

    id: str = Field(..., description="Rule ID")
    tenant_id: str = Field(..., description="Tenant ID")
    template_id: str = Field(..., description="Template ID")
    status: str = Field(..., description="Rule status")
    last_triggered: Optional[datetime] = Field(
        None, description="Last trigger timestamp"
    )
    trigger_count: int = Field(..., description="Total trigger count")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        """Class for Config operations."""
        from_attributes = True


class NotificationBase(BaseModel):
    """Base schema for notification."""

    notification_type: NotificationType = Field(..., description="Notification type")
    priority: NotificationPriority = Field(
        NotificationPriority.NORMAL, description="Notification priority"
    )
    subject: Optional[str] = Field(
        None, max_length=500, description="Notification subject"
    )
    body: str = Field(..., description="Notification body")
    html_body: Optional[str] = Field(None, description="HTML body")
    recipient_type: str = Field(..., max_length=50, description="Recipient type")
    recipient_id: Optional[str] = Field(
        None, max_length=100, description="Recipient ID"
    )
    recipient_email: Optional[str] = Field(
        None, max_length=255, description="Recipient email"
    )
    recipient_phone: Optional[str] = Field(
        None, max_length=20, description="Recipient phone"
    )
    recipient_name: Optional[str] = Field(
        None, max_length=255, description="Recipient name"
    )
    channels: List[NotificationChannel] = Field(..., description="Delivery channels")
    preferred_channel: Optional[NotificationChannel] = Field(
        None, description="Preferred channel"
    )
    scheduled_at: Optional[datetime] = Field(
        None, description="Scheduled delivery time"
    )
    source_system: Optional[str] = Field(
        None, max_length=100, description="Source system"
    )
    source_event: Optional[str] = Field(
        None, max_length=100, description="Source event"
    )
    source_reference_id: Optional[str] = Field(
        None, max_length=100, description="Source reference ID"
    )
    max_retries: int = Field(3, ge=0, description="Maximum retry attempts")
    notification_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata"
    )
    variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")


class NotificationCreate(NotificationBase):
    """Schema for creating notification."""

    template_id: Optional[str] = Field(None, description="Template ID")


class NotificationUpdate(BaseModel):
    """Schema for updating notification."""

    priority: Optional[NotificationPriority] = None
    scheduled_at: Optional[datetime] = None
    notification_metadata: Optional[Dict[str, Any]] = None


class NotificationResponse(NotificationBase):
    """Schema for notification responses."""

    id: str = Field(..., description="Notification ID")
    tenant_id: str = Field(..., description="Tenant ID")
    notification_id: str = Field(..., description="Notification identifier")
    template_id: Optional[str] = Field(None, description="Template ID")
    rule_id: Optional[str] = Field(None, description="Rule ID")
    status: NotificationStatus = Field(..., description="Notification status")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivered timestamp")
    retry_count: int = Field(..., description="Current retry count")
    next_retry_at: Optional[datetime] = Field(None, description="Next retry time")
    last_error: Optional[str] = Field(None, description="Last error message")
    error_count: int = Field(..., description="Error count")
    is_delivered: bool = Field(..., description="Delivery status")
    is_failed: bool = Field(..., description="Failed status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        """Class for Config operations."""
        from_attributes = True


class NotificationDeliveryBase(BaseModel):
    """Base schema for notification delivery."""

    channel: NotificationChannel = Field(..., description="Delivery channel")
    delivery_address: Optional[str] = Field(
        None, max_length=500, description="Delivery address"
    )
    provider: Optional[str] = Field(
        None, max_length=100, description="Delivery provider"
    )
    delivery_data: Optional[Dict[str, Any]] = Field(
        None, description="Provider-specific data"
    )


class NotificationDeliveryCreate(NotificationDeliveryBase):
    """Schema for creating notification delivery."""

    notification_id: str = Field(..., description="Notification ID")


class NotificationDeliveryResponse(NotificationDeliveryBase):
    """Schema for notification delivery responses."""

    id: str = Field(..., description="Delivery ID")
    tenant_id: str = Field(..., description="Tenant ID")
    notification_id: str = Field(..., description="Notification ID")
    status: DeliveryStatus = Field(..., description="Delivery status")
    attempted_at: datetime = Field(..., description="Attempt timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    provider_message_id: Optional[str] = Field(None, description="Provider message ID")
    response_code: Optional[str] = Field(None, description="Response code")
    response_message: Optional[str] = Field(None, description="Response message")
    response_time_ms: Optional[int] = Field(None, description="Response time in ms")
    delivery_cost: Optional[float] = Field(None, description="Delivery cost")
    cost_currency: Optional[str] = Field(None, description="Cost currency")
    error_code: Optional[str] = Field(None, description="Error code")
    error_message: Optional[str] = Field(None, description="Error message")

    class Config:
        """Class for Config operations."""
        from_attributes = True


class NotificationPreferenceBase(BaseModel):
    """Base schema for notification preference."""

    user_id: str = Field(..., description="User ID")
    user_type: str = Field("user", description="User type")
    notification_type: NotificationType = Field(..., description="Notification type")
    enabled: bool = Field(True, description="Preference enabled")
    preferred_channels: List[NotificationChannel] = Field(
        ..., description="Preferred channels"
    )
    disabled_channels: Optional[List[NotificationChannel]] = Field(
        None, description="Disabled channels"
    )
    quiet_hours_start: Optional[str] = Field(
        None,
        pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="Quiet hours start (HH:MM)",
    )
    quiet_hours_end: Optional[str] = Field(
        None,
        pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
        description="Quiet hours end (HH:MM)",
    )
    timezone: str = Field("UTC", description="User timezone")
    digest_enabled: bool = Field(False, description="Digest enabled")
    digest_frequency: Optional[str] = Field(None, description="Digest frequency")
    max_frequency: Optional[str] = Field(None, description="Max notification frequency")
    email_address: Optional[str] = Field(
        None, max_length=255, description="Email address"
    )
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number")
    push_token: Optional[str] = Field(
        None, max_length=500, description="Push notification token"
    )
    language: str = Field("en", description="Preferred language")
    custom_preferences: Optional[Dict[str, Any]] = Field(
        None, description="Custom preferences"
    )


class NotificationPreferenceCreate(NotificationPreferenceBase):
    """Schema for creating notification preference."""

    pass


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preference."""

    enabled: Optional[bool] = None
    preferred_channels: Optional[List[NotificationChannel]] = None
    disabled_channels: Optional[List[NotificationChannel]] = None
    quiet_hours_start: Optional[str] = Field(
        None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    quiet_hours_end: Optional[str] = Field(
        None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    )
    timezone: Optional[str] = None
    digest_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = None
    max_frequency: Optional[str] = None
    email_address: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)
    push_token: Optional[str] = Field(None, max_length=500)
    language: Optional[str] = None
    custom_preferences: Optional[Dict[str, Any]] = None


class NotificationPreferenceResponse(NotificationPreferenceBase):
    """Schema for notification preference responses."""

    id: str = Field(..., description="Preference ID")
    tenant_id: str = Field(..., description="Tenant ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        """Class for Config operations."""
        from_attributes = True


class NotificationSendRequest(BaseModel):
    """Schema for sending notification request."""

    template_code: str = Field(..., description="Template code")
    recipient_type: str = Field(..., description="Recipient type")
    recipient_id: Optional[str] = Field(None, description="Recipient ID")
    recipient_email: Optional[str] = Field(None, description="Recipient email")
    recipient_phone: Optional[str] = Field(None, description="Recipient phone")
    recipient_name: Optional[str] = Field(None, description="Recipient name")
    variables: Optional[Dict[str, Any]] = Field(None, description="Template variables")
    priority: NotificationPriority = Field(
        NotificationPriority.NORMAL, description="Priority override"
    )
    channels: Optional[List[NotificationChannel]] = Field(
        None, description="Channel override"
    )
    scheduled_at: Optional[datetime] = Field(
        None, description="Scheduled delivery time"
    )
    notification_metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata"
    )


class NotificationBulkSendRequest(BaseModel):
    """Schema for bulk notification sending."""

    template_code: str = Field(..., description="Template code")
    recipients: List[Dict[str, Any]] = Field(..., description="Recipient list")
    variables: Optional[Dict[str, Any]] = Field(
        None, description="Common template variables"
    )
    priority: NotificationPriority = Field(
        NotificationPriority.NORMAL, description="Priority override"
    )
    channels: Optional[List[NotificationChannel]] = Field(
        None, description="Channel override"
    )
    scheduled_at: Optional[datetime] = Field(
        None, description="Scheduled delivery time"
    )
    batch_size: int = Field(100, ge=1, le=1000, description="Batch processing size")


class NotificationStatsResponse(BaseModel):
    """Schema for notification statistics."""

    total_notifications: int = Field(..., description="Total notifications")
    pending_notifications: int = Field(..., description="Pending notifications")
    sent_notifications: int = Field(..., description="Sent notifications")
    delivered_notifications: int = Field(..., description="Delivered notifications")
    failed_notifications: int = Field(..., description="Failed notifications")
    delivery_rate: float = Field(..., description="Overall delivery rate")
    avg_delivery_time_ms: Optional[float] = Field(
        None, description="Average delivery time"
    )
    channel_stats: Dict[str, Dict[str, int]] = Field(
        ..., description="Per-channel statistics"
    )
    type_stats: Dict[str, Dict[str, int]] = Field(
        ..., description="Per-type statistics"
    )


class NotificationDashboardResponse(BaseModel):
    """Schema for notification dashboard data."""

    stats: NotificationStatsResponse = Field(..., description="Overall statistics")
    recent_notifications: List[NotificationResponse] = Field(
        ..., description="Recent notifications"
    )
    failed_deliveries: List[NotificationDeliveryResponse] = Field(
        ..., description="Recent failed deliveries"
    )
    top_templates: List[Dict[str, Any]] = Field(..., description="Most used templates")
    alert_summary: Dict[str, int] = Field(..., description="Alert type summary")


class NotificationQueueResponse(BaseModel):
    """Schema for notification queue status."""

    queue_name: str = Field(..., description="Queue name")
    total_items: int = Field(..., description="Total items in queue")
    pending_items: int = Field(..., description="Pending items")
    processing_items: int = Field(..., description="Processing items")
    failed_items: int = Field(..., description="Failed items")
    avg_processing_time_ms: Optional[float] = Field(
        None, description="Average processing time"
    )
    oldest_item_age_seconds: Optional[int] = Field(None, description="Oldest item age")
