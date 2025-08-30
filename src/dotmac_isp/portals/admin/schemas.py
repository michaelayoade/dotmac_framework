"""Admin portal API schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AdminDashboard(BaseModel):
    """Admin dashboard overview data."""

    total_customers: int
    active_services: int
    monthly_revenue: Decimal
    open_tickets: int
    system_alerts: int
    recent_activities: List[Dict[str, Any]] = Field(default_factory=list)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)


class CustomerOverview(BaseModel):
    """Customer overview for admin."""

    total: int
    active: int
    suspended: int
    pending: int
    new_this_month: int
    churn_rate: float
    by_type: Dict[str, int] = Field(default_factory=dict)


class ServicesOverview(BaseModel):
    """Services overview for admin."""

    total_instances: int
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)
    revenue_per_service: Dict[str, Decimal] = Field(default_factory=dict)


class FinancialOverview(BaseModel):
    """Financial overview for admin."""

    monthly_revenue: Decimal
    outstanding_invoices: int
    overdue_amount: Decimal
    collection_rate: float
    revenue_trend: List[Dict[str, Any]] = Field(default_factory=list)
    top_revenue_customers: List[Dict[str, Any]] = Field(default_factory=list)


class SupportOverview(BaseModel):
    """Support overview for admin."""

    open_tickets: int
    avg_response_time: float  # hours
    sla_compliance: float  # percentage
    escalated_tickets: int
    tickets_by_category: Dict[str, int] = Field(default_factory=dict)
    tickets_by_priority: Dict[str, int] = Field(default_factory=dict)


class SystemHealth(BaseModel):
    """System health status."""

    database: str
    redis: str
    services: str
    last_updated: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int


class AvailableReports(BaseModel):
    """Available admin reports."""

    financial: List[str]
    operational: List[str]
    support: List[str]
    custom: List[str] = Field(default_factory=list)


class ActivityLogEntry(BaseModel):
    """Activity log entry."""

    id: UUID
    timestamp: datetime
    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None


class NetworkMetrics(BaseModel):
    """Network performance metrics."""

    total_bandwidth: float  # Mbps
    utilized_bandwidth: float  # Mbps
    peak_usage: float  # Mbps
    average_latency: float  # ms
    packet_loss: float  # percentage
    uptime: float  # percentage


class CustomerManagementData(BaseModel):
    """Customer management data for admin."""

    customers: List[Dict[str, Any]]
    total_count: int
    active_count: int
    suspended_count: int
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class ServiceManagementData(BaseModel):
    """Service management data for admin."""

    services: List[Dict[str, Any]]
    total_count: int
    active_count: int
    pending_count: int
    suspended_count: int


class BillingManagementData(BaseModel):
    """Billing management data for admin."""

    recent_invoices: List[Dict[str, Any]]
    pending_payments: List[Dict[str, Any]]
    overdue_invoices: List[Dict[str, Any]]
    total_outstanding: Decimal
    collection_metrics: Dict[str, Any] = Field(default_factory=dict)
