"""
Main billing service orchestrator using DRY repository patterns.
Coordinates all billing operations with proper data layer separation.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

from dotmac.application import standard_exception_handler
from dotmac_shared.services.base import BaseService

from .repository import (
    BillingCustomerRepository,
    InvoiceRepository,
    PaymentRepository,
    SubscriptionRepository,
    UsageRecordRepository,
)

logger = logging.getLogger(__name__)


class BillingService(BaseService):
    """Main billing service using DRY repository patterns."""

    def __init__(self, db_session, tenant_id: str):
        super().__init__(db_session, tenant_id)

        # Initialize repositories following DRY patterns
        self.customer_repo = BillingCustomerRepository(db_session, tenant_id)
        self.invoice_repo = InvoiceRepository(db_session, tenant_id)
        self.payment_repo = PaymentRepository(db_session, tenant_id)
        self.subscription_repo = SubscriptionRepository(db_session, tenant_id)
        self.usage_repo = UsageRecordRepository(db_session, tenant_id)

    @standard_exception_handler
    async def get_dashboard_data(self, user_id: str) -> dict[str, Any]:
        """Get billing dashboard summary data using repository pattern."""
        try:
            # Get current period stats using repositories
            current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month_start = (current_month_start + timedelta(days=32)).replace(day=1)

            # Get revenue and invoice data for current month
            revenue, invoice_count = self.invoice_repo.get_revenue_by_period(current_month_start, next_month_start)

            # Get recent invoices and payments
            recent_invoices = self.invoice_repo.list(sort_by="created_at", sort_order="desc", limit=5)
            recent_payments = self.payment_repo.list(sort_by="payment_date", sort_order="desc", limit=5)

            # Get outstanding balance from unpaid invoices
            unpaid_invoices = self.invoice_repo.get_unpaid_invoices()
            outstanding_balance = sum(invoice.amount_due for invoice in unpaid_invoices)

            # Get revenue trend (last 12 months)
            revenue_trend = self.invoice_repo.get_monthly_revenue_trend(12)

            dashboard_data = {
                "current_period": {
                    "revenue": float(revenue),
                    "invoices_sent": invoice_count,
                    "payments_received": len(recent_payments),
                    "outstanding_balance": float(outstanding_balance),
                },
                "recent_invoices": [
                    {
                        "id": str(inv.id),
                        "invoice_number": inv.invoice_number,
                        "amount": float(inv.total_amount),
                        "status": inv.status,
                        "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    }
                    for inv in recent_invoices
                ],
                "recent_payments": [
                    {
                        "id": str(pay.id),
                        "amount": float(pay.amount),
                        "status": pay.status,
                        "payment_date": pay.payment_date.isoformat(),
                    }
                    for pay in recent_payments
                ],
                "revenue_trend": revenue_trend,
                "total_customers": self.customer_repo.count(),
                "active_subscriptions": self.subscription_repo.count({"status": "active"}),
            }

            logger.info(f"Generated billing dashboard for user {user_id}")
            return dashboard_data

        except Exception as e:
            logger.error(f"Error generating billing dashboard: {e}")
            raise

    @standard_exception_handler
    async def generate_revenue_report(self, filters: dict[str, Any], pagination: Any, user_id: str) -> dict[str, Any]:
        """Generate revenue report with filters using repository pattern."""
        try:
            period = filters.get("period", "monthly")

            # Determine date range based on period
            end_date = datetime.now()
            if period == "monthly":
                start_date = end_date - timedelta(days=30)
            elif period == "quarterly":
                start_date = end_date - timedelta(days=90)
            elif period == "yearly":
                start_date = end_date - timedelta(days=365)
            else:
                start_date = filters.get("start_date", end_date - timedelta(days=30))
                end_date = filters.get("end_date", end_date)

            # Get revenue data using repository
            total_revenue, total_invoices = self.invoice_repo.get_revenue_by_period(start_date, end_date)

            # Get revenue trend
            revenue_trend = self.invoice_repo.get_monthly_revenue_trend(12)

            # Get payment method breakdown
            payments = self.payment_repo.list(filters={"payment_date": {"gte": start_date, "lte": end_date}})

            payment_methods = {}
            for payment in payments:
                method = payment.payment_method
                if method not in payment_methods:
                    payment_methods[method] = {"count": 0, "amount": Decimal("0")}
                payment_methods[method]["count"] += 1
                payment_methods[method]["amount"] += payment.amount

            # Get customer analysis
            overdue_customers = self.customer_repo.get_customers_with_overdue_invoices()

            report = {
                "report_type": "revenue",
                "period": period,
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "total_revenue": float(total_revenue),
                "total_invoices": total_invoices,
                "revenue_breakdown": revenue_trend,
                "customer_analysis": {
                    "total_customers": self.customer_repo.count(),
                    "overdue_customers": len(overdue_customers),
                    "active_subscriptions": self.subscription_repo.count({"status": "active"}),
                },
                "payment_methods": [
                    {
                        "method": method,
                        "count": data["count"],
                        "amount": float(data["amount"]),
                    }
                    for method, data in payment_methods.items()
                ],
                "generated_by": user_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Generated revenue report for user {user_id}")
            return report

        except Exception as e:
            logger.error(f"Error generating revenue report: {e}")
            raise

    @standard_exception_handler
    async def generate_invoice_pdf(self, invoice_id: UUID, user_id: str) -> bytes:
        """Generate PDF for invoice using repository pattern."""
        try:
            # Get invoice data using repository
            invoice = self.invoice_repo.get_by_id_or_raise(invoice_id)

            # Use shared PDF generation service
            from dotmac_shared.pdf import PDFService

            pdf_service = PDFService()
            pdf_content = await pdf_service.generate_invoice_pdf(invoice)

            logger.info(f"Generated PDF for invoice {invoice_id} by user {user_id}")
            return pdf_content

        except Exception as e:
            logger.error(f"Error generating invoice PDF: {e}")
            raise

    @standard_exception_handler
    async def upload_invoice_attachment(
        self,
        invoice_id: UUID,
        file: Any,
        max_size: int,
        allowed_types: list[str],
        user_id: str,
    ) -> dict[str, Any]:
        """Upload attachment to invoice using repository pattern."""
        try:
            # Verify invoice exists using repository
            invoice = self.invoice_repo.get_by_id_or_raise(invoice_id)

            # Use shared file storage service
            from dotmac_shared.storage import StorageService

            storage_service = StorageService()
            file_url = await storage_service.upload_file(
                file=file, folder=f"invoices/{invoice.invoice_number}/attachments"
            )

            attachment_info = {
                "id": str(uuid4()),
                "invoice_id": str(invoice_id),
                "invoice_number": invoice.invoice_number,
                "filename": getattr(file, "filename", "unknown"),
                "size": getattr(file, "size", 0),
                "file_url": file_url,
                "uploaded_by": user_id,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Uploaded attachment to invoice {invoice_id}")
            return attachment_info

        except Exception as e:
            logger.error(f"Error uploading invoice attachment: {e}")
            raise


class InvoiceService(BaseService):
    """Invoice management service using DRY repository pattern."""

    def __init__(self, db_session, tenant_id: str):
        super().__init__(db_session, tenant_id)
        self.invoice_repo = InvoiceRepository(db_session, tenant_id)
        self.customer_repo = BillingCustomerRepository(db_session, tenant_id)

    @standard_exception_handler
    async def create(self, data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Create new invoice using repository pattern."""
        try:
            # Validate customer exists
            customer = self.customer_repo.get_by_id_or_raise(UUID(data["customer_id"]))

            # Generate invoice number
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"

            # Prepare invoice data
            invoice_data = {
                "customer_id": UUID(data["customer_id"]),
                "invoice_number": invoice_number,
                "invoice_date": data.get("invoice_date", datetime.now().date()),
                "due_date": data.get("due_date", (datetime.now() + timedelta(days=30)).date()),
                "status": "draft",
                "currency": data.get("currency", "USD"),
                "subtotal": Decimal(str(data.get("subtotal", 0))),
                "tax_amount": Decimal(str(data.get("tax_amount", 0))),
                "total_amount": Decimal(str(data.get("total_amount", 0))),
                "amount_due": Decimal(str(data.get("total_amount", 0))),
                "amount_paid": Decimal("0"),
                "notes": data.get("notes"),
                "terms": data.get("terms"),
                "custom_metadata": data.get("custom_metadata", {}),
            }

            # Create invoice using repository
            invoice = self.invoice_repo.create(invoice_data)

            logger.info(f"Created invoice {invoice.id} for customer {customer.customer_code}")

            # Return serialized invoice data
            return {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "customer_id": str(invoice.customer_id),
                "status": invoice.status,
                "total_amount": float(invoice.total_amount),
                "amount_due": float(invoice.amount_due),
                "created_at": invoice.created_at.isoformat(),
                "due_date": invoice.due_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            raise

    @standard_exception_handler
    async def get_by_id(self, entity_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Get invoice by ID using repository pattern."""
        try:
            invoice = self.invoice_repo.get_by_id(UUID(entity_id))
            if not invoice:
                return None

            return {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "customer_id": str(invoice.customer_id),
                "status": invoice.status,
                "total_amount": float(invoice.total_amount),
                "amount_due": float(invoice.amount_due),
                "amount_paid": float(invoice.amount_paid),
                "invoice_date": invoice.invoice_date.isoformat(),
                "due_date": invoice.due_date.isoformat(),
                "created_at": invoice.created_at.isoformat(),
                "tenant_id": str(invoice.tenant_id) if invoice.tenant_id else None,
            }

        except Exception as e:
            logger.error(f"Error getting invoice {entity_id}: {e}")
            return None

    @standard_exception_handler
    async def list_all(
        self,
        filters: Optional[dict[str, Any]] = None,
        pagination: Any = None,
        user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List invoices with filters using repository pattern."""
        try:
            # Extract pagination parameters
            limit = getattr(pagination, "limit", 50) if pagination else 50
            offset = getattr(pagination, "offset", 0) if pagination else 0

            # Get invoices from repository
            invoices = self.invoice_repo.list(
                filters=filters,
                limit=limit,
                offset=offset,
                sort_by="created_at",
                sort_order="desc",
            )

            return [
                {
                    "id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "customer_id": str(invoice.customer_id),
                    "status": invoice.status,
                    "total_amount": float(invoice.total_amount),
                    "amount_due": float(invoice.amount_due),
                    "invoice_date": invoice.invoice_date.isoformat(),
                    "due_date": invoice.due_date.isoformat(),
                    "created_at": invoice.created_at.isoformat(),
                }
                for invoice in invoices
            ]

        except Exception as e:
            logger.error(f"Error listing invoices: {e}")
            return []


class PaymentService(BaseService):
    """Payment management service using DRY repository pattern."""

    def __init__(self, db_session, tenant_id: str):
        super().__init__(db_session, tenant_id)
        self.payment_repo = PaymentRepository(db_session, tenant_id)
        self.invoice_repo = InvoiceRepository(db_session, tenant_id)
        self.customer_repo = BillingCustomerRepository(db_session, tenant_id)

    @standard_exception_handler
    async def create(self, data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Create new payment using repository pattern."""
        try:
            # Validate customer exists
            customer = self.customer_repo.get_by_id_or_raise(UUID(data["customer_id"]))

            # Validate invoice exists if provided
            if data.get("invoice_id"):
                self.invoice_repo.get_by_id_or_raise(UUID(data["invoice_id"]))

            # Generate payment number
            payment_number = f"PAY-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"

            # Prepare payment data
            payment_data = {
                "customer_id": UUID(data["customer_id"]),
                "invoice_id": UUID(data["invoice_id"]) if data.get("invoice_id") else None,
                "payment_number": payment_number,
                "amount": Decimal(str(data["amount"])),
                "currency": data.get("currency", "USD"),
                "payment_method": data["payment_method"],
                "payment_date": data.get("payment_date", datetime.now()),
                "status": data.get("status", "pending"),
                "notes": data.get("notes"),
                "gateway_transaction_id": data.get("gateway_transaction_id"),
                "custom_metadata": data.get("custom_metadata", {}),
            }

            # Create payment using repository
            payment = self.payment_repo.create(payment_data)

            logger.info(f"Created payment {payment.id} for customer {customer.customer_code}")

            # Return serialized payment data
            return {
                "id": str(payment.id),
                "payment_number": payment.payment_number,
                "customer_id": str(payment.customer_id),
                "invoice_id": str(payment.invoice_id) if payment.invoice_id else None,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "status": payment.status,
                "payment_date": payment.payment_date.isoformat(),
                "created_at": payment.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            raise

    @standard_exception_handler
    async def get_by_id(self, entity_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """Get payment by ID using repository pattern."""
        try:
            payment = self.payment_repo.get_by_id(UUID(entity_id))
            if not payment:
                return None

            return {
                "id": str(payment.id),
                "payment_number": payment.payment_number,
                "customer_id": str(payment.customer_id),
                "invoice_id": str(payment.invoice_id) if payment.invoice_id else None,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "status": payment.status,
                "payment_date": payment.payment_date.isoformat(),
                "created_at": payment.created_at.isoformat(),
                "tenant_id": str(payment.tenant_id) if payment.tenant_id else None,
            }

        except Exception as e:
            logger.error(f"Error getting payment {entity_id}: {e}")
            return None

    @standard_exception_handler
    async def list_all(
        self,
        filters: Optional[dict[str, Any]] = None,
        pagination: Any = None,
        user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List payments with filters using repository pattern."""
        try:
            # Extract pagination parameters
            limit = getattr(pagination, "limit", 50) if pagination else 50
            offset = getattr(pagination, "offset", 0) if pagination else 0

            # Get payments from repository
            payments = self.payment_repo.list(
                filters=filters,
                limit=limit,
                offset=offset,
                sort_by="payment_date",
                sort_order="desc",
            )

            return [
                {
                    "id": str(payment.id),
                    "payment_number": payment.payment_number,
                    "customer_id": str(payment.customer_id),
                    "invoice_id": str(payment.invoice_id) if payment.invoice_id else None,
                    "amount": float(payment.amount),
                    "currency": payment.currency,
                    "payment_method": payment.payment_method,
                    "status": payment.status,
                    "payment_date": payment.payment_date.isoformat(),
                    "created_at": payment.created_at.isoformat(),
                }
                for payment in payments
            ]

        except Exception as e:
            logger.error(f"Error listing payments: {e}")
            return []


# Export all services
__all__ = ["BillingService", "InvoiceService", "PaymentService"]
