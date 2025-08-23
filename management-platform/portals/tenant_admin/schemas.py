"""
Pydantic schemas for Tenant Admin Portal API requests and responses.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, EmailStr, ConfigDict

from ...src.mgmt.services.tenant_management.models import TenantStatus


class InstanceHealthMetrics(BaseModel):
    """Instance health and performance metrics."""
    
    uptime_percentage: float = Field(..., ge=0, le=100)
    avg_response_time_ms: int = Field(..., ge=0)
    requests_per_minute: int = Field(..., ge=0)
    error_rate_percentage: float = Field(..., ge=0, le=100)
    
    # Resource utilization
    cpu_usage_percentage: float = Field(..., ge=0, le=100)
    memory_usage_percentage: float = Field(..., ge=0, le=100)
    storage_usage_percentage: float = Field(..., ge=0, le=100)
    
    # Service status
    database_status: str = Field(..., regex="^(healthy|degraded|down)$")
    cache_status: str = Field(..., regex="^(healthy|degraded|down)$")
    queue_status: str = Field(..., regex="^(healthy|degraded|down)$")
    
    last_updated: datetime


class TenantInstanceOverview(BaseModel):
    """Comprehensive overview of tenant's DotMac instance."""
    
    # Instance identification
    tenant_id: str
    tenant_name: str
    instance_url: str
    custom_domain: Optional[str] = None
    
    # Instance status
    status: TenantStatus
    health_score: int = Field(..., ge=0, le=100)
    last_health_check: datetime
    
    # Subscription details
    subscription_tier: str
    billing_cycle: str
    next_billing_date: datetime
    
    # Usage summary
    current_customers: int
    current_services: int
    storage_used_gb: float
    storage_limit_gb: int
    
    # Performance metrics
    health_metrics: InstanceHealthMetrics
    
    # Recent activity
    recent_logins: int = Field(..., description="Logins in last 24 hours")
    recent_api_calls: int = Field(..., description="API calls in last 24 hours")
    recent_tickets: int = Field(..., description="Support tickets in last 30 days")
    
    # Alerts and notifications
    active_alerts: int = Field(0, ge=0)
    pending_updates: int = Field(0, ge=0)
    scheduled_maintenance: Optional[datetime] = None


class InstanceConfigurationCategory(BaseModel):
    """Configuration category with its settings."""
    
    category: str
    display_name: str
    description: str
    settings: Dict[str, Any]
    editable_by_tenant: bool = True
    requires_restart: bool = False


class InstanceConfigurationUpdate(BaseModel):
    """Request to update instance configuration."""
    
    category: str = Field(..., description="Configuration category to update")
    settings: Dict[str, Any] = Field(..., description="Settings to update")
    apply_immediately: bool = Field(True, description="Apply changes immediately")
    schedule_maintenance: Optional[datetime] = Field(None, description="Schedule maintenance window for changes")


class ScalingConfiguration(BaseModel):
    """Instance scaling configuration."""
    
    # Current resources
    current_cpu_cores: int
    current_memory_gb: int
    current_storage_gb: int
    
    # Requested resources
    target_cpu_cores: int = Field(..., ge=1, le=64)
    target_memory_gb: int = Field(..., ge=1, le=256) 
    target_storage_gb: int = Field(..., ge=10, le=10000)
    
    # Auto-scaling settings
    auto_scaling_enabled: bool = False
    min_instances: int = Field(1, ge=1, le=10)
    max_instances: int = Field(5, ge=1, le=50)
    scale_up_threshold: int = Field(80, ge=50, le=95)
    scale_down_threshold: int = Field(30, ge=10, le=70)
    
    # Cost estimates
    estimated_hourly_cost: Decimal
    estimated_monthly_cost: Decimal


class BackupConfiguration(BaseModel):
    """Backup management configuration."""
    
    # Current backup settings
    backup_enabled: bool
    backup_frequency: str = Field(..., regex="^(daily|weekly|monthly)$")
    backup_retention_days: int = Field(..., ge=1, le=365)
    backup_time: str = Field(..., description="Backup time in HH:MM format")
    
    # Backup storage
    backup_storage_used_gb: float
    backup_storage_limit_gb: int
    
    # Recent backups
    last_backup: Optional[datetime] = None
    last_backup_status: Optional[str] = Field(None, regex="^(success|failed|in_progress)$")
    
    # Available restore points
    available_restore_points: int


class UsageMetricsResponse(BaseModel):
    """Detailed usage metrics for tenant's instance."""
    
    # Time period
    period_start: datetime
    period_end: datetime
    
    # Customer metrics
    customers_active: int
    customers_new: int
    customers_churned: int
    
    # Service metrics
    services_active: int
    services_provisioned: int
    services_deprovisioned: int
    
    # Resource usage
    storage_used_gb: float
    bandwidth_used_gb: float
    api_requests_total: int
    
    # Performance metrics
    avg_response_time_ms: int
    uptime_percentage: float
    error_count: int
    
    # Usage trends (compared to previous period)
    customers_growth_rate: float
    services_growth_rate: float
    storage_growth_rate: float
    api_usage_growth_rate: float
    
    # Resource utilization
    storage_utilization_percentage: float
    bandwidth_utilization_percentage: float
    
    # Cost breakdown
    infrastructure_cost: Decimal
    feature_costs: Dict[str, Decimal]
    total_cost: Decimal


class BillingInvoice(BaseModel):
    """Billing invoice details."""
    
    invoice_id: str
    invoice_date: datetime
    due_date: datetime
    period_start: datetime
    period_end: datetime
    
    # Amount details
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    
    # Status
    status: str = Field(..., regex="^(draft|sent|paid|overdue|cancelled)$")
    payment_date: Optional[datetime] = None
    
    # Line items
    line_items: List[Dict[str, Any]]
    
    # Payment information
    payment_method: Optional[str] = None
    download_url: Optional[str] = None


class PaymentMethod(BaseModel):
    """Payment method details."""
    
    payment_method_id: str
    type: str = Field(..., regex="^(card|bank_account|paypal)$")
    
    # Card details (if type is card)
    card_brand: Optional[str] = None
    card_last_four: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
    
    # Bank account details (if type is bank_account)
    bank_name: Optional[str] = None
    account_last_four: Optional[str] = None
    
    is_default: bool = False
    created_at: datetime


class BillingPortalResponse(BaseModel):
    """Billing portal information and current subscription details."""
    
    # Subscription details
    subscription_id: str
    subscription_tier: str
    billing_cycle: str
    
    # Current period
    current_period_start: datetime
    current_period_end: datetime
    next_billing_date: datetime
    
    # Amounts
    current_amount: Decimal
    next_amount: Decimal
    
    # Usage-based billing
    usage_charges: Dict[str, Decimal]
    overage_charges: Dict[str, Decimal]
    
    # Payment information
    payment_methods: List[PaymentMethod]
    default_payment_method: Optional[str] = None
    
    # Recent invoices
    recent_invoices: List[BillingInvoice]
    
    # Account status
    account_status: str = Field(..., regex="^(active|past_due|cancelled|suspended)$")
    days_overdue: int = Field(0, ge=0)
    
    # Billing alerts
    usage_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    payment_alerts: List[Dict[str, Any]] = Field(default_factory=list)


class SupportTicketCreate(BaseModel):
    """Create new support ticket."""
    
    subject: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    category: str = Field(..., regex="^(technical|billing|feature_request|bug_report|general)$")
    priority: str = Field("normal", regex="^(low|normal|high|urgent)$")
    
    # Contact preferences
    preferred_contact_method: str = Field("email", regex="^(email|phone|chat)$")
    contact_phone: Optional[str] = Field(None, max_length=20)
    
    # Additional context
    affected_service: Optional[str] = None
    error_message: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    
    # Attachments (file URLs or base64 encoded)
    attachments: List[str] = Field(default_factory=list)


class SupportTicketResponse(BaseModel):
    """Support ticket response."""
    
    ticket_id: str
    subject: str
    description: str
    category: str
    priority: str
    status: str = Field(..., regex="^(new|open|in_progress|pending_customer|resolved|closed)$")
    
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    # Assignment
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    
    # SLA tracking
    response_sla_hours: int
    resolution_sla_hours: int
    time_to_first_response: Optional[int] = None
    time_to_resolution: Optional[int] = None
    
    # Customer satisfaction
    satisfaction_rating: Optional[int] = Field(None, ge=1, le=5)
    satisfaction_feedback: Optional[str] = None


class CustomBrandingSettings(BaseModel):
    """Custom branding configuration."""
    
    # Logo and visual identity
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: str = Field("#1f2937", regex="^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field("#374151", regex="^#[0-9A-Fa-f]{6}$")
    accent_color: str = Field("#3b82f6", regex="^#[0-9A-Fa-f]{6}$")
    
    # Typography
    font_family: str = Field("Inter", description="Font family name")
    
    # Company information
    company_name: str
    company_tagline: Optional[str] = None
    support_email: EmailStr
    support_phone: Optional[str] = None
    
    # Custom CSS
    custom_css: Optional[str] = Field(None, max_length=10000)
    
    # Email templates
    email_header_logo: Optional[str] = None
    email_footer_text: Optional[str] = None


class IntegrationConfiguration(BaseModel):
    """Third-party integration configuration."""
    
    integration_type: str
    integration_name: str
    is_enabled: bool = False
    
    # Configuration settings
    settings: Dict[str, Any]
    
    # Authentication
    auth_type: str = Field(..., regex="^(api_key|oauth|basic_auth|webhook)$")
    
    # Status
    connection_status: str = Field(..., regex="^(connected|disconnected|error)$")
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    
    # Webhook configuration (if applicable)
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None


class UserManagementUser(BaseModel):
    """User in tenant's instance."""
    
    user_id: str
    email: EmailStr
    first_name: str
    last_name: str
    
    # Role and permissions
    role: str
    permissions: List[str]
    
    # Status
    is_active: bool = True
    is_verified: bool = True
    last_login: Optional[datetime] = None
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None


class UserManagementCreateUser(BaseModel):
    """Create new user in tenant's instance."""
    
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    role: str
    
    # Optional fields
    send_invitation: bool = Field(True, description="Send invitation email")
    temporary_password: Optional[str] = Field(None, min_length=8)


class AnalyticsMetric(BaseModel):
    """Analytics metric data point."""
    
    metric_name: str
    metric_value: float
    metric_unit: str
    timestamp: datetime
    
    # Metadata
    dimensions: Dict[str, str] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)


class AnalyticsReport(BaseModel):
    """Analytics report response."""
    
    report_id: str
    report_name: str
    description: str
    
    # Time period
    period_start: datetime
    period_end: datetime
    
    # Metrics
    metrics: List[AnalyticsMetric]
    
    # Summary statistics
    total_records: int
    summary_stats: Dict[str, float]
    
    # Charts and visualizations
    chart_data: Dict[str, Any] = Field(default_factory=dict)
    
    generated_at: datetime


class MaintenanceWindow(BaseModel):
    """Scheduled maintenance window."""
    
    maintenance_id: str
    title: str
    description: str
    
    # Scheduling
    scheduled_start: datetime
    scheduled_end: datetime
    estimated_duration_minutes: int
    
    # Impact
    affected_services: List[str]
    impact_level: str = Field(..., regex="^(low|medium|high|critical)$")
    
    # Status
    status: str = Field(..., regex="^(scheduled|in_progress|completed|cancelled)$")
    
    # Notifications
    notify_customers: bool = True
    advance_notice_hours: int = Field(24, ge=1, le=168)
    
    # Metadata
    created_by: str
    created_at: datetime


class FeatureToggle(BaseModel):
    """Feature toggle configuration."""
    
    feature_key: str
    feature_name: str
    description: str
    
    # Status
    is_enabled: bool = False
    is_available: bool = True
    
    # Subscription requirements
    required_tier: Optional[str] = None
    requires_upgrade: bool = False
    
    # Configuration
    configuration: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    category: str
    documentation_url: Optional[str] = None