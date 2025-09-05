"""Lead repository for database operations."""

import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

try:
    from sqlalchemy import and_, desc, func
    from sqlalchemy.orm import Session

    from ..core.models import Lead, LeadStatus
    from ..core.schemas import LeadCreate, LeadUpdate

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Session = Lead = LeadStatus = LeadCreate = LeadUpdate = None


class LeadRepository:
    """Repository for lead database operations."""

    def __init__(self, db_session: Session, timezone):
        """Initialize repository with database session."""
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy dependencies not available")

        self.db = db_session

    async def create_lead(
        self, lead_data: LeadCreate, tenant_id: str, lead_score: int = 0
    ) -> Lead:
        """Create a new lead in the database."""
        # Generate unique lead ID
        lead_id = f"LEAD-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"

        # Create lead instance
        lead = Lead(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            lead_id=lead_id,
            first_name=lead_data.first_name,
            last_name=lead_data.last_name,
            email=lead_data.email,
            phone=lead_data.phone,
            company=lead_data.company,
            job_title=lead_data.job_title,
            lead_source=lead_data.lead_source,
            customer_type=lead_data.customer_type,
            budget=lead_data.budget,
            authority=lead_data.authority,
            need=lead_data.need,
            timeline=lead_data.timeline,
            street_address=lead_data.street_address,
            city=lead_data.city,
            state_province=lead_data.state_province,
            postal_code=lead_data.postal_code,
            country_code=lead_data.country_code,
            assigned_to=lead_data.assigned_to,
            sales_team=lead_data.sales_team,
            notes=lead_data.notes,
            lead_score=lead_score,
            lead_status=LeadStatus.NEW,
            first_contact_date=None,
            last_contact_date=None,
            next_follow_up_date=None,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)

        return lead

    async def get_lead_by_id(self, lead_id: str, tenant_id: str) -> Optional[Lead]:
        """Get a lead by ID and tenant."""
        return (
            self.db.query(Lead)
            .filter(
                and_(
                    Lead.lead_id == lead_id,
                    Lead.tenant_id == tenant_id,
                    Lead.is_active is True,
                )
            )
            .first()
        )

    async def update_lead(
        self, lead_id: str, lead_data: LeadUpdate, tenant_id: str
    ) -> Lead:
        """Update an existing lead."""
        lead = await self.get_lead_by_id(lead_id, tenant_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Update fields that are provided
        update_data = lead_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(lead, field):
                setattr(lead, field, value)

        lead.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(lead)

        return lead

    async def update_lead_score(
        self, lead_id: str, new_score: int, tenant_id: str
    ) -> Lead:
        """Update lead score."""
        lead = await self.get_lead_by_id(lead_id, tenant_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        lead.lead_score = new_score
        lead.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(lead)

        return lead

    async def update_lead_status(
        self, lead_id: str, tenant_id: str, new_status: LeadStatus
    ) -> Lead:
        """Update lead status."""
        lead = await self.get_lead_by_id(lead_id, tenant_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        lead.lead_status = new_status
        lead.updated_at = datetime.now(timezone.utc)

        # Set special dates based on status
        if new_status == LeadStatus.CONTACTED and not lead.first_contact_date:
            lead.first_contact_date = date.today()
            lead.last_contact_date = date.today()
        elif new_status in [LeadStatus.CONTACTED, LeadStatus.QUALIFIED]:
            lead.last_contact_date = date.today()
        elif new_status == LeadStatus.CONVERTED:
            lead.converted_date = date.today()

        self.db.commit()
        self.db.refresh(lead)

        return lead

    async def list_leads(
        self,
        tenant_id: str,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Lead], int]:
        """List leads with filtering and pagination."""
        query = self.db.query(Lead).filter(
            and_(Lead.tenant_id == tenant_id, Lead.is_active is True)
        )

        # Apply filters
        if filters:
            if filters.get("lead_source"):
                query = query.filter(Lead.lead_source == filters["lead_source"])

            if filters.get("lead_status"):
                query = query.filter(Lead.lead_status == filters["lead_status"])

            if filters.get("customer_type"):
                query = query.filter(Lead.customer_type == filters["customer_type"])

            if filters.get("assigned_to"):
                query = query.filter(Lead.assigned_to == filters["assigned_to"])

            if filters.get("sales_team"):
                query = query.filter(Lead.sales_team == filters["sales_team"])

            if filters.get("created_from"):
                query = query.filter(Lead.created_at >= filters["created_from"])

            if filters.get("created_to"):
                query = query.filter(Lead.created_at <= filters["created_to"])

            if filters.get("follow_up_overdue"):
                query = query.filter(
                    and_(
                        Lead.next_follow_up_date.isnot(None),
                        Lead.next_follow_up_date < date.today(),
                    )
                )

        # Get total count
        total_count = query.count()

        # Apply pagination and ordering
        leads = (
            query.order_by(desc(Lead.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return leads, total_count

    async def qualify_lead(
        self, lead_id: str, tenant_id: str, qualification_data: dict[str, Any]
    ) -> Lead:
        """Qualify a lead with BANT criteria."""
        lead = await self.get_lead_by_id(lead_id, tenant_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Update qualification fields
        if "budget" in qualification_data:
            lead.budget = qualification_data["budget"]

        if "authority" in qualification_data:
            lead.authority = qualification_data["authority"]

        if "need" in qualification_data:
            lead.need = qualification_data["need"]

        if "timeline" in qualification_data:
            lead.timeline = qualification_data["timeline"]

        if "qualification_notes" in qualification_data:
            lead.qualification_notes = qualification_data["qualification_notes"]

        # Update status to qualified
        lead.lead_status = LeadStatus.QUALIFIED
        lead.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(lead)

        return lead

    async def convert_lead(
        self, lead_id: str, tenant_id: str, opportunity_id: str
    ) -> Lead:
        """Convert a lead to an opportunity."""
        lead = await self.get_lead_by_id(lead_id, tenant_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        lead.lead_status = LeadStatus.CONVERTED
        lead.converted_date = date.today()
        lead.opportunity_id = opportunity_id
        lead.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(lead)

        return lead

    async def get_overdue_leads(self, tenant_id: str) -> list[Lead]:
        """Get leads that are overdue for follow-up."""
        return (
            self.db.query(Lead)
            .filter(
                and_(
                    Lead.tenant_id == tenant_id,
                    Lead.is_active is True,
                    Lead.lead_status.in_([LeadStatus.NEW, LeadStatus.CONTACTED]),
                    Lead.next_follow_up_date.isnot(None),
                    Lead.next_follow_up_date <= date.today(),
                )
            )
            .order_by(Lead.next_follow_up_date)
            .all()
        )

    async def get_all_leads_for_scoring(self, tenant_id: str) -> list[Lead]:
        """Get all active leads for bulk score updates."""
        return (
            self.db.query(Lead)
            .filter(
                and_(
                    Lead.tenant_id == tenant_id,
                    Lead.is_active is True,
                    Lead.lead_status != LeadStatus.CONVERTED,
                )
            )
            .all()
        )

    async def get_lead_statistics(self, tenant_id: str) -> dict[str, Any]:
        """Get lead statistics for analytics."""
        total_leads = (
            self.db.query(func.count(Lead.id))
            .filter(and_(Lead.tenant_id == tenant_id, Lead.is_active is True))
            .scalar()
        )

        # Count by status
        status_counts = (
            self.db.query(Lead.lead_status, func.count(Lead.id))
            .filter(and_(Lead.tenant_id == tenant_id, Lead.is_active is True))
            .group_by(Lead.lead_status)
            .all()
        )

        # Count by source
        source_counts = (
            self.db.query(Lead.lead_source, func.count(Lead.id))
            .filter(and_(Lead.tenant_id == tenant_id, Lead.is_active is True))
            .group_by(Lead.lead_source)
            .all()
        )

        # Average score
        avg_score = (
            self.db.query(func.avg(Lead.lead_score))
            .filter(and_(Lead.tenant_id == tenant_id, Lead.is_active is True))
            .scalar()
        )

        return {
            "total_leads": total_leads or 0,
            "status_breakdown": {
                status.value: count for status, count in status_counts
            },
            "source_breakdown": {
                source.value: count for source, count in source_counts
            },
            "average_score": round(float(avg_score or 0), 2),
            "high_score_leads": self.db.query(func.count(Lead.id))
            .filter(
                and_(
                    Lead.tenant_id == tenant_id,
                    Lead.is_active is True,
                    Lead.lead_score >= 70,
                )
            )
            .scalar()
            or 0,
        }

    async def delete_lead(self, lead_id: str, tenant_id: str) -> bool:
        """Soft delete a lead."""
        lead = await self.get_lead_by_id(lead_id, tenant_id)
        if not lead:
            return False

        lead.is_active = False
        lead.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        return True
