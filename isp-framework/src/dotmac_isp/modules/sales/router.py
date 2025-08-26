"""Sales API router."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_user
from dotmac_isp.modules.identity.models import User
from .service import (
    LeadManagementService,
    OpportunityManagementService,
    SalesActivityService,
    SalesAnalyticsService,
    SalesMainService,
)
from .models import (
    LeadSource,
    LeadStatus,
    OpportunityStage,
    OpportunityStatus,
    ActivityType,
    ActivityStatus,
    CustomerType,
)
from . import schemas

router = APIRouter(prefix="/sales", tags=["sales"])
sales_router = router  # Export with expected name


# Lead Management Endpoints
@router.post("/leads", response_model=schemas.LeadResponse)
async def create_lead(
    lead_data: schemas.LeadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new sales lead."""
    try:
        lead_service = LeadManagementService(db, str(current_user.tenant_id))
        lead = await lead_service.create_lead(lead_data.model_dump())

        # Convert to response format
        return schemas.LeadResponse(
            id=lead.id,
            tenant_id=lead.tenant_id,
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=lead.email,
            phone=lead.phone,
            company=lead.company,
            job_title=lead.job_title,
            lead_source=lead.lead_source,
            lead_status=lead.lead_status,
            customer_type=lead.customer_type,
            budget=lead.budget,
            authority=lead.authority,
            need=lead.need,
            timeline=lead.timeline,
            lead_score=lead.lead_score,
            first_contact_date=lead.first_contact_date,
            last_contact_date=lead.last_contact_date,
            qualification_date=lead.qualification_date,
            conversion_date=lead.conversion_date,
            assigned_to=lead.assigned_to,
            sales_team=lead.sales_team,
            opportunity_id=lead.opportunity_id,
            street_address=lead.street_address,
            city=lead.city,
            state_province=lead.state_province,
            postal_code=lead.postal_code,
            country_code=lead.country_code,
            notes=lead.notes,
            qualification_notes=lead.qualification_notes,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lead: {str(e)}",
        )


@router.get("/leads", response_model=schemas.LeadListResponse)
async def list_leads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    lead_source: Optional[LeadSource] = Query(None),
    lead_status: Optional[LeadStatus] = Query(None),
    customer_type: Optional[CustomerType] = Query(None),
    assigned_to: Optional[str] = Query(None),
    sales_team: Optional[str] = Query(None),
    follow_up_overdue: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List sales leads with filtering."""
    try:
        lead_service = LeadManagementService(db, str(current_user.tenant_id))
        leads = await lead_service.list_leads(
            lead_source=lead_source,
            lead_status=lead_status,
            customer_type=customer_type,
            assigned_to=assigned_to,
            sales_team=sales_team,
            follow_up_overdue=follow_up_overdue,
            skip=skip,
            limit=limit,
        )

        # Convert to response format
        lead_responses = []
        for lead in leads:
            lead_responses.append(
                schemas.LeadResponse(
                    id=lead.id,
                    tenant_id=lead.tenant_id,
                    first_name=lead.first_name,
                    last_name=lead.last_name,
                    email=lead.email,
                    phone=lead.phone,
                    company=lead.company,
                    job_title=lead.job_title,
                    lead_source=lead.lead_source,
                    lead_status=lead.lead_status,
                    customer_type=lead.customer_type,
                    budget=lead.budget,
                    authority=lead.authority,
                    need=lead.need,
                    timeline=lead.timeline,
                    lead_score=lead.lead_score,
                    first_contact_date=lead.first_contact_date,
                    last_contact_date=lead.last_contact_date,
                    qualification_date=lead.qualification_date,
                    conversion_date=lead.conversion_date,
                    assigned_to=lead.assigned_to,
                    sales_team=lead.sales_team,
                    opportunity_id=lead.opportunity_id,
                    street_address=lead.street_address,
                    city=lead.city,
                    state_province=lead.state_province,
                    postal_code=lead.postal_code,
                    country_code=lead.country_code,
                    notes=lead.notes,
                    qualification_notes=lead.qualification_notes,
                    created_at=lead.created_at,
                    updated_at=lead.updated_at,
                )
            )

        # Calculate summary stats
        new_leads = len([l for l in leads if l.lead_status == LeadStatus.NEW])
        qualified_leads = len(
            [l for l in leads if l.lead_status == LeadStatus.QUALIFIED]
        )
        converted_leads = len(
            [l for l in leads if l.lead_status == LeadStatus.CONVERTED]
        )

        return schemas.LeadListResponse(
            leads=lead_responses,
            total_count=len(leads),
            new_leads=new_leads,
            qualified_leads=qualified_leads,
            converted_leads=converted_leads,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list leads: {str(e)}",
        )


@router.get("/leads/{lead_id}", response_model=schemas.LeadResponse)
async def get_lead(
    lead_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific lead by ID."""
    try:
        lead_service = LeadManagementService(db, str(current_user.tenant_id))
        lead = await lead_service.get_lead(lead_id)

        return schemas.LeadResponse(
            id=lead.id,
            tenant_id=lead.tenant_id,
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=lead.email,
            phone=lead.phone,
            company=lead.company,
            job_title=lead.job_title,
            lead_source=lead.lead_source,
            lead_status=lead.lead_status,
            customer_type=lead.customer_type,
            budget=lead.budget,
            authority=lead.authority,
            need=lead.need,
            timeline=lead.timeline,
            lead_score=lead.lead_score,
            first_contact_date=lead.first_contact_date,
            last_contact_date=lead.last_contact_date,
            qualification_date=lead.qualification_date,
            conversion_date=lead.conversion_date,
            assigned_to=lead.assigned_to,
            sales_team=lead.sales_team,
            opportunity_id=lead.opportunity_id,
            street_address=lead.street_address,
            city=lead.city,
            state_province=lead.state_province,
            postal_code=lead.postal_code,
            country_code=lead.country_code,
            notes=lead.notes,
            qualification_notes=lead.qualification_notes,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead not found: {str(e)}"
        )


@router.put("/leads/{lead_id}/qualify", response_model=schemas.LeadResponse)
async def qualify_lead(
    lead_id: UUID,
    qualification_data: schemas.LeadQualification,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Qualify a lead using BANT criteria."""
    try:
        lead_service = LeadManagementService(db, str(current_user.tenant_id))
        lead = await lead_service.qualify_lead(lead_id, qualification_data.model_dump())

        return schemas.LeadResponse(
            id=lead.id,
            tenant_id=lead.tenant_id,
            first_name=lead.first_name,
            last_name=lead.last_name,
            email=lead.email,
            phone=lead.phone,
            company=lead.company,
            job_title=lead.job_title,
            lead_source=lead.lead_source,
            lead_status=lead.lead_status,
            customer_type=lead.customer_type,
            budget=lead.budget,
            authority=lead.authority,
            need=lead.need,
            timeline=lead.timeline,
            lead_score=lead.lead_score,
            first_contact_date=lead.first_contact_date,
            last_contact_date=lead.last_contact_date,
            qualification_date=lead.qualification_date,
            conversion_date=lead.conversion_date,
            assigned_to=lead.assigned_to,
            sales_team=lead.sales_team,
            opportunity_id=lead.opportunity_id,
            street_address=lead.street_address,
            city=lead.city,
            state_province=lead.state_province,
            postal_code=lead.postal_code,
            country_code=lead.country_code,
            notes=lead.notes,
            qualification_notes=lead.qualification_notes,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to qualify lead: {str(e)}",
        )


@router.post("/leads/{lead_id}/convert", response_model=schemas.OpportunityResponse)
async def convert_lead_to_opportunity(
    lead_id: UUID,
    opportunity_data: schemas.OpportunityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Convert a qualified lead to an opportunity."""
    try:
        lead_service = LeadManagementService(db, str(current_user.tenant_id))
        opportunity = await lead_service.convert_lead_to_opportunity(
            lead_id, opportunity_data.model_dump()
        )

        return schemas.OpportunityResponse(
            id=opportunity.id,
            tenant_id=opportunity.tenant_id,
            lead_id=opportunity.lead_id,
            opportunity_name=opportunity.opportunity_name,
            account_name=opportunity.account_name,
            contact_name=opportunity.contact_name,
            contact_email=opportunity.contact_email,
            contact_phone=opportunity.contact_phone,
            estimated_value=opportunity.estimated_value,
            expected_close_date=opportunity.expected_close_date,
            opportunity_stage=opportunity.opportunity_stage,
            opportunity_status=opportunity.opportunity_status,
            probability=opportunity.probability,
            weighted_value=opportunity.weighted_value,
            customer_type=opportunity.customer_type,
            description=opportunity.description,
            sales_owner=opportunity.sales_owner,
            sales_team=opportunity.sales_team,
            close_reason=opportunity.close_reason,
            street_address=opportunity.street_address,
            city=opportunity.city,
            state_province=opportunity.state_province,
            postal_code=opportunity.postal_code,
            country_code=opportunity.country_code,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert lead: {str(e)}",
        )


# Opportunity Management Endpoints
@router.post("/opportunities", response_model=schemas.OpportunityResponse)
async def create_opportunity(
    opportunity_data: schemas.OpportunityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new sales opportunity."""
    try:
        opportunity_service = OpportunityManagementService(
            db, str(current_user.tenant_id)
        )
        opportunity = await opportunity_service.create_opportunity(
            opportunity_data.model_dump()
        )

        return schemas.OpportunityResponse(
            id=opportunity.id,
            tenant_id=opportunity.tenant_id,
            lead_id=opportunity.lead_id,
            opportunity_name=opportunity.opportunity_name,
            account_name=opportunity.account_name,
            contact_name=opportunity.contact_name,
            contact_email=opportunity.contact_email,
            contact_phone=opportunity.contact_phone,
            estimated_value=opportunity.estimated_value,
            expected_close_date=opportunity.expected_close_date,
            opportunity_stage=opportunity.opportunity_stage,
            opportunity_status=opportunity.opportunity_status,
            probability=opportunity.probability,
            weighted_value=opportunity.weighted_value,
            customer_type=opportunity.customer_type,
            description=opportunity.description,
            sales_owner=opportunity.sales_owner,
            sales_team=opportunity.sales_team,
            close_reason=opportunity.close_reason,
            street_address=opportunity.street_address,
            city=opportunity.city,
            state_province=opportunity.state_province,
            postal_code=opportunity.postal_code,
            country_code=opportunity.country_code,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create opportunity: {str(e)}",
        )


@router.get("/opportunities", response_model=schemas.OpportunityListResponse)
async def list_opportunities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    opportunity_stage: Optional[OpportunityStage] = Query(None),
    opportunity_status: Optional[OpportunityStatus] = Query(None),
    sales_owner: Optional[str] = Query(None),
    sales_team: Optional[str] = Query(None),
    customer_type: Optional[CustomerType] = Query(None),
    min_value: Optional[Decimal] = Query(None, ge=0),
    max_value: Optional[Decimal] = Query(None, ge=0),
    overdue_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List sales opportunities with filtering."""
    try:
        opportunity_service = OpportunityManagementService(
            db, str(current_user.tenant_id)
        )
        opportunities = await opportunity_service.list_opportunities(
            opportunity_stage=opportunity_stage,
            opportunity_status=opportunity_status,
            sales_owner=sales_owner,
            sales_team=sales_team,
            customer_type=customer_type,
            min_value=min_value,
            max_value=max_value,
            overdue_only=overdue_only,
            skip=skip,
            limit=limit,
        )

        # Convert to response format
        opportunity_responses = []
        for opp in opportunities:
            opportunity_responses.append(
                schemas.OpportunityResponse(
                    id=opp.id,
                    tenant_id=opp.tenant_id,
                    lead_id=opp.lead_id,
                    opportunity_name=opp.opportunity_name,
                    account_name=opp.account_name,
                    contact_name=opp.contact_name,
                    contact_email=opp.contact_email,
                    contact_phone=opp.contact_phone,
                    estimated_value=opp.estimated_value,
                    expected_close_date=opp.expected_close_date,
                    opportunity_stage=opp.opportunity_stage,
                    opportunity_status=opp.opportunity_status,
                    probability=opp.probability,
                    weighted_value=opp.weighted_value,
                    customer_type=opp.customer_type,
                    description=opp.description,
                    sales_owner=opp.sales_owner,
                    sales_team=opp.sales_team,
                    close_reason=opp.close_reason,
                    street_address=opp.street_address,
                    city=opp.city,
                    state_province=opp.state_province,
                    postal_code=opp.postal_code,
                    country_code=opp.country_code,
                    created_at=opp.created_at,
                    updated_at=opp.updated_at,
                )
            )

        # Calculate summary stats
        active_opportunities = len(
            [
                o
                for o in opportunities
                if o.opportunity_status == OpportunityStatus.ACTIVE
            ]
        )
        won_opportunities = len(
            [o for o in opportunities if o.opportunity_status == OpportunityStatus.WON]
        )
        lost_opportunities = len(
            [o for o in opportunities if o.opportunity_status == OpportunityStatus.LOST]
        )
        total_pipeline_value = sum(
            o.estimated_value
            for o in opportunities
            if o.opportunity_status == OpportunityStatus.ACTIVE
        )

        return schemas.OpportunityListResponse(
            opportunities=opportunity_responses,
            total_count=len(opportunities),
            active_opportunities=active_opportunities,
            won_opportunities=won_opportunities,
            lost_opportunities=lost_opportunities,
            total_pipeline_value=total_pipeline_value,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list opportunities: {str(e)}",
        )


@router.get(
    "/opportunities/{opportunity_id}", response_model=schemas.OpportunityResponse
)
async def get_opportunity(
    opportunity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific opportunity by ID."""
    try:
        opportunity_service = OpportunityManagementService(
            db, str(current_user.tenant_id)
        )
        opportunity = await opportunity_service.get_opportunity(opportunity_id)

        return schemas.OpportunityResponse(
            id=opportunity.id,
            tenant_id=opportunity.tenant_id,
            lead_id=opportunity.lead_id,
            opportunity_name=opportunity.opportunity_name,
            account_name=opportunity.account_name,
            contact_name=opportunity.contact_name,
            contact_email=opportunity.contact_email,
            contact_phone=opportunity.contact_phone,
            estimated_value=opportunity.estimated_value,
            expected_close_date=opportunity.expected_close_date,
            opportunity_stage=opportunity.opportunity_stage,
            opportunity_status=opportunity.opportunity_status,
            probability=opportunity.probability,
            weighted_value=opportunity.weighted_value,
            customer_type=opportunity.customer_type,
            description=opportunity.description,
            sales_owner=opportunity.sales_owner,
            sales_team=opportunity.sales_team,
            close_reason=opportunity.close_reason,
            street_address=opportunity.street_address,
            city=opportunity.city,
            state_province=opportunity.state_province,
            postal_code=opportunity.postal_code,
            country_code=opportunity.country_code,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity not found: {str(e)}",
        )


@router.put(
    "/opportunities/{opportunity_id}/stage", response_model=schemas.OpportunityResponse
)
async def update_opportunity_stage(
    opportunity_id: UUID,
    stage_data: schemas.OpportunityStageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update opportunity stage."""
    try:
        opportunity_service = OpportunityManagementService(
            db, str(current_user.tenant_id)
        )
        opportunity = await opportunity_service.update_opportunity_stage(
            opportunity_id, stage_data.stage, stage_data.notes
        )

        return schemas.OpportunityResponse(
            id=opportunity.id,
            tenant_id=opportunity.tenant_id,
            lead_id=opportunity.lead_id,
            opportunity_name=opportunity.opportunity_name,
            account_name=opportunity.account_name,
            contact_name=opportunity.contact_name,
            contact_email=opportunity.contact_email,
            contact_phone=opportunity.contact_phone,
            estimated_value=opportunity.estimated_value,
            expected_close_date=opportunity.expected_close_date,
            opportunity_stage=opportunity.opportunity_stage,
            opportunity_status=opportunity.opportunity_status,
            probability=opportunity.probability,
            weighted_value=opportunity.weighted_value,
            customer_type=opportunity.customer_type,
            description=opportunity.description,
            sales_owner=opportunity.sales_owner,
            sales_team=opportunity.sales_team,
            close_reason=opportunity.close_reason,
            street_address=opportunity.street_address,
            city=opportunity.city,
            state_province=opportunity.state_province,
            postal_code=opportunity.postal_code,
            country_code=opportunity.country_code,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update opportunity stage: {str(e)}",
        )


@router.put(
    "/opportunities/{opportunity_id}/close", response_model=schemas.OpportunityResponse
)
async def close_opportunity(
    opportunity_id: UUID,
    close_data: schemas.OpportunityClose,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Close an opportunity as won or lost."""
    try:
        opportunity_service = OpportunityManagementService(
            db, str(current_user.tenant_id)
        )
        opportunity = await opportunity_service.close_opportunity(
            opportunity_id, close_data.is_won, close_data.close_reason, close_data.notes
        )

        return schemas.OpportunityResponse(
            id=opportunity.id,
            tenant_id=opportunity.tenant_id,
            lead_id=opportunity.lead_id,
            opportunity_name=opportunity.opportunity_name,
            account_name=opportunity.account_name,
            contact_name=opportunity.contact_name,
            contact_email=opportunity.contact_email,
            contact_phone=opportunity.contact_phone,
            estimated_value=opportunity.estimated_value,
            expected_close_date=opportunity.expected_close_date,
            opportunity_stage=opportunity.opportunity_stage,
            opportunity_status=opportunity.opportunity_status,
            probability=opportunity.probability,
            weighted_value=opportunity.weighted_value,
            customer_type=opportunity.customer_type,
            description=opportunity.description,
            sales_owner=opportunity.sales_owner,
            sales_team=opportunity.sales_team,
            close_reason=opportunity.close_reason,
            street_address=opportunity.street_address,
            city=opportunity.city,
            state_province=opportunity.state_province,
            postal_code=opportunity.postal_code,
            country_code=opportunity.country_code,
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close opportunity: {str(e)}",
        )


# Sales Analytics Endpoints
@router.get("/dashboard", response_model=schemas.SalesDashboard)
async def get_sales_dashboard(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get comprehensive sales dashboard."""
    try:
        analytics_service = SalesAnalyticsService(db, str(current_user.tenant_id))
        dashboard_data = await analytics_service.get_sales_dashboard()

        return schemas.SalesDashboard(**dashboard_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load sales dashboard: {str(e)}",
        )


@router.get("/pipeline", response_model=schemas.PipelineSummary)
async def get_pipeline_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    sales_owner: Optional[str] = Query(None),
):
    """Get sales pipeline summary."""
    try:
        opportunity_service = OpportunityManagementService(
            db, str(current_user.tenant_id)
        )
        pipeline_data = await opportunity_service.get_pipeline_summary(sales_owner)

        return schemas.PipelineSummary(**pipeline_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load pipeline summary: {str(e)}",
        )


@router.get("/forecast", response_model=schemas.SalesForecast)
async def get_sales_forecast(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    quarter: Optional[str] = Query(None, description="Quarter in format YYYY-Q1"),
):
    """Get sales forecast data."""
    try:
        opportunity_service = OpportunityManagementService(
            db, str(current_user.tenant_id)
        )
        forecast_data = await opportunity_service.get_forecast_data(quarter)

        return schemas.SalesForecast(**forecast_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load sales forecast: {str(e)}",
        )


@router.get("/conversion-funnel", response_model=schemas.LeadConversionFunnel)
async def get_lead_conversion_funnel(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get lead conversion funnel analysis."""
    try:
        analytics_service = SalesAnalyticsService(db, str(current_user.tenant_id))
        funnel_data = await analytics_service.get_lead_conversion_funnel()

        return schemas.LeadConversionFunnel(**funnel_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load conversion funnel: {str(e)}",
        )


# Campaign Management Endpoints (Basic Implementation)
@router.get("/campaigns", response_model=schemas.CampaignListResponse)
async def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List marketing campaigns."""
    try:
        # For now, return mock campaign data since campaign management is future implementation
        mock_campaigns = [
            schemas.CampaignResponse(
                id="12345678-1234-5678-9012-123456789012",
                tenant_id=current_user.tenant_id,
                campaign_name="Q4 Enterprise Outreach",
                campaign_type="email",
                description="Targeted email campaign for enterprise prospects",
                start_date=date(2024, 10, 1),
                end_date=date(2024, 12, 31),
                budget=Decimal("50000.00"),
                target_audience="Enterprise customers with 500+ employees",
                campaign_status="active",
                owner="sales-team",
                total_leads=150,
                qualified_leads=45,
                converted_leads=12,
                total_cost=Decimal("35000.00"),
                cost_per_lead=Decimal("233.33"),
                roi=1.8,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            schemas.CampaignResponse(
                id="12345678-1234-5678-9012-123456789013",
                tenant_id=current_user.tenant_id,
                campaign_name="Summer SMB Promotion",
                campaign_type="web",
                description="Web-based promotion for small to medium businesses",
                start_date=date(2024, 6, 1),
                end_date=date(2024, 8, 31),
                budget=Decimal("25000.00"),
                target_audience="SMB customers with 10-500 employees",
                campaign_status="completed",
                owner="marketing-team",
                total_leads=320,
                qualified_leads=96,
                converted_leads=28,
                total_cost=Decimal("22000.00"),
                cost_per_lead=Decimal("68.75"),
                roi=2.4,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        return schemas.CampaignListResponse(
            campaigns=mock_campaigns,
            total_count=len(mock_campaigns),
            active_campaigns=len(
                [c for c in mock_campaigns if c.campaign_status == "active"]
            ),
            completed_campaigns=len(
                [c for c in mock_campaigns if c.campaign_status == "completed"]
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list campaigns: {str(e)}",
        )
