"""
Reseller Network Service Layer.

Provides comprehensive business logic for managing reseller partners,
sales opportunities, commissions, and training programs.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from ...shared.base_service import BaseManagementService
from ...shared.exceptions import BusinessRuleError, ServiceError
from ..billing.models import Invoice, Payment
from .models import ()
    Reseller, SalesOpportunity, SalesQuote, CommissionRecord,
    ResellerTraining, TerritoryAssignment,
    ResellerStatus, ResellerTier, OpportunityStage,
    CommissionStatus, TrainingStatus
, timezone)
from . import schemas

logger = logging.getLogger(__name__)


class ResellerService(BaseManagementService):
    """Comprehensive reseller partner management service."""

    def __init__(self, db: AsyncSession):
        super().__init__(db=db)

    # Reseller Management
    async def create_reseller():
        self, 
        reseller_data: schemas.ResellerCreate,
        created_by: UUID
    ) -> Reseller:
        """Create new reseller with validation and territory assignment."""
        
        # Validate unique company name
        existing = await self.db.execute()
            select(Reseller).where()
                Reseller.company_name == reseller_data.company_name,
                Reseller.is_active == True
            )
        )
        if existing.scalar_one_or_none():
            raise BusinessRuleError()
                f"Reseller company '{reseller_data.company_name}' already exists"
            )

        # Create reseller
        reseller = Reseller()
            id=uuid4(),
            **reseller_data.model_dump(),
            created_by=created_by,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(reseller)
        await self.db.flush()

        # Auto-assign training based on tier
        await self._assign_mandatory_training(reseller.id, reseller.tier)

        await self.db.commit()
        
        logger.info(f"Created reseller {reseller.company_name} (ID: {reseller.id})")
        return reseller

    async def update_reseller_status():
        self, 
        reseller_id: UUID, 
        status: ResellerStatus,
        updated_by: UUID,
        notes: Optional[str] = None
    ) -> Reseller:
        """Update reseller status with business rule validation."""
        
        reseller = await self._get_reseller_or_raise(reseller_id)
        
        # Validate status transitions
        if not self._is_valid_status_transition(reseller.status, status):
            raise BusinessRuleError()
                f"Invalid status transition from {reseller.status.value} to {status.value}"
            )
        
        # Handle status-specific business logic
        if status == ResellerStatus.APPROVED:
            await self._handle_reseller_approval(reseller)
        elif status == ResellerStatus.SUSPENDED:
            await self._handle_reseller_suspension(reseller)
        elif status == ResellerStatus.TERMINATED:
            await self._handle_reseller_termination(reseller)

        reseller.status = status
        reseller.updated_by = updated_by
        reseller.updated_at = datetime.now(timezone.utc)
        
        if notes:
            reseller.notes = f"{reseller.notes}\n{datetime.now(timezone.utc).isoformat()}: {notes}" if reseller.notes else notes

        await self.db.commit()
        
        logger.info(f"Updated reseller {reseller_id} status to {status.value}")
        return reseller

    async def upgrade_reseller_tier():
        self,
        reseller_id: UUID,
        new_tier: ResellerTier,
        updated_by: UUID
    ) -> Reseller:
        """Upgrade reseller tier with commission rate adjustment."""
        
        reseller = await self._get_reseller_or_raise(reseller_id)
        
        if new_tier.value <= reseller.tier.value:
            raise BusinessRuleError("Can only upgrade to higher tier")

        # Calculate new commission rates based on tier
        tier_rates = {
            ResellerTier.BRONZE: Decimal("0.10"),
            ResellerTier.SILVER: Decimal("0.12"),
            ResellerTier.GOLD: Decimal("0.15"),
            ResellerTier.PLATINUM: Decimal("0.18")
        }

        old_tier = reseller.tier
        reseller.tier = new_tier
        reseller.base_commission_rate = tier_rates[new_tier]
        reseller.tier_upgrade_date = datetime.now(timezone.utc)
        reseller.updated_by = updated_by
        reseller.updated_at = datetime.now(timezone.utc)

        # Assign additional training for higher tier
        await self._assign_tier_upgrade_training(reseller_id, new_tier)

        await self.db.commit()
        
        logger.info(f"Upgraded reseller {reseller_id} from {old_tier.value} to {new_tier.value}")
        return reseller

    # Sales Opportunity Management
    async def create_opportunity():
        self,
        opportunity_data: schemas.SalesOpportunityCreate,
        reseller_id: UUID,
        created_by: UUID
    ) -> SalesOpportunity:
        """Create sales opportunity with territory validation."""
        
        # Validate reseller can create opportunities in this territory
        await self._validate_territory_access()
            reseller_id, 
            opportunity_data.customer_location
        )

        opportunity = SalesOpportunity()
            id=uuid4(),
            reseller_id=reseller_id,
            **opportunity_data.model_dump(),
            created_by=created_by,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(opportunity)
        await self.db.commit()
        
        logger.info(f"Created opportunity {opportunity.id} for reseller {reseller_id}")
        return opportunity

    async def update_opportunity_stage():
        self,
        opportunity_id: UUID,
        new_stage: OpportunityStage,
        updated_by: UUID,
        notes: Optional[str] = None
    ) -> SalesOpportunity:
        """Update opportunity stage with pipeline automation."""
        
        opportunity = await self._get_opportunity_or_raise(opportunity_id)
        
        # Handle stage-specific logic
        if new_stage == OpportunityStage.WON:
            await self._handle_opportunity_won(opportunity, updated_by)
        elif new_stage == OpportunityStage.LOST:
            await self._handle_opportunity_lost(opportunity, notes)

        opportunity.stage = new_stage
        opportunity.updated_by = updated_by
        opportunity.updated_at = datetime.now(timezone.utc)
        
        if notes:
            opportunity.notes = f"{opportunity.notes}\n{datetime.now(timezone.utc).isoformat()}: {notes}" if opportunity.notes else notes

        await self.db.commit()
        
        logger.info(f"Updated opportunity {opportunity_id} stage to {new_stage.value}")
        return opportunity

    # Quote Management
    async def create_quote():
        self,
        quote_data: schemas.SalesQuoteCreate,
        opportunity_id: UUID,
        created_by: UUID
    ) -> SalesQuote:
        """Create sales quote with commission calculation."""
        
        opportunity = await self._get_opportunity_or_raise(opportunity_id)
        reseller = await self._get_reseller_or_raise(opportunity.reseller_id)

        # Calculate commission based on reseller tier and quote value
        commission_rate = await self._calculate_commission_rate()
            reseller, quote_data.total_value
        )
        projected_commission = quote_data.total_value * commission_rate

        quote = SalesQuote()
            id=uuid4(),
            opportunity_id=opportunity_id,
            commission_rate=commission_rate,
            projected_commission=projected_commission,
            **quote_data.model_dump(),
            created_by=created_by,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(quote)
        await self.db.commit()
        
        logger.info(f"Created quote {quote.id} for opportunity {opportunity_id}")
        return quote

    # Commission Management
    async def calculate_commission():
        self,
        reseller_id: UUID,
        revenue_amount: Decimal,
        contract_id: UUID,
        period_start: datetime,
        period_end: datetime
    ) -> CommissionRecord:
        """Calculate and record commission with business rules."""
        
        reseller = await self._get_reseller_or_raise(reseller_id)
        
        if reseller.status != ResellerStatus.APPROVED:
            raise BusinessRuleError("Can only calculate commissions for approved resellers")

        # Get effective commission rate
        commission_rate = await self._get_effective_commission_rate()
            reseller, revenue_amount, period_start, period_end
        )
        
        commission_amount = revenue_amount * commission_rate
        
        # Apply any bonuses or penalties
        commission_amount = await self._apply_commission_adjustments()
            reseller, commission_amount, period_start, period_end
        )

        commission = CommissionRecord()
            id=uuid4(),
            reseller_id=reseller_id,
            revenue_amount=revenue_amount,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            contract_id=contract_id,
            period_start=period_start,
            period_end=period_end,
            status=CommissionStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(commission)
        await self.db.commit()
        
        logger.info(f"Calculated commission {commission.id} for reseller {reseller_id}")
        return commission

    async def process_commission_payment():
        self,
        commission_id: UUID,
        processed_by: UUID,
        payment_reference: Optional[str] = None
    ) -> CommissionRecord:
        """Process commission payment with validation."""
        
        commission = await self._get_commission_or_raise(commission_id)
        
        if commission.status != CommissionStatus.APPROVED:
            raise BusinessRuleError("Can only pay approved commissions")

        commission.status = CommissionStatus.PAID
        commission.paid_at = datetime.now(timezone.utc)
        commission.payment_reference = payment_reference
        commission.updated_by = processed_by
        commission.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        
        logger.info(f"Processed payment for commission {commission_id}")
        return commission

    # Training Management
    async def assign_training():
        self,
        reseller_id: UUID,
        training_program: str,
        required: bool = False,
        due_date: Optional[datetime] = None,
        assigned_by: Optional[UUID] = None
    ) -> ResellerTraining:
        """Assign training program to reseller."""
        
        await self._get_reseller_or_raise(reseller_id)  # Validate reseller exists

        # Check if training already assigned
        existing = await self.db.execute()
            select(ResellerTraining).where()
                and_()
                    ResellerTraining.reseller_id == reseller_id,
                    ResellerTraining.training_program == training_program,
                    ResellerTraining.status != TrainingStatus.EXPIRED
                )
            )
        )
        if existing.scalar_one_or_none():
            raise BusinessRuleError(f"Training program '{training_program}' already assigned")

        training = ResellerTraining()
            id=uuid4(),
            reseller_id=reseller_id,
            training_program=training_program,
            required=required,
            due_date=due_date,
            assigned_by=assigned_by,
            created_at=datetime.now(timezone.utc)
        )
        
        self.db.add(training)
        await self.db.commit()
        
        logger.info(f"Assigned training '{training_program}' to reseller {reseller_id}")
        return training

    # Analytics and Reporting
    async def get_reseller_performance():
        self,
        reseller_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get comprehensive reseller performance metrics."""
        
        # Opportunities metrics
        opportunities_query = await self.db.execute()
            select()
                func.count(SalesOpportunity.id).label('total_opportunities'),
                func.count(SalesOpportunity.id).filter()
                    SalesOpportunity.stage == OpportunityStage.WON
                ).label('won_opportunities'),
                func.sum(SalesOpportunity.estimated_value).label('total_pipeline_value'),
                func.sum(SalesOpportunity.estimated_value).filter()
                    SalesOpportunity.stage == OpportunityStage.WON
                ).label('won_value')
            ).where()
                and_()
                    SalesOpportunity.reseller_id == reseller_id,
                    SalesOpportunity.created_at >= start_date,
                    SalesOpportunity.created_at <= end_date
                )
            )
        )
        opportunities_stats = opportunities_query.first()

        # Commission metrics
        commission_query = await self.db.execute()
            select()
                func.count(CommissionRecord.id).label('total_commissions'),
                func.sum(CommissionRecord.commission_amount).label('total_commission_amount'),
                func.sum(CommissionRecord.commission_amount).filter()
                    CommissionRecord.status == CommissionStatus.PAID
                ).label('paid_commission_amount')
            ).where()
                and_()
                    CommissionRecord.reseller_id == reseller_id,
                    CommissionRecord.period_start >= start_date,
                    CommissionRecord.period_end <= end_date
                )
            )
        )
        commission_stats = commission_query.first()

        # Training completion rate
        training_query = await self.db.execute()
            select()
                func.count(ResellerTraining.id).label('total_assigned'),
                func.count(ResellerTraining.id).filter()
                    ResellerTraining.status == TrainingStatus.COMPLETED
                ).label('completed')
            ).where(ResellerTraining.reseller_id == reseller_id)
        )
        training_stats = training_query.first()

        return {
            'opportunities': {
                'total': opportunities_stats.total_opportunities or 0,
                'won': opportunities_stats.won_opportunities or 0,
                'win_rate': (opportunities_stats.won_opportunities or 0) / max(opportunities_stats.total_opportunities or 1, 1) * 100,
                'pipeline_value': opportunities_stats.total_pipeline_value or Decimal('0'),
                'won_value': opportunities_stats.won_value or Decimal('0')
            },
            'commissions': {
                'total_records': commission_stats.total_commissions or 0,
                'total_amount': commission_stats.total_commission_amount or Decimal('0'),
                'paid_amount': commission_stats.paid_commission_amount or Decimal('0'),
                'pending_amount': (commission_stats.total_commission_amount or Decimal('0') - (commission_stats.paid_commission_amount or Decimal('0')
            },
            'training': {
                'assigned': training_stats.total_assigned or 0,
                'completed': training_stats.completed or 0,
                'completion_rate': (training_stats.completed or 0) / max(training_stats.total_assigned or 1, 1) * 100
            }
        }

    # Private Helper Methods
    async def _get_reseller_or_raise(self, reseller_id: UUID) -> Reseller:
        """Get reseller by ID or raise exception."""
        result = await self.db.execute()
            select(Reseller).where(Reseller.id == reseller_id)
        )
        reseller = result.scalar_one_or_none()
        if not reseller:
            raise BusinessRuleError(f"Reseller {reseller_id} not found")
        return reseller

    async def _get_opportunity_or_raise(self, opportunity_id: UUID) -> SalesOpportunity:
        """Get opportunity by ID or raise exception."""
        result = await self.db.execute()
            select(SalesOpportunity).where(SalesOpportunity.id == opportunity_id)
        )
        opportunity = result.scalar_one_or_none()
        if not opportunity:
            raise BusinessRuleError(f"Opportunity {opportunity_id} not found")
        return opportunity

    async def _get_commission_or_raise(self, commission_id: UUID) -> CommissionRecord:
        """Get commission by ID or raise exception."""
        result = await self.db.execute()
            select(CommissionRecord).where(CommissionRecord.id == commission_id)
        )
        commission = result.scalar_one_or_none()
        if not commission:
            raise BusinessRuleError(f"Commission {commission_id} not found")
        return commission

    def _is_valid_status_transition(self, from_status: ResellerStatus, to_status: ResellerStatus) -> bool:
        """Validate reseller status transitions."""
        valid_transitions = {
            ResellerStatus.PENDING_APPROVAL: [ResellerStatus.APPROVED, ResellerStatus.REJECTED],
            ResellerStatus.APPROVED: [ResellerStatus.SUSPENDED, ResellerStatus.TERMINATED],
            ResellerStatus.SUSPENDED: [ResellerStatus.APPROVED, ResellerStatus.TERMINATED],
            ResellerStatus.REJECTED: [],
            ResellerStatus.TERMINATED: []
        }
        return to_status in valid_transitions.get(from_status, [])

    async def _assign_mandatory_training(self, reseller_id: UUID, tier: ResellerTier):
        """Auto-assign mandatory training based on tier."""
        mandatory_programs = {
            ResellerTier.BRONZE: ["Sales_Basics", "Product_Overview"],
            ResellerTier.SILVER: ["Sales_Basics", "Product_Overview", "Advanced_Features"],
            ResellerTier.GOLD: ["Sales_Basics", "Product_Overview", "Advanced_Features", "Technical_Deep_Dive"],
            ResellerTier.PLATINUM: ["Sales_Basics", "Product_Overview", "Advanced_Features", "Technical_Deep_Dive", "Partner_Leadership"]
        }
        
        programs = mandatory_programs.get(tier, [])
        for program in programs:
            await self.assign_training()
                reseller_id=reseller_id,
                training_program=program,
                required=True,
                due_date=datetime.now(timezone.utc) + timedelta(days=30)
            )

    async def _validate_territory_access(self, reseller_id: UUID, location: str):
        """Validate reseller has access to territory."""
        # For now, just validate reseller exists and is approved
        reseller = await self._get_reseller_or_raise(reseller_id)
        if reseller.status != ResellerStatus.APPROVED:
            raise BusinessRuleError("Only approved resellers can create opportunities")

    async def _calculate_commission_rate(self, reseller: Reseller, quote_value: Decimal) -> Decimal:
        """Calculate effective commission rate based on tier and volume."""
        base_rate = reseller.base_commission_rate
        
        # Volume bonuses
        if quote_value > Decimal("100000"):
            base_rate += Decimal("0.02")  # 2% bonus for large deals
        elif quote_value > Decimal("50000"):
            base_rate += Decimal("0.01")  # 1% bonus for medium deals
            
        return min(base_rate, Decimal("0.25")  # Cap at 25%

    async def _get_effective_commission_rate():
        self, 
        reseller: Reseller, 
        revenue_amount: Decimal,
        period_start: datetime, 
        period_end: datetime
    ) -> Decimal:
        """Get effective commission rate with all adjustments."""
        return await self._calculate_commission_rate(reseller, revenue_amount)

    async def _apply_commission_adjustments():
        self,
        reseller: Reseller,
        base_commission: Decimal,
        period_start: datetime,
        period_end: datetime
    ) -> Decimal:
        """Apply performance bonuses or penalties."""
        # Placeholder for future performance-based adjustments
        return base_commission

    async def _handle_reseller_approval(self, reseller: Reseller):
        """Handle business logic when reseller is approved."""
        # Could trigger welcome email, training assignments, etc.
        pass

    async def _handle_reseller_suspension(self, reseller: Reseller):
        """Handle business logic when reseller is suspended."""
        # Could pause commissions, disable portal access, etc.
        pass

    async def _handle_reseller_termination(self, reseller: Reseller):
        """Handle business logic when reseller is terminated."""
        # Could final commission payments, territory reassignment, etc.
        pass

    async def _handle_opportunity_won(self, opportunity: SalesOpportunity, updated_by: UUID):
        """Handle business logic when opportunity is won."""
        # Could trigger commission calculation, customer onboarding, etc.
        pass

    async def _handle_opportunity_lost(self, opportunity: SalesOpportunity, notes: Optional[str]):
        """Handle business logic when opportunity is lost."""
        # Could analyze loss reasons, update forecasts, etc.
        pass

    async def _assign_tier_upgrade_training(self, reseller_id: UUID, new_tier: ResellerTier):
        """Assign additional training for tier upgrades."""
        additional_programs = {
            ResellerTier.SILVER: ["Advanced_Sales_Techniques"],
            ResellerTier.GOLD: ["Technical_Implementation", "Customer_Success"],
            ResellerTier.PLATINUM: ["Strategic_Account_Management", "Partner_Program_Leadership"]
        }
        
        programs = additional_programs.get(new_tier, [])
        for program in programs:
            await self.assign_training()
                reseller_id=reseller_id,
                training_program=program,
                required=True,
                due_date=datetime.now(timezone.utc) + timedelta(days=45)
            )