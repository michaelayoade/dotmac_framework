"""DEPRECATED: Billing service - use modules/billing/service.py instead.

This file has been consolidated into the main billing service.
Use: from dotmac_isp.modules.billing.service import BillingService

This implementation will be removed in a future version.
"""

import warnings
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.modules.billing.models import (
    Invoice, InvoiceLineItem, Payment, Subscription, BillingAccount,
    InvoiceStatus, PaymentStatus, PaymentMethod, BillingCycle
)

warnings.warn(
    "This BillingService is deprecated. Use dotmac_isp.modules.billing.service.BillingService instead.",
    DeprecationWarning,
    stacklevel=2
)

class BillingService:
    """DEPRECATED: Use main BillingService instead."""
    
    def __init__(self, db_session: AsyncSession):
        """  Init   operation."""
        warnings.warn(
            "This BillingService is deprecated. Use dotmac_isp.modules.billing.service.BillingService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.db_session = db_session
    
    async def create_invoice(
        self,
        customer_id: str,
        tenant_id: str,
        line_items: List[Dict[str, Any]],
        due_date: Optional[date] = None
    ) -> Invoice:
        """DEPRECATED: Use main BillingService instead."""
        warnings.warn(
            "This method is deprecated. Use dotmac_isp.modules.billing.service.BillingService.create_invoice instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Redirect to main service (this would need proper implementation)
        raise NotImplementedError(
            "Use dotmac_isp.modules.billing.service.BillingService instead"
        )
    
    async def process_payment(
        self,
        invoice_id: str,
        amount: Decimal,
        payment_method: PaymentMethod,
        tenant_id: str,
        reference_number: Optional[str] = None
    ) -> Payment:
        """DEPRECATED: Use main BillingService instead."""
        warnings.warn(
            "This method is deprecated. Use dotmac_isp.modules.billing.service.PaymentService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Redirect to main service 
        raise NotImplementedError(
            "Use dotmac_isp.modules.billing.service.PaymentService instead"
        )
    
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