"""Credit service for managing credits and credit notes."""

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_isp.modules.billing.models import CreditNote, Invoice


class CreditService:
    """Service for credit management and credit note operations."""

    def __init__(self, db_session: AsyncSession):
        """Init   operation."""
        self.db_session = db_session

    async def create_credit_note(
        self,
        customer_id: str,
        tenant_id: str,
        amount: Decimal,
        reason: str,
        invoice_id: Optional[str] = None,
    ) -> CreditNote:
        """Create a new credit note."""
        credit_note = CreditNote(
            credit_note_number=self._generate_credit_note_number(),
            customer_id=customer_id,
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            amount=amount,
            reason=reason,
            credit_date=date.today(),
        )
        self.db_session.add(credit_note)
        await self.db_session.commit()
        await self.db_session.refresh(credit_note)

        return credit_note

    async def apply_credit_note(self, credit_note_id: str, invoice_id: str) -> bool:
        """Apply a credit note to an invoice."""
        credit_note = await self.db_session.get(CreditNote, credit_note_id)
        invoice = await self.db_session.get(Invoice, invoice_id)

        if not credit_note or not invoice or credit_note.is_applied:
            return False

        # Apply credit to invoice
        if invoice.total_amount >= credit_note.amount:
            invoice.total_amount -= credit_note.amount
            credit_note.is_applied = True
            credit_note.applied_date = date.today()

            await self.db_session.commit()
            return True

        return False

    async def get_credit_notes_by_customer(
        self, customer_id: str, tenant_id: str, unapplied_only: bool = False
    ) -> list[CreditNote]:
        """Get all credit notes for a customer."""
        query = select(CreditNote).where(
            CreditNote.customer_id == customer_id, CreditNote.tenant_id == tenant_id
        )
        if unapplied_only:
            query = query.where(CreditNote.is_applied is False)

        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def get_customer_credit_balance(
        self, customer_id: str, tenant_id: str
    ) -> Decimal:
        """Get total available credit balance for a customer."""
        query = select(CreditNote).where(
            CreditNote.customer_id == customer_id,
            CreditNote.tenant_id == tenant_id,
            CreditNote.is_applied is False,
        )
        result = await self.db_session.execute(query)
        credit_notes = result.scalars().all()

        return sum(note.amount for note in credit_notes)

    def _generate_credit_note_number(self) -> str:
        """Generate unique credit note number."""
        import uuid
        from datetime import datetime, timezone

        return f"CN-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4()[:8].upper())}"
