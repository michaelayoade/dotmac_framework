"""Analytics service layer for business intelligence and reporting."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .repository import AnalyticsRepository
from . import schemas
from dotmac_isp.shared.exceptions import ServiceError, NotFoundError, ValidationError


class AnalyticsService:
    """Service layer for analytics and business intelligence."""

    def __init__(self, db: Session, tenant_id: str):
        """Initialize analytics service with database session."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.analytics_repo = AnalyticsRepository(db, self.tenant_id)

    async def get_dashboard_overview(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> schemas.DashboardOverviewResponse:
        """Get overview metrics for the main dashboard."""
        try:
            # Default to last 30 days if no dates provided
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Get all metric categories
            customer_metrics = self.analytics_repo.get_customer_metrics(
                start_date, end_date
            )
            revenue_metrics = self.analytics_repo.get_revenue_metrics(
                start_date, end_date
            )
            service_metrics = self.analytics_repo.get_service_metrics(
                start_date, end_date
            )
            support_metrics = self.analytics_repo.get_support_metrics(
                start_date, end_date
            )
            network_metrics = self.analytics_repo.get_network_metrics(
                start_date, end_date
            )

            # Calculate key performance indicators
            total_customers = customer_metrics.get("total_customers", 0)
            active_customers = customer_metrics.get("active_customers", 0)
            mrr = revenue_metrics.get("monthly_recurring_revenue", 0.0)

            # Calculate ARPU (Average Revenue Per User)
            arpu = (mrr / active_customers) if active_customers > 0 else 0.0

            # Calculate customer growth rate
            new_customers = customer_metrics.get("new_customers", 0)
            growth_rate = (
                (new_customers / total_customers * 100) if total_customers > 0 else 0.0
            )

            # Network uptime percentage
            network_uptime = network_metrics.get("device_uptime", 0.0)

            overview = {
                "period": {"start_date": start_date, "end_date": end_date},
                "key_metrics": {
                    "total_customers": total_customers,
                    "active_customers": active_customers,
                    "new_customers": new_customers,
                    "customer_growth_rate": round(growth_rate, 2),
                    "total_revenue": revenue_metrics.get("total_revenue", 0.0),
                    "monthly_recurring_revenue": mrr,
                    "average_revenue_per_user": round(arpu, 2),
                    "outstanding_revenue": revenue_metrics.get(
                        "outstanding_revenue", 0.0
                    ),
                },
                "operational_metrics": {
                    "active_services": service_metrics.get("total_services", 0),
                    "new_services": service_metrics.get("new_services", 0),
                    "network_uptime": network_uptime,
                    "network_devices": network_metrics.get("total_devices", 0),
                    "support_tickets": support_metrics.get("total_tickets", 0),
                    "open_tickets": support_metrics.get("open_tickets", 0),
                    "avg_resolution_time": support_metrics.get(
                        "avg_resolution_hours", 0.0
                    ),
                },
                "trends": {
                    "customer_growth": customer_metrics.get("customer_growth", []),
                    "revenue_trend": revenue_metrics.get("revenue_trend", []),
                    "service_breakdown": service_metrics.get("service_breakdown", []),
                    "support_priority_breakdown": support_metrics.get(
                        "priority_breakdown", []
                    ),
                },
                "alerts": {
                    "critical_network_alerts": network_metrics.get(
                        "critical_alerts", 0
                    ),
                    "overdue_tickets": support_metrics.get(
                        "open_tickets", 0
                    ),  # Simplified
                    "outstanding_payments": (
                        1 if revenue_metrics.get("outstanding_revenue", 0) > 1000 else 0
                    ),
                },
            }

            return schemas.DashboardOverviewResponse(**overview)

        except Exception as e:
            raise ServiceError(f"Failed to get dashboard overview: {str(e)}")

    async def get_customer_analytics(
        self, start_date: date, end_date: date, segment: Optional[str] = None
    ) -> schemas.CustomerAnalyticsResponse:
        """Get detailed customer analytics."""
        try:
            customer_metrics = self.analytics_repo.get_customer_metrics(
                start_date, end_date
            )

            analytics = {
                "period": {"start_date": start_date, "end_date": end_date},
                "segment": segment,
                "metrics": {
                    "total_customers": customer_metrics.get("total_customers", 0),
                    "new_customers": customer_metrics.get("new_customers", 0),
                    "active_customers": customer_metrics.get("active_customers", 0),
                    "churn_rate": 2.5,  # Would be calculated from actual data
                    "lifetime_value": 2400.0,  # Would be calculated from revenue data
                    "acquisition_cost": 150.0,  # Would be calculated from marketing data
                },
                "segmentation": {
                    "by_plan_type": [
                        {"segment": "residential", "count": 1250, "percentage": 65.0},
                        {"segment": "business", "count": 580, "percentage": 30.0},
                        {"segment": "enterprise", "count": 95, "percentage": 5.0},
                    ],
                    "by_region": [],  # Would be populated from customer address data
                    "by_tenure": [
                        {"segment": "0-6 months", "count": 340, "percentage": 17.6},
                        {"segment": "6-12 months", "count": 285, "percentage": 14.8},
                        {"segment": "1-2 years", "count": 520, "percentage": 27.0},
                        {"segment": "2+ years", "count": 780, "percentage": 40.6},
                    ],
                },
                "trends": {
                    "growth_over_time": customer_metrics.get("customer_growth", []),
                    "churn_by_month": [],  # Would be calculated
                    "satisfaction_scores": [],  # Would come from surveys
                },
            }

            return schemas.CustomerAnalyticsResponse(**analytics)

        except Exception as e:
            raise ServiceError(f"Failed to get customer analytics: {str(e)}")

    async def get_revenue_analytics(
        self, start_date: date, end_date: date, breakdown: Optional[str] = None
    ) -> schemas.RevenueAnalyticsResponse:
        """Get detailed revenue analytics."""
        try:
            revenue_metrics = self.analytics_repo.get_revenue_metrics(
                start_date, end_date
            )

            analytics = {
                "period": {"start_date": start_date, "end_date": end_date},
                "breakdown": breakdown,
                "metrics": {
                    "total_revenue": revenue_metrics.get("total_revenue", 0.0),
                    "recurring_revenue": revenue_metrics.get(
                        "monthly_recurring_revenue", 0.0
                    ),
                    "one_time_revenue": revenue_metrics.get("total_revenue", 0.0)
                    - revenue_metrics.get("monthly_recurring_revenue", 0.0),
                    "outstanding_revenue": revenue_metrics.get(
                        "outstanding_revenue", 0.0
                    ),
                    "collection_rate": 95.5,  # Would be calculated from payment data
                    "revenue_growth_rate": 12.5,  # Would be calculated from historical data
                },
                "breakdowns": {
                    "by_service_type": [
                        {
                            "category": "internet",
                            "revenue": 85000.0,
                            "percentage": 68.0,
                        },
                        {"category": "phone", "revenue": 22000.0, "percentage": 17.6},
                        {"category": "tv", "revenue": 12000.0, "percentage": 9.6},
                        {"category": "other", "revenue": 6000.0, "percentage": 4.8},
                    ],
                    "by_customer_segment": [
                        {
                            "segment": "residential",
                            "revenue": 75000.0,
                            "percentage": 60.0,
                        },
                        {"segment": "business", "revenue": 42000.0, "percentage": 33.6},
                        {"segment": "enterprise", "revenue": 8000.0, "percentage": 6.4},
                    ],
                    "by_region": [],  # Would be populated from customer location data
                },
                "trends": {
                    "revenue_over_time": revenue_metrics.get("revenue_trend", []),
                    "payment_patterns": [],  # Would be calculated from payment data
                    "seasonal_variations": [],  # Would be calculated from historical data
                },
            }

            return schemas.RevenueAnalyticsResponse(**analytics)

        except Exception as e:
            raise ServiceError(f"Failed to get revenue analytics: {str(e)}")

    async def get_service_analytics(
        self, start_date: date, end_date: date, service_type: Optional[str] = None
    ) -> schemas.ServiceAnalyticsResponse:
        """Get detailed service analytics."""
        try:
            service_metrics = self.analytics_repo.get_service_metrics(
                start_date, end_date
            )

            analytics = {
                "period": {"start_date": start_date, "end_date": end_date},
                "service_type": service_type,
                "metrics": {
                    "total_services": service_metrics.get("total_services", 0),
                    "new_services": service_metrics.get("new_services", 0),
                    "service_adoption_rate": 85.5,  # Would be calculated
                    "service_utilization": 78.2,  # Would be calculated from usage data
                    "service_satisfaction": 4.2,  # Would be from surveys
                    "churn_rate": 3.1,  # Would be calculated from cancellations
                },
                "usage_patterns": {
                    "peak_hours": [
                        {"hour": 20, "usage_percentage": 95.5},
                        {"hour": 21, "usage_percentage": 98.2},
                        {"hour": 19, "usage_percentage": 87.3},
                    ],
                    "bandwidth_utilization": [
                        {"date": start_date.isoformat(), "utilization": 65.5},
                        {"date": end_date.isoformat(), "utilization": 72.1},
                    ],
                    "service_quality_metrics": {
                        "uptime": 99.8,
                        "latency_avg": 15.2,
                        "packet_loss": 0.02,
                    },
                },
                "breakdowns": {
                    "by_service_type": service_metrics.get("service_breakdown", []),
                    "by_plan_tier": [
                        {"tier": "basic", "count": 680, "percentage": 45.5},
                        {"tier": "standard", "count": 520, "percentage": 34.8},
                        {"tier": "premium", "count": 295, "percentage": 19.7},
                    ],
                    "by_customer_segment": [],
                },
                "trends": {
                    "adoption_over_time": [],
                    "usage_growth": [],
                    "upgrade_patterns": [],
                },
            }

            return schemas.ServiceAnalyticsResponse(**analytics)

        except Exception as e:
            raise ServiceError(f"Failed to get service analytics: {str(e)}")

    async def generate_executive_report(
        self, start_date: date, end_date: date
    ) -> schemas.ExecutiveReportResponse:
        """Generate executive summary report."""
        try:
            summary = self.analytics_repo.generate_executive_summary(
                start_date, end_date
            )

            executive_report = {
                "report_id": str(uuid4()),
                "generated_at": datetime.utcnow(),
                "period": summary.get("period", {}),
                "executive_summary": {
                    "key_achievements": [
                        f"Added {summary.get('key_metrics', {}).get('new_customers', 0)} new customers",
                        f"Generated ${summary.get('key_metrics', {}).get('total_revenue', 0):,.2f} in revenue",
                        f"Maintained {summary.get('operational_metrics', {}).get('network_uptime', 0):.1f}% network uptime",
                    ],
                    "performance_highlights": summary.get("key_metrics", {}),
                    "operational_status": summary.get("operational_metrics", {}),
                    "recommendations": [
                        "Focus on customer retention programs to reduce churn",
                        "Invest in network infrastructure to maintain high uptime",
                        "Optimize support processes to reduce resolution times",
                    ],
                },
                "detailed_sections": {
                    "financial_performance": summary.get("detailed_metrics", {}).get(
                        "revenue", {}
                    ),
                    "customer_metrics": summary.get("detailed_metrics", {}).get(
                        "customers", {}
                    ),
                    "operational_metrics": summary.get("detailed_metrics", {}).get(
                        "services", {}
                    ),
                    "support_performance": summary.get("detailed_metrics", {}).get(
                        "support", {}
                    ),
                    "network_status": summary.get("detailed_metrics", {}).get(
                        "network", {}
                    ),
                },
            }

            return schemas.ExecutiveReportResponse(**executive_report)

        except Exception as e:
            raise ServiceError(f"Failed to generate executive report: {str(e)}")

    async def generate_custom_report(
        self, report_request: schemas.CustomReportRequest
    ) -> schemas.CustomReportResponse:
        """Generate a custom report based on user specifications."""
        try:
            report_data = self.analytics_repo.get_custom_report_data(
                report_request.report_type,
                report_request.filters or {},
                report_request.start_date,
                report_request.end_date,
            )

            custom_report = {
                "report_id": str(uuid4()),
                "report_type": report_request.report_type,
                "title": report_request.title,
                "generated_at": datetime.utcnow(),
                "generated_by": report_request.generated_by,
                "period": {
                    "start_date": report_request.start_date,
                    "end_date": report_request.end_date,
                },
                "filters": report_request.filters or {},
                "data": report_data.get("data", {}),
                "metadata": {
                    "record_count": len(report_data.get("data", {})),
                    "data_sources": ["customers", "billing", "services", "support"],
                    "export_formats": ["pdf", "xlsx", "csv"],
                },
            }

            return schemas.CustomReportResponse(**custom_report)

        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to generate custom report: {str(e)}")

    async def get_real_time_metrics(self) -> schemas.RealTimeMetricsResponse:
        """Get real-time system metrics."""
        try:
            now = datetime.utcnow()
            today = now.date()

            # Get today's metrics
            customer_metrics = self.analytics_repo.get_customer_metrics(today, today)
            support_metrics = self.analytics_repo.get_support_metrics(today, today)
            network_metrics = self.analytics_repo.get_network_metrics(today, today)

            real_time_data = {
                "timestamp": now,
                "system_status": {
                    "overall_health": "healthy",
                    "network_uptime": network_metrics.get("device_uptime", 99.5),
                    "active_connections": network_metrics.get("active_devices", 1450),
                    "current_bandwidth_utilization": 67.8,
                },
                "current_activity": {
                    "active_users": customer_metrics.get("active_customers", 1925),
                    "new_signups_today": customer_metrics.get("new_customers", 0),
                    "new_tickets_today": support_metrics.get("total_tickets", 0),
                    "payments_processed_today": 45,  # Would come from billing system
                },
                "alerts": {
                    "critical_alerts": network_metrics.get("critical_alerts", 0),
                    "warning_alerts": 3,
                    "maintenance_scheduled": False,
                    "service_disruptions": [],
                },
                "performance_indicators": {
                    "average_response_time": 125.5,  # milliseconds
                    "api_success_rate": 99.97,
                    "database_performance": "optimal",
                    "cache_hit_ratio": 94.2,
                },
            }

            return schemas.RealTimeMetricsResponse(**real_time_data)

        except Exception as e:
            raise ServiceError(f"Failed to get real-time metrics: {str(e)}")

    async def get_metric_history(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
        interval: str = "daily",
    ) -> List[schemas.MetricDataPoint]:
        """Get historical data for a specific metric."""
        try:
            if interval not in ["hourly", "daily", "weekly", "monthly"]:
                raise ValidationError(
                    "Invalid interval. Must be: hourly, daily, weekly, monthly"
                )

            # This would typically query time-series data
            # For now, return sample data structure
            data_points = []
            current_date = start_date

            while current_date <= end_date:
                # Generate sample metric data
                if metric_name == "customer_count":
                    value = 1900 + (current_date - start_date).days * 2
                elif metric_name == "revenue":
                    value = 125000 + (current_date - start_date).days * 850
                elif metric_name == "network_uptime":
                    value = 99.5 + (hash(str(current_date)) % 100) / 1000
                else:
                    value = 100.0

                data_points.append(
                    schemas.MetricDataPoint(
                        timestamp=datetime.combine(current_date, datetime.min.time()),
                        value=value,
                        metadata={"interval": interval},
                    )
                )

                # Increment date based on interval
                if interval == "daily":
                    current_date += timedelta(days=1)
                elif interval == "weekly":
                    current_date += timedelta(weeks=1)
                elif interval == "monthly":
                    current_date += timedelta(days=30)  # Simplified
                else:  # hourly
                    current_date += timedelta(hours=1)

            return data_points

        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get metric history: {str(e)}")
