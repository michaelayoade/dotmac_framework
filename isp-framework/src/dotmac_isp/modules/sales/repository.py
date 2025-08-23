"""Repository pattern for sales database operations."""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc, asc, extract

from .models import (
    Lead,
    Opportunity,
    SalesActivity,
    Quote,
    QuoteLineItem,
    SalesForecast,
    Territory,
    LeadSource,
    LeadStatus,
    OpportunityStage,
    OpportunityStatus,
    ActivityType,
    ActivityStatus,
    QuoteStatus,
    CustomerType,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class LeadRepository:
    """Repository for lead database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, lead_data: Dict[str, Any]) -> Lead:
        """Create new lead."""
        try:
            # Generate lead ID if not provided
            if not lead_data.get("lead_id"):
                lead_data["lead_id"] = self._generate_lead_id()

            lead = Lead(id=uuid4(), tenant_id=self.tenant_id, **lead_data)

            self.db.add(lead)
            self.db.commit()
            self.db.refresh(lead)
            return lead

        except IntegrityError as e:
            self.db.rollback()
            if "lead_id" in str(e):
                raise ConflictError(
                    f"Lead ID {lead_data.get('lead_id')} already exists"
                )
            if "email" in str(e):
                raise ConflictError(f"Email {lead_data.get('email')} already exists")
            raise ConflictError("Lead creation failed due to data conflict")

    def get_by_id(self, lead_id: UUID) -> Optional[Lead]:
        """Get lead by ID."""
        return (
            self.db.query(Lead)
            .filter(and_(Lead.id == lead_id, Lead.tenant_id == self.tenant_id))
            .first()
        )

    def get_by_lead_id(self, lead_id: str) -> Optional[Lead]:
        """Get lead by lead ID string."""
        return (
            self.db.query(Lead)
            .filter(and_(Lead.lead_id == lead_id, Lead.tenant_id == self.tenant_id))
            .first()
        )

    def get_by_email(self, email: str) -> Optional[Lead]:
        """Get lead by email."""
        return (
            self.db.query(Lead)
            .filter(and_(Lead.email == email, Lead.tenant_id == self.tenant_id))
            .first()
        )

    def list_leads(
        self,
        lead_source: Optional[LeadSource] = None,
        lead_status: Optional[LeadStatus] = None,
        customer_type: Optional[CustomerType] = None,
        assigned_to: Optional[str] = None,
        sales_team: Optional[str] = None,
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
        follow_up_overdue: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Lead]:
        """List leads with filtering."""
        query = self.db.query(Lead).filter(Lead.tenant_id == self.tenant_id)

        if lead_source:
            query = query.filter(Lead.lead_source == lead_source)
        if lead_status:
            query = query.filter(Lead.lead_status == lead_status)
        if customer_type:
            query = query.filter(Lead.customer_type == customer_type)
        if assigned_to:
            query = query.filter(Lead.assigned_to == assigned_to)
        if sales_team:
            query = query.filter(Lead.sales_team == sales_team)
        if created_from:
            query = query.filter(func.date(Lead.created_at) >= created_from)
        if created_to:
            query = query.filter(func.date(Lead.created_at) <= created_to)
        if follow_up_overdue:
            query = query.filter(
                and_(
                    Lead.next_follow_up_date.isnot(None),
                    Lead.next_follow_up_date < date.today(),
                )
            )

        return query.order_by(desc(Lead.created_at)).offset(skip).limit(limit).all()

    def update_status(
        self, lead_id: UUID, status: LeadStatus, notes: Optional[str] = None
    ) -> Optional[Lead]:
        """Update lead status."""
        lead = self.get_by_id(lead_id)
        if not lead:
            return None

        lead.lead_status = status
        lead.updated_at = datetime.utcnow()

        if status == LeadStatus.CONVERTED:
            lead.converted_date = date.today()

        if notes:
            current_notes = lead.notes or ""
            lead.notes = (
                f"{current_notes}\n{datetime.utcnow().isoformat()}: {notes}".strip()
            )

        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update_assignment(
        self, lead_id: UUID, assigned_to: str, sales_team: Optional[str] = None
    ) -> Optional[Lead]:
        """Update lead assignment."""
        lead = self.get_by_id(lead_id)
        if not lead:
            return None

        lead.assigned_to = assigned_to
        if sales_team:
            lead.sales_team = sales_team
        lead.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(lead)
        return lead

    def update_score(self, lead_id: UUID, score: int) -> Optional[Lead]:
        """Update lead score."""
        lead = self.get_by_id(lead_id)
        if not lead:
            return None

        lead.lead_score = score
        lead.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(lead)
        return lead

    def get_leads_for_follow_up(self, assigned_to: Optional[str] = None) -> List[Lead]:
        """Get leads that need follow-up."""
        query = self.db.query(Lead).filter(
            and_(
                Lead.tenant_id == self.tenant_id,
                Lead.next_follow_up_date <= date.today(),
                Lead.lead_status.in_(
                    [LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED]
                ),
            )
        )

        if assigned_to:
            query = query.filter(Lead.assigned_to == assigned_to)

        return query.order_by(Lead.next_follow_up_date).all()

    def _generate_lead_id(self) -> str:
        """Generate unique lead ID."""
        today = date.today()
        count = (
            self.db.query(func.count(Lead.id))
            .filter(
                and_(
                    Lead.tenant_id == self.tenant_id,
                    func.date(Lead.created_at) == today,
                )
            )
            .scalar()
        )

        return f"LEAD-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class OpportunityRepository:
    """Repository for opportunity database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, opportunity_data: Dict[str, Any]) -> Opportunity:
        """Create new opportunity."""
        try:
            # Generate opportunity ID if not provided
            if not opportunity_data.get("opportunity_id"):
                opportunity_data["opportunity_id"] = self._generate_opportunity_id()

            # Calculate weighted value
            if opportunity_data.get("estimated_value") and opportunity_data.get(
                "probability"
            ):
                estimated_value = Decimal(str(opportunity_data["estimated_value"]))
                probability = opportunity_data["probability"]
                opportunity_data["weighted_value"] = estimated_value * (
                    probability / 100
                )

            opportunity = Opportunity(
                id=uuid4(), tenant_id=self.tenant_id, **opportunity_data
            )

            self.db.add(opportunity)
            self.db.commit()
            self.db.refresh(opportunity)
            return opportunity

        except IntegrityError as e:
            self.db.rollback()
            if "opportunity_id" in str(e):
                raise ConflictError(
                    f"Opportunity ID {opportunity_data.get('opportunity_id')} already exists"
                )
            raise ConflictError("Opportunity creation failed due to data conflict")

    def get_by_id(self, opportunity_id: UUID) -> Optional[Opportunity]:
        """Get opportunity by ID."""
        return (
            self.db.query(Opportunity)
            .filter(
                and_(
                    Opportunity.id == opportunity_id,
                    Opportunity.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_opportunity_id(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get opportunity by opportunity ID string."""
        return (
            self.db.query(Opportunity)
            .filter(
                and_(
                    Opportunity.opportunity_id == opportunity_id,
                    Opportunity.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_opportunities(
        self,
        opportunity_stage: Optional[OpportunityStage] = None,
        opportunity_status: Optional[OpportunityStatus] = None,
        sales_owner: Optional[str] = None,
        sales_team: Optional[str] = None,
        customer_type: Optional[CustomerType] = None,
        close_date_from: Optional[date] = None,
        close_date_to: Optional[date] = None,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
        overdue_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Opportunity]:
        """List opportunities with filtering."""
        query = self.db.query(Opportunity).filter(
            Opportunity.tenant_id == self.tenant_id
        )

        if opportunity_stage:
            query = query.filter(Opportunity.opportunity_stage == opportunity_stage)
        if opportunity_status:
            query = query.filter(Opportunity.opportunity_status == opportunity_status)
        if sales_owner:
            query = query.filter(Opportunity.sales_owner == sales_owner)
        if sales_team:
            query = query.filter(Opportunity.sales_team == sales_team)
        if customer_type:
            query = query.filter(Opportunity.customer_type == customer_type)
        if close_date_from:
            query = query.filter(Opportunity.expected_close_date >= close_date_from)
        if close_date_to:
            query = query.filter(Opportunity.expected_close_date <= close_date_to)
        if min_value:
            query = query.filter(Opportunity.estimated_value >= min_value)
        if max_value:
            query = query.filter(Opportunity.estimated_value <= max_value)
        if overdue_only:
            query = query.filter(
                and_(
                    Opportunity.opportunity_status == OpportunityStatus.ACTIVE,
                    Opportunity.expected_close_date < date.today(),
                )
            )

        return (
            query.order_by(desc(Opportunity.estimated_value))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_stage(
        self, opportunity_id: UUID, stage: OpportunityStage, notes: Optional[str] = None
    ) -> Optional[Opportunity]:
        """Update opportunity stage."""
        opportunity = self.get_by_id(opportunity_id)
        if not opportunity:
            return None

        opportunity.opportunity_stage = stage
        opportunity.updated_at = datetime.utcnow()

        # Update status based on stage
        if stage == OpportunityStage.CLOSED_WON:
            opportunity.opportunity_status = OpportunityStatus.WON
            opportunity.actual_close_date = date.today()
            opportunity.sales_cycle_days = (
                date.today() - opportunity.created_date
            ).days
        elif stage == OpportunityStage.CLOSED_LOST:
            opportunity.opportunity_status = OpportunityStatus.LOST
            opportunity.actual_close_date = date.today()
            opportunity.sales_cycle_days = (
                date.today() - opportunity.created_date
            ).days

        if notes:
            current_notes = opportunity.notes or ""
            opportunity.notes = (
                f"{current_notes}\n{datetime.utcnow().isoformat()}: {notes}".strip()
            )

        self.db.commit()
        self.db.refresh(opportunity)
        return opportunity

    def update_probability(
        self, opportunity_id: UUID, probability: int
    ) -> Optional[Opportunity]:
        """Update opportunity probability and recalculate weighted value."""
        opportunity = self.get_by_id(opportunity_id)
        if not opportunity:
            return None

        opportunity.probability = probability
        opportunity.weighted_value = opportunity.estimated_value * (probability / 100)
        opportunity.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(opportunity)
        return opportunity

    def get_pipeline_summary(self, sales_owner: Optional[str] = None) -> Dict[str, Any]:
        """Get pipeline summary statistics."""
        query = self.db.query(Opportunity).filter(
            and_(
                Opportunity.tenant_id == self.tenant_id,
                Opportunity.opportunity_status == OpportunityStatus.ACTIVE,
            )
        )

        if sales_owner:
            query = query.filter(Opportunity.sales_owner == sales_owner)

        opportunities = query.all()

        # Group by stage
        stage_summary = {}
        for stage in OpportunityStage:
            stage_opps = [
                opp for opp in opportunities if opp.opportunity_stage == stage
            ]
            stage_summary[stage.value] = {
                "count": len(stage_opps),
                "total_value": sum(opp.estimated_value for opp in stage_opps),
                "weighted_value": sum(opp.weighted_value or 0 for opp in stage_opps),
            }

        total_value = sum(opp.estimated_value for opp in opportunities)
        total_weighted = sum(opp.weighted_value or 0 for opp in opportunities)

        return {
            "total_opportunities": len(opportunities),
            "total_pipeline_value": total_value,
            "total_weighted_value": total_weighted,
            "stage_breakdown": stage_summary,
            "average_deal_size": (
                total_value / len(opportunities) if opportunities else 0
            ),
        }

    def _generate_opportunity_id(self) -> str:
        """Generate unique opportunity ID."""
        today = date.today()
        count = (
            self.db.query(func.count(Opportunity.id))
            .filter(
                and_(
                    Opportunity.tenant_id == self.tenant_id,
                    func.date(Opportunity.created_at) == today,
                )
            )
            .scalar()
        )

        return f"OPP-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class SalesActivityRepository:
    """Repository for sales activity database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, activity_data: Dict[str, Any]) -> SalesActivity:
        """Create new sales activity."""
        try:
            # Generate activity ID if not provided
            if not activity_data.get("activity_id"):
                activity_data["activity_id"] = self._generate_activity_id()

            activity = SalesActivity(
                id=uuid4(), tenant_id=self.tenant_id, **activity_data
            )

            self.db.add(activity)
            self.db.commit()
            self.db.refresh(activity)
            return activity

        except IntegrityError as e:
            self.db.rollback()
            if "activity_id" in str(e):
                raise ConflictError(
                    f"Activity ID {activity_data.get('activity_id')} already exists"
                )
            raise ConflictError("Activity creation failed due to data conflict")

    def get_by_id(self, activity_id: UUID) -> Optional[SalesActivity]:
        """Get activity by ID."""
        return (
            self.db.query(SalesActivity)
            .filter(
                and_(
                    SalesActivity.id == activity_id,
                    SalesActivity.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_activities(
        self,
        lead_id: Optional[UUID] = None,
        opportunity_id: Optional[UUID] = None,
        activity_type: Optional[ActivityType] = None,
        activity_status: Optional[ActivityStatus] = None,
        assigned_to: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        overdue_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SalesActivity]:
        """List activities with filtering."""
        query = self.db.query(SalesActivity).filter(
            SalesActivity.tenant_id == self.tenant_id
        )

        if lead_id:
            query = query.filter(SalesActivity.lead_id == lead_id)
        if opportunity_id:
            query = query.filter(SalesActivity.opportunity_id == opportunity_id)
        if activity_type:
            query = query.filter(SalesActivity.activity_type == activity_type)
        if activity_status:
            query = query.filter(SalesActivity.activity_status == activity_status)
        if assigned_to:
            query = query.filter(SalesActivity.assigned_to == assigned_to)
        if date_from:
            query = query.filter(SalesActivity.scheduled_date >= date_from)
        if date_to:
            query = query.filter(SalesActivity.scheduled_date <= date_to)
        if overdue_only:
            query = query.filter(
                and_(
                    SalesActivity.activity_status == ActivityStatus.PLANNED,
                    SalesActivity.scheduled_date < datetime.utcnow(),
                )
            )

        return (
            query.order_by(SalesActivity.scheduled_date).offset(skip).limit(limit).all()
        )

    def complete_activity(
        self, activity_id: UUID, outcome: str, outcome_description: Optional[str] = None
    ) -> Optional[SalesActivity]:
        """Mark activity as completed."""
        activity = self.get_by_id(activity_id)
        if not activity:
            return None

        activity.activity_status = ActivityStatus.COMPLETED
        activity.completed_date = datetime.utcnow()
        activity.outcome = outcome
        activity.outcome_description = outcome_description

        self.db.commit()
        self.db.refresh(activity)
        return activity

    def get_upcoming_activities(
        self, assigned_to: Optional[str] = None, days: int = 7
    ) -> List[SalesActivity]:
        """Get upcoming activities."""
        end_date = datetime.utcnow() + timedelta(days=days)

        query = self.db.query(SalesActivity).filter(
            and_(
                SalesActivity.tenant_id == self.tenant_id,
                SalesActivity.activity_status == ActivityStatus.PLANNED,
                SalesActivity.scheduled_date <= end_date,
            )
        )

        if assigned_to:
            query = query.filter(SalesActivity.assigned_to == assigned_to)

        return query.order_by(SalesActivity.scheduled_date).all()

    def _generate_activity_id(self) -> str:
        """Generate unique activity ID."""
        today = date.today()
        count = (
            self.db.query(func.count(SalesActivity.id))
            .filter(
                and_(
                    SalesActivity.tenant_id == self.tenant_id,
                    func.date(SalesActivity.created_at) == today,
                )
            )
            .scalar()
        )

        return f"ACT-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class QuoteRepository:
    """Repository for quote database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, quote_data: Dict[str, Any]) -> Quote:
        """Create new quote."""
        try:
            # Generate quote number if not provided
            if not quote_data.get("quote_number"):
                quote_data["quote_number"] = self._generate_quote_number()

            quote = Quote(id=uuid4(), tenant_id=self.tenant_id, **quote_data)

            self.db.add(quote)
            self.db.commit()
            self.db.refresh(quote)
            return quote

        except IntegrityError as e:
            self.db.rollback()
            if "quote_number" in str(e):
                raise ConflictError(
                    f"Quote number {quote_data.get('quote_number')} already exists"
                )
            raise ConflictError("Quote creation failed due to data conflict")

    def get_by_id(self, quote_id: UUID) -> Optional[Quote]:
        """Get quote by ID."""
        return (
            self.db.query(Quote)
            .filter(and_(Quote.id == quote_id, Quote.tenant_id == self.tenant_id))
            .first()
        )

    def get_by_quote_number(self, quote_number: str) -> Optional[Quote]:
        """Get quote by quote number."""
        return (
            self.db.query(Quote)
            .filter(
                and_(
                    Quote.quote_number == quote_number,
                    Quote.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_quotes(
        self,
        opportunity_id: Optional[UUID] = None,
        status: Optional[QuoteStatus] = None,
        sales_rep: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Quote]:
        """List quotes with filtering."""
        query = self.db.query(Quote).filter(Quote.tenant_id == self.tenant_id)

        if opportunity_id:
            query = query.filter(Quote.opportunity_id == opportunity_id)
        if status:
            query = query.filter(Quote.quote_status == status)
        if sales_rep:
            query = query.filter(Quote.sales_rep == sales_rep)
        if date_from:
            query = query.filter(Quote.quote_date >= date_from)
        if date_to:
            query = query.filter(Quote.quote_date <= date_to)

        return query.order_by(desc(Quote.created_at)).offset(skip).limit(limit).all()

    def update_status(self, quote_id: UUID, status: QuoteStatus) -> Optional[Quote]:
        """Update quote status."""
        quote = self.get_by_id(quote_id)
        if not quote:
            return None

        quote.quote_status = status
        quote.updated_at = datetime.utcnow()

        if status == QuoteStatus.SENT:
            quote.sent_date = date.today()
        elif status == QuoteStatus.ACCEPTED:
            quote.accepted_date = date.today()
        elif status == QuoteStatus.REJECTED:
            quote.rejected_date = date.today()

        self.db.commit()
        self.db.refresh(quote)
        return quote

    def _generate_quote_number(self) -> str:
        """Generate unique quote number."""
        today = date.today()
        count = (
            self.db.query(func.count(Quote.id))
            .filter(
                and_(
                    Quote.tenant_id == self.tenant_id,
                    func.date(Quote.created_at) == today,
                )
            )
            .scalar()
        )

        return f"QUO-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class SalesAnalyticsRepository:
    """Repository for sales analytics and reporting."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def get_sales_metrics(
        self,
        start_date: date,
        end_date: date,
        sales_rep: Optional[str] = None,
        sales_team: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get comprehensive sales metrics."""

        # Base filters
        lead_filters = [Lead.tenant_id == self.tenant_id]
        opp_filters = [Opportunity.tenant_id == self.tenant_id]

        if sales_rep:
            lead_filters.append(Lead.assigned_to == sales_rep)
            opp_filters.append(Opportunity.sales_owner == sales_rep)

        if sales_team:
            lead_filters.append(Lead.sales_team == sales_team)
            opp_filters.append(Opportunity.sales_team == sales_team)

        # Lead metrics
        lead_query = self.db.query(Lead).filter(
            and_(
                *lead_filters,
                func.date(Lead.created_at) >= start_date,
                func.date(Lead.created_at) <= end_date,
            )
        )

        leads = lead_query.all()
        leads_created = len(leads)
        leads_converted = len(
            [l for l in leads if l.lead_status == LeadStatus.CONVERTED]
        )
        conversion_rate = (
            (leads_converted / leads_created * 100) if leads_created > 0 else 0
        )

        # Opportunity metrics
        opp_query = self.db.query(Opportunity).filter(
            and_(
                *opp_filters,
                Opportunity.actual_close_date >= start_date,
                Opportunity.actual_close_date <= end_date,
            )
        )

        closed_opps = opp_query.all()
        won_opps = [
            o for o in closed_opps if o.opportunity_status == OpportunityStatus.WON
        ]

        revenue = sum(o.estimated_value for o in won_opps)
        deals_won = len(won_opps)
        deals_lost = len(closed_opps) - deals_won
        win_rate = (deals_won / len(closed_opps) * 100) if closed_opps else 0
        avg_deal_size = revenue / deals_won if deals_won > 0 else 0

        # Sales cycle
        avg_sales_cycle = (
            sum(o.sales_cycle_days or 0 for o in won_opps) / deals_won
            if deals_won > 0
            else 0
        )

        return {
            "leads_created": leads_created,
            "leads_converted": leads_converted,
            "conversion_rate": round(conversion_rate, 2),
            "revenue": float(revenue),
            "deals_won": deals_won,
            "deals_lost": deals_lost,
            "win_rate": round(win_rate, 2),
            "average_deal_size": float(avg_deal_size),
            "average_sales_cycle_days": round(avg_sales_cycle, 1),
        }
