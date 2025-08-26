"""
Admin dashboard schemas for validation and serialization.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.common import BaseSchema


class TenantStats(BaseModel):
    """Tenant statistics schema."""
    total: int = Field(..., description="Total number of tenants")
    new_this_month: int = Field(..., description="New tenants this month")
    active: int = Field(..., description="Active tenants")
    inactive: int = Field(..., description="Inactive tenants")
    growth_rate: float = Field(..., description="Growth rate percentage")


class UserStats(BaseModel):
    """User statistics schema."""
    total: int = Field(..., description="Total number of users")
    new_this_week: int = Field(..., description="New users this week")
    active_this_week: int = Field(..., description="Active users this week")
    activity_rate: float = Field(..., description="Activity rate percentage")


class SubscriptionStats(BaseModel):
    """Subscription statistics schema."""
    total: int = Field(..., description="Total subscriptions")
    active: int = Field(..., description="Active subscriptions")
    trial: int = Field(..., description="Trial subscriptions")
    cancelled: int = Field(..., description="Cancelled subscriptions")
    conversion_rate: float = Field(..., description="Trial to paid conversion rate")


class RevenueStats(BaseModel):
    """Revenue statistics schema."""
    total: float = Field(..., description="Total revenue")
    this_month: float = Field(..., description="Revenue this month")
    successful_payments: int = Field(..., description="Successful payments")
    failed_payments: int = Field(..., description="Failed payments")
    success_rate: float = Field(..., description="Payment success rate")


class InfrastructureStats(BaseModel):
    """Infrastructure statistics schema."""
    total_deployments: int = Field(..., description="Total deployments")
    active_deployments: int = Field(..., description="Active deployments")
    provisioning: int = Field(..., description="Deployments being provisioned")
    failed_deployments: int = Field(..., description="Failed deployments")
    success_rate: float = Field(..., description="Deployment success rate")


class NotificationStats(BaseModel):
    """Notification statistics schema."""
    total_sent: int = Field(..., description="Total notifications sent")
    sent_this_week: int = Field(..., description="Notifications sent this week")
    delivered: int = Field(..., description="Successfully delivered notifications")
    failed: int = Field(..., description="Failed notifications")
    delivery_rate: float = Field(..., description="Delivery success rate")


class AdminDashboardStats(BaseModel):
    """Main admin dashboard statistics schema."""
    tenants: TenantStats
    users: UserStats
    subscriptions: SubscriptionStats
    revenue: RevenueStats
    infrastructure: InfrastructureStats
    notifications: NotificationStats
    last_updated: datetime = Field(..., description="Last update timestamp")


class TenantOverview(BaseModel):
    """Tenant overview schema."""
    tenant_id: UUID = Field(..., description="Tenant identifier")
    name: str = Field(..., description="Tenant name")
    domain: Optional[str] = Field(None, description="Tenant domain")
    is_active: bool = Field(..., description="Whether tenant is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    user_count: int = Field(..., description="Number of users")
    subscription_status: str = Field(..., description="Current subscription status")
    last_activity: Optional[datetime] = Field(None, description="Last user activity")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UserOverview(BaseModel):
    """User overview schema."""
    user_id: UUID = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    is_active: bool = Field(..., description="Whether user is active")
    role: str = Field(..., description="User role")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    tenant_id: UUID = Field(..., description="Associated tenant")


class SystemComponentHealth(BaseModel):
    """System component health schema."""
    status: str = Field(..., description="Component status (healthy, degraded, unhealthy)")
    last_checked: datetime = Field(..., description="Last health check timestamp")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Additional metrics")


class SystemHealth(BaseModel):
    """Overall system health schema."""
    overall_status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    components: Dict[str, SystemComponentHealth] = Field(..., description="Component health status")
    metrics: Optional[Dict[str, Any]] = Field(None, description="System-wide metrics")


class UserActivity(BaseModel):
    """User activity schema."""
    user_id: UUID = Field(..., description="User identifier")
    tenant_id: UUID = Field(..., description="Tenant identifier")
    activity_type: str = Field(..., description="Type of activity")
    timestamp: datetime = Field(..., description="Activity timestamp")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional activity data")


class RevenueMetrics(BaseModel):
    """Revenue metrics schema."""
    period: str = Field(..., description="Time period")
    revenue: float = Field(..., description="Revenue amount")
    payment_count: int = Field(..., description="Number of payments")
    average_payment: float = Field(..., description="Average payment amount")
    growth_rate: Optional[float] = Field(None, description="Growth rate from previous period")


class InfrastructureMetrics(BaseModel):
    """Infrastructure metrics schema."""
    deployment_id: UUID = Field(..., description="Deployment identifier")
    tenant_id: UUID = Field(..., description="Tenant identifier")
    status: str = Field(..., description="Deployment status")
    resource_usage: Dict[str, Any] = Field(..., description="Resource usage metrics")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")
    last_updated: datetime = Field(..., description="Last update timestamp")


class NotificationMetrics(BaseModel):
    """Notification metrics schema."""
    channel: str = Field(..., description="Notification channel")
    total_sent: int = Field(..., description="Total notifications sent")
    delivered: int = Field(..., description="Successfully delivered")
    failed: int = Field(..., description="Failed deliveries")
    delivery_rate: float = Field(..., description="Delivery success rate")
    average_response_time: float = Field(..., description="Average delivery time in seconds")


class ActivityLog(BaseModel):
    """Activity log entry schema."""
    timestamp: datetime = Field(..., description="Log timestamp")
    level: str = Field(..., description="Log level (DEBUG, INFO, WARNING, ERROR)")
    component: str = Field(..., description="System component")
    message: str = Field(..., description="Log message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional log data")


class PaginatedActivityLogs(BaseModel):
    """Paginated activity logs schema."""
    logs: List[ActivityLog] = Field(..., description="Activity log entries")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")


class TenantActionRequest(BaseModel):
    """Tenant action request schema."""
    reason: Optional[str] = Field(None, description="Reason for the action")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional action data")


class TenantActionResponse(BaseModel):
    """Tenant action response schema."""
    tenant_id: UUID = Field(..., description="Tenant identifier")
    action: str = Field(..., description="Action performed")
    status: str = Field(..., description="Action status")
    timestamp: datetime = Field(..., description="Action timestamp")
    performed_by: str = Field(..., description="Admin user who performed the action")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response data")


class SystemMetrics(BaseModel):
    """System-wide metrics schema."""
    cpu_usage_percentage: float = Field(..., description="CPU usage percentage")
    memory_usage_percentage: float = Field(..., description="Memory usage percentage")
    disk_usage_percentage: float = Field(..., description="Disk usage percentage")
    network_throughput_mbps: float = Field(..., description="Network throughput in Mbps")
    active_connections: int = Field(..., description="Number of active connections")
    request_rate_per_second: float = Field(..., description="Request rate per second")
    error_rate_percentage: float = Field(..., description="Error rate percentage")
    uptime_percentage: float = Field(..., description="System uptime percentage")


class AlertConfiguration(BaseModel):
    """Alert configuration schema."""
    alert_id: UUID = Field(..., description="Alert identifier")
    name: str = Field(..., description="Alert name")
    description: Optional[str] = Field(None, description="Alert description")
    condition: str = Field(..., description="Alert condition")
    threshold: float = Field(..., description="Alert threshold")
    severity: str = Field(..., description="Alert severity")
    is_active: bool = Field(default=True, description="Whether alert is active")
    notification_channels: List[str] = Field(..., description="Notification channels")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional alert data")


class Alert(AlertConfiguration, BaseSchema):
    """Alert with database fields."""
    pass


class AlertHistory(BaseModel):
    """Alert history entry schema."""
    alert_id: UUID = Field(..., description="Alert identifier")
    triggered_at: datetime = Field(..., description="Alert trigger timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Alert resolution timestamp")
    severity: str = Field(..., description="Alert severity")
    message: str = Field(..., description="Alert message")
    value: float = Field(..., description="Metric value that triggered alert")
    threshold: float = Field(..., description="Alert threshold")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional alert data")


class MaintenanceWindow(BaseModel):
    """Maintenance window schema."""
    maintenance_id: UUID = Field(..., description="Maintenance identifier")
    title: str = Field(..., description="Maintenance title")
    description: Optional[str] = Field(None, description="Maintenance description")
    start_time: datetime = Field(..., description="Maintenance start time")
    end_time: datetime = Field(..., description="Maintenance end time")
    affected_services: List[str] = Field(..., description="Affected services")
    status: str = Field(..., description="Maintenance status")
    created_by: str = Field(..., description="User who created the maintenance")
    notifications_sent: bool = Field(default=False, description="Whether notifications were sent")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional maintenance data")


class BackupStatus(BaseModel):
    """Backup status schema."""
    backup_id: UUID = Field(..., description="Backup identifier")
    backup_type: str = Field(..., description="Backup type (full, incremental)")
    status: str = Field(..., description="Backup status")
    started_at: datetime = Field(..., description="Backup start time")
    completed_at: Optional[datetime] = Field(None, description="Backup completion time")
    size_bytes: Optional[int] = Field(None, description="Backup size in bytes")
    location: str = Field(..., description="Backup storage location")
    retention_days: int = Field(..., description="Backup retention period")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional backup data")


class SecurityEvent(BaseModel):
    """Security event schema."""
    event_id: UUID = Field(..., description="Event identifier")
    event_type: str = Field(..., description="Event type")
    severity: str = Field(..., description="Event severity")
    timestamp: datetime = Field(..., description="Event timestamp")
    source_ip: Optional[str] = Field(None, description="Source IP address")
    user_id: Optional[UUID] = Field(None, description="Associated user")
    tenant_id: Optional[UUID] = Field(None, description="Associated tenant")
    description: str = Field(..., description="Event description")
    action_taken: Optional[str] = Field(None, description="Action taken in response")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional event data")


class PerformanceMetrics(BaseModel):
    """Performance metrics schema."""
    timestamp: datetime = Field(..., description="Metrics timestamp")
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="HTTP method")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    status_code: int = Field(..., description="HTTP status code")
    request_size_bytes: Optional[int] = Field(None, description="Request size in bytes")
    response_size_bytes: Optional[int] = Field(None, description="Response size in bytes")
    user_id: Optional[UUID] = Field(None, description="User making the request")
    tenant_id: Optional[UUID] = Field(None, description="Associated tenant")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metrics data")


class ConfigurationChange(BaseModel):
    """Configuration change schema."""
    change_id: UUID = Field(..., description="Change identifier")
    component: str = Field(..., description="System component")
    setting_name: str = Field(..., description="Configuration setting name")
    old_value: Optional[str] = Field(None, description="Previous value")
    new_value: str = Field(..., description="New value")
    changed_by: str = Field(..., description="User who made the change")
    timestamp: datetime = Field(..., description="Change timestamp")
    approved_by: Optional[str] = Field(None, description="User who approved the change")
    rollback_available: bool = Field(default=True, description="Whether rollback is available")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional change data")