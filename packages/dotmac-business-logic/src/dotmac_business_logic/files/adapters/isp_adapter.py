"""
ISP Framework adapter for file service integration.

This module provides specialized file operations tailored for the ISP Framework
including customer invoices, usage reports, and network documentation.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from ..core.generators import (
    CSVGenerator,
    DocumentMetadata,
    ExcelGenerator,
    PDFGenerator,
)
from ..core.templates import TemplateEngine
from ..storage.tenant_storage import TenantStorageManager

logger = logging.getLogger(__name__)


@dataclass
class ISPCustomerInfo:
    """ISP Customer information for document generation."""

    customer_id: str
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: str = "US"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for template use."""
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "company": self.company,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "country": self.country,
        }


@dataclass
class ISPServiceUsage:
    """ISP Service usage data for reports."""

    service_name: str
    usage_amount: float
    usage_unit: str
    billing_rate: float
    total_cost: float
    period_start: datetime
    period_end: datetime
    service_type: str = "data"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_name": self.service_name,
            "usage_amount": self.usage_amount,
            "usage_unit": self.usage_unit,
            "billing_rate": self.billing_rate,
            "total_cost": self.total_cost,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "service_type": self.service_type,
        }


class ISPFileAdapter:
    """File service adapter for ISP Framework integration."""

    def __init__(
        self,
        storage_manager: TenantStorageManager,
        template_engine: Optional[TemplateEngine] = None,
        pdf_generator: Optional[PDFGenerator] = None,
        excel_generator: Optional[ExcelGenerator] = None,
        csv_generator: Optional[CSVGenerator] = None,
    ):
        """Initialize ISP file adapter."""
        self.storage = storage_manager
        self.template_engine = template_engine or TemplateEngine()
        self.pdf_generator = pdf_generator or PDFGenerator()
        self.excel_generator = excel_generator or ExcelGenerator()
        self.csv_generator = csv_generator or CSVGenerator()

        logger.info("ISP File Adapter initialized")

    async def generate_customer_invoice(
        self,
        customer_info: ISPCustomerInfo,
        invoice_data: dict[str, Any],
        tenant_id: str,
        template_name: str = "isp_invoice",
        save_to_storage: bool = True,
    ) -> tuple[str, DocumentMetadata]:
        """
        Generate customer invoice PDF for ISP services.

        Args:
            customer_info: Customer information
            invoice_data: Invoice details and line items
            tenant_id: Tenant ID
            template_name: Invoice template to use
            save_to_storage: Whether to save to tenant storage

        Returns:
            Tuple of (file_path, metadata)
        """
        try:
            # Enhance invoice data with customer info
            enhanced_invoice_data = invoice_data.copy()
            enhanced_invoice_data["customer_info"] = customer_info.to_dict()

            # Add ISP-specific company info if not provided
            if "company_info" not in enhanced_invoice_data:
                enhanced_invoice_data["company_info"] = {
                    "name": "DotMac ISP Services",
                    "address": "123 Network Lane",
                    "city": "Tech City, TC 12345",
                    "phone": "(555) 123-4567",
                    "email": "billing@dotmacisp.com",
                    "website": "www.dotmacisp.com",
                }

            # Generate PDF
            file_path, metadata = self.pdf_generator.generate_invoice(
                enhanced_invoice_data, template_name=template_name, tenant_id=tenant_id
            )

            # Save to tenant storage if requested
            if save_to_storage:
                storage_path = f"invoices/{customer_info.customer_id}/invoice_{invoice_data.get('invoice_number', 'unknown')}.pdf"

                with open(file_path, "rb") as f:
                    await self.storage.save_file(
                        storage_path,
                        f,
                        tenant_id,
                        metadata={
                            "type": "customer_invoice",
                            "customer_id": customer_info.customer_id,
                            "invoice_number": invoice_data.get("invoice_number"),
                            "total_amount": invoice_data.get("total_amount"),
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )

                logger.info(f"Saved customer invoice to storage: {storage_path}")
                return storage_path, metadata

            return file_path, metadata

        except Exception as e:
            logger.error(
                f"Error generating customer invoice for {customer_info.customer_id}: {e}"
            )
            raise

    async def generate_usage_report(
        self,
        customer_id: str,
        usage_data: list[ISPServiceUsage],
        date_range: dict[str, Any],
        tenant_id: str,
        format: str = "pdf",
        template_name: str = "usage_report",
    ) -> tuple[str, DocumentMetadata]:
        """
        Generate service usage report for customer.

        Args:
            customer_id: Customer ID
            usage_data: List of service usage records
            date_range: Report date range
            tenant_id: Tenant ID
            format: Output format (pdf, excel, csv)
            template_name: Template to use

        Returns:
            Tuple of (file_path, metadata)
        """
        try:
            # Prepare report data
            report_data = {
                "title": f"Usage Report - Customer {customer_id}",
                "customer_id": customer_id,
                "date_range": date_range,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_services": len(usage_data),
                "total_usage_cost": sum(usage.total_cost for usage in usage_data),
                "usage_summary": self._create_usage_summary(usage_data),
                "sections": [
                    {"type": "heading", "content": "Usage Summary"},
                    {
                        "type": "table",
                        "headers": ["Service", "Usage", "Rate", "Total Cost"],
                        "data": [
                            [
                                usage.service_name,
                                f"{usage.usage_amount} {usage.usage_unit}",
                                f"${usage.billing_rate:.2f}",
                                f"${usage.total_cost:.2f}",
                            ]
                            for usage in usage_data
                        ],
                    },
                ],
            }

            if format.lower() == "pdf":
                file_path, metadata = self.pdf_generator.generate_report(
                    report_data, template_name=template_name, tenant_id=tenant_id
                )
            elif format.lower() == "excel":
                # Convert to Excel format
                excel_data = [usage.to_dict() for usage in usage_data]
                file_path, metadata = self.excel_generator.generate_report(
                    excel_data, sheet_name="Usage Report", tenant_id=tenant_id
                )
            elif format.lower() == "csv":
                # Convert to CSV format
                csv_data = [usage.to_dict() for usage in usage_data]
                file_path, metadata = self.csv_generator.export_to_csv(
                    csv_data, tenant_id=tenant_id
                )
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Save to tenant storage
            storage_path = f"reports/{customer_id}/usage_report_{date_range.get('start', 'unknown')}_to_{date_range.get('end', 'unknown')}.{format.lower()}"

            with open(file_path, "rb") as f:
                await self.storage.save_file(
                    storage_path,
                    f,
                    tenant_id,
                    metadata={
                        "type": "usage_report",
                        "customer_id": customer_id,
                        "format": format,
                        "date_range": date_range,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            logger.info(
                f"Generated usage report for customer {customer_id}: {storage_path}"
            )
            return storage_path, metadata

        except Exception as e:
            logger.error(
                f"Error generating usage report for customer {customer_id}: {e}"
            )
            raise

    async def generate_network_diagram(
        self,
        network_data: dict[str, Any],
        tenant_id: str,
        diagram_type: str = "topology",
        output_format: str = "png",
    ) -> tuple[str, DocumentMetadata]:
        """
        Generate network topology diagram.

        Args:
            network_data: Network configuration and topology data
            tenant_id: Tenant ID
            diagram_type: Type of diagram (topology, coverage, etc.)
            output_format: Output format (png, pdf)

        Returns:
            Tuple of (file_path, metadata)
        """
        try:
            # For now, create a placeholder chart as network diagram
            # In a real implementation, this would use specialized network visualization libraries

            from ..core.processors import ImageProcessor

            processor = ImageProcessor()

            # Create a simple chart representation of network data
            chart_data = {
                "title": f"Network {diagram_type.title()} Diagram",
                "type": "bar",  # Could be more sophisticated network visualization
                "labels": list(network_data.get("nodes", {}).keys())[:10],
                "values": [
                    len(network_data.get("nodes", {}).get(node, []))
                    for node in list(network_data.get("nodes", {}).keys())[:10]
                ],
            }

            file_path, metadata = await processor.generate_chart(
                "bar",
                chart_data,
                style_config={"title": f"Network {diagram_type.title()}"},
            )

            # Save to tenant storage
            storage_path = f"network/{diagram_type}_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format}"

            with open(file_path, "rb") as f:
                await self.storage.save_file(
                    storage_path,
                    f,
                    tenant_id,
                    metadata={
                        "type": "network_diagram",
                        "diagram_type": diagram_type,
                        "format": output_format,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            logger.info(f"Generated network diagram: {storage_path}")
            return storage_path, metadata

        except Exception as e:
            logger.error(f"Error generating network diagram: {e}")
            raise

    async def export_customer_data(
        self,
        customer_id: str,
        data_types: list[str],
        tenant_id: str,
        format: str = "excel",
        include_usage: bool = True,
        date_range: Optional[dict[str, Any]] = None,
    ) -> tuple[str, DocumentMetadata]:
        """
        Export comprehensive customer data.

        Args:
            customer_id: Customer ID
            data_types: Types of data to include
            tenant_id: Tenant ID
            format: Export format
            include_usage: Whether to include usage data
            date_range: Optional date range filter

        Returns:
            Tuple of (file_path, metadata)
        """
        try:
            # This would typically query the ISP database for customer data
            # For demo purposes, create sample export data

            export_data = {
                "customer_info": {
                    "customer_id": customer_id,
                    "export_date": datetime.now(timezone.utc).isoformat(),
                    "data_types": data_types,
                    "date_range": date_range,
                },
                "profile": [
                    {"field": "Customer ID", "value": customer_id},
                    {"field": "Name", "value": f"Customer {customer_id}"},
                    {"field": "Email", "value": f"customer{customer_id}@example.com"},
                ],
            }

            if "billing" in data_types:
                export_data["billing"] = [
                    {
                        "invoice_number": f"INV-{customer_id}-001",
                        "amount": 99.99,
                        "date": "2023-12-01",
                        "status": "paid",
                    }
                ]

            if "usage" in data_types and include_usage:
                export_data["usage"] = [
                    {
                        "service": "Internet Service",
                        "usage": "150 GB",
                        "date": "2023-12-01",
                        "cost": 49.99,
                    }
                ]

            if format.lower() == "excel":
                # Create Excel with multiple sheets
                file_path, metadata = self.excel_generator.generate_report(
                    export_data["profile"],
                    sheet_name="Customer Profile",
                    tenant_id=tenant_id,
                )
            elif format.lower() == "csv":
                # Flatten data for CSV
                flat_data = []
                for data_type, records in export_data.items():
                    if data_type != "customer_info" and isinstance(records, list):
                        for record in records:
                            record["data_type"] = data_type
                            flat_data.append(record)

                file_path, metadata = self.csv_generator.export_to_csv(
                    flat_data, tenant_id=tenant_id
                )
            else:
                raise ValueError(f"Unsupported export format: {format}")

            # Save to tenant storage
            storage_path = f"exports/{customer_id}/data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format.lower()}"

            with open(file_path, "rb") as f:
                await self.storage.save_file(
                    storage_path,
                    f,
                    tenant_id,
                    metadata={
                        "type": "customer_data_export",
                        "customer_id": customer_id,
                        "data_types": data_types,
                        "format": format,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            logger.info(f"Generated customer data export: {storage_path}")
            return storage_path, metadata

        except Exception as e:
            logger.error(f"Error exporting customer data for {customer_id}: {e}")
            raise

    async def generate_service_certificate(
        self,
        customer_id: str,
        service_details: dict[str, Any],
        tenant_id: str,
        template_name: str = "service_certificate",
    ) -> tuple[str, DocumentMetadata]:
        """
        Generate service activation or completion certificate.

        Args:
            customer_id: Customer ID
            service_details: Service information
            tenant_id: Tenant ID
            template_name: Certificate template

        Returns:
            Tuple of (file_path, metadata)
        """
        try:
            # Prepare certificate data
            certificate_data = {
                "title": "Service Certificate",
                "customer_id": customer_id,
                "service_name": service_details.get("service_name", "Internet Service"),
                "activation_date": service_details.get(
                    "activation_date", datetime.now(timezone.utc).isoformat()
                ),
                "service_level": service_details.get("service_level", "Standard"),
                "technician": service_details.get("technician", "Technical Team"),
                "certificate_number": f"CERT-{customer_id}-{datetime.now().strftime('%Y%m%d')}",
                "company_info": {
                    "name": "DotMac ISP Services",
                    "address": "123 Network Lane, Tech City, TC 12345",
                    "phone": "(555) 123-4567",
                    "email": "support@dotmacisp.com",
                },
                "items": [
                    {
                        "description": service_details.get(
                            "service_name", "Internet Service"
                        ),
                        "specifications": service_details.get(
                            "specifications", "High-speed broadband connection"
                        ),
                        "status": "Activated",
                    }
                ],
            }

            # Generate certificate PDF
            file_path, metadata = self.pdf_generator.generate_invoice(
                certificate_data, template_name=template_name, tenant_id=tenant_id
            )

            # Save to tenant storage
            storage_path = f"certificates/{customer_id}/service_cert_{certificate_data['certificate_number']}.pdf"

            with open(file_path, "rb") as f:
                await self.storage.save_file(
                    storage_path,
                    f,
                    tenant_id,
                    metadata={
                        "type": "service_certificate",
                        "customer_id": customer_id,
                        "service_name": service_details.get("service_name"),
                        "certificate_number": certificate_data["certificate_number"],
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

            logger.info(f"Generated service certificate: {storage_path}")
            return storage_path, metadata

        except Exception as e:
            logger.error(
                f"Error generating service certificate for customer {customer_id}: {e}"
            )
            raise

    def _create_usage_summary(
        self, usage_data: list[ISPServiceUsage]
    ) -> dict[str, Any]:
        """Create usage summary statistics."""
        if not usage_data:
            return {}

        total_cost = sum(usage.total_cost for usage in usage_data)
        services_by_type = {}

        for usage in usage_data:
            service_type = usage.service_type
            if service_type not in services_by_type:
                services_by_type[service_type] = {
                    "count": 0,
                    "total_cost": 0,
                    "total_usage": 0,
                }

            services_by_type[service_type]["count"] += 1
            services_by_type[service_type]["total_cost"] += usage.total_cost
            services_by_type[service_type]["total_usage"] += usage.usage_amount

        return {
            "total_cost": total_cost,
            "total_services": len(usage_data),
            "services_by_type": services_by_type,
            "average_cost": total_cost / len(usage_data) if usage_data else 0,
        }
