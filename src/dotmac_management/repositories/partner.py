"""
Partner repository providing async CRUD operations and actions.
"""

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.partner import Partner
from .base import BaseRepository


class PartnerRepository(BaseRepository[Partner]):
    """Repository for partner management."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Partner)

    async def list_partners(
        self,
        skip: int = 0,
        limit: int = 50,
        q: Optional[str] = None,
        status: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> Tuple[List[Partner], int]:
        """List partners with optional filters and total count."""
        query = select(Partner).where(Partner.is_deleted == False)

        if status:
            query = query.where(Partner.status == status)
        if tier:
            query = query.where(Partner.tier == tier)
        if q:
            like = f"%{q}%"
            query = query.where(
                or_(
                    Partner.company_name.ilike(like),
                    Partner.contact_name.ilike(like),
                    Partner.contact_email.ilike(like),
                    Partner.partner_code.ilike(like),
                )
            )

        # Total count
        total_result = await self.db.execute(query.with_only_columns(Partner.id))
        total = len(total_result.scalars().all())

        # Page
        page_query = query.order_by(Partner.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(page_query)
        items = result.scalars().all()
        return items, total

    async def approve(self, partner_id: UUID) -> Optional[Partner]:
        partner = await self.get_by_id(partner_id)
        if not partner:
            return None
        partner.status = "active"
        await self.db.flush()
        await self.db.refresh(partner)
        return partner

    async def suspend(self, partner_id: UUID, reason: Optional[str] = None) -> Optional[Partner]:
        partner = await self.get_by_id(partner_id)
        if not partner:
            return None
        partner.status = "suspended"
        # Optionally store reason in metadata_json
        if reason:
            meta = dict(partner.metadata_json or {})
            meta["suspend_reason"] = reason
            partner.metadata_json = meta
        await self.db.flush()
        await self.db.refresh(partner)
        return partner

    async def update_tier(self, partner_id: UUID, tier: str) -> Optional[Partner]:
        partner = await self.get_by_id(partner_id)
        if not partner:
            return None
        partner.tier = tier
        await self.db.flush()
        await self.db.refresh(partner)
        return partner

