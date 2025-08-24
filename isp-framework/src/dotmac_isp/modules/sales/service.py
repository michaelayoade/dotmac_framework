"""Sales service layer for business logic."""

import re
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from .repository import (
    LeadRepository,
    OpportunityRepository,
    SalesActivityRepository,
    QuoteRepository,
    SalesAnalyticsRepository,
)
from .models import (
    Lead,
    Opportunity,
    SalesActivity,
    Quote,
    LeadSource,
    LeadStatus,
    OpportunityStage,
    OpportunityStatus,
    ActivityType,
    ActivityStatus,
    QuoteStatus,
    CustomerType,
)
from . import schemas
from dotmac_isp.shared.exceptions import NotFoundError, ValidationError, ServiceError


class LeadManagementService:
    """Service for lead management and qualification."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.lead_repo = LeadRepository(db, self.tenant_id)
        self.activity_repo = SalesActivityRepository(db, self.tenant_id)

    async def create_lead(self, lead_data: Dict[str, Any]) -> Lead:
        """Create a new lead with validation and scoring."""
        # Validate email format
        if lead_data.get("email"):
            if not self._validate_email(lead_data["email"]):
                raise ValidationError("Invalid email format")

        # Check for duplicate email
        if lead_data.get("email"):
            existing_lead = self.lead_repo.get_by_email(lead_data["email"])
            if existing_lead:
                raise ValidationError(
                    f"Lead with email {lead_data['email']} already exists"
                )

        # Calculate initial lead score
        lead_data["lead_score"] = self._calculate_lead_score(lead_data)

        # Set initial status based on source
        if not lead_data.get("lead_status"):
            lead_data["lead_status"] = LeadStatus.NEW

        # Set first contact date
        if not lead_data.get("first_contact_date"):
            lead_data["first_contact_date"] = date.today()

        lead = self.lead_repo.create(lead_data)

        # Create initial follow-up activity
        await self._create_initial_follow_up(lead)

        return lead

    async def get_lead(self, lead_id: UUID) -> Lead:
        """Get lead by ID."""
        lead = self.lead_repo.get_by_id(lead_id)
        if not lead:
            raise NotFoundError(f"Lead with ID {lead_id} not found")
        return lead

    async def list_leads(
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
        return self.lead_repo.list_leads(
            lead_source,
            lead_status,
            customer_type,
            assigned_to,
            sales_team,
            created_from,
            created_to,
            follow_up_overdue,
            skip,
            limit,
        )

    async def qualify_lead(
        self, lead_id: UUID, qualification_data: Dict[str, Any]
    ) -> Lead:
        """Qualify a lead using BANT criteria."""
        lead = await self.get_lead(lead_id)

        # Update qualification fields
        if "budget" in qualification_data:
            lead.budget = qualification_data["budget"]
        if "authority" in qualification_data:
            lead.authority = qualification_data["authority"]
        if "need" in qualification_data:
            lead.need = qualification_data["need"]
        if "timeline" in qualification_data:
            lead.timeline = qualification_data["timeline"]

        # Update qualification notes
        if "qualification_notes" in qualification_data:
            lead.qualification_notes = qualification_data["qualification_notes"]

        # Recalculate lead score
        lead_dict = {
            "budget": lead.budget,
            "authority": lead.authority,
            "need": lead.need,
            "timeline": lead.timeline,
            "customer_type": lead.customer_type,
            "lead_source": lead.lead_source,
        }
        new_score = self._calculate_lead_score(lead_dict)
        self.lead_repo.update_score(lead_id, new_score)

        # Determine if qualified
        is_qualified = self._is_lead_qualified(lead_dict)

        if is_qualified:
            self.lead_repo.update_status(
                lead_id, LeadStatus.QUALIFIED, "Lead qualified based on BANT criteria"
            )
        else:
            self.lead_repo.update_status(
                lead_id,
                LeadStatus.UNQUALIFIED,
                "Lead did not meet qualification criteria",
            )

        self.db.commit()
        self.db.refresh(lead)
        return lead

    async def convert_lead_to_opportunity(
        self, lead_id: UUID, opportunity_data: Dict[str, Any]
    ) -> Opportunity:
        """Convert qualified lead to opportunity."""
        lead = await self.get_lead(lead_id)

        if lead.lead_status != LeadStatus.QUALIFIED:
            raise ValidationError(
                "Only qualified leads can be converted to opportunities"
            )

        # Create opportunity from lead data
        opp_service = OpportunityManagementService(self.db, str(self.tenant_id))

        # Map lead data to opportunity
        opportunity_data.update(
            {
                "lead_id": lead_id,
                "account_name": lead.company or f"{lead.first_name} {lead.last_name}",
                "contact_name": f"{lead.first_name} {lead.last_name}",
                "contact_email": lead.email,
                "contact_phone": lead.phone,
                "customer_type": lead.customer_type,
                "sales_owner": lead.assigned_to,
                "sales_team": lead.sales_team,
                "street_address": lead.street_address,
                "city": lead.city,
                "state_province": lead.state_province,
                "postal_code": lead.postal_code,
                "country_code": lead.country_code,
            }
        )

        if not opportunity_data.get("opportunity_name"):
            opportunity_data["opportunity_name"] = (
                f"{opportunity_data['account_name']} - {opportunity_data.get('description', 'Opportunity')}"
            )

        opportunity = await opp_service.create_opportunity(opportunity_data)

        # Update lead status
        lead.opportunity_id = opportunity.id
        self.lead_repo.update_status(
            lead_id,
            LeadStatus.CONVERTED,
            f"Converted to opportunity {opportunity.opportunity_id}",
        )

        return opportunity

    async def assign_lead(
        self, lead_id: UUID, assigned_to: str, sales_team: Optional[str] = None
    ) -> Lead:
        """Assign lead to sales rep."""
        lead = self.lead_repo.update_assignment(lead_id, assigned_to, sales_team)
        if not lead:
            raise NotFoundError(f"Lead with ID {lead_id} not found")
        return lead

    async def get_leads_for_follow_up(
        self, assigned_to: Optional[str] = None
    ) -> List[Lead]:
        """Get leads that need follow-up."""
        return self.lead_repo.get_leads_for_follow_up(assigned_to)

    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def _calculate_lead_score(self, lead_data: Dict[str, Any]) -> int:
        """
        Calculate lead score based on various factors.
        
        REFACTORED: Replaced 14-complexity method with Strategy pattern.
        Now uses LeadScoringEngine for extensible scoring (Complexity: 2).
        """
        # Import here to avoid circular dependencies
        from .scoring_strategies import create_lead_scoring_engine
        
        # Use strategy pattern for lead scoring (Complexity: 1)
        scoring_engine = create_lead_scoring_engine()
        
        # Return calculated score (Complexity: 1)
        return scoring_engine.calculate_lead_score(lead_data)

    def _is_lead_qualified(self, lead_data: Dict[str, Any]) -> bool:
        """Determine if lead is qualified based on BANT."""
        has_budget = bool(lead_data.get("budget"))
        has_authority = bool(lead_data.get("authority"))
        has_need = bool(lead_data.get("need"))
        has_timeline = bool(lead_data.get("timeline"))

        # Lead is qualified if it has at least 3 of 4 BANT criteria
        bant_score = sum([has_budget, has_authority, has_need, has_timeline])
        return bant_score >= 3

    async def _create_initial_follow_up(self, lead: Lead) -> SalesActivity:
        """Create initial follow-up activity for new lead."""
        activity_data = {
            "lead_id": lead.id,
            "subject": f"Initial contact - {lead.full_name}",
            "description": f"Follow up on new lead from {lead.lead_source}",
            "activity_type": ActivityType.CALL,
            "assigned_to": lead.assigned_to or "unassigned",
            "scheduled_date": datetime.utcnow() + timedelta(hours=24),  # Next day
        }

        return self.activity_repo.create(activity_data)


class OpportunityManagementService:
    """Service for opportunity management and sales pipeline."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.opportunity_repo = OpportunityRepository(db, self.tenant_id)
        self.activity_repo = SalesActivityRepository(db, self.tenant_id)

    async def create_opportunity(self, opportunity_data: Dict[str, Any]) -> Opportunity:
        """Create a new sales opportunity."""
        # Validate required fields
        required_fields = [
            "opportunity_name",
            "account_name",
            "estimated_value",
            "expected_close_date",
            "sales_owner",
        ]
        for field in required_fields:
            if not opportunity_data.get(field):
                raise ValidationError(f"Required field '{field}' is missing")

        # Set default values
        if not opportunity_data.get("opportunity_stage"):
            opportunity_data["opportunity_stage"] = OpportunityStage.PROSPECTING

        if not opportunity_data.get("probability"):
            # Set default probability based on stage
            stage_probabilities = {
                OpportunityStage.PROSPECTING: 10,
                OpportunityStage.QUALIFICATION: 25,
                OpportunityStage.NEEDS_ANALYSIS: 40,
                OpportunityStage.PROPOSAL: 60,
                OpportunityStage.NEGOTIATION: 80,
                OpportunityStage.CLOSED_WON: 100,
                OpportunityStage.CLOSED_LOST: 0,
            }
            opportunity_data["probability"] = stage_probabilities.get(
                opportunity_data["opportunity_stage"], 10
            )

        # Validate close date
        if opportunity_data["expected_close_date"] <= date.today():
            raise ValidationError("Expected close date must be in the future")

        opportunity = self.opportunity_repo.create(opportunity_data)

        # Create initial activity
        await self._create_initial_opportunity_activity(opportunity)

        return opportunity

    async def get_opportunity(self, opportunity_id: UUID) -> Opportunity:
        """Get opportunity by ID."""
        opportunity = self.opportunity_repo.get_by_id(opportunity_id)
        if not opportunity:
            raise NotFoundError(f"Opportunity with ID {opportunity_id} not found")
        return opportunity

    async def list_opportunities(
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
        return self.opportunity_repo.list_opportunities(
            opportunity_stage,
            opportunity_status,
            sales_owner,
            sales_team,
            customer_type,
            close_date_from,
            close_date_to,
            min_value,
            max_value,
            overdue_only,
            skip,
            limit,
        )

    async def update_opportunity_stage(
        self, opportunity_id: UUID, stage: OpportunityStage, notes: Optional[str] = None
    ) -> Opportunity:
        """Update opportunity stage and handle stage-specific logic."""
        opportunity = await self.get_opportunity(opportunity_id)

        # Validate stage progression
        if not self._is_valid_stage_transition(opportunity.opportunity_stage, stage):
            raise ValidationError(
                f"Invalid stage transition from {opportunity.opportunity_stage} to {stage}"
            )

        # Update probability based on stage
        stage_probabilities = {
            OpportunityStage.PROSPECTING: 10,
            OpportunityStage.QUALIFICATION: 25,
            OpportunityStage.NEEDS_ANALYSIS: 40,
            OpportunityStage.PROPOSAL: 60,
            OpportunityStage.NEGOTIATION: 80,
            OpportunityStage.CLOSED_WON: 100,
            OpportunityStage.CLOSED_LOST: 0,
        }

        new_probability = stage_probabilities.get(stage, opportunity.probability)
        self.opportunity_repo.update_probability(opportunity_id, new_probability)

        # Update stage
        opportunity = self.opportunity_repo.update_stage(opportunity_id, stage, notes)

        # Create stage change activity
        await self._create_stage_change_activity(opportunity, stage)

        return opportunity

    async def close_opportunity(
        self,
        opportunity_id: UUID,
        is_won: bool,
        close_reason: str,
        notes: Optional[str] = None,
    ) -> Opportunity:
        """Close opportunity as won or lost."""
        stage = OpportunityStage.CLOSED_WON if is_won else OpportunityStage.CLOSED_LOST

        opportunity = await self.update_opportunity_stage(opportunity_id, stage, notes)

        # Update close reason
        opportunity.close_reason = close_reason
        self.db.commit()
        self.db.refresh(opportunity)

        return opportunity

    async def get_pipeline_summary(
        self, sales_owner: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get pipeline summary and forecasting data."""
        return self.opportunity_repo.get_pipeline_summary(sales_owner)

    async def get_forecast_data(self, quarter: Optional[str] = None) -> Dict[str, Any]:
        """Get sales forecast data."""
        # Determine quarter
        if not quarter:
            today = date.today()
            quarter_map = {
                1: "Q1",
                2: "Q1",
                3: "Q1",
                4: "Q2",
                5: "Q2",
                6: "Q2",
                7: "Q3",
                8: "Q3",
                9: "Q3",
                10: "Q4",
                11: "Q4",
                12: "Q4",
            }
            quarter = f"{today.year}-{quarter_map[today.month]}"

        # Get opportunities in forecast period
        year, q = quarter.split("-")
        quarter_start, quarter_end = self._get_quarter_dates(int(year), q)

        opportunities = self.opportunity_repo.list_opportunities(
            opportunity_status=OpportunityStatus.ACTIVE,
            close_date_from=quarter_start,
            close_date_to=quarter_end,
            limit=1000,
        )

        # Categorize forecast
        pipeline = []
        best_case = []
        commit = []

        for opp in opportunities:
            if opp.probability >= 90:
                commit.append(opp)
            elif opp.probability >= 70:
                best_case.append(opp)

            pipeline.append(opp)

        return {
            "quarter": quarter,
            "pipeline": {
                "count": len(pipeline),
                "value": sum(o.estimated_value for o in pipeline),
                "weighted_value": sum(o.weighted_value or 0 for o in pipeline),
            },
            "best_case": {
                "count": len(best_case),
                "value": sum(o.estimated_value for o in best_case),
                "weighted_value": sum(o.weighted_value or 0 for o in best_case),
            },
            "commit": {
                "count": len(commit),
                "value": sum(o.estimated_value for o in commit),
                "weighted_value": sum(o.weighted_value or 0 for o in commit),
            },
        }

    def _is_valid_stage_transition(
        self, current_stage: OpportunityStage, new_stage: OpportunityStage
    ) -> bool:
        """Validate stage transition."""
        # Allow any transition to closed stages
        if new_stage in [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]:
            return True

        # Define valid transitions
        valid_transitions = {
            OpportunityStage.PROSPECTING: [OpportunityStage.QUALIFICATION],
            OpportunityStage.QUALIFICATION: [
                OpportunityStage.NEEDS_ANALYSIS,
                OpportunityStage.PROSPECTING,
            ],
            OpportunityStage.NEEDS_ANALYSIS: [
                OpportunityStage.PROPOSAL,
                OpportunityStage.QUALIFICATION,
            ],
            OpportunityStage.PROPOSAL: [
                OpportunityStage.NEGOTIATION,
                OpportunityStage.NEEDS_ANALYSIS,
            ],
            OpportunityStage.NEGOTIATION: [
                OpportunityStage.PROPOSAL,
                OpportunityStage.CLOSED_WON,
            ],
        }

        return new_stage in valid_transitions.get(current_stage, [])

    def _get_quarter_dates(self, year: int, quarter: str) -> Tuple[date, date]:
        """Get start and end dates for quarter."""
        quarter_starts = {
            "Q1": date(year, 1, 1),
            "Q2": date(year, 4, 1),
            "Q3": date(year, 7, 1),
            "Q4": date(year, 10, 1),
        }

        quarter_ends = {
            "Q1": date(year, 3, 31),
            "Q2": date(year, 6, 30),
            "Q3": date(year, 9, 30),
            "Q4": date(year, 12, 31),
        }

        return quarter_starts[quarter], quarter_ends[quarter]

    async def _create_initial_opportunity_activity(
        self, opportunity: Opportunity
    ) -> SalesActivity:
        """Create initial activity for new opportunity."""
        activity_data = {
            "opportunity_id": opportunity.id,
            "subject": f"Discovery call - {opportunity.opportunity_name}",
            "description": f"Initial discovery call for opportunity {opportunity.opportunity_name}",
            "activity_type": ActivityType.CALL,
            "assigned_to": opportunity.sales_owner,
            "scheduled_date": datetime.utcnow() + timedelta(days=1),
        }

        return self.activity_repo.create(activity_data)

    async def _create_stage_change_activity(
        self, opportunity: Opportunity, new_stage: OpportunityStage
    ) -> SalesActivity:
        """Create activity for stage change."""
        activity_data = {
            "opportunity_id": opportunity.id,
            "subject": f"Stage changed to {new_stage.value}",
            "description": f"Opportunity {opportunity.opportunity_name} moved to {new_stage.value} stage",
            "activity_type": ActivityType.OTHER,
            "activity_status": ActivityStatus.COMPLETED,
            "assigned_to": opportunity.sales_owner,
            "scheduled_date": datetime.utcnow(),
            "completed_date": datetime.utcnow(),
        }

        return self.activity_repo.create(activity_data)


class SalesActivityService:
    """Service for sales activity management."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.activity_repo = SalesActivityRepository(db, self.tenant_id)

    async def create_activity(self, activity_data: Dict[str, Any]) -> SalesActivity:
        """Create a new sales activity."""
        # Validate that either lead_id or opportunity_id is provided
        if not activity_data.get("lead_id") and not activity_data.get("opportunity_id"):
            raise ValidationError("Either lead_id or opportunity_id must be provided")

        # Validate scheduled date
        if activity_data["scheduled_date"] < datetime.utcnow():
            raise ValidationError("Scheduled date cannot be in the past")

        return self.activity_repo.create(activity_data)

    async def get_activity(self, activity_id: UUID) -> SalesActivity:
        """Get activity by ID."""
        activity = self.activity_repo.get_by_id(activity_id)
        if not activity:
            raise NotFoundError(f"Activity with ID {activity_id} not found")
        return activity

    async def list_activities(
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
        return self.activity_repo.list_activities(
            lead_id,
            opportunity_id,
            activity_type,
            activity_status,
            assigned_to,
            date_from,
            date_to,
            overdue_only,
            skip,
            limit,
        )

    async def complete_activity(
        self, activity_id: UUID, outcome: str, outcome_description: Optional[str] = None
    ) -> SalesActivity:
        """Mark activity as completed."""
        activity = self.activity_repo.complete_activity(
            activity_id, outcome, outcome_description
        )
        if not activity:
            raise NotFoundError(f"Activity with ID {activity_id} not found")
        return activity

    async def get_upcoming_activities(
        self, assigned_to: Optional[str] = None, days: int = 7
    ) -> List[SalesActivity]:
        """Get upcoming activities."""
        return self.activity_repo.get_upcoming_activities(assigned_to, days)


class SalesAnalyticsService:
    """Service for sales analytics and reporting."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.analytics_repo = SalesAnalyticsRepository(db, self.tenant_id)
        self.lead_repo = LeadRepository(db, self.tenant_id)
        self.opportunity_repo = OpportunityRepository(db, self.tenant_id)

    async def get_sales_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive sales dashboard data."""
        today = date.today()
        month_start = today.replace(day=1)
        quarter_start = self._get_quarter_start(today)
        year_start = today.replace(month=1, day=1)

        # Current month metrics
        monthly_metrics = self.analytics_repo.get_sales_metrics(month_start, today)

        # Current quarter metrics
        quarterly_metrics = self.analytics_repo.get_sales_metrics(quarter_start, today)

        # Current year metrics
        yearly_metrics = self.analytics_repo.get_sales_metrics(year_start, today)

        # Pipeline summary
        pipeline = self.opportunity_repo.get_pipeline_summary()

        # Activity counts
        activities_today = len(
            self.activity_repo.list_activities(
                date_from=datetime.combine(today, datetime.min.time()),
                date_to=datetime.combine(today, datetime.max.time()),
                limit=1000,
            )
        )

        overdue_activities = len(
            self.activity_repo.list_activities(overdue_only=True, limit=1000)
        )

        # Lead statistics
        new_leads_today = len(
            self.lead_repo.list_leads(created_from=today, created_to=today, limit=1000)
        )

        follow_up_leads = len(self.lead_repo.get_leads_for_follow_up())

        return {
            "current_month": monthly_metrics,
            "current_quarter": quarterly_metrics,
            "current_year": yearly_metrics,
            "pipeline": pipeline,
            "activities": {
                "scheduled_today": activities_today,
                "overdue": overdue_activities,
            },
            "leads": {
                "new_today": new_leads_today,
                "pending_follow_up": follow_up_leads,
            },
            "last_updated": datetime.utcnow().isoformat(),
        }

    async def get_sales_performance(
        self,
        start_date: date,
        end_date: date,
        sales_rep: Optional[str] = None,
        sales_team: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get detailed sales performance metrics."""
        return self.analytics_repo.get_sales_metrics(
            start_date, end_date, sales_rep, sales_team
        )

    async def get_lead_conversion_funnel(self) -> Dict[str, Any]:
        """Get lead conversion funnel analysis."""
        # Get all leads
        all_leads = self.lead_repo.list_leads(limit=10000)

        # Count by status
        status_counts = {}
        for status in LeadStatus:
            status_counts[status.value] = len(
                [l for l in all_leads if l.lead_status == status]
            )

        # Calculate conversion rates
        total_leads = len(all_leads)
        contacted = (
            status_counts.get("contacted", 0)
            + status_counts.get("qualified", 0)
            + status_counts.get("converted", 0)
        )
        qualified = status_counts.get("qualified", 0) + status_counts.get(
            "converted", 0
        )
        converted = status_counts.get("converted", 0)

        return {
            "total_leads": total_leads,
            "status_breakdown": status_counts,
            "conversion_rates": {
                "contact_rate": (
                    (contacted / total_leads * 100) if total_leads > 0 else 0
                ),
                "qualification_rate": (
                    (qualified / contacted * 100) if contacted > 0 else 0
                ),
                "conversion_rate": (
                    (converted / qualified * 100) if qualified > 0 else 0
                ),
                "overall_conversion_rate": (
                    (converted / total_leads * 100) if total_leads > 0 else 0
                ),
            },
        }

    def _get_quarter_start(self, today: date) -> date:
        """Get start of current quarter."""
        quarter = (today.month - 1) // 3 + 1
        month = (quarter - 1) * 3 + 1
        return today.replace(month=month, day=1)


class SalesMainService:
    """Main service orchestrating all sales operations."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id
        self.lead_service = LeadManagementService(db, tenant_id)
        self.opportunity_service = OpportunityManagementService(db, tenant_id)
        self.activity_service = SalesActivityService(db, tenant_id)
        self.analytics_service = SalesAnalyticsService(db, tenant_id)

    async def create_lead_and_activity(
        self,
        lead_data: schemas.LeadCreate,
        initial_activity: Optional[schemas.SalesActivityCreate] = None,
    ) -> Tuple[Lead, Optional[SalesActivity]]:
        """Create lead with optional initial activity."""
        # Create lead
        lead = await self.lead_service.create_lead(lead_data.dict())

        # Create custom activity if provided
        activity = None
        if initial_activity:
            activity_data = initial_activity.dict()
            activity_data["lead_id"] = lead.id
            activity = await self.activity_service.create_activity(activity_data)

        return lead, activity

    async def complete_sales_cycle(
        self, opportunity_id: UUID, is_won: bool, close_data: Dict[str, Any]
    ) -> Opportunity:
        """Complete entire sales cycle from opportunity to close."""
        # Close opportunity
        opportunity = await self.opportunity_service.close_opportunity(
            opportunity_id,
            is_won,
            close_data.get("close_reason", ""),
            close_data.get("notes"),
        )

        # Create completion activity
        activity_data = {
            "opportunity_id": opportunity_id,
            "subject": f"Opportunity {'Won' if is_won else 'Lost'}",
            "description": f"Opportunity {opportunity.opportunity_name} was {'won' if is_won else 'lost'}: {close_data.get('close_reason', '')}",
            "activity_type": ActivityType.OTHER,
            "activity_status": ActivityStatus.COMPLETED,
            "assigned_to": opportunity.sales_owner,
            "scheduled_date": datetime.utcnow(),
            "completed_date": datetime.utcnow(),
            "outcome": "won" if is_won else "lost",
            "outcome_description": close_data.get("notes"),
        }

        await self.activity_service.create_activity(activity_data)

        return opportunity

    async def get_sales_rep_dashboard(self, sales_rep: str) -> Dict[str, Any]:
        """Get personalized dashboard for sales rep."""
        # Get dashboard data
        dashboard = await self.analytics_service.get_sales_dashboard()

        # Get rep-specific data
        today = date.today()
        month_start = today.replace(day=1)

        rep_performance = await self.analytics_service.get_sales_performance(
            month_start, today, sales_rep
        )

        # Get assigned leads and opportunities
        assigned_leads = await self.lead_service.list_leads(
            assigned_to=sales_rep, limit=1000
        )
        assigned_opportunities = await self.opportunity_service.list_opportunities(
            sales_owner=sales_rep, limit=1000
        )

        # Get upcoming activities
        upcoming_activities = await self.activity_service.get_upcoming_activities(
            sales_rep
        )

        # Get leads needing follow-up
        follow_up_leads = await self.lead_service.get_leads_for_follow_up(sales_rep)

        return {
            "personal_performance": rep_performance,
            "assigned_leads": len(assigned_leads),
            "assigned_opportunities": len(assigned_opportunities),
            "upcoming_activities": len(upcoming_activities),
            "follow_up_leads": len(follow_up_leads),
            "team_summary": dashboard,
            "next_actions": {
                "overdue_activities": len(
                    [a for a in upcoming_activities if a.is_overdue]
                ),
                "follow_ups_due": len(follow_up_leads),
                "opportunities_closing_soon": len(
                    [
                        o
                        for o in assigned_opportunities
                        if o.opportunity_status == OpportunityStatus.ACTIVE
                        and o.expected_close_date <= today + timedelta(days=7)
                    ]
                ),
            },
        }
