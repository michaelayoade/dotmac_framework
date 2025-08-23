"""
Tenant portal schemas for validation and serialization.
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr

from .common import BaseSchema


class TenantProfile(BaseModel):
    """Tenant profile schema."""
    id: UUID = Field(..., description="Tenant identifier")
    name: str = Field(..., description="Tenant name")
    domain: Optional[str] = Field(None, description="Tenant domain")
    is_active: bool = Field(..., description="Whether tenant is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TenantProfileUpdate(BaseModel):
    """Tenant profile update schema."""
    name: Optional[str] = Field(None, description="Updated tenant name")
    domain: Optional[str] = Field(None, description="Updated tenant domain")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")


class UserInvitation(BaseModel):
    """User invitation schema."""
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="User full name")
    role: str = Field(..., description="User role")
    send_welcome_email: bool = Field(default=True, description="Send welcome email")


class UserProfile(BaseModel):
    """User profile schema."""
    id: UUID = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class SubscriptionInfo(BaseModel):
    """Subscription information schema."""
    id: Optional[UUID] = Field(None, description="Subscription identifier")
    status: str = Field(..., description="Subscription status")
    plan_name: Optional[str] = Field(None, description="Billing plan name")
    plan_price: float = Field(default=0, description="Plan price")
    billing_cycle: Optional[str] = Field(None, description="Billing cycle")
    next_billing_date: Optional[date] = Field(None, description="Next billing date")
    auto_renew: bool = Field(default=False, description="Auto-renewal enabled")


class InvoiceInfo(BaseModel):
    """Invoice information schema."""
    id: UUID = Field(..., description="Invoice identifier")
    invoice_number: str = Field(..., description="Invoice number")
    amount: float = Field(..., description="Invoice amount")
    status: str = Field(..., description="Invoice status")
    due_date: date = Field(..., description="Due date")
    created_at: datetime = Field(..., description="Creation timestamp")


class PaymentInfo(BaseModel):
    """Payment information schema."""
    id: UUID = Field(..., description="Payment identifier")
    amount: float = Field(..., description="Payment amount")
    status: str = Field(..., description="Payment status")
    payment_method: str = Field(..., description="Payment method")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class BillingOverview(BaseModel):
    """Billing overview schema."""
    subscription: SubscriptionInfo = Field(..., description="Subscription information")
    outstanding_balance: float = Field(..., description="Outstanding balance")
    recent_invoices: List[InvoiceInfo] = Field(..., description="Recent invoices")
    recent_payments: List[PaymentInfo] = Field(..., description="Recent payments")
    currency: str = Field(default="USD", description="Currency code")


class UsageMetric(BaseModel):
    """Usage metric schema."""
    metric_name: str = Field(..., description="Metric name")
    current_value: float = Field(..., description="Current value")
    limit_value: Optional[float] = Field(None, description="Limit value")
    unit: str = Field(..., description="Unit of measurement")
    period: str = Field(..., description="Measurement period")


class UsageMetrics(BaseModel):
    """Usage metrics collection schema."""
    period_start: datetime = Field(..., description="Metrics period start")
    period_end: datetime = Field(..., description="Metrics period end")
    infrastructure: Dict[str, Any] = Field(..., description="Infrastructure usage")
    notifications: Dict[str, Any] = Field(..., description="Notification usage")
    summary: Dict[str, Any] = Field(..., description="Usage summary")


class InfrastructureDeployment(BaseModel):
    """Infrastructure deployment schema."""
    id: UUID = Field(..., description="Deployment identifier")
    name: str = Field(..., description="Deployment name")
    status: str = Field(..., description="Deployment status")
    resource_limits: Dict[str, Any] = Field(..., description="Resource limits")
    created_at: datetime = Field(..., description="Creation timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class NotificationTemplate(BaseModel):
    """Notification template schema."""
    id: UUID = Field(..., description="Template identifier")
    name: str = Field(..., description="Template name")
    notification_type: str = Field(..., description="Notification type")
    channel: str = Field(..., description="Delivery channel")
    subject_template: Optional[str] = Field(None, description="Subject template")
    body_template: str = Field(..., description="Body template")
    variables: List[str] = Field(..., description="Template variables")
    created_at: datetime = Field(..., description="Creation timestamp")


class ActivityItem(BaseModel):
    """Activity item schema."""
    type: str = Field(..., description="Activity type")
    description: str = Field(..., description="Activity description")
    timestamp: datetime = Field(..., description="Activity timestamp")
    status: Optional[str] = Field(None, description="Activity status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional data")


class PortalDashboard(BaseModel):
    """Portal dashboard schema."""
    tenant: Dict[str, Any] = Field(..., description="Tenant information")
    subscription: Dict[str, Any] = Field(..., description="Subscription information")
    users: Dict[str, Any] = Field(..., description="User information")
    billing: Dict[str, Any] = Field(..., description="Billing information")
    infrastructure: Dict[str, Any] = Field(..., description="Infrastructure information")
    recent_activity: List[ActivityItem] = Field(..., description="Recent activity")
    last_updated: datetime = Field(..., description="Last update timestamp")


class SupportTicket(BaseModel):
    """Support ticket schema."""
    subject: str = Field(..., min_length=5, max_length=200, description="Ticket subject")
    description: str = Field(..., min_length=20, description="Ticket description")
    category: str = Field(..., description="Ticket category")
    priority: str = Field(default="normal", description="Ticket priority")
    attachments: Optional[List[str]] = Field(None, description="Attachment file names")


class SupportTicketResponse(BaseModel):
    """Support ticket response schema."""
    ticket_id: str = Field(..., description="Ticket identifier")
    status: str = Field(..., description="Ticket status")
    subject: str = Field(..., description="Ticket subject")
    category: str = Field(..., description="Ticket category")
    priority: str = Field(..., description="Ticket priority")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: str = Field(..., description="Creator user ID")


class NotificationSettings(BaseModel):
    """Notification settings schema."""
    email_enabled: bool = Field(default=True, description="Email notifications enabled")
    sms_enabled: bool = Field(default=False, description="SMS notifications enabled")
    default_channel: str = Field(default="email", description="Default notification channel")
    digest_frequency: str = Field(default="daily", description="Digest frequency")


class SecuritySettings(BaseModel):
    """Security settings schema."""
    two_factor_required: bool = Field(default=False, description="Two-factor authentication required")
    session_timeout_minutes: int = Field(default=30, description="Session timeout in minutes")
    password_policy: str = Field(default="standard", description="Password policy level")
    ip_whitelist: Optional[List[str]] = Field(None, description="IP whitelist")


class BillingSettings(BaseModel):
    """Billing settings schema."""
    auto_pay_enabled: bool = Field(default=False, description="Auto-payment enabled")
    invoice_email: str = Field(default="", description="Invoice email address")
    currency: str = Field(default="USD", description="Preferred currency")
    payment_method: Optional[str] = Field(None, description="Default payment method")


class InfrastructureSettings(BaseModel):
    """Infrastructure settings schema."""
    auto_scaling_enabled: bool = Field(default=True, description="Auto-scaling enabled")
    backup_enabled: bool = Field(default=True, description="Backup enabled")
    monitoring_level: str = Field(default="standard", description="Monitoring level")
    maintenance_window: Optional[str] = Field(None, description="Preferred maintenance window")


class ServiceConfiguration(BaseModel):
    """Service configuration schema."""
    notifications: Optional[NotificationSettings] = Field(None, description="Notification settings")
    security: Optional[SecuritySettings] = Field(None, description="Security settings")
    billing: Optional[BillingSettings] = Field(None, description="Billing settings")
    infrastructure: Optional[InfrastructureSettings] = Field(None, description="Infrastructure settings")


class ApiKey(BaseModel):
    """API key schema."""
    id: UUID = Field(..., description="API key identifier")
    name: str = Field(..., description="API key name")
    key_prefix: str = Field(..., description="API key prefix (first 8 characters)")
    permissions: List[str] = Field(..., description="API key permissions")
    last_used: Optional[datetime] = Field(None, description="Last used timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    is_active: bool = Field(..., description="Whether API key is active")
    created_at: datetime = Field(..., description="Creation timestamp")


class ApiKeyCreate(BaseModel):
    """API key creation schema."""
    name: str = Field(..., min_length=3, max_length=100, description="API key name")
    permissions: List[str] = Field(..., description="API key permissions")
    expires_in_days: Optional[int] = Field(None, gt=0, le=365, description="Expiration in days")


class ApiKeyResponse(BaseModel):
    """API key response schema."""
    id: UUID = Field(..., description="API key identifier")
    name: str = Field(..., description="API key name")
    api_key: str = Field(..., description="Full API key (only shown once)")
    permissions: List[str] = Field(..., description="API key permissions")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class WebhookEndpoint(BaseModel):
    """Webhook endpoint schema."""
    id: UUID = Field(..., description="Webhook identifier")
    name: str = Field(..., description="Webhook name")
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="Subscribed events")
    secret: Optional[str] = Field(None, description="Webhook secret")
    is_active: bool = Field(..., description="Whether webhook is active")
    last_triggered: Optional[datetime] = Field(None, description="Last trigger timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class WebhookEndpointCreate(BaseModel):
    """Webhook endpoint creation schema."""
    name: str = Field(..., min_length=3, max_length=100, description="Webhook name")
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., min_items=1, description="Events to subscribe to")
    secret: Optional[str] = Field(None, description="Webhook secret")


class WebhookDelivery(BaseModel):
    """Webhook delivery schema."""
    id: UUID = Field(..., description="Delivery identifier")
    webhook_id: UUID = Field(..., description="Webhook identifier")
    event_type: str = Field(..., description="Event type")
    status: str = Field(..., description="Delivery status")
    response_code: Optional[int] = Field(None, description="HTTP response code")
    response_body: Optional[str] = Field(None, description="Response body")
    attempt_count: int = Field(..., description="Number of attempts")
    next_retry: Optional[datetime] = Field(None, description="Next retry timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class BackupInfo(BaseModel):
    """Backup information schema."""
    id: UUID = Field(..., description="Backup identifier")
    backup_type: str = Field(..., description="Backup type")
    status: str = Field(..., description="Backup status")
    size_bytes: Optional[int] = Field(None, description="Backup size in bytes")
    started_at: datetime = Field(..., description="Backup start time")
    completed_at: Optional[datetime] = Field(None, description="Backup completion time")
    retention_days: int = Field(..., description="Retention period in days")
    download_url: Optional[str] = Field(None, description="Download URL")


class BackupCreate(BaseModel):
    """Backup creation schema."""
    backup_type: str = Field(..., description="Type of backup to create")
    include_data: bool = Field(default=True, description="Include data in backup")
    include_config: bool = Field(default=True, description="Include configuration in backup")
    retention_days: int = Field(default=30, ge=1, le=365, description="Retention period in days")


class AuditLog(BaseModel):
    """Audit log entry schema."""
    id: UUID = Field(..., description="Audit log identifier")
    user_id: UUID = Field(..., description="User who performed the action")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="Identifier of affected resource")
    details: Dict[str, Any] = Field(..., description="Action details")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    timestamp: datetime = Field(..., description="Action timestamp")


class AuditLogQuery(BaseModel):
    """Audit log query parameters."""
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(None, description="Filter by action")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    limit: int = Field(default=100, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Result offset")


class TeamMember(BaseModel):
    """Team member schema."""
    id: UUID = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    invited_at: Optional[datetime] = Field(None, description="Invitation timestamp")
    joined_at: Optional[datetime] = Field(None, description="Join timestamp")


class TeamInvitation(BaseModel):
    """Team invitation schema."""
    email: EmailStr = Field(..., description="Email address to invite")
    role: str = Field(..., description="Role to assign")
    full_name: Optional[str] = Field(None, description="Full name of invitee")
    custom_message: Optional[str] = Field(None, description="Custom invitation message")


class RolePermissions(BaseModel):
    """Role permissions schema."""
    role: str = Field(..., description="Role name")
    permissions: List[str] = Field(..., description="List of permissions")
    description: str = Field(..., description="Role description")


class TenantSettings(BaseModel):
    """Tenant settings schema."""
    general: Dict[str, Any] = Field(..., description="General settings")
    notifications: NotificationSettings = Field(..., description="Notification settings")
    security: SecuritySettings = Field(..., description="Security settings")
    billing: BillingSettings = Field(..., description="Billing settings")
    infrastructure: InfrastructureSettings = Field(..., description="Infrastructure settings")
    integrations: Dict[str, Any] = Field(default_factory=dict, description="Integration settings")


class QuotaUsage(BaseModel):
    """Quota usage schema."""
    resource: str = Field(..., description="Resource name")
    used: float = Field(..., description="Used amount")
    limit: float = Field(..., description="Limit amount")
    unit: str = Field(..., description="Unit of measurement")
    percentage: float = Field(..., description="Usage percentage")
    warning_threshold: float = Field(default=80.0, description="Warning threshold percentage")


class QuotaOverview(BaseModel):
    """Quota overview schema."""
    quotas: List[QuotaUsage] = Field(..., description="List of quota usages")
    overall_usage_percentage: float = Field(..., description="Overall usage percentage")
    warnings: List[str] = Field(default_factory=list, description="Quota warnings")
    last_updated: datetime = Field(..., description="Last update timestamp")