"""Invoice service for managing invoices."""

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_isp.modules.billing.models import Invoice, InvoiceStatus


class InvoiceService:
    """Service for invoice operations."""

    def __init__(self, db_session: AsyncSession):
        """Init   operation."""
        self.db_session = db_session

    async def get_invoice_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Get invoice by ID."""
        return await self.db_session.get(Invoice, invoice_id)

    async def get_invoices_by_customer(
        self, customer_id: str, tenant_id: str, status: Optional[InvoiceStatus] = None
    ) -> list[Invoice]:
        """Get all invoices for a customer."""
        query = select(Invoice).where(Invoice.customer_id == customer_id, Invoice.tenant_id == tenant_id)
        if status:
            query = query.where(Invoice.status == status)

        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def mark_invoice_overdue(self, invoice_id: str) -> bool:
        """Mark invoice as overdue."""
        invoice = await self.db_session.get(Invoice, invoice_id)
        if invoice and invoice.status == InvoiceStatus.SENT:
            invoice.status = InvoiceStatus.OVERDUE
            await self.db_session.commit()
            return True
        return False

    async def calculate_invoice_totals(self, invoice: Invoice) -> None:
        """Recalculate invoice totals based on line items."""
        subtotal = sum(item.line_total for item in invoice.line_items)
        tax_amount = sum(item.tax_amount or Decimal("0.00") for item in invoice.line_items)
        discount_amount = invoice.discount_amount or Decimal("0.00")

        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total_amount = subtotal + tax_amount - discount_amount
