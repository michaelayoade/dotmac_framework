"""
Reports SDK for analytics report generation and scheduling.
"""

import logging
from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.exceptions import AnalyticsError, NotFoundError
from ..models.enums import ReportType
from ..models.reports import Report, ReportExecution, ReportSubscription

logger = logging.getLogger(__name__)


class ReportsSDK:
    """SDK for analytics reports operations."""

    def __init__(self, tenant_id: str, db: Session):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.db = db

    async def create_report(
        self,
        name: str,
        display_name: str,
        report_type: ReportType,
        query_config: Dict[str, Any],
        description: Optional[str] = None,
        template_config: Optional[Dict[str, Any]] = None,
        output_formats: Optional[List[str]] = None,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new report."""
        try:
            report = Report(
                tenant_id=self.tenant_id,
                name=name,
                display_name=display_name,
                report_type=report_type.value,
                description=description,
                query_config=query_config,
                template_config=template_config or {},
                output_formats=output_formats or ["pdf"],
                owner_id=owner_id or "system",
            )

            self.db.add(report)
            self.db.commit()
            self.db.refresh(report)

            return {
                "report_id": str(report.id),
                "name": report.name,
                "display_name": report.display_name,
                "report_type": report.report_type,
                "created_at": report.created_at,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create report: {e}")
            raise AnalyticsError(f"Report creation failed: {str(e)}")

    async def generate_report(
        self, report_id: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a report execution."""
        try:
            # Get report
            report = (
                self.db.query(Report)
                .filter(Report.tenant_id == self.tenant_id, Report.id == report_id)
                .first()
            )

            if not report:
                raise NotFoundError(f"Report {report_id} not found")

            # Create execution record
            execution = ReportExecution(
                tenant_id=self.tenant_id,
                report_id=report_id,
                execution_id=f"exec_{utc_now().timestamp()}",
                triggered_by="manual",
                started_at=utc_now(),
                status="running",
            )

            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)

            # Simulate report generation (in real implementation, this would be async)
            execution.completed_at = utc_now()
            execution.status = "completed"
            execution.output_files = ["report.pdf"]
            self.db.commit()

            return {
                "execution_id": execution.execution_id,
                "report_id": report_id,
                "status": execution.status,
                "started_at": execution.started_at,
                "completed_at": execution.completed_at,
                "output_files": execution.output_files,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to generate report: {e}")
            raise AnalyticsError(f"Report generation failed: {str(e)}")

    async def subscribe_to_report(
        self,
        report_id: str,
        user_id: str,
        email: str,
        delivery_method: str = "email",
        preferred_format: str = "pdf",
    ) -> Dict[str, Any]:
        """Subscribe to report notifications."""
        try:
            subscription = ReportSubscription(
                tenant_id=self.tenant_id,
                report_id=report_id,
                user_id=user_id,
                email=email,
                delivery_method=delivery_method,
                preferred_format=preferred_format,
            )

            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)

            return {
                "subscription_id": str(subscription.id),
                "report_id": report_id,
                "user_id": user_id,
                "created_at": subscription.created_at,
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create report subscription: {e}")
            raise AnalyticsError(f"Report subscription failed: {str(e)}")
