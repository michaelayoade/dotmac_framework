"""Billing service for managing billing operations."""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.modules.billing.models import (
    Invoice, InvoiceLineItem, Payment, Subscription, BillingAccount,
    InvoiceStatus, PaymentStatus, PaymentMethod, BillingCycle
)


class BillingService:
    """Service for billing operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def create_invoice(
        self,
        customer_id: str,
        tenant_id: str,
        line_items: List[Dict[str, Any]],
        due_date: Optional[date] = None
    ) -> Invoice:
        """Create a new invoice."""
        invoice = Invoice(
            customer_id=customer_id,
            tenant_id=tenant_id,
            invoice_number=self._generate_invoice_number(),
            invoice_date=date.today(),
            due_date=due_date or date.today(),
            status=InvoiceStatus.DRAFT
        )
        
        # Add line items
        subtotal = Decimal('0.00')
        tax_total = Decimal('0.00')
        
        for item_data in line_items:
            line_item = InvoiceLineItem(
                invoice_id=invoice.id,
                tenant_id=tenant_id,
                description=item_data['description'],
                quantity=Decimal(str(item_data['quantity'])),
                unit_price=Decimal(str(item_data['unit_price'])),
                line_total=Decimal(str(item_data['quantity'])) * Decimal(str(item_data['unit_price']))
            )
            
            # Calculate tax if applicable
            if 'tax_rate' in item_data and item_data['tax_rate']:
                tax_rate = Decimal(str(item_data['tax_rate']))
                line_item.tax_rate = tax_rate
                line_item.tax_amount = line_item.line_total * tax_rate
                tax_total += line_item.tax_amount
            
            invoice.line_items.append(line_item)
            subtotal += line_item.line_total
        
        invoice.subtotal = subtotal
        invoice.tax_amount = tax_total
        invoice.total_amount = subtotal + tax_total
        
        self.db_session.add(invoice)
        await self.db_session.commit()
        await self.db_session.refresh(invoice)
        
        return invoice
    
    async def process_payment(
        self,
        invoice_id: str,
        amount: Decimal,
        payment_method: PaymentMethod,
        tenant_id: str,
        reference_number: Optional[str] = None
    ) -> Payment:
        """Process a payment for an invoice."""
        payment = Payment(
            payment_number=self._generate_payment_number(),
            invoice_id=invoice_id,
            tenant_id=tenant_id,
            amount=amount,
            payment_method=payment_method,
            status=PaymentStatus.PENDING,
            reference_number=reference_number
        )
        
        self.db_session.add(payment)
        
        # Update invoice paid amount
        invoice = await self.db_session.get(Invoice, invoice_id)
        if invoice:
            invoice.paid_amount = (invoice.paid_amount or Decimal('0.00')) + amount
            if invoice.paid_amount >= invoice.total_amount:
                invoice.status = InvoiceStatus.PAID
                invoice.paid_date = date.today()
        
        await self.db_session.commit()
        await self.db_session.refresh(payment)
        
        return payment
    
    async def create_subscription(
        self,
        customer_id: str,
        service_instance_id: str,
        billing_cycle: BillingCycle,
        amount: Decimal,
        tenant_id: str,
        start_date: Optional[date] = None
    ) -> Subscription:
        """Create a new subscription."""
        subscription = Subscription(
            customer_id=customer_id,
            service_instance_id=service_instance_id,
            tenant_id=tenant_id,
            billing_cycle=billing_cycle,
            amount=amount,
            start_date=start_date or date.today(),
            next_billing_date=self._calculate_next_billing_date(
                start_date or date.today(), billing_cycle
            )
        )
        
        self.db_session.add(subscription)
        await self.db_session.commit()
        await self.db_session.refresh(subscription)
        
        return subscription
    
    async def get_customer_balance(self, customer_id: str, tenant_id: str) -> Dict[str, Decimal]:
        """Get customer's current balance."""
        # This would typically query invoices and payments
        return {
            "total_invoiced": Decimal('0.00'),
            "total_paid": Decimal('0.00'),
            "balance_due": Decimal('0.00')
        }
    
    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        import uuid
        return f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    def _generate_payment_number(self) -> str:
        """Generate unique payment number.""" 
        import uuid
        return f"PAY-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    def _calculate_next_billing_date(self, start_date: date, cycle: BillingCycle) -> date:
        """Calculate next billing date based on cycle."""
        from dateutil.relativedelta import relativedelta
        
        if cycle == BillingCycle.MONTHLY:
            return start_date + relativedelta(months=1)
        elif cycle == BillingCycle.QUARTERLY:
            return start_date + relativedelta(months=3)
        elif cycle == BillingCycle.ANNUALLY:
            return start_date + relativedelta(years=1)
        else:  # ONE_TIME
            return start_date