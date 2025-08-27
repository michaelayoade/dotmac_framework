"""
Analytics and reporting service.
Provides comprehensive business intelligence, metrics collection, and reporting capabilities.
"""

import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from enum import Enum
import json
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, case, extract
from sqlalchemy.sql import text as sql_text

from core.exceptions import ValidationError, DatabaseError
from core.logging import get_logger
from models.tenant import Tenant
from models.user import User
from models.billing import Subscription, Invoice, Payment, BillingPlan
from models.infrastructure import InfrastructureDeployment
from models.notifications import NotificationLog
from schemas.analytics import ()
    AnalyticsTimeframe,
    MetricType,
    ReportFormat,
    AnalyticsQuery,
    TenantAnalytics,
    RevenueAnalytics,
    UsageAnalytics,
    PerformanceMetrics
, timezone)

logger = get_logger(__name__)


class MetricAggregation(str, Enum):
    """Metric aggregation types."""
    SUM = "sum"
    COUNT = "count"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    DISTINCT_COUNT = "distinct_count"


class TimeGranularity(str, Enum):
    """Time granularity for analytics."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


@dataclass
class AnalyticsFilter:
    """Analytics filter configuration."""
    field: str
    operator: str  # eq, ne, gt, gte, lt, lte, in, not_in, like
    value: Any


class AnalyticsService:
    """Service for analytics, reporting, and business intelligence."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_tenant_analytics(:)
        self,
        tenant_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    granularity: TimeGranularity = TimeGranularity.DAY)
    ) -> Dict[str, Any]:
        """
        Get comprehensive tenant analytics.
        
        Args:
            tenant_id: Optional tenant filter
            start_date: Start of analysis period
            end_date: End of analysis period
            granularity: Time granularity for metrics
            
        Returns:
            Dict containing tenant analytics data
        """
        try:
            logger.info(f"Generating tenant analytics for period {start_date} to {end_date}")
            
            # Set default date range
            if not end_date:
                end_date = datetime.now(None)
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Build tenant filter
            tenant_filter = []
            if tenant_id:
                tenant_filter = [Tenant.id == tenant_id]
            
            # Get tenant metrics
            tenant_metrics = await self._get_tenant_metrics(tenant_filter, start_date, end_date)
            
            # Get user growth metrics
            user_growth = await self._get_user_growth_metrics(tenant_filter, start_date, end_date, granularity)
            
            # Get subscription metrics
            subscription_metrics = await self._get_subscription_metrics(tenant_filter, start_date, end_date)
            
            # Get usage metrics
            usage_metrics = await self._get_usage_metrics(tenant_filter, start_date, end_date, granularity)
            
            # Get top tenants (if not filtering by specific tenant)
            top_tenants = []
            if not tenant_id:
                top_tenants = await self._get_top_tenants(start_date, end_date)
            
            return {
                "period": {
                    "start": start_date.isoformat(,
)                    "end": end_date.isoformat(),
                    "granularity": granularity.value
                },
                "tenant_metrics": tenant_metrics,
                "user_growth": user_growth,
                "subscription_metrics": subscription_metrics,
                "usage_metrics": usage_metrics,
                "top_tenants": top_tenants,
                "generated_at": datetime.now(None).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate tenant analytics: {e}")
            raise DatabaseError(f"Failed to generate tenant analytics: {e}")
    
    async def get_revenue_analytics(:)
        self,
        tenant_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: TimeGranularity = TimeGranularity.DAY,
    currency: str = "USD")
    ) -> Dict[str, Any]:
        """
        Get comprehensive revenue analytics.
        
        Args:
            tenant_id: Optional tenant filter
            start_date: Start of analysis period
            end_date: End of analysis period
            granularity: Time granularity for metrics
            currency: Currency filter
            
        Returns:
            Dict containing revenue analytics data
        """
        try:
            logger.info(f"Generating revenue analytics for period {start_date} to {end_date}")
            
            # Set default date range
            if not end_date:
                end_date = datetime.now(None)
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Build filters
            filters = [Payment.status == "completed"]
            if tenant_id:
                filters.append(Invoice.tenant_id == tenant_id)
            
            # Revenue time series
            revenue_series = await self._get_revenue_time_series()
                filters, start_date, end_date, granularity
            
            # Revenue by plan
            revenue_by_plan = await self._get_revenue_by_plan(filters, start_date, end_date)
            
            # Revenue cohort analysis
            cohort_analysis = await self._get_revenue_cohort_analysis()
                tenant_id, start_date, end_date
            
            # MRR/ARR calculations
            recurring_revenue = await self._calculate_recurring_revenue()
                tenant_id, end_date
            
            # Revenue forecasting
            forecast = await self._forecast_revenue(revenue_series, granularity)
            
            # Churn analysis
            churn_analysis = await self._get_churn_analysis(tenant_id, start_date, end_date)
            
            # Calculate total metrics
            total_revenue = sum(item["revenue"] for item in revenue_series)
            total_payments = sum(item["payment_count"] for item in revenue_series)
            
            return {
                "period": {
                    "start": start_date.isoformat(,
)                    "end": end_date.isoformat(),
                    "granularity": granularity.value,
                    "currency": currency
                },
                "summary": {
                    "total_revenue": total_revenue,
                    "total_payments": total_payments,
                    "average_payment": total_revenue / total_payments if total_payments > 0 else 0,
                    "mrr": recurring_revenue["mrr"],
                    "arr": recurring_revenue["arr"],
                    "growth_rate": self._calculate_growth_rate(revenue_series)
                },
                "time_series": revenue_series,
                "revenue_by_plan": revenue_by_plan,
                "cohort_analysis": cohort_analysis,
                "recurring_revenue": recurring_revenue,
                "forecast": forecast,
                "churn_analysis": churn_analysis,
                "generated_at": datetime.now(None).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate revenue analytics: {e}")
            raise DatabaseError(f"Failed to generate revenue analytics: {e}")
    
    async def get_usage_analytics(:)
        self,
        tenant_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    resource_type: Optional[str] = None)
    ) -> Dict[str, Any]:
        """
        Get usage analytics across platform resources.
        
        Args:
            tenant_id: Optional tenant filter
            start_date: Start of analysis period
            end_date: End of analysis period
            resource_type: Optional resource type filter
            
        Returns:
            Dict containing usage analytics data
        """
        try:
            logger.info(f"Generating usage analytics for period {start_date} to {end_date}")
            
            # Set default date range
            if not end_date:
                end_date = datetime.now(None)
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Infrastructure usage
            infrastructure_usage = await self._get_infrastructure_usage()
                tenant_id, start_date, end_date
            
            # Notification usage
            notification_usage = await self._get_notification_usage()
                tenant_id, start_date, end_date
            
            # API usage (would need API logging table)
            api_usage = await self._get_api_usage(tenant_id, start_date, end_date)
            
            # Storage usage
            storage_usage = await self._get_storage_usage(tenant_id, start_date, end_date)
            
            # User activity patterns
            user_activity = await self._get_user_activity_patterns()
                tenant_id, start_date, end_date
            
            # Peak usage analysis
            peak_usage = await self._get_peak_usage_analysis()
                tenant_id, start_date, end_date
            
            return {
                "period": {
                    "start": start_date.isoformat(,
)                    "end": end_date.isoformat()
                },
                "infrastructure_usage": infrastructure_usage,
                "notification_usage": notification_usage,
                "api_usage": api_usage,
                "storage_usage": storage_usage,
                "user_activity": user_activity,
                "peak_usage": peak_usage,
                "generated_at": datetime.now(None).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate usage analytics: {e}")
            raise DatabaseError(f"Failed to generate usage analytics: {e}")
    
    async def get_performance_metrics(:)
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    metric_types: Optional[List[str]] = None)
    ) -> Dict[str, Any]:
        """
        Get system performance metrics.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            metric_types: Optional list of metric types to include
            
        Returns:
            Dict containing performance metrics
        """
        try:
            logger.info(f"Generating performance metrics for period {start_date} to {end_date}")
            
            # Set default date range
            if not end_date:
                end_date = datetime.now(None)
            if not start_date:
                start_date = end_date - timedelta(hours=24)
            
            # Response time metrics
            response_times = await self._get_response_time_metrics(start_date, end_date)
            
            # Error rate metrics
            error_rates = await self._get_error_rate_metrics(start_date, end_date)
            
            # Throughput metrics
            throughput = await self._get_throughput_metrics(start_date, end_date)
            
            # Resource utilization
            resource_utilization = await self._get_resource_utilization(start_date, end_date)
            
            # Database performance
            db_performance = await self._get_database_performance(start_date, end_date)
            
            # External service performance
            external_services = await self._get_external_service_performance(start_date, end_date)
            
            return {
                "period": {
                    "start": start_date.isoformat(,
)                    "end": end_date.isoformat()
                },
                "response_times": response_times,
                "error_rates": error_rates,
                "throughput": throughput,
                "resource_utilization": resource_utilization,
                "database_performance": db_performance,
                "external_services": external_services,
                "generated_at": datetime.now(None).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate performance metrics: {e}")
            raise DatabaseError(f"Failed to generate performance metrics: {e}")
    
    async def create_custom_report(:)
        self,
        query: AnalyticsQuery,
    user_id: str)
    ) -> Dict[str, Any]:
        """
        Create a custom analytics report based on user query.
        
        Args:
            query: Analytics query configuration
            user_id: User creating the report
            
        Returns:
            Dict containing custom report data
        """
        try:
            logger.info(f"Creating custom report: {query.name}")
            
            # Validate query
            await self._validate_analytics_query(query)
            
            # Execute query based on type
            if query.metric_type == MetricType.REVENUE:
                data = await self._execute_revenue_query(query)
            elif query.metric_type == MetricType.USAGE:
                data = await self._execute_usage_query(query)
            elif query.metric_type == MetricType.USER_ACTIVITY:
                data = await self._execute_user_activity_query(query)
            elif query.metric_type == MetricType.PERFORMANCE:
                data = await self._execute_performance_query(query)
            else:
                data = await self._execute_generic_query(query)
            
            # Format data based on requested format
            formatted_data = await self._format_report_data(data, query.format)
            
            # Save report if requested
            report_id = None
            if query.save_report:
                report_id = await self._save_custom_report(query, formatted_data, user_id)
            
            return {
                "report_id": report_id,
                "name": query.name,
                "metric_type": query.metric_type,
                "period": {
                    "start": query.start_date.isoformat(,
)                    "end": query.end_date.isoformat()
                },
                "data": formatted_data,
                "metadata": {
                    "created_by": user_id,
                    "created_at": datetime.now(None).isoformat(),
                    "query_execution_time": "< 1s"  # Would measure actual time
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create custom report: {e}")
            raise DatabaseError(f"Failed to create custom report: {e}")
    
    async def get_dashboard_kpis(:)
        self,
        tenant_id: Optional[UUID] = None,
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS)
    ) -> Dict[str, Any]:
        """
        Get key performance indicators for dashboard display.
        
        Args:
            tenant_id: Optional tenant filter
            timeframe: Analysis timeframe
            
        Returns:
            Dict containing KPI data
        """
        try:
            # Calculate date range from timeframe
            end_date = datetime.now(None)
            if timeframe == AnalyticsTimeframe.LAST_7_DAYS:
                start_date = end_date - timedelta(days=7)
            elif timeframe == AnalyticsTimeframe.LAST_30_DAYS:
                start_date = end_date - timedelta(days=30)
            elif timeframe == AnalyticsTimeframe.LAST_90_DAYS:
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            # Get current period metrics
            current_metrics = await self._get_kpi_metrics(tenant_id, start_date, end_date)
            
            # Get previous period for comparison
            period_length = end_date - start_date
            previous_start = start_date - period_length
            previous_end = start_date
            previous_metrics = await self._get_kpi_metrics(tenant_id, previous_start, previous_end)
            
            # Calculate changes
            kpis = {}
            for metric, current_value in current_metrics.items(:
    )                previous_value = previous_metrics.get(metric, 0)
                change = self._calculate_percentage_change(previous_value, current_value)
                
                kpis[metric] = {
                    "current": current_value,
                    "previous": previous_value,
                    "change_percentage": change,
                    "trend": "up" if change > 0 else "down" if change < 0 else "stable"
                }
            
            return {
                "timeframe": timeframe.value,
                "period": {
                    "current": {"start": start_date.isoformat(), "end": end_date.isoformat(},
)                    "previous": {"start": previous_start.isoformat(), "end": previous_end.isoformat(}
                },
                "kpis": kpis,
)                "generated_at": datetime.now(None).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard KPIs: {e}")
            raise DatabaseError(f"Failed to get dashboard KPIs: {e}")
    
    # Private helper methods
    
    async def _get_tenant_metrics(:)
        self,
        tenant_filter: List,
        start_date: datetime,
    end_date: datetime)
    ) -> Dict[str, Any]:
        """Get basic tenant metrics."""
        # Total tenants
        total_result = await self.db.execute(
)            select(func.count(Tenant.id).where(and_(*tenant_filter)
        total_tenants = total_result.scalar()
        
        # Active tenants
)        active_result = await self.db.execute()
            select(func.count(Tenant.id).where())
                and_(Tenant.is_active == True, *tenant_filter)
        active_tenants = active_result.scalar()
        
        # New tenants in period
)        new_result = await self.db.execute()
            select(func.count(Tenant.id).where())
                and_()
                    Tenant.created_at >= start_date,
                    Tenant.created_at <= end_date,
                    *tenant_filter
        new_tenants = new_result.scalar()
        
        return {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "inactive_tenants": total_tenants - active_tenants,
            "new_tenants": new_tenants,
)            "activation_rate": (active_tenants / total_tenants * 100) if total_tenants > 0 else 0
        }
    
    async def _get_user_growth_metrics(:)
        self,
        tenant_filter: List,
        start_date: datetime,
        end_date: datetime,
    granularity: TimeGranularity)
    ) -> List[Dict[str, Any]]:
        """Get user growth metrics over time."""
        # This would be more complex in a real implementation
        # For now, return sample data structure
        growth_data = []
        
        current_date = start_date
        delta = timedelta(days=1) if granularity == TimeGranularity.DAY else timedelta(weeks=1)
        
        while current_date <= end_date:
            # Simulate user growth data
            period_end = min(current_date + delta, end_date)
            
            # Get user count for this period
            user_result = await self.db.execute(
)                select(func.count(User.id).where()
                    and_()
                        User.created_at >= current_date,
                        User.created_at < period_end,
                        User.tenant_id.in_(
)                            select(Tenant.id).where(and_(*tenant_filter)
                        ) if tenant_filter else True
            user_count = user_result.scalar()
            
)            growth_data.append({)
                "period": current_date.isoformat(,
                "new_users": user_count,
)                "cumulative_users": sum(item["new_users"] for item in growth_data) + user_count
            })
            
            current_date = period_end
        
        return growth_data
    
    async def _get_subscription_metrics(:)
        self,
        tenant_filter: List,
        start_date: datetime,
    end_date: datetime)
    ) -> Dict[str, Any]:
        """Get subscription metrics."""
        filters = []
        if tenant_filter:
            filters.append(
)                Subscription.tenant_id.in_()
                    select(Tenant.id).where(and_(*tenant_filter)
        
        # Active subscriptions
        active_result = await self.db.execute(
)            select(func.count(Subscription.id).where()
                and_(Subscription.status == "active", *filters)
        active_subscriptions = active_result.scalar()
        
        # New subscriptions in period
)        new_result = await self.db.execute()
            select(func.count(Subscription.id).where())
                and_()
                    Subscription.created_at >= start_date,
                    Subscription.created_at <= end_date,
                    *filters
        new_subscriptions = new_result.scalar()
        
        # Cancelled subscriptions
)        cancelled_result = await self.db.execute()
            select(func.count(Subscription.id).where())
                and_()
                    Subscription.status == "cancelled",
                    Subscription.updated_at >= start_date,
                    Subscription.updated_at <= end_date,
                    *filters
        cancelled_subscriptions = cancelled_result.scalar()
        
        return {
            "active_subscriptions": active_subscriptions,
            "new_subscriptions": new_subscriptions,
            "cancelled_subscriptions": cancelled_subscriptions,
)            "churn_rate": (cancelled_subscriptions / max(active_subscriptions, 1) * 100
    
    async def _get_usage_metrics(:)
        self,
        tenant_filter: List,
        start_date: datetime,
        end_date: datetime,
    granularity: TimeGranularity)
    ) -> Dict[str, Any]:
        """Get usage metrics."""
        # Infrastructure deployments
        deployment_filters = []
        if tenant_filter:
            deployment_filters.append(
)                InfrastructureDeployment.tenant_id.in_()
                    select(Tenant.id).where(and_(*tenant_filter)
        
        deployment_result = await self.db.execute(
)            select(func.count(InfrastructureDeployment.id).where()
                and_()
                    InfrastructureDeployment.created_at >= start_date,
                    InfrastructureDeployment.created_at <= end_date,
                    *deployment_filters
        deployments = deployment_result.scalar()
        
        # Notifications
        notification_filters = []
        if tenant_filter:
    )            notification_filters.append()
                NotificationLog.tenant_id.in_(
)                    select(Tenant.id).where(and_(*tenant_filter)
        
        notification_result = await self.db.execute(
)            select()
                func.count(NotificationLog.id),
                func.count(case((NotificationLog.status == "delivered", 1)
            ).where()
                and_()
                    NotificationLog.created_at >= start_date,
                    NotificationLog.created_at <= end_date,
                    *notification_filters
        total_notifications, delivered_notifications = notification_result.one()
        
        return {
            "infrastructure_deployments": deployments,
            "total_notifications": total_notifications,
            "delivered_notifications": delivered_notifications,
)            "notification_delivery_rate": (delivered_notifications / max(total_notifications, 1) * 100
    
    async def _get_top_tenants(:)
        self,
        start_date: datetime,
        end_date: datetime,
    limit: int = 10)
    ) -> List[Dict[str, Any]]:
        """Get top tenants by various metrics."""
        # Top tenants by revenue
        revenue_result = await self.db.execute(
)            select()
                Invoice.tenant_id,
                func.sum(Payment.amount).label("total_revenue")
            .join(Payment, Invoice.id == Payment.invoice_id)
            .where()
                and_()
                    Payment.status == "completed",
                    Payment.processed_at >= start_date,
                    Payment.processed_at <= end_date
            .group_by(Invoice.tenant_id)
            .order_by(func.sum(Payment.amount).desc())
            .limit(limit)
        
        top_tenants = []
        for tenant_id, revenue in revenue_result.all(:)
            # Get tenant details
)            tenant_result = await self.db.execute()
                select(Tenant).where(Tenant.id == tenant_id)
            tenant = tenant_result.scalar_one_or_none()
            
            if tenant:
    )                top_tenants.append({)
                    "tenant_id": str(tenant_id),
                    "tenant_name": tenant.name,
                    "total_revenue": float(revenue),
                    "metric_type": "revenue"
                })
        
        return top_tenants
    
    async def _get_revenue_time_series(:)
        self,
        filters: List,
        start_date: datetime,
        end_date: datetime,
    granularity: TimeGranularity)
    ) -> List[Dict[str, Any]]:
        """Get revenue time series data."""
        # Determine date truncation based on granularity
        date_trunc_format = "day"
        if granularity == TimeGranularity.HOUR:
            date_trunc_format = "hour"
        elif granularity == TimeGranularity.WEEK:
            date_trunc_format = "week"
        elif granularity == TimeGranularity.MONTH:
            date_trunc_format = "month"
        
        result = await self.db.execute(
)            select()
                func.date_trunc(date_trunc_format, Payment.processed_at).label("period"),
                func.sum(Payment.amount).label("revenue"),
                func.count(Payment.id).label("payment_count")
            .join(Invoice, Payment.invoice_id == Invoice.id)
            .where()
                and_()
                    Payment.processed_at >= start_date,
                    Payment.processed_at <= end_date,
                    *filters
            .group_by(func.date_trunc(date_trunc_format, Payment.processed_at))
            .order_by(func.date_trunc(date_trunc_format, Payment.processed_at)
        
        return [
            {
                "period": period.isoformat(,
)                "revenue": float(revenue),
                "payment_count": payment_count
            for period, revenue, payment_count in result.all( ])
    
)    def _calculate_growth_rate(self, time_series: List[Dict[str, Any]]) -> float:
        """Calculate growth rate from time series data."""
        if len(time_series) < 2:
            return 0.0
        
        first_value = time_series[0]["revenue"]
        last_value = time_series[-1]["revenue"]
        
        if first_value == 0:
            return 100.0 if last_value > 0 else 0.0
        
        return ((last_value - first_value) / first_value) * 100
    
    def _calculate_percentage_change(self, old_value: float, new_value: float) -> float:
        """Calculate percentage change between two values."""
        if old_value == 0:
            return 100.0 if new_value > 0 else 0.0
        
        return ((new_value - old_value) / old_value) * 100
    
    # Placeholder methods for additional analytics features
    async def _get_revenue_by_plan(self, filters, start_date, end_date):
        """Get revenue broken down by billing plan."""
        # Placeholder implementation
        return {}
    
    async def get_tenant_usage_summary(
        self, 
        tenant_id: str, 
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get tenant usage summary for specified period."""
        try:
            # Mock data - in production this would query actual usage metrics
            return {
                "current_usage": {
                    "active_customers": 1247,
                    "active_services": 3891,
                    "storage_used_gb": 67.5,
                    "bandwidth_used_gb": 1250.0,
                    "api_requests": 450000
                },
                "utilization": {
                    "storage_percent": 67.5,
                    "cpu_percent": 45.2,
                    "memory_percent": 68.7
                },
                "performance": {
                    "avg_response_time_ms": 185,
                    "avg_uptime_percent": 99.95,
                    "total_api_requests": 450000
                },
                "new_customers": 25,
                "churned_customers": 3,
                "services_provisioned": 127,
                "services_deprovisioned": 8,
                "estimated_monthly_cost": 2650.0
            }
        except Exception as e:
            logger.error(f"Error getting usage summary for tenant {tenant_id}: {e}")
            return {}
    
    async def get_recent_activity(self, tenant_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get recent activity metrics for tenant."""
        try:
            # Mock data - in production this would query actual activity logs
            return {
                "logins_24h": 156,
                "api_calls_24h": 12450,
                "open_tickets": 2,
                "failed_logins": 5,
                "new_users": 3,
                "service_changes": 1
            }
        except Exception as e:
            logger.error(f"Error getting recent activity for tenant {tenant_id}: {e}")
            return {}
    
    async def get_performance_metrics(
        self, 
        tenant_id: str, 
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for tenant."""
        try:
            # Mock data - in production this would query monitoring systems
            return {
                "api_requests_total": 450000,
                "avg_response_time_ms": 185,
                "uptime_percentage": 99.95,
                "error_count": 45,
                "peak_concurrent_users": 250,
                "cache_hit_rate": 89.5
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics for tenant {tenant_id}: {e}")
            return {}
    
    async def _get_revenue_cohort_analysis(self, tenant_id, start_date, end_date):
        """Get revenue cohort analysis."""
        return {"cohorts": [], "retention_rates": []}
    
    async def _calculate_recurring_revenue(self, tenant_id, end_date):
        """Calculate MRR and ARR."""
        return {"mrr": 50000, "arr": 600000}
    
    async def _forecast_revenue(self, revenue_series, granularity):
        """Forecast future revenue based on historical data."""
        return {"forecast": [], "confidence_interval": []}
    
    async def _get_churn_analysis(self, tenant_id, start_date, end_date):
        """Get customer churn analysis."""
        return {"churn_rate": 5.2, "churn_reasons": []}
    
    async def _get_infrastructure_usage(self, tenant_id, start_date, end_date):
        """Get infrastructure usage metrics."""
        return {"cpu_hours": 1000, "memory_gb_hours": 5000, "storage_gb": 1000}
    
    async def _get_notification_usage(self, tenant_id, start_date, end_date):
        """Get notification usage metrics."""
        return {"email": 10000, "sms": 2000, "push": 15000}
    
    async def _get_api_usage(self, tenant_id, start_date, end_date):
        """Get API usage metrics."""
        return {"total_requests": 100000, "successful_requests": 99500, "error_rate": 0.5}
    
    async def _get_storage_usage(self, tenant_id, start_date, end_date):
        """Get storage usage metrics."""
        return {"total_storage_gb": 500, "backup_storage_gb": 200}
    
    async def _get_user_activity_patterns(self, tenant_id, start_date, end_date):
        """Get user activity patterns."""
        return {"peak_hours": [9, 10, 11, 14, 15], "daily_active_users": 1000}
    
    async def _get_peak_usage_analysis(self, tenant_id, start_date, end_date):
        """Get peak usage analysis."""
        return {"peak_cpu": 80, "peak_memory": 75, "peak_concurrent_users": 500}
    
    async def _get_response_time_metrics(self, start_date, end_date):
        """Get response time metrics."""
        return {"p50": 150, "p95": 500, "p99": 1000}
    
    async def _get_error_rate_metrics(self, start_date, end_date):
        """Get error rate metrics."""
        return {"4xx_rate": 2.5, "5xx_rate": 0.5, "total_error_rate": 3.0}
    
    async def _get_throughput_metrics(self, start_date, end_date):
        """Get throughput metrics."""
        return {"requests_per_second": 100, "peak_rps": 500}
    
    async def _get_resource_utilization(self, start_date, end_date):
        """Get resource utilization metrics."""
        return {"cpu_utilization": 65, "memory_utilization": 70, "disk_utilization": 45}
    
    async def _get_database_performance(self, start_date, end_date):
        """Get database performance metrics."""
        return {"query_time_ms": 25, "connections": 50, "slow_queries": 5}
    
    async def _get_external_service_performance(self, start_date, end_date):
        """Get external service performance metrics."""
        return {"stripe": {"uptime": 99.9, "response_time": 200}, "sendgrid": {"uptime": 99.8, "response_time": 150}}
    
    async def _validate_analytics_query(self, query: AnalyticsQuery):
        """Validate analytics query."""
        if query.start_date >= query.end_date:
            raise ValidationError("Start date must be before end date")
    
    async def _execute_revenue_query(self, query: AnalyticsQuery):
        """Execute revenue-specific query."""
        return {"data": []}
    
    async def _execute_usage_query(self, query: AnalyticsQuery):
        """Execute usage-specific query."""
        return {"data": []}
    
    async def _execute_user_activity_query(self, query: AnalyticsQuery):
        """Execute user activity query."""
        return {"data": []}
    
    async def _execute_performance_query(self, query: AnalyticsQuery):
        """Execute performance query."""
        return {"data": []}
    
    async def _execute_generic_query(self, query: AnalyticsQuery):
        """Execute generic analytics query."""
        return {"data": []}
    
    async def _format_report_data(self, data: Dict[str, Any], format: ReportFormat):
        """Format report data based on requested format."""
        return data
    
    async def _save_custom_report(self, query: AnalyticsQuery, data: Dict[str, Any], user_id: str):
        """Save custom report to database."""
        return "report_123"
    
    async def _get_kpi_metrics(self, tenant_id: Optional[UUID], start_date: datetime, end_date: datetime):
        """Get KPI metrics for a time period."""
        # This would calculate various KPIs
        return {
            "total_revenue": 100000,
            "active_users": 1000,
            "new_signups": 50,
            "infrastructure_deployments": 25,
            "notification_delivery_rate": 98.5
        }
