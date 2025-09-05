"""
Repository layer for reseller data access
Provides clean data access patterns with proper error handling
"""

from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .db_models import (
    ApplicationStatus,
    Reseller,
    ResellerApplication,
    ResellerCommission,
    ResellerCustomer,
    ResellerOpportunity,
    ResellerStatus,
)


class BaseRepository:
    """Base repository with common database operations"""

    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id

    async def commit(self):
        """Commit the current transaction"""
        await self.db.commit()

    async def rollback(self):
        """Rollback the current transaction"""
        await self.db.rollback()

    async def refresh(self, instance):
        """Refresh an instance from the database"""
        await self.db.refresh(instance)


class ResellerApplicationRepository(BaseRepository):
    """Repository for reseller application data access"""

    async def create(self, application_data: dict[str, Any]) -> ResellerApplication:
        """Create a new reseller application"""
        if self.tenant_id:
            application_data["tenant_id"] = self.tenant_id

        application = ResellerApplication(**application_data)
        self.db.add(application)
        await self.db.flush()
        await self.db.refresh(application)
        return application

    async def get_by_id(self, application_id: str) -> Optional[ResellerApplication]:
        """Get application by application_id"""
        query = select(ResellerApplication).where(ResellerApplication.application_id == application_id)
        if self.tenant_id:
            query = query.where(ResellerApplication.tenant_id == self.tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[ResellerApplication]:
        """Get application by contact email"""
        query = select(ResellerApplication).where(ResellerApplication.contact_email == email)
        if self.tenant_id:
            query = query.where(ResellerApplication.tenant_id == self.tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_status(
        self, status: ApplicationStatus, limit: int = 50, offset: int = 0
    ) -> list[ResellerApplication]:
        """List applications by status"""
        query = select(ResellerApplication).where(ResellerApplication.status == status)
        if self.tenant_id:
            query = query.where(ResellerApplication.tenant_id == self.tenant_id)

        query = query.order_by(desc(ResellerApplication.submitted_at))
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_pending_review(self, limit: int = 50, offset: int = 0) -> list[ResellerApplication]:
        """List applications pending review"""
        return await self.list_by_status(ApplicationStatus.SUBMITTED, limit, offset)

    async def update_status(
        self,
        application_id: str,
        status: ApplicationStatus,
        reviewer_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[ResellerApplication]:
        """Update application status"""
        application = await self.get_by_id(application_id)
        if not application:
            return None

        application.status = status
        application.reviewed_at = datetime.now(timezone.utc)
        if reviewer_id:
            application.reviewed_by = reviewer_id
        if notes:
            application.review_notes = notes

        if status in [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]:
            application.decision_date = date.today()

        await self.db.flush()
        await self.db.refresh(application)
        return application

    async def add_communication_log(
        self, application_id: str, communication: dict[str, Any]
    ) -> Optional[ResellerApplication]:
        """Add communication entry to application log"""
        application = await self.get_by_id(application_id)
        if not application:
            return None

        if not application.communication_log:
            application.communication_log = []

        communication["timestamp"] = datetime.now(timezone.utc).isoformat()
        application.communication_log.append(communication)

        await self.db.flush()
        await self.db.refresh(application)
        return application

    async def search(
        self, search_term: str, status: Optional[ApplicationStatus] = None, limit: int = 50, offset: int = 0
    ) -> list[ResellerApplication]:
        """Search applications by company name, contact name, or email"""
        query = select(ResellerApplication)

        # Search conditions
        search_conditions = [
            ResellerApplication.company_name.ilike(f"%{search_term}%"),
            ResellerApplication.contact_name.ilike(f"%{search_term}%"),
            ResellerApplication.contact_email.ilike(f"%{search_term}%"),
        ]
        query = query.where(func.or_(*search_conditions))

        if status:
            query = query.where(ResellerApplication.status == status)

        if self.tenant_id:
            query = query.where(ResellerApplication.tenant_id == self.tenant_id)

        query = query.order_by(desc(ResellerApplication.submitted_at))
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()


class ResellerRepository(BaseRepository):
    """Repository for reseller data access"""

    async def create(self, reseller_data: dict[str, Any]) -> Reseller:
        """Create a new reseller"""
        if self.tenant_id:
            reseller_data["tenant_id"] = self.tenant_id

        reseller = Reseller(**reseller_data)
        self.db.add(reseller)
        await self.db.flush()
        await self.db.refresh(reseller)
        return reseller

    async def get_by_id(self, reseller_id: str) -> Optional[Reseller]:
        """Get reseller by reseller_id"""
        query = select(Reseller).where(Reseller.reseller_id == reseller_id)
        if self.tenant_id:
            query = query.where(Reseller.tenant_id == self.tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_uuid(self, uuid_id: UUID) -> Optional[Reseller]:
        """Get reseller by UUID"""
        query = select(Reseller).where(Reseller.id == uuid_id)
        if self.tenant_id:
            query = query.where(Reseller.tenant_id == self.tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_active(self, limit: int = 50, offset: int = 0) -> list[Reseller]:
        """List active resellers"""
        query = select(Reseller).where(Reseller.status == ResellerStatus.ACTIVE)
        if self.tenant_id:
            query = query.where(Reseller.tenant_id == self.tenant_id)

        query = query.order_by(Reseller.company_name)
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_by_status(self, status: ResellerStatus, limit: int = 50, offset: int = 0) -> list[Reseller]:
        """List resellers by status"""
        query = select(Reseller).where(Reseller.status == status)
        if self.tenant_id:
            query = query.where(Reseller.tenant_id == self.tenant_id)

        query = query.order_by(Reseller.company_name)
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_metrics(self, reseller_id: str, metrics: dict[str, Any]) -> Optional[Reseller]:
        """Update reseller performance metrics"""
        reseller = await self.get_by_id(reseller_id)
        if not reseller:
            return None

        for key, value in metrics.items():
            if hasattr(reseller, key):
                setattr(reseller, key, value)

        await self.db.flush()
        await self.db.refresh(reseller)
        return reseller

    async def get_with_relationships(self, reseller_id: str) -> Optional[Reseller]:
        """Get reseller with loaded relationships"""
        query = (
            select(Reseller)
            .options(
                selectinload(Reseller.customers),
                selectinload(Reseller.opportunities),
                selectinload(Reseller.commissions),
            )
            .where(Reseller.reseller_id == reseller_id)
        )

        if self.tenant_id:
            query = query.where(Reseller.tenant_id == self.tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_dashboard_data(self, reseller_id: str) -> Optional[dict[str, Any]]:
        """Get comprehensive dashboard data for reseller"""
        reseller = await self.get_with_relationships(reseller_id)
        if not reseller:
            return None

        # Calculate derived metrics
        return {
            "reseller": {
                "id": reseller.reseller_id,
                "company_name": reseller.company_name,
                "status": reseller.status,
                "total_customers": reseller.total_customers,
                "active_customers": reseller.active_customers,
                "monthly_sales": float(reseller.monthly_sales or 0),
                "ytd_sales": float(reseller.ytd_sales or 0),
                "lifetime_sales": float(reseller.lifetime_sales or 0),
            },
            "recent_customers": len([c for c in reseller.customers if c.relationship_status == "active"]),
            "active_opportunities": len([o for o in reseller.opportunities if o.is_active]),
            "pending_commissions": len([c for c in reseller.commissions if c.payment_status == "pending"]),
            "commission_total_pending": sum(
                float(c.commission_amount) for c in reseller.commissions if c.payment_status == "pending"
            ),
        }


class ResellerCustomerRepository(BaseRepository):
    """Repository for reseller-customer relationships"""

    async def assign_customer(
        self, reseller_id: UUID, customer_id: UUID, assignment_data: dict[str, Any]
    ) -> ResellerCustomer:
        """Assign a customer to a reseller"""
        if self.tenant_id:
            assignment_data["tenant_id"] = self.tenant_id

        assignment_data.update({"reseller_id": reseller_id, "customer_id": customer_id})

        assignment = ResellerCustomer(**assignment_data)
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def get_by_customer(self, customer_id: UUID) -> Optional[ResellerCustomer]:
        """Get reseller assignment for a customer"""
        query = select(ResellerCustomer).where(
            and_(ResellerCustomer.customer_id == customer_id, ResellerCustomer.relationship_status == "active")
        )
        if self.tenant_id:
            query = query.where(ResellerCustomer.tenant_id == self.tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_for_reseller(self, reseller_id: UUID, limit: int = 50, offset: int = 0) -> list[ResellerCustomer]:
        """List customers for a reseller"""
        query = select(ResellerCustomer).where(ResellerCustomer.reseller_id == reseller_id)
        if self.tenant_id:
            query = query.where(ResellerCustomer.tenant_id == self.tenant_id)

        query = query.order_by(desc(ResellerCustomer.relationship_start_date))
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()


class ResellerOpportunityRepository(BaseRepository):
    """Repository for reseller opportunities"""

    async def create(self, opportunity_data: dict[str, Any]) -> ResellerOpportunity:
        """Create a new opportunity"""
        if self.tenant_id:
            opportunity_data["tenant_id"] = self.tenant_id

        opportunity = ResellerOpportunity(**opportunity_data)
        self.db.add(opportunity)
        await self.db.flush()
        await self.db.refresh(opportunity)
        return opportunity

    async def get_by_id(self, opportunity_id: str) -> Optional[ResellerOpportunity]:
        """Get opportunity by ID"""
        query = select(ResellerOpportunity).where(ResellerOpportunity.opportunity_id == opportunity_id)
        if self.tenant_id:
            query = query.where(ResellerOpportunity.tenant_id == self.tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_for_reseller(
        self, reseller_id: UUID, stage: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> list[ResellerOpportunity]:
        """List opportunities for a reseller"""
        query = select(ResellerOpportunity).where(ResellerOpportunity.reseller_id == reseller_id)

        if stage:
            query = query.where(ResellerOpportunity.stage == stage)

        if self.tenant_id:
            query = query.where(ResellerOpportunity.tenant_id == self.tenant_id)

        query = query.order_by(desc(ResellerOpportunity.created_at))
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_stage(
        self, opportunity_id: str, stage: str, notes: Optional[str] = None
    ) -> Optional[ResellerOpportunity]:
        """Update opportunity stage"""
        opportunity = await self.get_by_id(opportunity_id)
        if not opportunity:
            return None

        opportunity.stage = stage
        if notes:
            opportunity.notes = notes

        if stage in ["closed_won", "closed_lost"]:
            opportunity.actual_close_date = date.today()

        await self.db.flush()
        await self.db.refresh(opportunity)
        return opportunity


class ResellerCommissionRepository(BaseRepository):
    """Repository for reseller commissions"""

    async def create(self, commission_data: dict[str, Any]) -> ResellerCommission:
        """Create a new commission record"""
        if self.tenant_id:
            commission_data["tenant_id"] = self.tenant_id

        commission = ResellerCommission(**commission_data)
        self.db.add(commission)
        await self.db.flush()
        await self.db.refresh(commission)
        return commission

    async def get_by_id(self, commission_id: str) -> Optional[ResellerCommission]:
        """Get commission by ID"""
        query = select(ResellerCommission).where(ResellerCommission.commission_id == commission_id)
        if self.tenant_id:
            query = query.where(ResellerCommission.tenant_id == self.tenant_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_pending_for_reseller(
        self, reseller_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[ResellerCommission]:
        """List pending commissions for a reseller"""
        query = select(ResellerCommission).where(
            and_(ResellerCommission.reseller_id == reseller_id, ResellerCommission.payment_status == "pending")
        )
        if self.tenant_id:
            query = query.where(ResellerCommission.tenant_id == self.tenant_id)

        query = query.order_by(ResellerCommission.payment_due_date)
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_paid(
        self, commission_id: str, payment_reference: str, payment_method: str = "bank_transfer"
    ) -> Optional[ResellerCommission]:
        """Mark commission as paid"""
        commission = await self.get_by_id(commission_id)
        if not commission:
            return None

        commission.payment_status = "paid"
        commission.payment_date = date.today()
        commission.payment_reference = payment_reference
        commission.payment_method = payment_method

        await self.db.flush()
        await self.db.refresh(commission)
        return commission


# Export all repositories
__all__ = [
    "BaseRepository",
    "ResellerApplicationRepository",
    "ResellerRepository",
    "ResellerCustomerRepository",
    "ResellerOpportunityRepository",
    "ResellerCommissionRepository",
]
