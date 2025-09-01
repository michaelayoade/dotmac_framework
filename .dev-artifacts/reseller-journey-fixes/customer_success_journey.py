"""
Customer Success Journey Implementation
Extends journey orchestration with post-sale customer lifecycle management
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.database.base import Base
from dotmac_isp.shared.base_service import BaseService


class CustomerHealthStatus(str, Enum):
    HEALTHY = "healthy"
    AT_RISK = "at_risk"
    CRITICAL = "critical"
    CHURNED = "churned"


class ExpansionOpportunityType(str, Enum):
    SERVICE_UPGRADE = "service_upgrade"
    ADDITIONAL_LOCATIONS = "additional_locations"
    NEW_SERVICES = "new_services"
    VOLUME_INCREASE = "volume_increase"


class CustomerSuccessMetrics(BaseModel):
    customer_id: str
    health_score: float = Field(ge=0, le=10, description="Customer health score 0-10")
    usage_trend: str = Field(..., regex="^(increasing|stable|decreasing)$")
    last_interaction: datetime
    support_tickets_30d: int = Field(ge=0)
    payment_history_score: float = Field(ge=0, le=10)
    service_adoption_rate: float = Field(ge=0, le=1)
    nps_score: Optional[int] = Field(None, ge=-100, le=100)
    contract_renewal_date: Optional[datetime] = None
    expansion_opportunities: List[ExpansionOpportunityType] = []


class CustomerSuccessJourneyService(BaseService):
    """Service for managing customer success journeys and lifecycle automation"""
    
    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        super().__init__(db, tenant_id)
        self.journey_templates = self._initialize_journey_templates()
    
    def _initialize_journey_templates(self) -> Dict[str, Any]:
        """Initialize customer success journey templates"""
        return {
            "CUSTOMER_SUCCESS_MONITORING": {
                "id": "customer_success_monitoring",
                "name": "Customer Success Monitoring Journey",
                "description": "Continuous monitoring and proactive success management",
                "category": "customer_success",
                "version": "1.0.0",
                "steps": [
                    {
                        "id": "health_assessment",
                        "name": "Customer Health Assessment",
                        "description": "Analyze customer health metrics and identify risk factors",
                        "stage": "monitoring",
                        "order": 1,
                        "type": "automated",
                        "packageName": "customer-success",
                        "actionType": "assess_customer_health",
                        "estimatedDuration": 5,
                        "triggers": [
                            "weekly_health_check",
                            "usage_anomaly_detected",
                            "support_ticket_threshold"
                        ],
                        "integration": {
                            "service": "customer_success_service",
                            "method": "assess_customer_health"
                        }
                    },
                    {
                        "id": "risk_identification",
                        "name": "Risk Identification",
                        "description": "Identify at-risk customers and categorize risk factors",
                        "stage": "monitoring",
                        "order": 2,
                        "type": "automated",
                        "packageName": "customer-success",
                        "actionType": "identify_risks",
                        "estimatedDuration": 10,
                        "dependencies": ["health_assessment"],
                        "conditions": [
                            {"field": "health_score", "operator": "less_than", "value": 7.0}
                        ]
                    },
                    {
                        "id": "intervention_planning",
                        "name": "Intervention Planning",
                        "description": "Create intervention plan for at-risk customers",
                        "stage": "intervention",
                        "order": 3,
                        "type": "automated",
                        "packageName": "customer-success",
                        "actionType": "plan_intervention",
                        "estimatedDuration": 15,
                        "dependencies": ["risk_identification"],
                        "conditions": [
                            {"field": "health_status", "operator": "equals", "value": "at_risk"}
                        ]
                    },
                    {
                        "id": "success_outreach",
                        "name": "Success Team Outreach",
                        "description": "Proactive outreach by customer success team",
                        "stage": "intervention",
                        "order": 4,
                        "type": "manual",
                        "packageName": "communication-system",
                        "actionType": "schedule_outreach",
                        "estimatedDuration": 30,
                        "dependencies": ["intervention_planning"]
                    }
                ],
                "triggers": [
                    {
                        "id": "weekly_health_check",
                        "name": "Weekly Health Check",
                        "type": "schedule",
                        "schedule": "0 9 * * MON",  # Every Monday at 9 AM
                        "isActive": True
                    },
                    {
                        "id": "usage_drop_trigger",
                        "name": "Usage Drop Detected",
                        "type": "event",
                        "event": "customer:usage_drop_detected",
                        "isActive": True
                    }
                ]
            },
            
            "EXPANSION_OPPORTUNITY": {
                "id": "expansion_opportunity",
                "name": "Expansion Opportunity Journey",
                "description": "Identify and pursue revenue expansion opportunities",
                "category": "growth",
                "version": "1.0.0",
                "steps": [
                    {
                        "id": "opportunity_analysis",
                        "name": "Opportunity Analysis",
                        "description": "Analyze customer data for expansion opportunities",
                        "stage": "analysis",
                        "order": 1,
                        "type": "automated",
                        "packageName": "analytics",
                        "actionType": "analyze_expansion_opportunities",
                        "estimatedDuration": 10
                    },
                    {
                        "id": "opportunity_scoring",
                        "name": "Opportunity Scoring",
                        "description": "Score and prioritize expansion opportunities",
                        "stage": "analysis",
                        "order": 2,
                        "type": "automated",
                        "packageName": "analytics",
                        "actionType": "score_opportunities",
                        "estimatedDuration": 5,
                        "dependencies": ["opportunity_analysis"]
                    },
                    {
                        "id": "sales_handoff",
                        "name": "Sales Team Handoff",
                        "description": "Transfer qualified opportunities to sales team",
                        "stage": "handoff",
                        "order": 3,
                        "type": "integration",
                        "packageName": "crm",
                        "actionType": "create_expansion_opportunity",
                        "estimatedDuration": 15,
                        "dependencies": ["opportunity_scoring"],
                        "conditions": [
                            {"field": "opportunity_score", "operator": "greater_than", "value": 7.0}
                        ]
                    }
                ],
                "triggers": [
                    {
                        "id": "monthly_expansion_analysis",
                        "name": "Monthly Expansion Analysis",
                        "type": "schedule",
                        "schedule": "0 10 1 * *",  # 1st of each month at 10 AM
                        "isActive": True
                    }
                ]
            },
            
            "RENEWAL_MANAGEMENT": {
                "id": "renewal_management",
                "name": "Contract Renewal Management",
                "description": "Proactive contract renewal management and retention",
                "category": "retention",
                "version": "1.0.0",
                "steps": [
                    {
                        "id": "renewal_planning",
                        "name": "Renewal Planning",
                        "description": "Plan renewal approach based on customer health",
                        "stage": "planning",
                        "order": 1,
                        "type": "automated",
                        "packageName": "customer-success",
                        "actionType": "plan_renewal",
                        "estimatedDuration": 20
                    },
                    {
                        "id": "renewal_outreach",
                        "name": "Renewal Outreach",
                        "description": "Initiate renewal conversation with customer",
                        "stage": "engagement",
                        "order": 2,
                        "type": "manual",
                        "packageName": "communication-system",
                        "actionType": "initiate_renewal_conversation",
                        "estimatedDuration": 45,
                        "dependencies": ["renewal_planning"]
                    },
                    {
                        "id": "renewal_negotiation",
                        "name": "Renewal Negotiation",
                        "description": "Negotiate renewal terms and pricing",
                        "stage": "negotiation",
                        "order": 3,
                        "type": "manual",
                        "packageName": "business-logic",
                        "actionType": "negotiate_renewal",
                        "estimatedDuration": 60,
                        "dependencies": ["renewal_outreach"]
                    },
                    {
                        "id": "renewal_completion",
                        "name": "Renewal Completion",
                        "description": "Finalize renewal and update systems",
                        "stage": "completion",
                        "order": 4,
                        "type": "integration",
                        "packageName": "billing-system",
                        "actionType": "process_renewal",
                        "estimatedDuration": 30,
                        "dependencies": ["renewal_negotiation"]
                    }
                ],
                "triggers": [
                    {
                        "id": "renewal_60_days",
                        "name": "60 Days Before Renewal",
                        "type": "event",
                        "event": "contract:renewal_approaching_60d",
                        "isActive": True
                    }
                ]
            }
        }
    
    @standard_exception_handler
    async def assess_customer_health(self, customer_id: str) -> CustomerSuccessMetrics:
        """Assess overall customer health and generate metrics"""
        
        # Mock implementation - would integrate with actual customer data
        health_metrics = CustomerSuccessMetrics(
            customer_id=customer_id,
            health_score=8.2,
            usage_trend="stable",
            last_interaction=datetime.utcnow() - timedelta(days=3),
            support_tickets_30d=2,
            payment_history_score=9.5,
            service_adoption_rate=0.85,
            nps_score=8,
            contract_renewal_date=datetime.utcnow() + timedelta(days=90),
            expansion_opportunities=[
                ExpansionOpportunityType.SERVICE_UPGRADE,
                ExpansionOpportunityType.ADDITIONAL_LOCATIONS
            ]
        )
        
        return health_metrics
    
    @standard_exception_handler
    async def identify_at_risk_customers(self) -> List[Dict[str, Any]]:
        """Identify customers at risk of churn"""
        
        # Mock implementation - would query actual customer data
        at_risk_customers = [
            {
                "customer_id": "cust_001",
                "health_score": 5.2,
                "risk_factors": [
                    "declining_usage",
                    "payment_delays",
                    "increased_support_tickets"
                ],
                "recommended_actions": [
                    "schedule_success_call",
                    "review_service_fit",
                    "offer_training_session"
                ]
            }
        ]
        
        return at_risk_customers
    
    @standard_exception_handler
    async def analyze_expansion_opportunities(self, customer_id: str) -> List[Dict[str, Any]]:
        """Analyze potential expansion opportunities for customer"""
        
        # Mock implementation - would analyze usage patterns, growth, etc.
        opportunities = [
            {
                "type": ExpansionOpportunityType.SERVICE_UPGRADE,
                "description": "Customer showing high bandwidth utilization - ready for upgrade",
                "potential_revenue": 500.00,
                "confidence_score": 8.5,
                "timeline": "30_days"
            },
            {
                "type": ExpansionOpportunityType.ADDITIONAL_LOCATIONS,
                "description": "Customer mentioned expansion plans in support ticket",
                "potential_revenue": 2000.00,
                "confidence_score": 6.8,
                "timeline": "90_days"
            }
        ]
        
        return opportunities
    
    @standard_exception_handler
    async def create_intervention_plan(self, customer_id: str, risk_factors: List[str]) -> Dict[str, Any]:
        """Create intervention plan for at-risk customer"""
        
        intervention_plan = {
            "customer_id": customer_id,
            "plan_id": f"plan_{datetime.utcnow().strftime('%Y%m%d')}_{customer_id}",
            "risk_level": "medium",
            "interventions": [
                {
                    "type": "success_call",
                    "priority": "high",
                    "due_date": datetime.utcnow() + timedelta(days=3),
                    "assigned_to": "success_team"
                },
                {
                    "type": "usage_review",
                    "priority": "medium",
                    "due_date": datetime.utcnow() + timedelta(days=7),
                    "assigned_to": "technical_team"
                }
            ],
            "success_metrics": {
                "target_health_score": 8.0,
                "target_engagement_increase": 0.3,
                "review_date": datetime.utcnow() + timedelta(days=30)
            }
        }
        
        return intervention_plan
    
    @standard_exception_handler
    async def track_journey_progress(self, journey_id: str) -> Dict[str, Any]:
        """Track progress of customer success journeys"""
        
        # Mock implementation - would query actual journey data
        progress = {
            "journey_id": journey_id,
            "status": "in_progress",
            "completed_steps": 2,
            "total_steps": 4,
            "current_step": "intervention_planning",
            "estimated_completion": datetime.utcnow() + timedelta(days=5),
            "success_indicators": {
                "health_score_improvement": 1.2,
                "engagement_increase": 0.15,
                "risk_reduction": True
            }
        }
        
        return progress


# Journey template exports for integration with orchestrator
CUSTOMER_SUCCESS_JOURNEY_TEMPLATES = {
    "CUSTOMER_SUCCESS_MONITORING": CustomerSuccessJourneyService(None)._initialize_journey_templates()["CUSTOMER_SUCCESS_MONITORING"],
    "EXPANSION_OPPORTUNITY": CustomerSuccessJourneyService(None)._initialize_journey_templates()["EXPANSION_OPPORTUNITY"],
    "RENEWAL_MANAGEMENT": CustomerSuccessJourneyService(None)._initialize_journey_templates()["RENEWAL_MANAGEMENT"]
}

__all__ = [
    "CustomerHealthStatus",
    "ExpansionOpportunityType", 
    "CustomerSuccessMetrics",
    "CustomerSuccessJourneyService",
    "CUSTOMER_SUCCESS_JOURNEY_TEMPLATES"
]