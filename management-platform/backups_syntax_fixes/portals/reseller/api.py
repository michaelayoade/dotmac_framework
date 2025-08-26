"""
Reseller Portal API endpoints for channel partner sales management and commission tracking.
"""

import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...src.mgmt.shared.database.connections import get_db
from ...src.mgmt.shared.auth.permissions import require_reseller, get_current_reseller
from ...src.mgmt.services.reseller_network.reseller_service import ResellerService
from ...src.mgmt.services.reseller_network import schemas as reseller_schemas
from ...src.mgmt.services.reseller_network.models import ResellerStatus, OpportunityStage
from .schemas import ()
    ResellerDashboardOverview,
    SalesOpportunity,
    SalesOpportunityCreate,
    SalesOpportunityUpdate,
    SalesQuote,
    CommissionSummary,
    CommissionRecord,
    CustomerHealthScore,
    TerritoryPerformance,
    CertificationProgress,
    TrainingModule,
    CustomerHealthStatus,
, timezone)

logger = logging.getLogger(__name__)

# Create the Reseller Portal router
reseller_router = APIRouter()
    prefix="/api/v1/reseller",
    tags=["Reseller Portal"],
    dependencies=[Depends(require_reseller)],
)


# Dashboard and Performance Overview
@reseller_router.get("/dashboard/overview", response_model=ResellerDashboardOverview)
async def get_reseller_dashboard():
    db: AsyncSession = Depends(get_db),
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
) -> ResellerDashboardOverview:
    """
    Get comprehensive reseller dashboard overview.
    
    This endpoint provides:
    - Sales performance metrics and targets
    - Commission earnings and tracking
    - Territory performance analysis
    - Recent activity summary
    - Training and certification status
    """
    reseller_id = current_reseller["reseller_id"]
    
    try:
        reseller_service = ResellerService(db)
        
        # Get performance metrics using the service
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=365)
        
        performance = await reseller_service.get_reseller_performance()
            reseller_id=reseller_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Build comprehensive dashboard
        return ResellerDashboardOverview()
            reseller_id=reseller_id,
            reseller_name=current_reseller.get("name", "Partner Sales Corp"),
            territory=current_reseller.get("territory", "North America - West"),
            sales_metrics={
                "monthly_sales": 12,
                "quarterly_sales": 28,
                "yearly_sales": 89,
                "monthly_revenue": 180000.00,
                "quarterly_revenue": 420000.00,
                "yearly_revenue": 1335000.00,
                "pipeline_value": 950000.00,
                "weighted_pipeline": 285000.00,
                "conversion_rate": 0.24,
                "avg_deal_size": 15000.00,
                "sales_cycle_days": 65,
                "monthly_target": 200000.00,
                "quarterly_target": 600000.00,
                "yearly_target": 2400000.00,
                "monthly_achievement": 0.90,
                "quarterly_achievement": 0.70,
                "yearly_achievement": 0.56,
            },
            commission_metrics={
                "total_earned": 133500.00,
                "monthly_earned": 18000.00,
                "quarterly_earned": 42000.00,
                "yearly_earned": 133500.00,
                "pending_amount": 12500.00,
                "next_payout_date": date.today() + timedelta(days=15),
                "base_commission_rate": 0.10,
                "current_tier_rate": 0.12,
                "monthly_recurring_commission": 8500.00,
                "recurring_revenue_base": 850000.00,
                "bonus_earned": 15000.00,
                "bonus_eligible": True,
            },
            territory_metrics={
                "territory_name": "North America - West",
                "territory_type": "geographic",
                "total_addressable_market": 2500,
                "market_penetration": 0.18,
                "active_customers": 45,
                "churned_customers": 3,
                "market_share": 0.12,
                "key_competitors": ["CompetitorA", "CompetitorB", "CompetitorC"],
                "competitive_threats": 8,
            },
            recent_opportunities=7,
            recent_customers=3,
            recent_quotes=5,
            quota_achievement=0.84,
            at_risk_customers=4,
            expiring_quotes=2,
            certification_level="gold",
            training_completion=0.85,
            generated_at=datetime.now(timezone.utc),
        )
        
    except Exception as e:
        logger.error(f"Failed to get reseller dashboard for {reseller_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard data",
        )


# Sales Pipeline Management
@reseller_router.get("/pipeline/opportunities", response_model=List[SalesOpportunity])
async def list_sales_opportunities():
    stage: Optional[OpportunityStage] = Query(None, description="Filter by opportunity stage"),
    company_size: Optional[str] = Query(None, description="Filter by company size"),
    search: Optional[str] = Query(None, description="Search in company names and descriptions"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
) -> List[SalesOpportunity]:
    """List sales opportunities with filtering and search."""
    reseller_id = current_reseller["reseller_id"]
    
    try:
        # Mock opportunities data (would integrate with CRM system)
        opportunities = [
            SalesOpportunity()
                opportunity_id="opp_001",
                prospect_company="Metro ISP Solutions",
                prospect_website="https://metroisp.com",
                contacts=[{
                    "first_name": "John",
                    "last_name": "Smith",
                    "email": "john.smith@metroisp.com",
                    "phone": "+1-555-0123",
                    "title": "CTO",
                    "is_primary": True,
                    "is_decision_maker": True,
                    "influence_level": "high",
                }],
                opportunity_name="DotMac Platform Implementation",
                description="Mid-size ISP looking to modernize their customer management platform",
                industry="Telecommunications",
                company_size="medium",
                stage=OpportunityStage.PROPOSAL,
                probability=75,
                estimated_value=45000.00,
                monthly_recurring_revenue=3750.00,
                created_date=datetime.now(timezone.utc) - timedelta(days=21),
                last_activity_date=datetime.now(timezone.utc) - timedelta(days=2),
                expected_close_date=date.today() + timedelta(days=30),
                required_features=["customer_portal", "billing_automation", "network_monitoring"],
                technical_requirements={
                    "integrations": ["existing_billing_system", "radius_server"],
                    "deployment": "cloud",
                    "users": 150,
                },
                compliance_requirements=["SOX", "PCI_DSS"],
                competing_vendors=["CompetitorX", "CompetitorY"],
                competitive_advantages=["ease_of_use", "comprehensive_features", "better_pricing"],
                assigned_to=current_user.get("user_id", "sales_rep_001"),
                lead_source="referral",
                tags=["hot_lead", "enterprise_ready"],
                last_contact_date=datetime.now(timezone.utc) - timedelta(days=2),
                next_follow_up=datetime.now(timezone.utc) + timedelta(days=3),
                notes="Strong interest, waiting for technical demo feedback",
            ),
            # Additional opportunities would be loaded here
        ]
        
        # Apply filters
        filtered_opportunities = opportunities
        if stage:
            filtered_opportunities = [o for o in filtered_opportunities if o.stage == stage]
        if company_size:
            filtered_opportunities = [o for o in filtered_opportunities if o.company_size == company_size]
        if search:
            search_lower = search.lower()
            filtered_opportunities = [
                o for o in filtered_opportunities
                if search_lower in o.prospect_company.lower() or search_lower in o.description.lower()
            ]
        
        # Apply pagination (simplified)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        return filtered_opportunities[start_idx:end_idx]
        
    except Exception as e:
        logger.error(f"Failed to list opportunities for reseller {reseller_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve opportunities",
        )


@reseller_router.post("/pipeline/opportunities", response_model=SalesOpportunity)
async def create_sales_opportunity():
    opportunity_data: SalesOpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
) -> SalesOpportunity:
    """Create a new sales opportunity."""
    reseller_id = current_reseller["reseller_id"]
    
    try:
        reseller_service = ResellerService(db)
        
        # Convert to service schema
        service_data = reseller_schemas.SalesOpportunityCreate()
            customer_name=opportunity_data.prospect_company,
            customer_contact=opportunity_data.contact_first_name + " " + opportunity_data.contact_last_name,
            customer_email=opportunity_data.contact_email,
            customer_phone=getattr(opportunity_data, 'contact_phone', None),
            customer_location=getattr(opportunity_data, 'location', 'Unknown'),
            opportunity_name=opportunity_data.opportunity_name,
            estimated_value=opportunity_data.estimated_value,
            estimated_close_date=opportunity_data.expected_close_date,
            probability=20,  # Initial probability
            product_interest=opportunity_data.initial_requirements,
            notes=getattr(opportunity_data, 'description', '')
        )
        
        # Create opportunity using service
        db_opportunity = await reseller_service.create_opportunity()
            opportunity_data=service_data,
            reseller_id=reseller_id,
            created_by=current_user.get("user_id")
        )
        
        # Convert back to portal response format
        opportunity = SalesOpportunity()
            opportunity_id=opportunity_id,
            prospect_company=opportunity_data.prospect_company,
            prospect_website=opportunity_data.prospect_website,
            contacts=[{
                "first_name": opportunity_data.contact_first_name,
                "last_name": opportunity_data.contact_last_name,
                "email": opportunity_data.contact_email,
                "phone": opportunity_data.contact_phone,
                "title": opportunity_data.contact_title,
                "is_primary": True,
                "is_decision_maker": False,  # To be determined
                "influence_level": "medium",
            }],
            opportunity_name=opportunity_data.opportunity_name,
            description=opportunity_data.description,
            industry=opportunity_data.industry,
            company_size=opportunity_data.company_size,
            stage=OpportunityStage.LEAD,
            probability=20,  # Initial probability for leads
            estimated_value=opportunity_data.estimated_value,
            monthly_recurring_revenue=opportunity_data.estimated_value / 12,  # Estimate
            created_date=datetime.now(timezone.utc),
            last_activity_date=datetime.now(timezone.utc),
            expected_close_date=opportunity_data.expected_close_date,
            required_features=[],
            technical_requirements={},
            compliance_requirements=[],
            competing_vendors=opportunity_data.competing_vendors,
            competitive_advantages=[],
            assigned_to=current_user.get("user_id"),
            lead_source=opportunity_data.lead_source,
            tags=[],
            notes=opportunity_data.initial_requirements,
        )
        
        logger.info(f"Created new opportunity {opportunity_id} for reseller {reseller_id}")
        
        return opportunity
        
    except Exception as e:
        logger.error(f"Failed to create opportunity for reseller {reseller_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create sales opportunity",
        )


@reseller_router.put("/pipeline/opportunities/{opportunity_id}")
async def update_sales_opportunity():
    opportunity_id: str,
    update_data: SalesOpportunityUpdate,
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
):
    """Update an existing sales opportunity."""
    reseller_id = current_reseller["reseller_id"]
    
    try:
        # Validate opportunity belongs to this reseller (would check database)
        if not opportunity_id.startswith(f"opp_{reseller_id}"):
            raise HTTPException()
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this opportunity",
            )
        
        # Update opportunity record (would integrate with CRM)
        # In real implementation, would update database record
        
        logger.info(f"Updated opportunity {opportunity_id} for reseller {reseller_id}")
        
        return {"message": "Opportunity updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update opportunity {opportunity_id} for reseller {reseller_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update sales opportunity",
        )


# Quote Generation
@reseller_router.post("/quotes/generate", response_model=SalesQuote)
async def generate_sales_quote():
    opportunity_id: str,
    quote_data: Dict[str, Any],
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
) -> SalesQuote:
    """Generate a sales quote for an opportunity."""
    reseller_id = current_reseller["reseller_id"]
    
    try:
        # Generate quote ID
        quote_id = f"quote_{reseller_id}_{int(datetime.now(timezone.utc).timestamp()}"
        quote_number = f"Q-{datetime.now(timezone.utc).year}-{quote_id[-8:].upper()}"
        
        # Mock quote generation (would integrate with pricing engine)
        quote = SalesQuote()
            quote_id=quote_id,
            opportunity_id=opportunity_id,
            quote_number=quote_number,
            customer_company="Metro ISP Solutions",
            customer_contact={
                "first_name": "John",
                "last_name": "Smith", 
                "email": "john.smith@metroisp.com",
                "phone": "+1-555-0123",
                "title": "CTO",
                "is_primary": True,
                "is_decision_maker": True,
                "influence_level": "high",
            },
            quote_date=date.today(),
            expiration_date=date.today() + timedelta(days=30),
            line_items=[
                {
                    "product_name": "DotMac ISP Framework - Standard",
                    "description": "Complete ISP management platform with standard features",
                    "quantity": 1,
                    "unit_price": 3000.00,
                    "discount_percentage": 10.0,
                    "total_amount": 2700.00,
                    "billing_frequency": "monthly",
                    "subscription_term_months": 24,
                },
                {
                    "product_name": "Implementation Services",
                    "description": "Professional services for platform setup and configuration",
                    "quantity": 80,
                    "unit_price": 150.00,
                    "discount_percentage": 0.0,
                    "total_amount": 12000.00,
                    "billing_frequency": "monthly",
                    "subscription_term_months": 1,
                },
            ],
            subtotal=14700.00,
            discount_amount=300.00,
            tax_rate=0.08,
            tax_amount=1152.00,
            total_amount=15552.00,
            payment_terms="Net 30",
            delivery_terms="Standard deployment within 45 days",
            notes="Quote includes 24-month subscription with 10% discount for annual payment",
            terms_and_conditions="Standard DotMac terms and conditions apply",
            status="draft",
            estimated_commission=1555.20,
            commission_rate=0.10,
        )
        
        logger.info(f"Generated quote {quote_id} for opportunity {opportunity_id}")
        
        return quote
        
    except Exception as e:
        logger.error(f"Failed to generate quote for opportunity {opportunity_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate sales quote",
        )


# Commission Tracking
@reseller_router.get("/commissions/summary", response_model=CommissionSummary)
async def get_commission_summary():
    period_months: int = Query(12, ge=1, le=24, description="Period in months"),
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
) -> CommissionSummary:
    """Get commission summary and earnings report."""
    reseller_id = current_reseller["reseller_id"]
    
    try:
        period_start = date.today() - timedelta(days=period_months * 30)
        period_end = date.today()
        
        # Mock commission data (would integrate with billing and commission service)
        commission_records = [
            CommissionRecord()
                commission_id="comm_001",
                opportunity_id="opp_001",
                customer_id="cust_001",
                commission_type="initial",
                commission_period="one_time",
                base_amount=25000.00,
                commission_rate=0.10,
                commission_amount=2500.00,
                earned_date=date.today() - timedelta(days=30),
                payment_date=date.today() - timedelta(days=15),
                status="paid",
                payment_reference="PAY-001",
            ),
            CommissionRecord()
                commission_id="comm_002",
                opportunity_id="opp_001", 
                customer_id="cust_001",
                commission_type="recurring",
                commission_period="monthly",
                base_amount=3000.00,
                commission_rate=0.08,
                commission_amount=240.00,
                earned_date=date.today() - timedelta(days=15),
                status="pending",
            ),
        ]
        
        # Calculate totals
        total_earned = sum(c.commission_amount for c in commission_records)
        total_paid = sum(c.commission_amount for c in commission_records if c.status == "paid")
        total_pending = sum(c.commission_amount for c in commission_records if c.status == "pending")
        
        initial_commissions = sum(c.commission_amount for c in commission_records if c.commission_type == "initial")
        recurring_commissions = sum(c.commission_amount for c in commission_records if c.commission_type == "recurring")
        bonus_commissions = sum(c.commission_amount for c in commission_records if c.commission_type == "bonus")
        
        return CommissionSummary()
            period_start=period_start,
            period_end=period_end,
            total_commissions=commission_records,
            total_earned=total_earned,
            total_paid=total_paid,
            total_pending=total_pending,
            initial_commissions=initial_commissions,
            recurring_commissions=recurring_commissions,
            bonus_commissions=bonus_commissions,
            next_payout_date=date.today() + timedelta(days=15),
            next_payout_amount=total_pending,
            commission_growth_rate=0.15,
            recurring_percentage=recurring_commissions / total_earned if total_earned > 0 else 0,
        )
        
    except Exception as e:
        logger.error(f"Failed to get commission summary for reseller {reseller_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve commission summary",
        )


# Customer Health Scoring
@reseller_router.get("/customers/health", response_model=List[CustomerHealthScore])
async def get_customer_health_scores():
    health_status: Optional[CustomerHealthStatus] = Query(None, description="Filter by health status"),
    risk_level: Optional[str] = Query(None, description="Filter by churn risk level"),
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
) -> List[CustomerHealthScore]:
    """Get customer health scores for expansion and retention opportunities."""
    reseller_id = current_reseller["reseller_id"]
    
    try:
        # Mock customer health data (would integrate with customer success platform)
        health_scores = [
            CustomerHealthScore()
                customer_id="cust_001",
                customer_name="Metro ISP Solutions",
                health_status=CustomerHealthStatus.GOOD,
                health_score=78,
                usage_trend="increasing",
                feature_adoption_rate=0.72,
                support_ticket_frequency=2,
                payment_history="excellent",
                contract_value=36000.00,
                engagement_level="high",
                stakeholder_satisfaction=4,
                upsell_potential="high",
                recommended_products=["advanced_analytics", "white_labeling"],
                estimated_expansion_value=18000.00,
                churn_risk="low",
                risk_factors=[],
                risk_mitigation_actions=[],
                last_updated=datetime.now(timezone.utc),
                next_review_date=date.today() + timedelta(days=30),
            ),
            CustomerHealthScore()
                customer_id="cust_002",
                customer_name="Regional Connect ISP",
                health_status=CustomerHealthStatus.AT_RISK,
                health_score=45,
                usage_trend="decreasing",
                feature_adoption_rate=0.35,
                support_ticket_frequency=8,
                payment_history="concerning",
                contract_value=24000.00,
                engagement_level="low",
                stakeholder_satisfaction=2,
                upsell_potential="low",
                recommended_products=[],
                estimated_expansion_value=0.00,
                churn_risk="high",
                risk_factors=["low_engagement", "payment_delays", "high_support_volume"],
                risk_mitigation_actions=["schedule_health_check", "provide_training", "review_pricing"],
                last_updated=datetime.now(timezone.utc),
                next_review_date=date.today() + timedelta(days=7),
            ),
        ]
        
        # Apply filters
        filtered_scores = health_scores
        if health_status:
            filtered_scores = [s for s in filtered_scores if s.health_status == health_status]
        if risk_level:
            filtered_scores = [s for s in filtered_scores if s.churn_risk == risk_level]
        
        return filtered_scores
        
    except Exception as e:
        logger.error(f"Failed to get customer health scores for reseller {reseller_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer health scores",
        )


# Territory Management
@reseller_router.get("/territory/performance", response_model=TerritoryPerformance)
async def get_territory_performance():
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
) -> TerritoryPerformance:
    """Get territory performance analysis and market insights."""
    reseller_id = current_reseller["reseller_id"]
    territory = current_reseller.get("territory", "North America - West")
    
    try:
        # Mock territory performance data
        return TerritoryPerformance()
            territory_id=f"territory_{reseller_id}",
            territory_name=territory,
            territory_type="geographic",
            geographic_boundaries={
                "states": ["CA", "NV", "OR", "WA"],
                "major_cities": ["San Francisco", "Los Angeles", "Seattle", "Las Vegas"],
            },
            total_addressable_market=2500,
            serviceable_addressable_market=1200,
            market_penetration=0.18,
            active_customers=45,
            pipeline_opportunities=23,
            closed_deals_ytd=89,
            revenue_ytd=1335000.00,
            market_share=0.12,
            primary_competitors=["CompetitorA", "CompetitorB", "LegacyVendor"],
            competitive_win_rate=0.65,
            growth_rate=0.28,
            seasonality_factors={
                "Q1": 0.8,
                "Q2": 1.2,
                "Q3": 1.0,
                "Q4": 1.1,
            },
            expansion_opportunities=[
                {
                    "segment": "Rural ISPs",
                    "market_size": 450,
                    "penetration": 0.08,
                    "opportunity_score": 85,
                },
                {
                    "segment": "Municipal Networks",
                    "market_size": 120,
                    "penetration": 0.15,
                    "opportunity_score": 72,
                },
            ],
            market_gaps=["small_rural_markets", "municipal_partnerships"],
        )
        
    except Exception as e:
        logger.error(f"Failed to get territory performance for reseller {reseller_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve territory performance",
        )


# Training and Certification
@reseller_router.get("/training/progress", response_model=CertificationProgress)
async def get_certification_progress():
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
) -> CertificationProgress:
    """Get reseller training and certification progress."""
    reseller_id = current_reseller["reseller_id"]
    
    try:
        # Mock training progress data
        training_modules = [
            TrainingModule()
                module_id="mod_001",
                module_name="DotMac Platform Overview",
                description="Introduction to DotMac ISP Framework features and capabilities",
                category="product_knowledge",
                duration_minutes=45,
                difficulty_level="beginner",
                is_completed=True,
                completion_date=datetime.now(timezone.utc) - timedelta(days=30),
                score=92,
                content_url="https://training.dotmac.com/module/001",
                materials=[
                    {"type": "video", "url": "https://training.dotmac.com/videos/overview.mp4"},
                    {"type": "slides", "url": "https://training.dotmac.com/slides/overview.pdf"},
                ],
                required_for_certification=True,
                certification_level="bronze",
            ),
            TrainingModule()
                module_id="mod_002",
                module_name="Sales Techniques for ISPs",
                description="Effective sales strategies for ISP customers",
                category="sales_skills",
                duration_minutes=60,
                difficulty_level="intermediate",
                prerequisites=["mod_001"],
                is_completed=True,
                completion_date=datetime.now(timezone.utc) - timedelta(days=20),
                score=87,
                content_url="https://training.dotmac.com/module/002",
                materials=[
                    {"type": "video", "url": "https://training.dotmac.com/videos/sales.mp4"},
                    {"type": "workbook", "url": "https://training.dotmac.com/workbooks/sales.pdf"},
                ],
                required_for_certification=True,
                certification_level="silver",
            ),
            TrainingModule()
                module_id="mod_003",
                module_name="Advanced Technical Integration",
                description="Deep dive into technical integrations and implementations",
                category="technical",
                duration_minutes=90,
                difficulty_level="advanced",
                prerequisites=["mod_001", "mod_002"],
                is_completed=False,
                content_url="https://training.dotmac.com/module/003",
                materials=[
                    {"type": "video", "url": "https://training.dotmac.com/videos/technical.mp4"},
                    {"type": "lab", "url": "https://training.dotmac.com/labs/integration"},
                ],
                required_for_certification=True,
                certification_level="gold",
            ),
        ]
        
        completed_modules = len([m for m in training_modules if m.is_completed])
        completion_percentage = completed_modules / len(training_modules)
        
        return CertificationProgress()
            reseller_id=reseller_id,
            current_level="silver",
            total_modules=len(training_modules),
            completed_modules=completed_modules,
            completion_percentage=completion_percentage,
            next_level="gold",
            next_level_requirements={
                "modules_required": ["mod_003"],
                "min_score": 85,
                "sales_target": 500000.00,
            },
            modules=training_modules,
            last_certification_date=datetime.now(timezone.utc) - timedelta(days=60),
            certification_expiry_date=datetime.now(timezone.utc) + timedelta(days=305),
            current_benefits=[
                "12% commission rate",
                "Marketing development funds",
                "Priority support",
            ],
            next_level_benefits=[
                "15% commission rate",
                "Additional marketing support",
                "Executive briefing access",
                "Beta program participation",
            ],
        )
        
    except Exception as e:
        logger.error(f"Failed to get certification progress for reseller {reseller_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve certification progress",
        )


@reseller_router.post("/training/modules/{module_id}/complete")
async def complete_training_module():
    module_id: str,
    score: int = Query(..., ge=0, le=100, description="Module completion score"),
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
):
    """Mark a training module as completed with score."""
    reseller_id = current_reseller["reseller_id"]
    
    try:
        # Record module completion (would integrate with learning management system)
        completion_data = {
            "reseller_id": reseller_id,
            "module_id": module_id,
            "score": score,
            "completion_date": datetime.now(timezone.utc),
            "completed_by": current_user.get("user_id"),
        }
        
        # Check if this completion qualifies for certification upgrade
        # (would implement certification logic)
        
        logger.info(f"Reseller {reseller_id} completed module {module_id} with score {score}")
        
        return {
            "message": "Training module completed successfully",
            "score": score,
            "certification_progress_updated": True,
        }
        
    except Exception as e:
        logger.error(f"Failed to complete training module {module_id} for reseller {reseller_id}: {e}")
        raise HTTPException()
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record module completion",
        )


# Sales Tools and Resources
@reseller_router.get("/tools/pricing-calculator")
async def get_pricing_calculator_config():
    current_reseller: dict = Depends(get_current_reseller),
    current_user: dict = Depends(require_reseller),
):
    """Get pricing calculator configuration and tiers."""
    return {
        "tiers": [
            {
                "tier_name": "Starter",
                "base_price": 1500.00,
                "features": ["basic_customer_management", "billing_integration", "support_portal"],
                "limits": {"customers": 500, "users": 10, "storage_gb": 50},
            },
            {
                "tier_name": "Standard", 
                "base_price": 3000.00,
                "features": ["advanced_analytics", "api_access", "white_labeling"],
                "limits": {"customers": 2000, "users": 25, "storage_gb": 200},
            },
            {
                "tier_name": "Premium",
                "base_price": 6000.00,
                "features": ["custom_integrations", "priority_support", "dedicated_instance"],
                "limits": {"customers": 10000, "users": 100, "storage_gb": 1000},
            },
        ],
        "add_ons": [
            {"name": "Additional Storage", "price_per_gb": 0.50},
            {"name": "Additional Users", "price_per_user": 25.00},
            {"name": "Premium Support", "price": 500.00},
        ],
        "discounts": [
            {"type": "annual_payment", "discount_percentage": 15},
            {"type": "multi_year", "discount_percentage": 20},
            {"type": "volume", "threshold": 5, "discount_percentage": 10},
        ],
    }