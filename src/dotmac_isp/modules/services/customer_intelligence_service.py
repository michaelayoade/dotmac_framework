"""Customer service intelligence for proactive portal notifications."""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_shared.api.exception_handlers import standard_exception_handler

from .service import ServiceProvisioningService


class CustomerServiceIntelligenceService:
    """Simple service intelligence for customer portal enhancements."""

    def __init__(self, db: Session, tenant_id: str, timezone):
        """__init__ service method."""
        self.db = db
        self.tenant_id = tenant_id
        self.service_provisioning = ServiceProvisioningService(db, tenant_id)

    async def get_proactive_notifications(self, customer_id: UUID) -> Dict[str, Any]:
        """Get proactive service status notifications for customer."""
        services = await self.service_provisioning.list_customer_services(
            customer_id, skip=0, limit=100
        )
        notifications = []
        service_summary = {
            "total_services": len(services),
            "active_services": 0,
            "issues": 0,
            "maintenance_scheduled": 0,
        }

        for service in services:
            service_summary["active_services"] += 1 if service.status == "ACTIVE" else 0

            # Check for service issues (simplified logic)
            if hasattr(service, "status") and service.status in ["SUSPENDED", "ERROR"]:
                service_summary["issues"] += 1
                notifications.append(
                    {
                        "type": "service_issue",
                        "priority": "high",
                        "title": f"{service.service_plan.name} - Service Issue",
                        "message": f"Your {service.service_plan.name} service is currently experiencing issues. Our team is working to resolve this.",
                        "service_id": str(service.id),
                        "service_name": service.service_plan.name,
                        "action_required": False,
                        "estimated_resolution": "2 hours",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

            # Proactive maintenance notifications (demo logic)
            if hasattr(service, "created_at"):
                # Simulate maintenance for services older than 30 days
                days_old = (datetime.now(timezone.utc) - service.created_at).days
                if days_old > 30 and days_old % 60 == 0:  # Every 60 days
                    service_summary["maintenance_scheduled"] += 1
                    notifications.append(
                        {
                            "type": "maintenance_scheduled",
                            "priority": "medium",
                            "title": f"Scheduled Maintenance - {service.service_plan.name}",
                            "message": f"We have scheduled maintenance for your {service.service_plan.name} service. Brief interruption expected.",
                            "service_id": str(service.id),
                            "service_name": service.service_plan.name,
                            "action_required": False,
                            "scheduled_date": (
                                datetime.now(timezone.utc) + timedelta(days=7)
                            ).isoformat(),
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )

        # Add general service health notification
        if service_summary["active_services"] > 0:
            notifications.insert(
                0,
                {
                    "type": "service_health",
                    "priority": "low",
                    "title": "All Services Operating Normally",
                    "message": f'All {service_summary["active_services"]} of your services are running smoothly.',
                    "service_id": None,
                    "service_name": "All Services",
                    "action_required": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        return {
            "notifications": notifications,
            "service_summary": service_summary,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def get_usage_insights(self, customer_id: UUID) -> Dict[str, Any]:
        """Get usage insights for customer optimization."""
        services = await self.service_provisioning.list_customer_services(
            customer_id, skip=0, limit=100
        )
        insights = []

        # Simple usage-based insights (demo logic)
        for service in services:
            if service.service_plan.service_type == "INTERNET":
                insights.append(
                    {
                        "type": "usage_optimization",
                        "title": "Internet Usage Insight",
                        "message": "You're using 75% of your data allowance. Consider upgrading to unlimited.",
                        "service_id": str(service.id),
                        "service_name": service.service_plan.name,
                        "recommendation": "Upgrade to Unlimited Plan",
                        "potential_savings": "Avoid overage charges",
                        "action_url": "/services/upgrade",
                    }
                )

            elif service.service_plan.service_type == "PHONE":
                insights.append(
                    {
                        "type": "usage_insight",
                        "title": "Phone Usage Pattern",
                        "message": "You use mostly WiFi calling. A cheaper plan might work better.",
                        "service_id": str(service.id),
                        "service_name": service.service_plan.name,
                        "recommendation": "Consider Basic Phone Plan",
                        "potential_savings": "Save $20/month",
                        "action_url": "/services/downgrade",
                    }
                )

        return {
            "usage_insights": insights,
            "summary": {
                "total_insights": len(insights),
                "potential_monthly_impact": (
                    "$20 savings" if insights else "No recommendations"
                ),
            },
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
