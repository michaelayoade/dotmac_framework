"""
Reseller Customer Lifecycle Management
Advanced customer relationship management for resellers
"""

import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from dotmac_shared.database.base import Base

from .services_complete import ResellerCustomerService
from .db_models import ResellerCustomer


class CustomerLifecycleStage(str, Enum):
    """Customer lifecycle stages"""
    PROSPECT = "prospect"
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    EXPANSION = "expansion"
    AT_RISK = "at_risk"
    CHURNED = "churned"
    REACTIVATION = "reactivation"


class CustomerHealthScore(str, Enum):
    """Customer health scoring"""
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"           # 70-89
    FAIR = "fair"           # 50-69
    POOR = "poor"           # 30-49
    CRITICAL = "critical"   # 0-29


class CustomerInteractionType(str, Enum):
    """Types of customer interactions"""
    SALES_CALL = "sales_call"
    SUPPORT_TICKET = "support_ticket"
    EMAIL = "email"
    MEETING = "meeting"
    TRAINING = "training"
    BILLING_INQUIRY = "billing_inquiry"
    TECHNICAL_ISSUE = "technical_issue"
    FEATURE_REQUEST = "feature_request"
    COMPLAINT = "complaint"
    COMPLIMENT = "compliment"


class CustomerLifecycleRecord(Base):
    """Track customer lifecycle progression"""
    __tablename__ = "customer_lifecycle_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    reseller_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Lifecycle tracking
    previous_stage = Column(String(50), nullable=True)
    current_stage = Column(String(50), default=CustomerLifecycleStage.PROSPECT.value)
    stage_entered_at = Column(DateTime, default=datetime.utcnow)
    stage_duration_days = Column(Numeric(5, 1), default=0)
    
    # Health and scoring
    health_score = Column(Numeric(5, 2), default=75.0)  # 0-100
    health_category = Column(String(20), default=CustomerHealthScore.GOOD.value)
    risk_factors = Column(JSON, default=list)
    
    # Performance metrics
    monthly_value = Column(Numeric(10, 2), default=0)
    lifetime_value = Column(Numeric(12, 2), default=0)
    engagement_score = Column(Numeric(5, 2), default=50.0)  # 0-100
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    notes = Column(Text, nullable=True)


class CustomerInteraction(Base):
    """Track customer interactions and touchpoints"""
    __tablename__ = "customer_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    reseller_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Interaction details
    interaction_type = Column(String(50), nullable=False)
    interaction_date = Column(DateTime, default=datetime.utcnow)
    duration_minutes = Column(Numeric(5, 0), nullable=True)
    
    # Content and context
    subject = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(DateTime, nullable=True)
    
    # Participants
    reseller_contact = Column(String(200), nullable=True)
    customer_contact = Column(String(200), nullable=True)
    
    # Impact tracking
    satisfaction_rating = Column(Numeric(3, 1), nullable=True)  # 1-10 scale
    impact_on_health_score = Column(Numeric(4, 1), default=0)  # -10 to +10
    tags = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    metadata = Column(JSON, default=dict)


class CustomerLifecycleManager:
    """Manages customer lifecycle stages and health scoring"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.customer_service = ResellerCustomerService(db, tenant_id)
    
    async def advance_customer_stage(
        self,
        customer_id: UUID,
        reseller_id: UUID,
        new_stage: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Advance customer to next lifecycle stage"""
        
        # Validate stage
        try:
            stage_enum = CustomerLifecycleStage(new_stage)
        except ValueError:
            raise ValueError(f"Invalid lifecycle stage: {new_stage}")
        
        # Get current lifecycle record or create new one
        current_record = await self._get_current_lifecycle_record(customer_id, reseller_id)
        
        if current_record:
            # Update existing record
            previous_stage = current_record.current_stage
            stage_duration = (datetime.now(timezone.utc) - current_record.stage_entered_at).days
            
            # Create new record for the stage transition
            new_record = CustomerLifecycleRecord(
                customer_id=customer_id,
                reseller_id=reseller_id,
                previous_stage=previous_stage,
                current_stage=new_stage,
                stage_entered_at=datetime.now(timezone.utc),
                health_score=current_record.health_score,
                health_category=current_record.health_category,
                monthly_value=current_record.monthly_value,
                lifetime_value=current_record.lifetime_value,
                engagement_score=current_record.engagement_score,
                notes=notes,
                metadata={
                    'stage_transition': True,
                    'previous_stage_duration_days': stage_duration,
                    'automated': False
                }
            )
        else:
            # Create first lifecycle record
            new_record = CustomerLifecycleRecord(
                customer_id=customer_id,
                reseller_id=reseller_id,
                current_stage=new_stage,
                notes=notes,
                metadata={'initial_stage': True, 'automated': False}
            )
        
        self.db.add(new_record)
        await self.db.commit()
        
        # Trigger stage-specific actions
        await self._trigger_stage_actions(customer_id, reseller_id, new_stage)
        
        return {
            'customer_id': str(customer_id),
            'reseller_id': str(reseller_id),
            'previous_stage': current_record.current_stage if current_record else None,
            'new_stage': new_stage,
            'stage_entered_at': new_record.stage_entered_at.isoformat(),
            'health_score': float(new_record.health_score),
            'actions_triggered': await self._get_stage_actions(new_stage)
        }
    
    async def update_health_score(
        self,
        customer_id: UUID,
        reseller_id: UUID,
        new_score: float,
        risk_factors: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update customer health score and category"""
        
        if not 0 <= new_score <= 100:
            raise ValueError("Health score must be between 0 and 100")
        
        # Determine health category
        if new_score >= 90:
            health_category = CustomerHealthScore.EXCELLENT
        elif new_score >= 70:
            health_category = CustomerHealthScore.GOOD
        elif new_score >= 50:
            health_category = CustomerHealthScore.FAIR
        elif new_score >= 30:
            health_category = CustomerHealthScore.POOR
        else:
            health_category = CustomerHealthScore.CRITICAL
        
        # Get or create lifecycle record
        current_record = await self._get_current_lifecycle_record(customer_id, reseller_id)
        
        if current_record:
            # Update existing record
            old_score = float(current_record.health_score)
            current_record.health_score = new_score
            current_record.health_category = health_category.value
            current_record.risk_factors = risk_factors or []
            current_record.updated_at = datetime.now(timezone.utc)
        else:
            # Create new record
            current_record = CustomerLifecycleRecord(
                customer_id=customer_id,
                reseller_id=reseller_id,
                health_score=new_score,
                health_category=health_category.value,
                risk_factors=risk_factors or [],
                metadata={'initial_health_update': True}
            )
            old_score = 0
            self.db.add(current_record)
        
        await self.db.commit()
        
        # Check if health score change requires action
        score_change = new_score - old_score
        if score_change <= -20:  # Significant decline
            await self._trigger_health_alert(customer_id, reseller_id, new_score, 'significant_decline')
        elif health_category == CustomerHealthScore.CRITICAL:
            await self._trigger_health_alert(customer_id, reseller_id, new_score, 'critical_health')
        
        return {
            'customer_id': str(customer_id),
            'reseller_id': str(reseller_id),
            'old_score': old_score,
            'new_score': new_score,
            'health_category': health_category.value,
            'score_change': score_change,
            'risk_factors': risk_factors or [],
            'updated_at': current_record.updated_at.isoformat()
        }
    
    async def log_customer_interaction(
        self,
        customer_id: UUID,
        reseller_id: UUID,
        interaction_type: str,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        outcome: Optional[str] = None,
        satisfaction_rating: Optional[float] = None,
        duration_minutes: Optional[int] = None,
        follow_up_required: bool = False,
        follow_up_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Log a customer interaction"""
        
        # Validate interaction type
        try:
            interaction_enum = CustomerInteractionType(interaction_type)
        except ValueError:
            raise ValueError(f"Invalid interaction type: {interaction_type}")
        
        # Create interaction record
        interaction = CustomerInteraction(
            customer_id=customer_id,
            reseller_id=reseller_id,
            interaction_type=interaction_type,
            subject=subject,
            description=description,
            outcome=outcome,
            satisfaction_rating=satisfaction_rating,
            duration_minutes=duration_minutes,
            follow_up_required=follow_up_required,
            follow_up_date=follow_up_date,
            tags=tags or [],
            metadata={
                'logged_via': 'api',
                'auto_health_impact': True
            }
        )
        
        self.db.add(interaction)
        await self.db.commit()
        
        # Calculate health impact
        health_impact = await self._calculate_interaction_health_impact(interaction_type, satisfaction_rating)
        if health_impact != 0:
            # Update health score
            current_record = await self._get_current_lifecycle_record(customer_id, reseller_id)
            if current_record:
                new_score = max(0, min(100, float(current_record.health_score) + health_impact))
                await self.update_health_score(customer_id, reseller_id, new_score)
        
        return {
            'interaction_id': str(interaction.id),
            'customer_id': str(customer_id),
            'reseller_id': str(reseller_id),
            'interaction_type': interaction_type,
            'logged_at': interaction.created_at.isoformat(),
            'health_impact': health_impact,
            'follow_up_required': follow_up_required
        }
    
    async def get_customer_lifecycle_summary(
        self,
        customer_id: UUID,
        reseller_id: UUID
    ) -> Dict[str, Any]:
        """Get comprehensive customer lifecycle summary"""
        
        # Get current lifecycle record
        current_record = await self._get_current_lifecycle_record(customer_id, reseller_id)
        
        if not current_record:
            return {
                'customer_id': str(customer_id),
                'reseller_id': str(reseller_id),
                'error': 'No lifecycle data found',
                'current_stage': None,
                'health_score': None
            }
        
        # Get interaction history (last 30 days)
        recent_interactions = await self._get_recent_interactions(customer_id, reseller_id, days=30)
        
        # Get stage history
        stage_history = await self._get_stage_history(customer_id, reseller_id)
        
        # Calculate engagement metrics
        engagement_metrics = await self._calculate_engagement_metrics(customer_id, reseller_id)
        
        summary = {
            'customer_id': str(customer_id),
            'reseller_id': str(reseller_id),
            'current_stage': current_record.current_stage,
            'stage_entered_at': current_record.stage_entered_at.isoformat(),
            'days_in_current_stage': (datetime.now(timezone.utc) - current_record.stage_entered_at).days,
            'health_score': float(current_record.health_score),
            'health_category': current_record.health_category,
            'risk_factors': current_record.risk_factors,
            'monthly_value': float(current_record.monthly_value),
            'lifetime_value': float(current_record.lifetime_value),
            'engagement_score': float(current_record.engagement_score),
            'recent_interactions': {
                'total_count': len(recent_interactions),
                'by_type': self._group_interactions_by_type(recent_interactions),
                'avg_satisfaction': self._calculate_avg_satisfaction(recent_interactions),
                'last_interaction_date': max(
                    [i.interaction_date for i in recent_interactions]
                ).isoformat() if recent_interactions else None
            },
            'stage_progression': [
                {
                    'stage': record.current_stage,
                    'entered_at': record.stage_entered_at.isoformat(),
                    'duration_days': record.stage_duration_days or 0
                } for record in stage_history
            ],
            'engagement_metrics': engagement_metrics,
            'recommendations': await self._generate_customer_recommendations(current_record, recent_interactions),
            'next_actions': await self._get_suggested_next_actions(current_record)
        }
        
        return summary
    
    async def _get_current_lifecycle_record(
        self,
        customer_id: UUID,
        reseller_id: UUID
    ) -> Optional[CustomerLifecycleRecord]:
        """Get the most recent lifecycle record for a customer"""
        # In production, this would query the database
        # For now, return a simulated record
        return None
    
    async def _get_recent_interactions(
        self,
        customer_id: UUID,
        reseller_id: UUID,
        days: int = 30
    ) -> List[CustomerInteraction]:
        """Get recent customer interactions"""
        # In production, this would query the database
        return []
    
    async def _get_stage_history(
        self,
        customer_id: UUID,
        reseller_id: UUID
    ) -> List[CustomerLifecycleRecord]:
        """Get customer's stage progression history"""
        # In production, this would query the database
        return []
    
    async def _calculate_engagement_metrics(
        self,
        customer_id: UUID,
        reseller_id: UUID
    ) -> Dict[str, Any]:
        """Calculate customer engagement metrics"""
        return {
            'communication_frequency': 8.5,  # interactions per month
            'response_rate': 85.0,  # percentage
            'support_ticket_resolution_time': 2.3,  # average days
            'training_completion_rate': 75.0,  # percentage
            'feature_adoption_rate': 60.0  # percentage
        }
    
    def _group_interactions_by_type(self, interactions: List[CustomerInteraction]) -> Dict[str, int]:
        """Group interactions by type"""
        grouped = {}
        for interaction in interactions:
            interaction_type = interaction.interaction_type
            grouped[interaction_type] = grouped.get(interaction_type, 0) + 1
        return grouped
    
    def _calculate_avg_satisfaction(self, interactions: List[CustomerInteraction]) -> Optional[float]:
        """Calculate average satisfaction rating"""
        ratings = [i.satisfaction_rating for i in interactions if i.satisfaction_rating is not None]
        return sum(ratings) / len(ratings) if ratings else None
    
    async def _calculate_interaction_health_impact(
        self,
        interaction_type: str,
        satisfaction_rating: Optional[float]
    ) -> float:
        """Calculate how an interaction impacts health score"""
        
        # Base impact by interaction type
        base_impacts = {
            CustomerInteractionType.SALES_CALL: 2.0,
            CustomerInteractionType.SUPPORT_TICKET: -1.0,
            CustomerInteractionType.EMAIL: 0.5,
            CustomerInteractionType.MEETING: 3.0,
            CustomerInteractionType.TRAINING: 4.0,
            CustomerInteractionType.BILLING_INQUIRY: -0.5,
            CustomerInteractionType.TECHNICAL_ISSUE: -2.0,
            CustomerInteractionType.FEATURE_REQUEST: 1.0,
            CustomerInteractionType.COMPLAINT: -5.0,
            CustomerInteractionType.COMPLIMENT: 8.0
        }
        
        base_impact = base_impacts.get(interaction_type, 0.0)
        
        # Adjust based on satisfaction rating
        if satisfaction_rating is not None:
            if satisfaction_rating >= 8:
                satisfaction_multiplier = 1.5
            elif satisfaction_rating >= 6:
                satisfaction_multiplier = 1.0
            elif satisfaction_rating >= 4:
                satisfaction_multiplier = 0.5
            else:
                satisfaction_multiplier = -0.5
            
            return base_impact * satisfaction_multiplier
        
        return base_impact
    
    async def _trigger_stage_actions(self, customer_id: UUID, reseller_id: UUID, stage: str):
        """Trigger automated actions based on stage transition"""
        actions = {
            CustomerLifecycleStage.PROSPECT: [
                "Send welcome email sequence",
                "Schedule discovery call",
                "Add to nurture campaign"
            ],
            CustomerLifecycleStage.QUALIFIED: [
                "Send product demo invitation",
                "Assign account manager",
                "Create opportunity record"
            ],
            CustomerLifecycleStage.CLOSED_WON: [
                "Send congratulations email",
                "Start onboarding process",
                "Schedule kickoff call"
            ],
            CustomerLifecycleStage.ACTIVE: [
                "Enable regular health checks",
                "Start quarterly business reviews",
                "Monitor usage patterns"
            ],
            CustomerLifecycleStage.AT_RISK: [
                "Trigger intervention workflow",
                "Schedule retention call",
                "Offer value-add services"
            ],
            CustomerLifecycleStage.CHURNED: [
                "Send exit survey",
                "Document churn reason",
                "Add to win-back campaign"
            ]
        }
        
        # In production, these would trigger actual automated workflows
        stage_actions = actions.get(CustomerLifecycleStage(stage), [])
        print(f"🎯 Stage actions triggered for {customer_id} in stage {stage}:")
        for action in stage_actions:
            print(f"   - {action}")
    
    async def _get_stage_actions(self, stage: str) -> List[str]:
        """Get list of actions triggered for a stage"""
        actions = {
            CustomerLifecycleStage.PROSPECT: ["welcome_email", "discovery_call", "nurture_campaign"],
            CustomerLifecycleStage.QUALIFIED: ["demo_invitation", "assign_manager", "create_opportunity"],
            CustomerLifecycleStage.CLOSED_WON: ["congratulations_email", "onboarding_start", "kickoff_call"],
            CustomerLifecycleStage.ACTIVE: ["health_monitoring", "quarterly_reviews", "usage_tracking"],
            CustomerLifecycleStage.AT_RISK: ["intervention_workflow", "retention_call", "value_add_offer"],
            CustomerLifecycleStage.CHURNED: ["exit_survey", "churn_documentation", "winback_campaign"]
        }
        
        return actions.get(CustomerLifecycleStage(stage), [])
    
    async def _trigger_health_alert(self, customer_id: UUID, reseller_id: UUID, score: float, alert_type: str):
        """Trigger alerts for health score issues"""
        print(f"🚨 Health Alert for {customer_id}: {alert_type} (Score: {score})")
        # In production, this would send notifications, create tasks, etc.
    
    async def _generate_customer_recommendations(
        self,
        lifecycle_record: CustomerLifecycleRecord,
        recent_interactions: List[CustomerInteraction]
    ) -> List[str]:
        """Generate recommendations based on customer data"""
        recommendations = []
        
        if lifecycle_record.health_score < 50:
            recommendations.append("Schedule immediate check-in call to address concerns")
        
        if len(recent_interactions) == 0:
            recommendations.append("Reach out to maintain regular communication")
        
        if lifecycle_record.engagement_score < 40:
            recommendations.append("Provide additional training or support resources")
        
        return recommendations
    
    async def _get_suggested_next_actions(self, lifecycle_record: CustomerLifecycleRecord) -> List[str]:
        """Get suggested next actions based on current state"""
        stage = lifecycle_record.current_stage
        
        next_actions = {
            CustomerLifecycleStage.PROSPECT: ["Qualify needs", "Schedule demo"],
            CustomerLifecycleStage.QUALIFIED: ["Send proposal", "Address objections"],
            CustomerLifecycleStage.ACTIVE: ["Check satisfaction", "Identify expansion opportunities"],
            CustomerLifecycleStage.AT_RISK: ["Address concerns", "Offer solutions"]
        }
        
        return next_actions.get(CustomerLifecycleStage(stage), ["Monitor progress"])


# Export classes
__all__ = [
    "CustomerLifecycleStage",
    "CustomerHealthScore", 
    "CustomerInteractionType",
    "CustomerLifecycleRecord",
    "CustomerInteraction",
    "CustomerLifecycleManager"
]