"""Payment service for managing payments."""

from typing import List, Optional
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dotmac_isp.modules.billing.models import Payment, PaymentStatus, PaymentMethod


class PaymentService:
    """Service for payment operations."""
    
    def __init__(self, db_session: AsyncSession):
        """  Init   operation."""
        self.db_session = db_session
    
    async def get_payment_by_id(self, payment_id: str) -> Optional[Payment]:
        """Get payment by ID."""
        return await self.db_session.get(Payment, payment_id)
    
    async def get_payments_by_invoice(
        self, 
        invoice_id: str,
        tenant_id: str
    ) -> List[Payment]:
        """Get all payments for an invoice."""
        query = select(Payment).where(
            Payment.invoice_id == invoice_id,
            Payment.tenant_id == tenant_id
        )
        
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def update_payment_status(
        self, 
        payment_id: str, 
        status: PaymentStatus,
        transaction_id: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> bool:
        """Update payment status."""
        payment = await self.db_session.get(Payment, payment_id)
        if payment:
            payment.status = status
            if transaction_id:
                payment.transaction_id = transaction_id
            if failure_reason:
                payment.failure_reason = failure_reason
            
            await self.db_session.commit()
            return True
        return False
    
    async def process_refund(
        self,
        original_payment_id: str,
        refund_amount: Decimal,
        tenant_id: str,
        reason: Optional[str] = None
    ) -> Optional[Payment]:
        """Process a refund for a payment."""
        original_payment = await self.db_session.get(Payment, original_payment_id)
        if not original_payment:
            return None
        
        refund_payment = Payment(
            payment_number=self._generate_payment_number(),
            invoice_id=original_payment.invoice_id,
            tenant_id=tenant_id,
            amount=-refund_amount,  # Negative amount for refunds
            payment_method=original_payment.payment_method,
            status=PaymentStatus.REFUNDED,
            reference_number=f"REFUND-{original_payment.payment_number}",
            notes=reason
        )
        
        self.db_session.add(refund_payment)
        await self.db_session.commit()
        await self.db_session.refresh(refund_payment)
        
        return refund_payment
    
    def _generate_payment_number(self) -> str:
        """Generate unique payment number."""
        import uuid
        from datetime import datetime
        return f"PAY-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"