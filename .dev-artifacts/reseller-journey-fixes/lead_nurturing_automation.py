"""
Lead Nurturing Automation Service
Implements automated lead nurturing workflows with email sequences, behavioral triggers, and conversion optimization
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
import json

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.database.base import Base
from dotmac_isp.shared.base_service import BaseService


class LeadSource(str, Enum):
    WEBSITE_FORM = "website_form"
    SOCIAL_MEDIA = "social_media"
    REFERRAL = "referral"
    COLD_OUTREACH = "cold_outreach"
    WEBINAR = "webinar"
    CONTENT_DOWNLOAD = "content_download"
    TRADE_SHOW = "trade_show"
    PARTNER_REFERRAL = "partner_referral"


class LeadScore(str, Enum):
    COLD = "cold"          # 0-25
    WARM = "warm"          # 26-50  
    HOT = "hot"            # 51-75
    QUALIFIED = "qualified" # 76-100


class LeadStage(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATING = "negotiating"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class NurtureSequenceType(str, Enum):
    WELCOME_SERIES = "welcome_series"
    EDUCATIONAL_CONTENT = "educational_content"
    PRODUCT_DEMO = "product_demo"
    CASE_STUDIES = "case_studies"
    PRICING_SEQUENCE = "pricing_sequence"
    ABANDONMENT_RECOVERY = "abandonment_recovery"
    RE_ENGAGEMENT = "re_engagement"


class CommunicationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PHONE_CALL = "phone_call"
    SOCIAL_MEDIA = "social_media"
    DIRECT_MAIL = "direct_mail"


class LeadBehavior(BaseModel):
    lead_id: str
    behavior_type: str = Field(..., regex="^(email_open|email_click|website_visit|form_submit|download|video_watch)$")
    timestamp: datetime
    details: Dict[str, Any] = {}
    score_impact: int = Field(ge=0, le=10, description="Impact on lead score")


class LeadProfile(BaseModel):
    lead_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    industry: Optional[str] = None
    lead_source: LeadSource
    current_score: int = Field(ge=0, le=100)
    lead_score_category: LeadScore
    current_stage: LeadStage
    assigned_reseller_id: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    interests: List[str] = []
    pain_points: List[str] = []
    budget_range: Optional[str] = None
    decision_timeframe: Optional[str] = None
    behavioral_data: List[LeadBehavior] = []


class NurtureEmailTemplate(BaseModel):
    template_id: str
    sequence_type: NurtureSequenceType
    sequence_position: int = Field(ge=1, le=20)
    subject_line: str
    email_content: str
    send_delay_hours: int = Field(ge=0, le=8760)  # Max 1 year
    trigger_conditions: List[Dict[str, Any]] = []
    personalization_fields: List[str] = []
    call_to_action: Optional[str] = None


class NurtureSequence(BaseModel):
    sequence_id: str
    sequence_name: str
    sequence_type: NurtureSequenceType
    target_audience: Dict[str, Any] = {}  # Criteria for who enters sequence
    email_templates: List[NurtureEmailTemplate] = []
    is_active: bool = True
    success_metrics: Dict[str, float] = {}


class LeadInteraction(BaseModel):
    interaction_id: str
    lead_id: str
    reseller_id: str
    interaction_type: str = Field(..., regex="^(email|call|meeting|demo|proposal)$")
    interaction_date: datetime
    outcome: Optional[str] = None
    notes: Optional[str] = None
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None
    score_change: int = Field(ge=-10, le=10)


class ConversionFunnelStage(BaseModel):
    stage_name: str
    leads_entered: int = Field(ge=0)
    leads_converted: int = Field(ge=0)
    conversion_rate: float = Field(ge=0, le=1)
    average_time_in_stage_days: float = Field(ge=0)
    drop_off_rate: float = Field(ge=0, le=1)


class LeadNurturingService(BaseService):
    """Service for automated lead nurturing and conversion optimization"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, tenant_id)
        self.nurture_sequences = self._initialize_nurture_sequences()
        self.scoring_rules = self._initialize_scoring_rules()
        self.journey_templates = self._initialize_journey_templates()
    
    def _initialize_nurture_sequences(self) -> Dict[str, NurtureSequence]:
        """Initialize automated nurture sequences"""
        
        return {
            "welcome_series": NurtureSequence(
                sequence_id="welcome_001",
                sequence_name="New Lead Welcome Series",
                sequence_type=NurtureSequenceType.WELCOME_SERIES,
                target_audience={"lead_source": ["website_form", "content_download"]},
                email_templates=[
                    NurtureEmailTemplate(
                        template_id="welcome_01",
                        sequence_type=NurtureSequenceType.WELCOME_SERIES,
                        sequence_position=1,
                        subject_line="Welcome to {{company_name}} - Your ISP Journey Starts Here",
                        email_content="""
                        Hi {{first_name}},
                        
                        Welcome to {{company_name}}! We're excited to help you find the perfect internet solution.
                        
                        Over the next few days, we'll share valuable information to help you:
                        • Understand your connectivity options
                        • Compare service plans
                        • Learn about our installation process
                        
                        Your dedicated advisor {{reseller_name}} will be in touch within 24 hours.
                        
                        Best regards,
                        The {{company_name}} Team
                        """,
                        send_delay_hours=1,
                        personalization_fields=["first_name", "company_name", "reseller_name"],
                        call_to_action="Schedule a Free Consultation"
                    ),
                    NurtureEmailTemplate(
                        template_id="welcome_02",
                        sequence_type=NurtureSequenceType.WELCOME_SERIES,
                        sequence_position=2,
                        subject_line="{{first_name}}, Here's What Makes Us Different",
                        email_content="""
                        Hi {{first_name}},
                        
                        Choosing an internet provider is a big decision. Here's what sets us apart:
                        
                        ✓ 99.9% uptime guarantee
                        ✓ 24/7 local customer support
                        ✓ No long-term contracts required
                        ✓ Free installation and setup
                        
                        See what our customers are saying: [testimonial links]
                        
                        Questions? Reply to this email or call {{support_phone}}.
                        """,
                        send_delay_hours=48,
                        call_to_action="View Customer Reviews"
                    ),
                    NurtureEmailTemplate(
                        template_id="welcome_03",
                        sequence_type=NurtureSequenceType.WELCOME_SERIES,
                        sequence_position=3,
                        subject_line="Ready for Faster Internet? Let's Talk Pricing",
                        email_content="""
                        Hi {{first_name}},
                        
                        Ready to see how much you could save with better internet?
                        
                        Our most popular plans:
                        • Residential: Starting at $49/month
                        • Business: Starting at $89/month  
                        • Enterprise: Custom pricing available
                        
                        Schedule a quick call with {{reseller_name}} to:
                        • Get a personalized quote
                        • Check availability at your location
                        • Learn about current promotions
                        """,
                        send_delay_hours=120,
                        call_to_action="Get My Custom Quote"
                    )
                ],
                success_metrics={"open_rate": 0.45, "click_rate": 0.18, "conversion_rate": 0.12}
            ),
            
            "educational_content": NurtureSequence(
                sequence_id="education_001", 
                sequence_name="ISP Education Series",
                sequence_type=NurtureSequenceType.EDUCATIONAL_CONTENT,
                target_audience={"lead_score_category": ["cold", "warm"]},
                email_templates=[
                    NurtureEmailTemplate(
                        template_id="edu_01",
                        sequence_type=NurtureSequenceType.EDUCATIONAL_CONTENT,
                        sequence_position=1,
                        subject_line="Fiber vs Cable Internet: Which is Right for You?",
                        email_content="""
                        Hi {{first_name}},
                        
                        Confused about internet options? You're not alone!
                        
                        Here's a simple breakdown:
                        
                        FIBER INTERNET:
                        ✓ Fastest speeds (up to 1 Gig)
                        ✓ Most reliable connection
                        ✓ Same upload/download speeds
                        ✓ Future-proof technology
                        
                        CABLE INTERNET:
                        ✓ Widely available
                        ✓ Good for basic needs
                        ✓ More affordable entry point
                        ✗ Slower upload speeds
                        
                        [Download our detailed comparison guide]
                        """,
                        send_delay_hours=24,
                        call_to_action="Download Comparison Guide"
                    )
                ]
            ),
            
            "abandonment_recovery": NurtureSequence(
                sequence_id="abandon_001",
                sequence_name="Quote Abandonment Recovery",
                sequence_type=NurtureSequenceType.ABANDONMENT_RECOVERY,
                target_audience={"behavior": "quote_abandoned"},
                email_templates=[
                    NurtureEmailTemplate(
                        template_id="abandon_01",
                        sequence_type=NurtureSequenceType.ABANDONMENT_RECOVERY,
                        sequence_position=1,
                        subject_line="{{first_name}}, You Were So Close! Complete Your Quote?",
                        email_content="""
                        Hi {{first_name}},
                        
                        I noticed you started getting a quote but didn't finish. No worries - it happens!
                        
                        Your partially completed quote:
                        • Service Type: {{service_type}}
                        • Location: {{location}}
                        • Estimated Monthly Cost: {{estimated_cost}}
                        
                        Complete your quote in just 2 minutes and get:
                        ✓ Instant pricing
                        ✓ Availability confirmation  
                        ✓ Special promotion eligibility
                        
                        [Complete My Quote Now]
                        """,
                        send_delay_hours=4,
                        call_to_action="Complete Quote"
                    )
                ]
            )
        }
    
    def _initialize_scoring_rules(self) -> Dict[str, int]:
        """Initialize lead scoring rules"""
        
        return {
            # Behavioral scoring
            "email_open": 2,
            "email_click": 5,
            "website_visit": 3,
            "pricing_page_visit": 8,
            "contact_form_submit": 15,
            "quote_request": 20,
            "whitepaper_download": 10,
            "video_watch": 7,
            "demo_request": 25,
            
            # Profile scoring
            "has_company": 10,
            "has_phone": 5,
            "decision_maker_title": 15,
            "enterprise_industry": 20,
            "high_budget_range": 25,
            "urgent_timeframe": 20,
            
            # Engagement scoring
            "multiple_page_visits": 10,
            "return_visitor": 8,
            "social_media_engagement": 5,
            "referral_source": 15
        }
    
    def _initialize_journey_templates(self) -> Dict[str, Any]:
        """Initialize lead nurturing journey templates"""
        
        return {
            "LEAD_NURTURING": {
                "id": "lead_nurturing_automation",
                "name": "Lead Nurturing Automation Journey",
                "description": "Automated lead nurturing with behavioral triggers and scoring",
                "category": "lead_nurturing",
                "version": "1.0.0",
                "steps": [
                    {
                        "id": "lead_scoring_update",
                        "name": "Update Lead Score",
                        "description": "Calculate and update lead score based on recent activities",
                        "stage": "scoring",
                        "order": 1,
                        "type": "automated",
                        "packageName": "lead-nurturing",
                        "actionType": "update_lead_score",
                        "estimatedDuration": 5,
                        "integration": {
                            "service": "lead_nurturing_service",
                            "method": "calculate_lead_score"
                        }
                    },
                    {
                        "id": "sequence_enrollment",
                        "name": "Nurture Sequence Enrollment",
                        "description": "Enroll lead in appropriate nurture sequence",
                        "stage": "nurturing",
                        "order": 2,
                        "type": "automated",
                        "packageName": "lead-nurturing", 
                        "actionType": "enroll_in_sequence",
                        "estimatedDuration": 10,
                        "dependencies": ["lead_scoring_update"]
                    },
                    {
                        "id": "reseller_notification",
                        "name": "Reseller Notification",
                        "description": "Notify assigned reseller of high-score leads",
                        "stage": "handoff",
                        "order": 3,
                        "type": "automated",
                        "packageName": "communication-system",
                        "actionType": "notify_reseller",
                        "estimatedDuration": 5,
                        "dependencies": ["sequence_enrollment"],
                        "conditions": [
                            {"field": "lead_score", "operator": "greater_than", "value": 75}
                        ]
                    }
                ],
                "triggers": [
                    {
                        "id": "lead_behavior_trigger",
                        "name": "Lead Behavior Change",
                        "type": "event",
                        "event": "lead:behavior_recorded",
                        "isActive": True
                    },
                    {
                        "id": "daily_lead_scoring",
                        "name": "Daily Lead Score Update",
                        "type": "schedule",
                        "schedule": "0 10 * * *",  # Daily at 10 AM
                        "isActive": True
                    }
                ]
            }
        }
    
    @standard_exception_handler
    async def calculate_lead_score(self, lead_id: str) -> Dict[str, Any]:
        """Calculate comprehensive lead score based on profile and behavior"""
        
        # Get lead profile and behaviors
        lead_profile = await self._get_lead_profile(lead_id)
        
        score = 0
        scoring_breakdown = {}
        
        # Profile-based scoring
        if lead_profile.company:
            score += self.scoring_rules["has_company"]
            scoring_breakdown["has_company"] = self.scoring_rules["has_company"]
        
        if lead_profile.phone:
            score += self.scoring_rules["has_phone"]
            scoring_breakdown["has_phone"] = self.scoring_rules["has_phone"]
        
        if lead_profile.job_title and any(title in lead_profile.job_title.lower() for title in ["ceo", "cto", "manager", "director"]):
            score += self.scoring_rules["decision_maker_title"]
            scoring_breakdown["decision_maker_title"] = self.scoring_rules["decision_maker_title"]
        
        # Behavioral scoring
        for behavior in lead_profile.behavioral_data:
            behavior_score = self.scoring_rules.get(behavior.behavior_type, 0)
            score += behavior_score
            
            behavior_key = f"behavior_{behavior.behavior_type}"
            scoring_breakdown[behavior_key] = scoring_breakdown.get(behavior_key, 0) + behavior_score
        
        # Engagement recency boost
        recent_activity = datetime.utcnow() - lead_profile.last_activity
        if recent_activity.days <= 1:
            score += 10  # Recent activity bonus
            scoring_breakdown["recent_activity_bonus"] = 10
        elif recent_activity.days <= 7:
            score += 5   # Weekly activity bonus
            scoring_breakdown["weekly_activity_bonus"] = 5
        
        # Determine score category
        if score >= 76:
            score_category = LeadScore.QUALIFIED
        elif score >= 51:
            score_category = LeadScore.HOT
        elif score >= 26:
            score_category = LeadScore.WARM
        else:
            score_category = LeadScore.COLD
        
        return {
            "lead_id": lead_id,
            "total_score": min(score, 100),  # Cap at 100
            "score_category": score_category,
            "scoring_breakdown": scoring_breakdown,
            "previous_score": lead_profile.current_score,
            "score_change": min(score, 100) - lead_profile.current_score,
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    @standard_exception_handler
    async def enroll_lead_in_nurture_sequence(self, lead_id: str, sequence_type: NurtureSequenceType) -> Dict[str, Any]:
        """Enroll lead in appropriate nurture sequence"""
        
        lead_profile = await self._get_lead_profile(lead_id)
        sequence = self.nurture_sequences.get(sequence_type.value)
        
        if not sequence:
            raise ValueError(f"Nurture sequence {sequence_type} not found")
        
        # Check if lead meets target audience criteria
        if not self._lead_matches_audience(lead_profile, sequence.target_audience):
            return {"enrolled": False, "reason": "Lead doesn't match target audience"}
        
        # Schedule sequence emails
        scheduled_emails = []
        for template in sequence.email_templates:
            send_time = datetime.utcnow() + timedelta(hours=template.send_delay_hours)
            
            scheduled_email = {
                "email_id": f"email_{lead_id}_{template.template_id}",
                "template_id": template.template_id,
                "recipient": lead_profile.email,
                "scheduled_send_time": send_time.isoformat(),
                "personalization_data": {
                    "first_name": lead_profile.first_name,
                    "last_name": lead_profile.last_name,
                    "company_name": lead_profile.company or "your organization",
                    "reseller_name": "Your Advisor"  # Would get from assigned reseller
                },
                "status": "scheduled"
            }
            scheduled_emails.append(scheduled_email)
        
        return {
            "enrolled": True,
            "sequence_id": sequence.sequence_id,
            "sequence_name": sequence.sequence_name,
            "scheduled_emails": len(scheduled_emails),
            "enrollment_date": datetime.utcnow().isoformat(),
            "estimated_completion": (datetime.utcnow() + timedelta(hours=max(t.send_delay_hours for t in sequence.email_templates))).isoformat()
        }
    
    @standard_exception_handler
    async def track_lead_behavior(self, lead_id: str, behavior: LeadBehavior) -> Dict[str, Any]:
        """Track and process lead behavioral data"""
        
        # Update lead score based on behavior
        score_update = await self.calculate_lead_score(lead_id)
        
        # Check for sequence triggers
        triggered_sequences = []
        
        if behavior.behavior_type == "quote_abandoned":
            # Trigger abandonment recovery sequence
            enrollment = await self.enroll_lead_in_nurture_sequence(lead_id, NurtureSequenceType.ABANDONMENT_RECOVERY)
            if enrollment["enrolled"]:
                triggered_sequences.append("abandonment_recovery")
        
        elif behavior.behavior_type == "demo_request":
            # High-intent behavior - notify reseller immediately
            await self._notify_reseller_urgent(lead_id, "Demo request submitted")
        
        elif behavior.behavior_type == "pricing_page_visit" and behavior.details.get("time_on_page", 0) > 60:
            # Extended pricing page visit - high intent
            triggered_sequences.append("pricing_sequence")
        
        return {
            "behavior_tracked": True,
            "behavior_type": behavior.behavior_type,
            "score_impact": behavior.score_impact,
            "new_score": score_update["total_score"],
            "score_change": score_update["score_change"],
            "triggered_sequences": triggered_sequences,
            "tracked_at": datetime.utcnow().isoformat()
        }
    
    @standard_exception_handler
    async def analyze_conversion_funnel(self) -> Dict[str, Any]:
        """Analyze lead conversion funnel performance"""
        
        # Mock implementation - would query actual lead progression data
        funnel_stages = [
            ConversionFunnelStage(
                stage_name="Lead Generated",
                leads_entered=1000,
                leads_converted=850,
                conversion_rate=0.85,
                average_time_in_stage_days=0,
                drop_off_rate=0.15
            ),
            ConversionFunnelStage(
                stage_name="Qualified Lead",
                leads_entered=850,
                leads_converted=425,
                conversion_rate=0.50,
                average_time_in_stage_days=3.5,
                drop_off_rate=0.50
            ),
            ConversionFunnelStage(
                stage_name="Proposal Sent",
                leads_entered=425,
                leads_converted=255,
                conversion_rate=0.60,
                average_time_in_stage_days=7.2,
                drop_off_rate=0.40
            ),
            ConversionFunnelStage(
                stage_name="Customer",
                leads_entered=255,
                leads_converted=204,
                conversion_rate=0.80,
                average_time_in_stage_days=14.0,
                drop_off_rate=0.20
            )
        ]
        
        # Calculate overall funnel metrics
        total_leads = funnel_stages[0].leads_entered
        total_customers = funnel_stages[-1].leads_converted
        overall_conversion_rate = total_customers / total_leads
        
        # Identify bottlenecks (stages with lowest conversion rates)
        bottleneck_stages = sorted(funnel_stages, key=lambda x: x.conversion_rate)[:2]
        
        return {
            "funnel_analysis": {
                "total_leads": total_leads,
                "total_customers": total_customers,
                "overall_conversion_rate": overall_conversion_rate,
                "average_sales_cycle_days": sum(stage.average_time_in_stage_days for stage in funnel_stages)
            },
            "stage_performance": [
                {
                    "stage": stage.stage_name,
                    "conversion_rate": stage.conversion_rate,
                    "drop_off_rate": stage.drop_off_rate,
                    "avg_time_days": stage.average_time_in_stage_days
                }
                for stage in funnel_stages
            ],
            "bottlenecks": [
                {
                    "stage": stage.stage_name,
                    "conversion_rate": stage.conversion_rate,
                    "improvement_opportunity": f"Improve by {(0.8 - stage.conversion_rate) * 100:.1f}%"
                }
                for stage in bottleneck_stages
            ],
            "recommendations": [
                "Focus on qualifying lead stage - 50% conversion rate below target",
                "Implement faster follow-up for proposal stage",
                "Add nurture sequence for lost leads"
            ]
        }
    
    async def _get_lead_profile(self, lead_id: str) -> LeadProfile:
        """Get lead profile with behavioral data"""
        
        # Mock implementation - would query actual lead data
        return LeadProfile(
            lead_id=lead_id,
            first_name="John",
            last_name="Smith",
            email="john.smith@example.com",
            phone="555-123-4567",
            company="TechCorp Solutions",
            job_title="IT Director",
            industry="Technology",
            lead_source=LeadSource.WEBSITE_FORM,
            current_score=45,
            lead_score_category=LeadScore.WARM,
            current_stage=LeadStage.CONTACTED,
            created_at=datetime.utcnow() - timedelta(days=5),
            last_activity=datetime.utcnow() - timedelta(hours=2),
            interests=["fiber_internet", "business_solutions"],
            pain_points=["slow_connection", "unreliable_service"],
            budget_range="$100-500/month",
            decision_timeframe="1-3 months",
            behavioral_data=[
                LeadBehavior(
                    lead_id=lead_id,
                    behavior_type="email_open",
                    timestamp=datetime.utcnow() - timedelta(hours=1),
                    score_impact=2
                ),
                LeadBehavior(
                    lead_id=lead_id,
                    behavior_type="website_visit",
                    timestamp=datetime.utcnow() - timedelta(hours=2),
                    details={"page": "/pricing", "duration": 90},
                    score_impact=8
                )
            ]
        )
    
    def _lead_matches_audience(self, lead: LeadProfile, audience_criteria: Dict[str, Any]) -> bool:
        """Check if lead matches nurture sequence target audience"""
        
        for criterion, values in audience_criteria.items():
            if criterion == "lead_source":
                if lead.lead_source.value not in values:
                    return False
            elif criterion == "lead_score_category":
                if lead.lead_score_category.value not in values:
                    return False
            elif criterion == "behavior":
                # Check if lead has specific behavior
                behaviors = [b.behavior_type for b in lead.behavioral_data]
                if not any(behavior in behaviors for behavior in values):
                    return False
        
        return True
    
    async def _notify_reseller_urgent(self, lead_id: str, message: str):
        """Send urgent notification to assigned reseller"""
        
        # Mock implementation - would send actual notification
        print(f"URGENT: Lead {lead_id} - {message}")


# Journey template exports
LEAD_NURTURING_JOURNEY_TEMPLATES = {
    "LEAD_NURTURING": LeadNurturingService(None)._initialize_journey_templates()["LEAD_NURTURING"]
}

__all__ = [
    "LeadSource",
    "LeadScore", 
    "LeadStage",
    "NurtureSequenceType",
    "CommunicationChannel",
    "LeadBehavior",
    "LeadProfile",
    "NurtureEmailTemplate",
    "NurtureSequence",
    "LeadInteraction",
    "ConversionFunnelStage",
    "LeadNurturingService",
    "LEAD_NURTURING_JOURNEY_TEMPLATES"
]