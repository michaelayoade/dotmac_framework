"""
Repository layer for ISP reseller operations.
Provides data access layer for reseller management.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from dotmac_shared.repositories.base import BaseRepository
from dotmac_shared.schemas import PaginatedResponse

from .models import (
    Commission,
    Reseller,
    ResellerAgreement,
    ResellerContact,
    ResellerOpportunity,
    ResellerPerformance,
    ResellerTerritory,
    ResellerType,
    ResellerTier,
    CommissionStatus,
)


class ResellerRepository(BaseRepository[Reseller]):
    """Repository for reseller operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Reseller)

    async def create_reseller(
        self, tenant_id: str, reseller_data: Dict[str, Any]
    ) -> Reseller:
        """Create a new reseller."""
        reseller = Reseller(tenant_id=tenant_id, **reseller_data)
        self.session.add(reseller)
        await self.session.commit()
        await self.session.refresh(reseller)
        return reseller

    async def get_reseller_with_details(
        self, tenant_id: str, reseller_id: str
    ) -> Optional[Reseller]:
        """Get reseller with all related details."""
        stmt = (
            select(Reseller)
            .options(
                selectinload(Reseller.contacts),
                selectinload(Reseller.opportunities),
                selectinload(Reseller.commissions),
                selectinload(Reseller.territories),
                selectinload(Reseller.agreements),
                selectinload(Reseller.performance_records),
            )
            .where(
                and_(
                    Reseller.tenant_id == tenant_id,
                    Reseller.reseller_id == reseller_id,
                    Reseller.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_resellers(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[Reseller]:
        """List resellers with filtering and pagination."""
        stmt = select(Reseller).where(
            and_(Reseller.tenant_id == tenant_id, Reseller.deleted_at.is_(None))
        )

        # Apply filters
        if filters:
            if "reseller_type" in filters:
                stmt = stmt.where(Reseller.reseller_type == filters["reseller_type"])
            if "reseller_tier" in filters:
                stmt = stmt.where(Reseller.reseller_tier == filters["reseller_tier"])
            if "status" in filters:
                stmt = stmt.where(Reseller.status == filters["status"])
            if "territory" in filters:
                # Join with territories table to filter by territory
                stmt = stmt.join(ResellerTerritory).where(
                    ResellerTerritory.territory == filters["territory"]
                )

        # Apply search
        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Reseller.company_name.ilike(search_pattern),
                    Reseller.contact_email.ilike(search_pattern),
                    Reseller.contact_person.ilike(search_pattern),
                )
            )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar()

        # Apply pagination and ordering
        stmt = stmt.order_by(desc(Reseller.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        items = result.scalars().all()

        return PaginatedResponse(items=list(items), total=total, limit=limit, offset=offset)

    async def get_resellers_by_territory(
        self, tenant_id: str, territory: str
    ) -> List[Reseller]:
        """Get all resellers assigned to a specific territory."""
        stmt = (
            select(Reseller)
            .join(ResellerTerritory)
            .where(
                and_(
                    Reseller.tenant_id == tenant_id,
                    ResellerTerritory.territory == territory,
                    ResellerTerritory.is_active == True,
                    Reseller.deleted_at.is_(None),
                )
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_resellers_by_type(
        self, tenant_id: str, reseller_type: ResellerType
    ) -> List[Reseller]:
        """Get all resellers of a specific type."""
        stmt = select(Reseller).where(
            and_(
                Reseller.tenant_id == tenant_id,
                Reseller.reseller_type == reseller_type,
                Reseller.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ResellerContactRepository(BaseRepository[ResellerContact]):
    """Repository for reseller contact operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ResellerContact)

    async def create_contact(
        self, tenant_id: str, reseller_id: str, contact_data: Dict[str, Any]
    ) -> ResellerContact:
        """Create a new reseller contact."""
        contact = ResellerContact(
            tenant_id=tenant_id, reseller_id=reseller_id, **contact_data
        )
        self.session.add(contact)
        await self.session.commit()
        await self.session.refresh(contact)
        return contact

    async def get_contacts_by_reseller(
        self, tenant_id: str, reseller_id: str
    ) -> List[ResellerContact]:
        """Get all contacts for a reseller."""
        stmt = select(ResellerContact).where(
            and_(
                ResellerContact.tenant_id == tenant_id,
                ResellerContact.reseller_id == reseller_id,
                ResellerContact.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ResellerOpportunityRepository(BaseRepository[ResellerOpportunity]):
    """Repository for reseller opportunity operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ResellerOpportunity)

    async def assign_opportunity(
        self, tenant_id: str, reseller_id: str, opportunity_data: Dict[str, Any]
    ) -> ResellerOpportunity:
        """Assign an opportunity to a reseller."""
        opportunity = ResellerOpportunity(
            tenant_id=tenant_id, reseller_id=reseller_id, **opportunity_data
        )
        self.session.add(opportunity)
        await self.session.commit()
        await self.session.refresh(opportunity)
        return opportunity

    async def get_opportunities_by_reseller(
        self, tenant_id: str, reseller_id: str, status: Optional[str] = None
    ) -> List[ResellerOpportunity]:
        """Get opportunities assigned to a reseller."""
        stmt = select(ResellerOpportunity).where(
            and_(
                ResellerOpportunity.tenant_id == tenant_id,
                ResellerOpportunity.reseller_id == reseller_id,
            )
        )
        if status:
            stmt = stmt.where(ResellerOpportunity.status == status)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class CommissionRepository(BaseRepository[Commission]):
    """Repository for commission operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Commission)

    async def create_commission(
        self, tenant_id: str, commission_data: Dict[str, Any]
    ) -> Commission:
        """Create a new commission record."""
        commission = Commission(tenant_id=tenant_id, **commission_data)
        self.session.add(commission)
        await self.session.commit()
        await self.session.refresh(commission)
        return commission

    async def get_commissions_by_reseller(
        self,
        tenant_id: str,
        reseller_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[CommissionStatus] = None,
    ) -> List[Commission]:
        """Get commissions for a reseller with optional date and status filtering."""
        stmt = select(Commission).where(
            and_(
                Commission.tenant_id == tenant_id,
                Commission.reseller_id == reseller_id,
            )
        )

        if start_date:
            stmt = stmt.where(Commission.calculated_date >= start_date)
        if end_date:
            stmt = stmt.where(Commission.calculated_date <= end_date)
        if status:
            stmt = stmt.where(Commission.payment_status == status)

        stmt = stmt.order_by(desc(Commission.calculated_date))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_commission_amount(
        self,
        tenant_id: str,
        reseller_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[CommissionStatus] = None,
    ) -> Decimal:
        """Get total commission amount for a reseller."""
        stmt = select(func.sum(Commission.commission_amount)).where(
            and_(
                Commission.tenant_id == tenant_id,
                Commission.reseller_id == reseller_id,
            )
        )

        if start_date:
            stmt = stmt.where(Commission.calculated_date >= start_date)
        if end_date:
            stmt = stmt.where(Commission.calculated_date <= end_date)
        if status:
            stmt = stmt.where(Commission.payment_status == status)

        result = await self.session.execute(stmt)
        total = result.scalar()
        return total or Decimal("0.00")

    async def update_commission_status(
        self, tenant_id: str, commission_id: str, status: CommissionStatus
    ) -> Optional[Commission]:
        """Update commission payment status."""
        commission = await self.get_by_id(tenant_id, commission_id)
        if commission:
            commission.payment_status = status
            if status == CommissionStatus.PAID:
                commission.paid_date = datetime.utcnow().date()
            await self.session.commit()
            await self.session.refresh(commission)
        return commission


class ResellerPerformanceRepository(BaseRepository[ResellerPerformance]):
    """Repository for reseller performance operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ResellerPerformance)

    async def create_performance_record(
        self, tenant_id: str, performance_data: Dict[str, Any]
    ) -> ResellerPerformance:
        """Create a new performance record."""
        performance = ResellerPerformance(tenant_id=tenant_id, **performance_data)
        self.session.add(performance)
        await self.session.commit()
        await self.session.refresh(performance)
        return performance

    async def get_performance_by_period(
        self,
        tenant_id: str,
        reseller_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[ResellerPerformance]:
        """Get performance records for a reseller by period."""
        stmt = select(ResellerPerformance).where(
            and_(
                ResellerPerformance.tenant_id == tenant_id,
                ResellerPerformance.reseller_id == reseller_id,
            )
        )

        if start_date:
            stmt = stmt.where(ResellerPerformance.period_start >= start_date)
        if end_date:
            stmt = stmt.where(ResellerPerformance.period_end <= end_date)

        stmt = stmt.order_by(desc(ResellerPerformance.period_start))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ResellerTerritoryRepository(BaseRepository[ResellerTerritory]):
    """Repository for reseller territory operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ResellerTerritory)

    async def assign_territory(
        self, tenant_id: str, reseller_id: str, territory: str
    ) -> ResellerTerritory:
        """Assign a territory to a reseller."""
        territory_assignment = ResellerTerritory(
            tenant_id=tenant_id, reseller_id=reseller_id, territory=territory
        )
        self.session.add(territory_assignment)
        await self.session.commit()
        await self.session.refresh(territory_assignment)
        return territory_assignment

    async def get_territories_by_reseller(
        self, tenant_id: str, reseller_id: str, active_only: bool = True
    ) -> List[ResellerTerritory]:
        """Get territories assigned to a reseller."""
        stmt = select(ResellerTerritory).where(
            and_(
                ResellerTerritory.tenant_id == tenant_id,
                ResellerTerritory.reseller_id == reseller_id,
            )
        )
        if active_only:
            stmt = stmt.where(ResellerTerritory.is_active == True)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def deactivate_territory(
        self, tenant_id: str, reseller_id: str, territory: str
    ) -> Optional[ResellerTerritory]:
        """Deactivate a territory assignment."""
        stmt = select(ResellerTerritory).where(
            and_(
                ResellerTerritory.tenant_id == tenant_id,
                ResellerTerritory.reseller_id == reseller_id,
                ResellerTerritory.territory == territory,
            )
        )
        result = await self.session.execute(stmt)
        territory_assignment = result.scalar_one_or_none()

        if territory_assignment:
            territory_assignment.is_active = False
            await self.session.commit()
            await self.session.refresh(territory_assignment)

        return territory_assignment


class ResellerAgreementRepository(BaseRepository[ResellerAgreement]):
    """Repository for reseller agreement operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ResellerAgreement)

    async def create_agreement(
        self, tenant_id: str, reseller_id: str, agreement_data: Dict[str, Any]
    ) -> ResellerAgreement:
        """Create a new reseller agreement."""
        agreement = ResellerAgreement(
            tenant_id=tenant_id, reseller_id=reseller_id, **agreement_data
        )
        self.session.add(agreement)
        await self.session.commit()
        await self.session.refresh(agreement)
        return agreement

    async def get_active_agreement(
        self, tenant_id: str, reseller_id: str
    ) -> Optional[ResellerAgreement]:
        """Get the active agreement for a reseller."""
        current_date = datetime.utcnow().date()
        stmt = select(ResellerAgreement).where(
            and_(
                ResellerAgreement.tenant_id == tenant_id,
                ResellerAgreement.reseller_id == reseller_id,
                ResellerAgreement.start_date <= current_date,
                or_(
                    ResellerAgreement.end_date.is_(None),
                    ResellerAgreement.end_date >= current_date,
                ),
                ResellerAgreement.is_active == True,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_agreements_by_reseller(
        self, tenant_id: str, reseller_id: str
    ) -> List[ResellerAgreement]:
        """Get all agreements for a reseller."""
        stmt = (
            select(ResellerAgreement)
            .where(
                and_(
                    ResellerAgreement.tenant_id == tenant_id,
                    ResellerAgreement.reseller_id == reseller_id,
                )
            )
            .order_by(desc(ResellerAgreement.start_date))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())