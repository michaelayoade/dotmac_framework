"""
Management Platform adapter for file service integration.

This module provides specialized file operations for the Management Platform
including analytics reports, tenant management documents, and system exports.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..core.generators import (
    CSVGenerator,
    DocumentMetadata,
    ExcelGenerator,
    PDFGenerator,
)
from ..core.processors import ImageProcessor
from ..core.templates import TemplateEngine
from ..storage.tenant_storage import TenantStorageManager

logger = logging.getLogger(__name__)


@dataclass
class TenantInfo:
    """Tenant information for management reports."""

    tenant_id: str
    name: str
    contact_email: str
    created_at: datetime
    status: str
    subscription_plan: str
    user_count: int = 0
    storage_used: int = 0
    storage_quota: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "contact_email": self.contact_email,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "subscription_plan": self.subscription_plan,
            "user_count": self.user_count,
            "storage_used": self.storage_used,
            "storage_quota": self.storage_quota,
            "storage_utilization": (
                (self.storage_used / self.storage_quota * 100)
                if self.storage_quota > 0
                else 0
            ),
        }


@dataclass
class SystemMetrics:
    """System performance metrics."""

    metric_name: str
    current_value: float
    target_value: Optional[float]
    unit: str
    timestamp: datetime
    trend: str = "stable"  # up, down, stable

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "trend": self.trend,
        }


class ManagementPlatformAdapter:
    """File service adapter for Management Platform integration."""

    def __init__(
        self,
        storage_manager: TenantStorageManager,
        template_engine: Optional[TemplateEngine] = None,
        pdf_generator: Optional[PDFGenerator] = None,
        excel_generator: Optional[ExcelGenerator] = None,
        csv_generator: Optional[CSVGenerator] = None,
        image_processor: Optional[ImageProcessor] = None,
    ):
        """Initialize Management Platform file adapter."""
        self.storage = storage_manager
        self.template_engine = template_engine or TemplateEngine()
        self.pdf_generator = pdf_generator or PDFGenerator()
        self.excel_generator = excel_generator or ExcelGenerator()
        self.csv_generator = csv_generator or CSVGenerator()
        self.image_processor = image_processor or ImageProcessor()

        logger.info("Management Platform File Adapter initialized")

    async def generate_tenant_report(
        self,
        tenant_info: TenantInfo,
        report_type: str,
        data: Dict[str, Any],
        admin_tenant_id: str,
        format: str = "pdf",
    ) -> Tuple[str, DocumentMetadata]:
        """
        Generate tenant management report.

        Args:
            tenant_info: Tenant information
            report_type: Type of report (usage, activity, billing, etc.)
            data: Report data
            admin_tenant_id: Admin tenant ID for storage
            format: Output format

        Returns:
            Tuple of (file_path, metadata)
        """
        try:
            # Prepare report data
            report_data = {
                "title": f"{report_type.title()} Report - {tenant_info.name}",
                "tenant_info": tenant_info.to_dict(),
                "report_type": report_type,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generated_by": "Management Platform",
                "summary": self._create_tenant_summary(tenant_info, data),
                "sections": [],
            }

            # Add type-specific sections
            if report_type == "usage":
                report_data["sections"].extend(self._create_usage_sections(data))
            elif report_type == "activity":
                report_data["sections"].extend(self._create_activity_sections(data))
            elif report_type == "billing":
                report_data["sections"].extend(self._create_billing_sections(data))
            else:
                report_data["sections"].append(
                    {
                        "type": "paragraph",
                        "content": f"General report for tenant {tenant_info.name}",
                    }
                )

            # Generate file based on format
            if format.lower() == "pdf":
                file_path, metadata = self.pdf_generator.generate_report(
                    report_data,
                    template_name="management_tenant_report",
                    tenant_id=admin_tenant_id,
                )
            elif format.lower() == "excel":
                # Convert to tabular data for Excel
                excel_data = self._convert_report_to_excel_data(report_data)
                file_path, metadata = self.excel_generator.generate_report(
                    excel_data,
                    sheet_name=f"{report_type.title()} Report",
                    tenant_id=admin_tenant_id,
                )
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Save to admin tenant storage
            storage_path = f"tenant_reports/{tenant_info.tenant_id}/{report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.lower()}"

            with open(file_path, "rb") as f:
                await self.storage.save_file(
                    storage_path,
                    f,
                    admin_tenant_id,
                    metadata={
                        "type": "tenant_report",
                        "tenant_id": tenant_info.tenant_id,
                        "report_type": report_type,
                        "format": format,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            logger.info(f"Generated tenant report: {storage_path}")
            return storage_path, metadata

        except Exception as e:
            logger.error(
                f"Error generating tenant report for {tenant_info.tenant_id}: {e}"
            )
            raise

    async def generate_analytics_dashboard_export(
        self,
        dashboard_data: Dict[str, Any],
        admin_tenant_id: str,
        format: str = "pdf",
        include_charts: bool = True,
    ) -> Tuple[str, DocumentMetadata]:
        """
        Generate analytics dashboard export.

        Args:
            dashboard_data: Dashboard data and metrics
            admin_tenant_id: Admin tenant ID
            format: Export format
            include_charts: Whether to include chart visualizations

        Returns:
            Tuple of (file_path, metadata)
        """
        try:
            # Prepare dashboard report
            report_data = {
                "title": "Analytics Dashboard Export",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "time_period": dashboard_data.get("time_period", "Last 30 Days"),
                "summary": dashboard_data.get("summary", {}),
                "sections": [],
            }

            # Add overview section
            if "overview" in dashboard_data:
                overview = dashboard_data["overview"]
                report_data["sections"].append(
                    {"type": "heading", "content": "Platform Overview"}
                )
                report_data["sections"].append(
                    {
                        "type": "table",
                        "headers": ["Metric", "Value"],
                        "data": [[k, str(v)] for k, v in overview.items()],
                    }
                )

            # Add metrics sections
            if "metrics" in dashboard_data:
                for metric_category, metrics in dashboard_data["metrics"].items():
                    report_data["sections"].append(
                        {
                            "type": "heading",
                            "content": f"{metric_category.title()} Metrics",
                        }
                    )

                    if isinstance(metrics, list):
                        metric_data = []
                        for metric in metrics:
                            if isinstance(metric, SystemMetrics):
                                metric_data.append(
                                    [
                                        metric.metric_name,
                                        f"{metric.current_value} {metric.unit}",
                                        (
                                            f"{metric.target_value} {metric.unit}"
                                            if metric.target_value
                                            else "N/A"
                                        ),
                                        metric.trend,
                                    ]
                                )
                            else:
                                metric_data.append(
                                    [str(k), str(v)] for k, v in metric.items()
                                )

                        report_data["sections"].append(
                            {
                                "type": "table",
                                "headers": ["Metric", "Current", "Target", "Trend"],
                                "data": metric_data,
                            }
                        )

            # Generate charts if requested
            chart_paths = []
            if include_charts and "charts" in dashboard_data:
                for chart_config in dashboard_data["charts"]:
                    try:
                        chart_path, _ = await self.image_processor.generate_chart(
                            chart_config.get("type", "bar"),
                            chart_config.get("data", {}),
                            style_config=chart_config.get("style", {}),
                        )
                        chart_paths.append(chart_path)
                    except Exception as e:
                        logger.warning(f"Could not generate chart: {e}")

            # Generate report
            if format.lower() == "pdf":
                file_path, metadata = self.pdf_generator.generate_report(
                    report_data,
                    template_name="analytics_dashboard",
                    tenant_id=admin_tenant_id,
                )
            elif format.lower() == "excel":
                # Create comprehensive Excel export
                file_path, metadata = await self._create_analytics_excel(
                    dashboard_data, admin_tenant_id
                )
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Save to storage
            storage_path = f"analytics/dashboard_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.lower()}"

            with open(file_path, "rb") as f:
                await self.storage.save_file(
                    storage_path,
                    f,
                    admin_tenant_id,
                    metadata={
                        "type": "analytics_dashboard_export",
                        "format": format,
                        "includes_charts": include_charts,
                        "chart_count": len(chart_paths),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            logger.info(f"Generated analytics dashboard export: {storage_path}")
            return storage_path, metadata

        except Exception as e:
            logger.error(f"Error generating analytics dashboard export: {e}")
            raise

    async def generate_system_status_report(
        self,
        system_metrics: List[SystemMetrics],
        admin_tenant_id: str,
        include_trends: bool = True,
    ) -> Tuple[str, DocumentMetadata]:
        """
        Generate system status and health report.

        Args:
            system_metrics: List of system metrics
            admin_tenant_id: Admin tenant ID
            include_trends: Whether to include trend analysis

        Returns:
            Tuple of (file_path, metadata)
        """
        try:
            # Analyze metrics
            critical_metrics = [m for m in system_metrics if m.trend == "down"]
            warning_metrics = [
                m
                for m in system_metrics
                if m.target_value and m.current_value > m.target_value * 0.8
            ]

            # Prepare report data
            report_data = {
                "title": "System Status Report",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_metrics": len(system_metrics),
                    "critical_issues": len(critical_metrics),
                    "warnings": len(warning_metrics),
                    "status": (
                        "Critical"
                        if critical_metrics
                        else ("Warning" if warning_metrics else "Healthy")
                    ),
                },
                "sections": [],
            }

            # Executive summary
            report_data["sections"].append(
                {"type": "heading", "content": "Executive Summary"}
            )

            status_text = (
                f"System shows {report_data['summary']['status'].lower()} status with "
            )
            status_text += f"{len(critical_metrics)} critical issues and {len(warning_metrics)} warnings."

            report_data["sections"].append(
                {"type": "paragraph", "content": status_text}
            )

            # Critical issues
            if critical_metrics:
                report_data["sections"].append(
                    {"type": "heading", "content": "Critical Issues"}
                )

                critical_data = []
                for metric in critical_metrics:
                    critical_data.append(
                        [
                            metric.metric_name,
                            f"{metric.current_value} {metric.unit}",
                            (
                                f"{metric.target_value} {metric.unit}"
                                if metric.target_value
                                else "N/A"
                            ),
                            metric.trend,
                        ]
                    )

                report_data["sections"].append(
                    {
                        "type": "table",
                        "headers": ["Metric", "Current", "Target", "Trend"],
                        "data": critical_data,
                    }
                )

            # All metrics table
            report_data["sections"].append(
                {"type": "heading", "content": "All System Metrics"}
            )

            metrics_data = []
            for metric in system_metrics:
                metrics_data.append(
                    [
                        metric.metric_name,
                        f"{metric.current_value} {metric.unit}",
                        (
                            f"{metric.target_value} {metric.unit}"
                            if metric.target_value
                            else "N/A"
                        ),
                        metric.trend,
                        metric.timestamp.strftime("%Y-%m-%d %H:%M"),
                    ]
                )

            report_data["sections"].append(
                {
                    "type": "table",
                    "headers": ["Metric", "Current", "Target", "Trend", "Timestamp"],
                    "data": metrics_data,
                }
            )

            # Generate trend charts if requested
            if include_trends:
                try:
                    # Create a trend chart (simplified for demo)
                    chart_data = {
                        "title": "System Metrics Trends",
                        "labels": [m.metric_name for m in system_metrics[:10]],
                        "values": [m.current_value for m in system_metrics[:10]],
                    }

                    chart_path, _ = await self.image_processor.generate_chart(
                        "bar",
                        chart_data,
                        style_config={"title": "Current System Metrics"},
                    )

                except Exception as e:
                    logger.warning(f"Could not generate trend chart: {e}")

            # Generate PDF report
            file_path, metadata = self.pdf_generator.generate_report(
                report_data,
                template_name="system_status_report",
                tenant_id=admin_tenant_id,
            )

            # Save to storage
            storage_path = (
                f"system/status_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

            with open(file_path, "rb") as f:
                await self.storage.save_file(
                    storage_path,
                    f,
                    admin_tenant_id,
                    metadata={
                        "type": "system_status_report",
                        "metrics_count": len(system_metrics),
                        "critical_issues": len(critical_metrics),
                        "warnings": len(warning_metrics),
                        "status": report_data["summary"]["status"],
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            logger.info(f"Generated system status report: {storage_path}")
            return storage_path, metadata

        except Exception as e:
            logger.error(f"Error generating system status report: {e}")
            raise

    async def generate_tenant_onboarding_package(
        self, tenant_info: TenantInfo, admin_tenant_id: str, include_guides: bool = True
    ) -> Tuple[str, DocumentMetadata]:
        """
        Generate tenant onboarding documentation package.

        Args:
            tenant_info: New tenant information
            admin_tenant_id: Admin tenant ID
            include_guides: Whether to include user guides

        Returns:
            Tuple of (file_path, metadata)
        """
        try:
            # Prepare onboarding document
            onboarding_data = {
                "title": f"Welcome to DotMac Platform - {tenant_info.name}",
                "tenant_info": tenant_info.to_dict(),
                "welcome_message": f"Welcome to the DotMac Platform! This document contains important information to help you get started.",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sections": [],
            }

            # Add welcome section
            onboarding_data["sections"].append(
                {"type": "heading", "content": "Getting Started"}
            )

            onboarding_data["sections"].append(
                {
                    "type": "paragraph",
                    "content": f"Your account has been successfully created with the following details:",
                }
            )

            # Account details table
            account_details = [
                ["Tenant ID", tenant_info.tenant_id],
                ["Organization Name", tenant_info.name],
                ["Contact Email", tenant_info.contact_email],
                ["Subscription Plan", tenant_info.subscription_plan],
                ["Account Status", tenant_info.status],
                ["Storage Quota", f"{tenant_info.storage_quota / (1024*1024):.1f} MB"],
            ]

            onboarding_data["sections"].append(
                {
                    "type": "table",
                    "headers": ["Field", "Value"],
                    "data": account_details,
                }
            )

            # Add platform features section
            onboarding_data["sections"].append(
                {"type": "heading", "content": "Platform Features"}
            )

            features = [
                "User Management and Access Control",
                "File Storage and Document Generation",
                "Analytics and Reporting Dashboard",
                "API Access and Integration Tools",
                "Multi-tenant Data Isolation",
                "24/7 Technical Support",
            ]

            onboarding_data["sections"].append({"type": "list", "items": features})

            # Add next steps
            onboarding_data["sections"].append(
                {"type": "heading", "content": "Next Steps"}
            )

            next_steps = [
                "Log in to your admin portal using the credentials provided",
                "Create your first user accounts",
                "Configure your organization settings",
                "Explore the analytics dashboard",
                "Set up API integrations if needed",
                "Contact support if you have any questions",
            ]

            onboarding_data["sections"].append({"type": "list", "items": next_steps})

            # Generate PDF
            file_path, metadata = self.pdf_generator.generate_report(
                onboarding_data,
                template_name="tenant_onboarding",
                tenant_id=admin_tenant_id,
            )

            # Save to storage
            storage_path = f"onboarding/{tenant_info.tenant_id}/welcome_package_{datetime.now().strftime('%Y%m%d')}.pdf"

            with open(file_path, "rb") as f:
                await self.storage.save_file(
                    storage_path,
                    f,
                    admin_tenant_id,
                    metadata={
                        "type": "tenant_onboarding_package",
                        "tenant_id": tenant_info.tenant_id,
                        "tenant_name": tenant_info.name,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            logger.info(f"Generated tenant onboarding package: {storage_path}")
            return storage_path, metadata

        except Exception as e:
            logger.error(
                f"Error generating tenant onboarding package for {tenant_info.tenant_id}: {e}"
            )
            raise

    def _create_tenant_summary(
        self, tenant_info: TenantInfo, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create tenant summary from info and data."""
        return {
            "tenant_name": tenant_info.name,
            "status": tenant_info.status,
            "plan": tenant_info.subscription_plan,
            "users": tenant_info.user_count,
            "storage_used_mb": tenant_info.storage_used / (1024 * 1024),
            "storage_quota_mb": tenant_info.storage_quota / (1024 * 1024),
            "storage_utilization_percent": (
                (tenant_info.storage_used / tenant_info.storage_quota * 100)
                if tenant_info.storage_quota > 0
                else 0
            ),
        }

    def _create_usage_sections(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create usage report sections."""
        sections = []

        sections.append({"type": "heading", "content": "Usage Statistics"})

        if "usage_stats" in data:
            stats = data["usage_stats"]
            sections.append(
                {
                    "type": "table",
                    "headers": ["Metric", "Value"],
                    "data": [[k, str(v)] for k, v in stats.items()],
                }
            )

        return sections

    def _create_activity_sections(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create activity report sections."""
        sections = []

        sections.append({"type": "heading", "content": "Activity Summary"})

        if "activities" in data:
            activities = data["activities"][:10]  # Show last 10
            sections.append(
                {
                    "type": "table",
                    "headers": ["Timestamp", "User", "Action", "Resource"],
                    "data": [
                        [
                            a.get("timestamp", ""),
                            a.get("user", ""),
                            a.get("action", ""),
                            a.get("resource", ""),
                        ]
                        for a in activities
                    ],
                }
            )

        return sections

    def _create_billing_sections(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create billing report sections."""
        sections = []

        sections.append({"type": "heading", "content": "Billing Information"})

        if "billing_summary" in data:
            summary = data["billing_summary"]
            sections.append(
                {
                    "type": "table",
                    "headers": ["Item", "Amount"],
                    "data": [
                        [k, f"${v:.2f}"]
                        for k, v in summary.items()
                        if isinstance(v, (int, float))
                    ],
                }
            )

        return sections

    def _convert_report_to_excel_data(
        self, report_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Convert report data to Excel-friendly format."""
        excel_data = []

        # Add summary row
        excel_data.append(
            {
                "section": "Summary",
                "item": "Report Title",
                "value": report_data.get("title", ""),
                "timestamp": report_data.get("generated_at", ""),
            }
        )

        # Process sections
        for section in report_data.get("sections", []):
            if section.get("type") == "table":
                headers = section.get("headers", [])
                for row in section.get("data", []):
                    row_dict = {"section": "Data"}
                    for i, header in enumerate(headers):
                        if i < len(row):
                            row_dict[header.lower().replace(" ", "_")] = row[i]
                    excel_data.append(row_dict)

        return excel_data

    async def _create_analytics_excel(
        self, dashboard_data: Dict[str, Any], admin_tenant_id: str
    ) -> Tuple[str, DocumentMetadata]:
        """Create comprehensive analytics Excel export."""
        # Create multiple sheets for different data types
        overview_data = []
        if "overview" in dashboard_data:
            for key, value in dashboard_data["overview"].items():
                overview_data.append(
                    {
                        "metric": key,
                        "value": value,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

        return self.excel_generator.generate_report(
            overview_data
            or [
                {
                    "metric": "No data",
                    "value": 0,
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            sheet_name="Analytics Overview",
            tenant_id=admin_tenant_id,
        )
