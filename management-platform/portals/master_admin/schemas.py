"""
Pydantic schemas for Master Admin Portal API requests and responses.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

from ...src.mgmt.services.tenant_management.models import TenantStatus


class PlatformMetrics(BaseModel):
    """Platform-wide metrics for the dashboard."""
    
    total_tenants: int = Field(..., description="Total number of tenants")
    active_tenants: int = Field(..., description="Number of active tenants")
    pending_tenants: int = Field(..., description="Number of pending tenants")
    suspended_tenants: int = Field(..., description="Number of suspended tenants")
    
    total_revenue_monthly: Decimal = Field(..., description="Monthly recurring revenue")
    total_revenue_annual: Decimal = Field(..., description="Annual recurring revenue")
    avg_revenue_per_tenant: Decimal = Field(..., description="Average revenue per tenant")
    
    total_infrastructure_cost: Decimal = Field(..., description="Total infrastructure costs")
    platform_margin: Decimal = Field(..., description="Platform profit margin percentage")
    
    total_api_requests: int = Field(..., description="Total API requests across all tenants")
    avg_response_time_ms: int = Field(..., description="Average response time in milliseconds")
    overall_uptime_percentage: float = Field(..., description="Overall platform uptime percentage")
    
    active_deployments: int = Field(..., description="Number of active deployments")
    pending_deployments: int = Field(..., description="Number of pending deployments")
    failed_deployments: int = Field(..., description="Number of failed deployments")


class TenantHealthSummary(BaseModel):
    """Summary of tenant health across the platform."""
    
    tenant_id: str
    tenant_name: str
    status: TenantStatus
    health_score: int = Field(..., ge=0, le=100)
    uptime_percentage: Optional[float] = None
    last_health_check: datetime
    
    active_alerts: int = Field(0, ge=0)
    critical_issues: int = Field(0, ge=0)
    
    monthly_revenue: Decimal
    monthly_cost: Decimal
    
    # Resource utilization
    customers_utilization: float = Field(..., ge=0, le=100)
    storage_utilization: float = Field(..., ge=0, le=100)
    
    # Performance indicators
    avg_response_time_ms: Optional[int] = None
    error_rate: Optional[float] = None


class InfrastructureOverview(BaseModel):
    """Infrastructure resource overview across all tenants."""
    
    total_instances: int
    running_instances: int
    stopped_instances: int
    
    # Cloud provider breakdown
    cloud_distribution: Dict[str, int] = Field(
        ..., description="Distribution of instances across cloud providers"
    )
    
    # Region distribution
    region_distribution: Dict[str, int] = Field(
        ..., description="Distribution of instances across regions"
    )
    
    # Resource totals
    total_cpu_cores: int
    total_memory_gb: int
    total_storage_gb: int
    
    # Cost breakdown
    total_monthly_cost: Decimal
    cost_by_provider: Dict[str, Decimal]
    cost_trend_percentage: float = Field(..., description="Cost trend vs previous month")


class PlatformOverviewResponse(BaseModel):
    """Complete platform overview for Master Admin dashboard."""
    
    metrics: PlatformMetrics
    tenant_health: List[TenantHealthSummary]
    infrastructure: InfrastructureOverview
    
    # Recent activity
    recent_tenant_signups: int = Field(..., description="New tenants in last 30 days")
    recent_churn_rate: float = Field(..., description="Churn rate in last 30 days")
    
    # System health
    platform_health_score: int = Field(..., ge=0, le=100, description="Overall platform health")
    active_incidents: int = Field(0, ge=0, description="Number of active incidents")
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class TenantOnboardingStep(BaseModel):
    """Individual step in the tenant onboarding workflow."""
    
    step_id: str
    step_name: str
    description: str
    status: str = Field(..., regex="^(pending|in_progress|completed|failed|skipped)$")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Step-specific data
    step_data: Optional[Dict[str, Any]] = None


class TenantOnboardingWorkflow(BaseModel):
    """Complete tenant onboarding workflow tracking."""
    
    workflow_id: str
    tenant_id: str
    tenant_name: str
    
    overall_status: str = Field(..., regex="^(pending|in_progress|completed|failed|cancelled)$")
    started_at: datetime
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    progress_percentage: int = Field(..., ge=0, le=100)
    
    steps: List[TenantOnboardingStep]
    
    # Workflow metadata
    initiated_by: str = Field(..., description="User who initiated the workflow")
    assigned_to: Optional[str] = Field(None, description="Staff member assigned to the workflow")
    priority: str = Field("normal", regex="^(low|normal|high|urgent)$")
    
    # Customer communication
    customer_notified: bool = Field(False, description="Whether customer has been notified of progress")
    last_customer_update: Optional[datetime] = None


class DeploymentTemplate(BaseModel):
    """Infrastructure deployment template."""
    
    template_id: str
    template_name: str
    description: str
    
    cloud_provider: str
    region: str
    instance_type: str
    
    # Resource specifications
    cpu_cores: int
    memory_gb: int
    storage_gb: int
    
    # Estimated costs
    hourly_cost: Decimal
    monthly_cost: Decimal
    
    # Template configuration
    configuration: Dict[str, Any]
    
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class InfrastructureDeploymentRequest(BaseModel):
    """Request to deploy infrastructure for a tenant."""
    
    tenant_id: str
    template_id: Optional[str] = None
    
    # Custom deployment configuration
    cloud_provider: str = Field(..., regex="^(aws|azure|gcp|digitalocean)$")
    region: str
    instance_type: str
    
    # Resource requirements
    cpu_cores: int = Field(..., ge=1, le=64)
    memory_gb: int = Field(..., ge=1, le=256)
    storage_gb: int = Field(..., ge=10, le=10000)
    
    # Deployment options
    auto_scaling_enabled: bool = Field(True, description="Enable auto-scaling")
    backup_enabled: bool = Field(True, description="Enable automated backups")
    monitoring_enabled: bool = Field(True, description="Enable monitoring")
    
    # Network configuration
    vpc_config: Optional[Dict[str, Any]] = None
    security_group_rules: Optional[List[Dict[str, Any]]] = None
    
    # Deployment timeline
    scheduled_deployment: Optional[datetime] = None
    priority: str = Field("normal", regex="^(low|normal|high|urgent)$")
    
    # Metadata
    deployment_notes: Optional[str] = None
    requested_by: str = Field(..., description="User requesting the deployment")


class DeploymentStatus(BaseModel):
    """Current status of a deployment."""
    
    deployment_id: str
    tenant_id: str
    
    status: str = Field(..., regex="^(pending|provisioning|deploying|active|failed|destroying)$")
    progress_percentage: int = Field(..., ge=0, le=100)
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Infrastructure details
    provisioned_resources: Dict[str, Any] = Field(default_factory=dict)
    resource_identifiers: Dict[str, str] = Field(default_factory=dict)
    
    # Deployment logs and events
    current_step: Optional[str] = None
    last_log_entry: Optional[str] = None
    error_details: Optional[str] = None
    
    # Cost tracking
    current_hourly_cost: Optional[Decimal] = None
    estimated_monthly_cost: Optional[Decimal] = None


class CrossTenantAnalytics(BaseModel):
    """Cross-tenant analytics while maintaining privacy boundaries."""
    
    # Tenant segmentation
    tenant_count_by_tier: Dict[str, int]
    tenant_count_by_region: Dict[str, int]
    tenant_count_by_provider: Dict[str, int]
    
    # Usage patterns (anonymized)
    avg_customers_per_tenant: float
    avg_services_per_tenant: float
    avg_storage_usage_gb: float
    avg_bandwidth_usage_gb: float
    
    # Performance benchmarks
    performance_quartiles: Dict[str, Dict[str, float]] = Field(
        ..., description="Performance metrics in quartiles (25th, 50th, 75th, 95th)"
    )
    
    # Growth metrics
    monthly_growth_rate: float
    churn_rate: float
    expansion_revenue: Decimal
    
    # Feature adoption
    feature_adoption_rates: Dict[str, float]
    
    # Cost analytics
    cost_per_tenant_quartiles: Dict[str, Decimal]
    margin_by_tier: Dict[str, float]
    
    generated_at: datetime


class SupportTicketSummary(BaseModel):
    """Support ticket summary across all tenants."""
    
    total_open_tickets: int
    total_tickets_this_month: int
    avg_resolution_time_hours: float
    
    tickets_by_priority: Dict[str, int]
    tickets_by_category: Dict[str, int]
    tickets_by_status: Dict[str, int]
    
    sla_compliance_percentage: float
    escalated_tickets: int
    
    # Customer satisfaction
    avg_satisfaction_score: Optional[float] = None
    response_time_sla_met: float = Field(..., description="Percentage of tickets meeting response SLA")


class PlatformSettingsUpdate(BaseModel):
    """Update platform-wide settings."""
    
    # Feature flags
    feature_flags: Optional[Dict[str, bool]] = None
    
    # Billing settings
    default_billing_cycle: Optional[str] = Field(None, regex="^(monthly|annual)$")
    late_payment_grace_days: Optional[int] = Field(None, ge=0, le=90)
    
    # Resource limits
    default_max_customers: Optional[int] = Field(None, ge=1, le=100000)
    default_max_services: Optional[int] = Field(None, ge=1, le=1000000)
    default_storage_gb: Optional[int] = Field(None, ge=1, le=10000)
    
    # Support settings
    support_response_sla_hours: Optional[int] = Field(None, ge=1, le=168)
    escalation_threshold_hours: Optional[int] = Field(None, ge=1, le=72)
    
    # Security settings
    session_timeout_minutes: Optional[int] = Field(None, ge=15, le=480)
    password_expiry_days: Optional[int] = Field(None, ge=30, le=365)


class ResellerPartnerSummary(BaseModel):
    """Summary of reseller partner performance."""
    
    partner_id: str
    partner_name: str
    territory: str
    
    # Sales metrics
    total_sales: int
    monthly_sales: int
    quarterly_sales: int
    
    # Revenue metrics
    total_revenue: Decimal
    monthly_recurring_revenue: Decimal
    
    # Commission tracking
    total_commission_earned: Decimal
    pending_commission: Decimal
    commission_rate: float
    
    # Performance metrics
    conversion_rate: float
    avg_deal_size: Decimal
    sales_cycle_days: int
    
    # Customer metrics
    active_customers: int
    customer_satisfaction: Optional[float] = None
    churn_rate: float
    
    # Activity status
    last_activity: datetime
    is_active: bool
    performance_rating: str = Field(..., regex="^(excellent|good|average|needs_improvement|poor)$")