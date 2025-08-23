"""Repository pattern for analytics database operations."""

from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.sql import extract

from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class AnalyticsRepository:
    """Repository for analytics and reporting operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def get_customer_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get customer-related metrics."""
        try:
            # Total customers
            from dotmac_isp.modules.identity.models import Customer

            total_customers = (
                self.db.query(func.count(Customer.id))
                .filter(
                    and_(
                        Customer.tenant_id == str(self.tenant_id),
                        Customer.is_deleted == False,
                    )
                )
                .scalar()
                or 0
            )

            # New customers in period
            new_customers = (
                self.db.query(func.count(Customer.id))
                .filter(
                    and_(
                        Customer.tenant_id == str(self.tenant_id),
                        Customer.is_deleted == False,
                        Customer.created_at >= start_date,
                        Customer.created_at <= end_date,
                    )
                )
                .scalar()
                or 0
            )

            # Active customers (with recent activity)
            active_customers = (
                self.db.query(func.count(Customer.id))
                .filter(
                    and_(
                        Customer.tenant_id == str(self.tenant_id),
                        Customer.is_deleted == False,
                        Customer.status == "active",
                    )
                )
                .scalar()
                or 0
            )

            # Customer growth over time
            growth_query = (
                self.db.query(
                    func.date(Customer.created_at).label("date"),
                    func.count(Customer.id).label("count"),
                )
                .filter(
                    and_(
                        Customer.tenant_id == str(self.tenant_id),
                        Customer.is_deleted == False,
                        Customer.created_at >= start_date,
                        Customer.created_at <= end_date,
                    )
                )
                .group_by(func.date(Customer.created_at))
                .all()
            )

            customer_growth = [
                {"date": row.date.isoformat(), "count": row.count}
                for row in growth_query
            ]

            return {
                "total_customers": total_customers,
                "new_customers": new_customers,
                "active_customers": active_customers,
                "customer_growth": customer_growth,
            }

        except Exception as e:
            return {
                "total_customers": 0,
                "new_customers": 0,
                "active_customers": 0,
                "customer_growth": [],
            }

    def get_revenue_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get revenue-related metrics."""
        try:
            # Mock implementation - would integrate with billing module
            from dotmac_isp.modules.billing.models import Invoice, Payment

            # Total revenue in period
            total_revenue = self.db.query(func.sum(Invoice.total_amount)).filter(
                and_(
                    Invoice.tenant_id == str(self.tenant_id),
                    Invoice.is_deleted == False,
                    Invoice.issue_date >= start_date,
                    Invoice.issue_date <= end_date,
                    Invoice.status.in_(["paid", "partially_paid"]),
                )
            ).scalar() or Decimal("0.00")

            # Outstanding revenue
            outstanding_revenue = self.db.query(func.sum(Invoice.amount_due)).filter(
                and_(
                    Invoice.tenant_id == str(self.tenant_id),
                    Invoice.is_deleted == False,
                    Invoice.status.in_(["sent", "overdue"]),
                )
            ).scalar() or Decimal("0.00")

            # Monthly recurring revenue (MRR)
            # This would be calculated from subscriptions
            mrr = Decimal("0.00")  # Placeholder

            # Revenue by month
            monthly_revenue = (
                self.db.query(
                    extract("year", Invoice.issue_date).label("year"),
                    extract("month", Invoice.issue_date).label("month"),
                    func.sum(Invoice.total_amount).label("revenue"),
                )
                .filter(
                    and_(
                        Invoice.tenant_id == str(self.tenant_id),
                        Invoice.is_deleted == False,
                        Invoice.issue_date >= start_date,
                        Invoice.issue_date <= end_date,
                        Invoice.status.in_(["paid", "partially_paid"]),
                    )
                )
                .group_by(
                    extract("year", Invoice.issue_date),
                    extract("month", Invoice.issue_date),
                )
                .order_by("year", "month")
                .all()
            )

            revenue_trend = [
                {
                    "period": f"{int(row.year)}-{int(row.month):02d}",
                    "revenue": float(row.revenue),
                }
                for row in monthly_revenue
            ]

            return {
                "total_revenue": float(total_revenue),
                "outstanding_revenue": float(outstanding_revenue),
                "monthly_recurring_revenue": float(mrr),
                "revenue_trend": revenue_trend,
            }

        except Exception as e:
            return {
                "total_revenue": 0.0,
                "outstanding_revenue": 0.0,
                "monthly_recurring_revenue": 0.0,
                "revenue_trend": [],
            }

    def get_service_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get service-related metrics."""
        try:
            from dotmac_isp.modules.services.models import ServiceInstance

            # Total active services
            total_services = (
                self.db.query(func.count(ServiceInstance.id))
                .filter(
                    and_(
                        ServiceInstance.tenant_id == str(self.tenant_id),
                        ServiceInstance.is_deleted == False,
                        ServiceInstance.status == "active",
                    )
                )
                .scalar()
                or 0
            )

            # New services in period
            new_services = (
                self.db.query(func.count(ServiceInstance.id))
                .filter(
                    and_(
                        ServiceInstance.tenant_id == str(self.tenant_id),
                        ServiceInstance.is_deleted == False,
                        ServiceInstance.created_at >= start_date,
                        ServiceInstance.created_at <= end_date,
                    )
                )
                .scalar()
                or 0
            )

            # Services by type
            service_breakdown = (
                self.db.query(
                    ServiceInstance.service_type,
                    func.count(ServiceInstance.id).label("count"),
                )
                .filter(
                    and_(
                        ServiceInstance.tenant_id == str(self.tenant_id),
                        ServiceInstance.is_deleted == False,
                        ServiceInstance.status == "active",
                    )
                )
                .group_by(ServiceInstance.service_type)
                .all()
            )

            service_types = [
                {"service_type": row.service_type, "count": row.count}
                for row in service_breakdown
            ]

            return {
                "total_services": total_services,
                "new_services": new_services,
                "service_breakdown": service_types,
            }

        except Exception as e:
            return {"total_services": 0, "new_services": 0, "service_breakdown": []}

    def get_support_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get support-related metrics."""
        try:
            from dotmac_isp.modules.support.models import Ticket

            # Total tickets in period
            total_tickets = (
                self.db.query(func.count(Ticket.id))
                .filter(
                    and_(
                        Ticket.tenant_id == str(self.tenant_id),
                        Ticket.is_deleted == False,
                        Ticket.created_at >= start_date,
                        Ticket.created_at <= end_date,
                    )
                )
                .scalar()
                or 0
            )

            # Open tickets
            open_tickets = (
                self.db.query(func.count(Ticket.id))
                .filter(
                    and_(
                        Ticket.tenant_id == str(self.tenant_id),
                        Ticket.is_deleted == False,
                        Ticket.ticket_status.in_(["open", "in_progress", "escalated"]),
                    )
                )
                .scalar()
                or 0
            )

            # Average resolution time (in hours)
            resolved_tickets = (
                self.db.query(
                    func.avg(
                        func.extract("epoch", Ticket.resolved_at - Ticket.created_at)
                        / 3600
                    ).label("avg_resolution_hours")
                )
                .filter(
                    and_(
                        Ticket.tenant_id == str(self.tenant_id),
                        Ticket.is_deleted == False,
                        Ticket.ticket_status == "resolved",
                        Ticket.created_at >= start_date,
                        Ticket.created_at <= end_date,
                    )
                )
                .scalar()
                or 0
            )

            # Tickets by priority
            priority_breakdown = (
                self.db.query(Ticket.priority, func.count(Ticket.id).label("count"))
                .filter(
                    and_(
                        Ticket.tenant_id == str(self.tenant_id),
                        Ticket.is_deleted == False,
                        Ticket.created_at >= start_date,
                        Ticket.created_at <= end_date,
                    )
                )
                .group_by(Ticket.priority)
                .all()
            )

            priority_stats = [
                {"priority": row.priority, "count": row.count}
                for row in priority_breakdown
            ]

            return {
                "total_tickets": total_tickets,
                "open_tickets": open_tickets,
                "avg_resolution_hours": (
                    round(float(resolved_tickets), 2) if resolved_tickets else 0.0
                ),
                "priority_breakdown": priority_stats,
            }

        except Exception as e:
            return {
                "total_tickets": 0,
                "open_tickets": 0,
                "avg_resolution_hours": 0.0,
                "priority_breakdown": [],
            }

    def get_network_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get network-related metrics."""
        try:
            from dotmac_isp.modules.network_integration.models import (
                NetworkDevice,
                NetworkAlert,
            )

            # Total network devices
            total_devices = (
                self.db.query(func.count(NetworkDevice.id))
                .filter(
                    and_(
                        NetworkDevice.tenant_id == str(self.tenant_id),
                        NetworkDevice.is_deleted == False,
                    )
                )
                .scalar()
                or 0
            )

            # Active devices
            active_devices = (
                self.db.query(func.count(NetworkDevice.id))
                .filter(
                    and_(
                        NetworkDevice.tenant_id == str(self.tenant_id),
                        NetworkDevice.is_deleted == False,
                        NetworkDevice.status == "active",
                    )
                )
                .scalar()
                or 0
            )

            # Network alerts in period
            total_alerts = (
                self.db.query(func.count(NetworkAlert.id))
                .filter(
                    and_(
                        NetworkAlert.tenant_id == str(self.tenant_id),
                        NetworkAlert.is_deleted == False,
                        NetworkAlert.created_at >= start_date,
                        NetworkAlert.created_at <= end_date,
                    )
                )
                .scalar()
                or 0
            )

            # Critical alerts
            critical_alerts = (
                self.db.query(func.count(NetworkAlert.id))
                .filter(
                    and_(
                        NetworkAlert.tenant_id == str(self.tenant_id),
                        NetworkAlert.is_deleted == False,
                        NetworkAlert.severity == "critical",
                        NetworkAlert.is_active == True,
                    )
                )
                .scalar()
                or 0
            )

            return {
                "total_devices": total_devices,
                "active_devices": active_devices,
                "device_uptime": round(
                    (
                        (active_devices / total_devices * 100)
                        if total_devices > 0
                        else 0.0
                    ),
                    2,
                ),
                "total_alerts": total_alerts,
                "critical_alerts": critical_alerts,
            }

        except Exception as e:
            return {
                "total_devices": 0,
                "active_devices": 0,
                "device_uptime": 0.0,
                "total_alerts": 0,
                "critical_alerts": 0,
            }

    def generate_executive_summary(
        self, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Generate executive summary combining all metrics."""
        try:
            customer_metrics = self.get_customer_metrics(start_date, end_date)
            revenue_metrics = self.get_revenue_metrics(start_date, end_date)
            service_metrics = self.get_service_metrics(start_date, end_date)
            support_metrics = self.get_support_metrics(start_date, end_date)
            network_metrics = self.get_network_metrics(start_date, end_date)

            # Calculate key performance indicators
            customer_satisfaction = 85.0  # Would be calculated from surveys
            churn_rate = 2.5  # Would be calculated from cancellations
            arpu = (
                (
                    revenue_metrics["monthly_recurring_revenue"]
                    / customer_metrics["active_customers"]
                )
                if customer_metrics["active_customers"] > 0
                else 0.0
            )

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "key_metrics": {
                    "total_customers": customer_metrics["total_customers"],
                    "new_customers": customer_metrics["new_customers"],
                    "total_revenue": revenue_metrics["total_revenue"],
                    "monthly_recurring_revenue": revenue_metrics[
                        "monthly_recurring_revenue"
                    ],
                    "average_revenue_per_user": round(arpu, 2),
                    "customer_satisfaction": customer_satisfaction,
                    "churn_rate": churn_rate,
                },
                "operational_metrics": {
                    "total_services": service_metrics["total_services"],
                    "network_uptime": network_metrics["device_uptime"],
                    "support_tickets": support_metrics["total_tickets"],
                    "avg_resolution_time": support_metrics["avg_resolution_hours"],
                },
                "detailed_metrics": {
                    "customers": customer_metrics,
                    "revenue": revenue_metrics,
                    "services": service_metrics,
                    "support": support_metrics,
                    "network": network_metrics,
                },
            }

        except Exception as e:
            # Return empty summary on error
            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "key_metrics": {},
                "operational_metrics": {},
                "detailed_metrics": {},
            }

    def get_custom_report_data(
        self,
        report_type: str,
        filters: Dict[str, Any],
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Get data for custom reports."""
        try:
            if report_type == "customer_acquisition":
                return self._get_customer_acquisition_report(
                    filters, start_date, end_date
                )
            elif report_type == "revenue_analysis":
                return self._get_revenue_analysis_report(filters, start_date, end_date)
            elif report_type == "service_usage":
                return self._get_service_usage_report(filters, start_date, end_date)
            elif report_type == "support_performance":
                return self._get_support_performance_report(
                    filters, start_date, end_date
                )
            else:
                raise ValidationError(f"Unknown report type: {report_type}")

        except Exception as e:
            raise ValidationError(f"Failed to generate report: {str(e)}")

    def _get_customer_acquisition_report(
        self, filters: Dict[str, Any], start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Generate customer acquisition report."""
        # Implementation would query customer data with various breakdowns
        return {
            "report_type": "customer_acquisition",
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "data": {
                "new_customers_by_month": [],
                "acquisition_channels": [],
                "customer_segments": [],
                "conversion_rates": {},
            },
        }

    def _get_revenue_analysis_report(
        self, filters: Dict[str, Any], start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Generate revenue analysis report."""
        # Implementation would query billing/payment data
        return {
            "report_type": "revenue_analysis",
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "data": {
                "revenue_by_service": [],
                "payment_methods": [],
                "recurring_vs_onetime": {},
                "geographic_breakdown": [],
            },
        }

    def _get_service_usage_report(
        self, filters: Dict[str, Any], start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Generate service usage report."""
        # Implementation would query service instance and usage data
        return {
            "report_type": "service_usage",
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "data": {
                "bandwidth_usage": [],
                "service_adoption": [],
                "peak_usage_times": [],
                "capacity_planning": {},
            },
        }

    def _get_support_performance_report(
        self, filters: Dict[str, Any], start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Generate support performance report."""
        # Implementation would query ticket and resolution data
        return {
            "report_type": "support_performance",
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "data": {
                "resolution_times": [],
                "first_contact_resolution": 0.0,
                "escalation_rates": [],
                "agent_performance": [],
            },
        }
