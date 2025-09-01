"""
Complete reseller API router with database persistence
Comprehensive endpoints for reseller lifecycle management
"""

from datetime import date, datetime
from typing import Dict, List, Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Database and authentication dependencies
from dotmac_shared.database.session import get_async_db

from .db_models import ApplicationStatus, ResellerStatus, ResellerType
from .services_complete import (
    ResellerApplicationService, ResellerService,
    ResellerCustomerService, ResellerOnboardingService
)

# Create main router
reseller_router = APIRouter(prefix="/resellers", tags=["Resellers"])

# Import portal router
from .portal_router import portal_router

# === REQUEST/RESPONSE SCHEMAS ===

class ResellerApplicationCreate(BaseModel):
    """Schema for creating reseller application"""
    # Company information
    company_name: str = Field(..., min_length=2, max_length=300)
    legal_company_name: Optional[str] = Field(None, max_length=300)
    website_url: Optional[str] = Field(None, max_length=500)
    business_type: Optional[str] = Field(None, max_length=100)
    years_in_business: Optional[int] = Field(None, ge=0, le=200)
    employee_count: Optional[int] = Field(None, ge=1, le=1000000)
    annual_revenue_range: Optional[str] = None
    
    # Primary contact
    contact_name: str = Field(..., min_length=2, max_length=200)
    contact_title: Optional[str] = Field(None, max_length=100)
    contact_email: EmailStr
    contact_phone: Optional[str] = Field(None, max_length=20)
    
    # Business details
    business_description: Optional[str] = None
    telecom_experience_years: Optional[int] = Field(None, ge=0, le=100)
    target_customer_segments: Optional[List[str]] = []
    desired_territories: Optional[List[str]] = []
    estimated_monthly_customers: Optional[int] = Field(None, ge=0, le=10000)
    preferred_commission_structure: Optional[str] = None
    
    # Technical capabilities
    technical_capabilities: Optional[List[str]] = []
    installation_experience: bool = False
    support_capabilities: Optional[List[str]] = []
    
    # Financial information
    business_license_number: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    insurance_coverage: bool = False

class ResellerApplicationResponse(BaseModel):
    """Response for reseller application"""
    application_id: str
    company_name: str
    contact_name: str
    contact_email: str
    status: ApplicationStatus
    submitted_at: datetime
    message: str
    
    class Config:
        from_attributes = True

class ResellerResponse(BaseModel):
    """Response for reseller details"""
    reseller_id: str
    company_name: str
    status: ResellerStatus
    reseller_type: ResellerType
    primary_contact_name: str
    primary_contact_email: str
    total_customers: int
    active_customers: int
    monthly_sales: float
    commission_rate_display: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ApplicationApprovalRequest(BaseModel):
    """Request for approving application"""
    notes: Optional[str] = None
    commission_rate: Optional[float] = Field(None, ge=0, le=100)
    agreement_terms: Optional[Dict[str, Any]] = None

class ApplicationRejectionRequest(BaseModel):
    """Request for rejecting application"""
    reason: str = Field(..., min_length=10, max_length=1000)

class ResellerMetricsUpdate(BaseModel):
    """Request for updating reseller metrics"""
    total_customers: Optional[int] = Field(None, ge=0)
    active_customers: Optional[int] = Field(None, ge=0)
    monthly_sales: Optional[float] = Field(None, ge=0)
    ytd_sales: Optional[float] = Field(None, ge=0)
    lifetime_sales: Optional[float] = Field(None, ge=0)
    customer_churn_rate: Optional[float] = Field(None, ge=0, le=100)
    customer_satisfaction_score: Optional[float] = Field(None, ge=0, le=10)

class CustomerAssignmentRequest(BaseModel):
    """Request for assigning customer to reseller"""
    customer_id: UUID
    assignment_type: str = "direct"
    service_type: Optional[str] = None
    monthly_value: Optional[float] = Field(None, ge=0)

# === PUBLIC ENDPOINTS (No Authentication) ===

@reseller_router.post(
    "/applications",
    response_model=ResellerApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit reseller application from website"
)
async def submit_reseller_application(
    application: ResellerApplicationCreate,
    db: AsyncSession = Depends(get_async_db)
) -> ResellerApplicationResponse:
    """Submit new reseller application from website signup."""
    
    try:
        service = ResellerApplicationService(db)
        created_application = await service.submit_application(application.dict())
        
        return ResellerApplicationResponse(
            application_id=created_application.application_id,
            company_name=created_application.company_name,
            contact_name=created_application.contact_name,
            contact_email=created_application.contact_email,
            status=created_application.status,
            submitted_at=created_application.submitted_at,
            message="Application submitted successfully. We'll review it within 24-48 hours and contact you via email."
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to submit application. Please try again.")

@reseller_router.get("/ping")
async def ping():
    """Health check endpoint"""
    return {
        "message": "Reseller API is working",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

# === ADMIN ENDPOINTS (Protected) ===

@reseller_router.get(
    "/applications",
    response_model=List[ResellerApplicationResponse],
    summary="List reseller applications for admin review"
)
async def list_reseller_applications(
    db: AsyncSession = Depends(get_async_db),
    status_filter: Optional[ApplicationStatus] = Query(None, description="Filter by application status"),
    search: Optional[str] = Query(None, description="Search by company name, contact name, or email"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> List[ResellerApplicationResponse]:
    """List reseller applications for admin review."""
    
    try:
        service = ResellerApplicationService(db)
        
        if search:
            applications = await service.search_applications(
                search_term=search,
                status=status_filter,
                limit=limit,
                offset=offset
            )
        elif status_filter:
            repo = service.repo
            applications = await repo.list_by_status(status_filter, limit, offset)
        else:
            applications = await service.get_pending_applications(limit, offset)
        
        return [
            ResellerApplicationResponse(
                application_id=app.application_id,
                company_name=app.company_name,
                contact_name=app.contact_name,
                contact_email=app.contact_email,
                status=app.status,
                submitted_at=app.submitted_at,
                message=f"Application {app.status.value}"
            )
            for app in applications
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve applications")

@reseller_router.get(
    "/applications/{application_id}",
    summary="Get detailed application information"
)
async def get_application_details(
    application_id: str,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get detailed information about a reseller application."""
    
    try:
        service = ResellerApplicationService(db)
        application = await service.repo.get_by_id(application_id)
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        return {
            "application_id": application.application_id,
            "status": application.status,
            "company_info": {
                "company_name": application.company_name,
                "legal_company_name": application.legal_company_name,
                "website_url": application.website_url,
                "business_type": application.business_type,
                "years_in_business": application.years_in_business,
                "employee_count": application.employee_count
            },
            "contact_info": {
                "name": application.contact_name,
                "title": application.contact_title,
                "email": application.contact_email,
                "phone": application.contact_phone
            },
            "business_details": {
                "description": application.business_description,
                "telecom_experience": application.telecom_experience_years,
                "target_segments": application.target_customer_segments,
                "territories": application.desired_territories,
                "estimated_customers": application.estimated_monthly_customers
            },
            "processing_info": {
                "submitted_at": application.submitted_at,
                "reviewed_by": application.reviewed_by,
                "reviewed_at": application.reviewed_at,
                "decision_date": application.decision_date,
                "review_notes": application.review_notes,
                "communication_log": application.communication_log
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve application details")

@reseller_router.post(
    "/applications/{application_id}/review",
    summary="Mark application as under review"
)
async def mark_application_under_review(
    application_id: str,
    reviewer_id: str = Query(..., description="ID of the reviewing admin"),
    notes: Optional[str] = Query(None, description="Review notes"),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Mark application as under review."""
    
    try:
        service = ResellerApplicationService(db)
        application = await service.review_application(application_id, reviewer_id, notes)
        
        return {
            "message": "Application marked as under review",
            "application_id": application.application_id,
            "status": application.status,
            "reviewed_by": application.reviewed_by,
            "reviewed_at": application.reviewed_at
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update application status")

@reseller_router.post(
    "/applications/{application_id}/approve",
    summary="Approve reseller application and create reseller account"
)
async def approve_reseller_application(
    application_id: str,
    approval_request: ApplicationApprovalRequest,
    reviewer_id: str = Query(..., description="ID of the approving admin"),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Approve reseller application and create reseller account."""
    
    try:
        service = ResellerApplicationService(db)
        
        # Prepare approval data
        approval_data = {'notes': approval_request.notes}
        if approval_request.commission_rate:
            approval_data['base_commission_rate'] = approval_request.commission_rate
        if approval_request.agreement_terms:
            approval_data.update(approval_request.agreement_terms)
        
        result = await service.approve_application(
            application_id=application_id,
            reviewer_id=reviewer_id,
            approval_data=approval_data
        )
        
        return {
            "message": "Application approved successfully",
            "application_id": result['application'].application_id,
            "reseller_id": result['reseller'].reseller_id,
            "reseller_status": result['reseller'].status,
            "next_steps": [
                "Portal account will be created within 24 hours",
                "Welcome package sent via email",
                "Account manager will contact within 48 hours"
            ]
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to approve application")

@reseller_router.post(
    "/applications/{application_id}/reject",
    summary="Reject reseller application"
)
async def reject_reseller_application(
    application_id: str,
    rejection_request: ApplicationRejectionRequest,
    reviewer_id: str = Query(..., description="ID of the reviewing admin"),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Reject reseller application."""
    
    try:
        service = ResellerApplicationService(db)
        application = await service.reject_application(
            application_id=application_id,
            reviewer_id=reviewer_id,
            rejection_reason=rejection_request.reason
        )
        
        return {
            "message": "Application rejected",
            "application_id": application.application_id,
            "status": application.status,
            "rejection_reason": rejection_request.reason,
            "notification_sent": True
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to reject application")

# === RESELLER MANAGEMENT ENDPOINTS ===

@reseller_router.get(
    "/",
    response_model=List[ResellerResponse],
    summary="List active resellers"
)
async def list_resellers(
    db: AsyncSession = Depends(get_async_db),
    status_filter: Optional[ResellerStatus] = Query(None, description="Filter by reseller status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> List[ResellerResponse]:
    """List resellers with optional status filtering."""
    
    try:
        service = ResellerService(db)
        
        if status_filter:
            resellers = await service.repo.list_by_status(status_filter, limit, offset)
        else:
            resellers = await service.list_active_resellers(limit, offset)
        
        return [
            ResellerResponse(
                reseller_id=r.reseller_id,
                company_name=r.company_name,
                status=r.status,
                reseller_type=r.reseller_type,
                primary_contact_name=r.primary_contact_name,
                primary_contact_email=r.primary_contact_email,
                total_customers=r.total_customers,
                active_customers=r.active_customers,
                monthly_sales=float(r.monthly_sales or 0),
                commission_rate_display=r.commission_rate_display,
                created_at=r.created_at
            )
            for r in resellers
        ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve resellers")

@reseller_router.get(
    "/{reseller_id}",
    summary="Get reseller details"
)
async def get_reseller_details(
    reseller_id: str,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get detailed reseller information."""
    
    try:
        service = ResellerService(db)
        reseller = await service.get_reseller(reseller_id)
        
        if not reseller:
            raise HTTPException(status_code=404, detail="Reseller not found")
        
        return {
            "reseller_id": reseller.reseller_id,
            "company_info": {
                "company_name": reseller.company_name,
                "legal_name": reseller.legal_name,
                "doing_business_as": reseller.doing_business_as,
                "website_url": reseller.website_url,
                "business_address": reseller.business_address
            },
            "contact_info": {
                "primary_contact_name": reseller.primary_contact_name,
                "primary_contact_email": reseller.primary_contact_email,
                "primary_contact_phone": reseller.primary_contact_phone
            },
            "partnership": {
                "status": reseller.status,
                "reseller_type": reseller.reseller_type,
                "agreement_start_date": reseller.agreement_start_date,
                "agreement_end_date": reseller.agreement_end_date,
                "commission_structure": reseller.commission_structure,
                "base_commission_rate": float(reseller.base_commission_rate or 0)
            },
            "performance": {
                "total_customers": reseller.total_customers,
                "active_customers": reseller.active_customers,
                "monthly_sales": float(reseller.monthly_sales or 0),
                "ytd_sales": float(reseller.ytd_sales or 0),
                "lifetime_sales": float(reseller.lifetime_sales or 0),
                "customer_satisfaction_score": float(reseller.customer_satisfaction_score or 0)
            },
            "portal_access": {
                "enabled": reseller.portal_enabled,
                "last_login": reseller.portal_last_login
            },
            "created_at": reseller.created_at
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve reseller details")

@reseller_router.get(
    "/{reseller_id}/dashboard",
    summary="Get reseller dashboard data"
)
async def get_reseller_dashboard(
    reseller_id: str,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get comprehensive dashboard data for reseller."""
    
    try:
        service = ResellerService(db)
        dashboard_data = await service.get_dashboard_data(reseller_id)
        
        if not dashboard_data:
            raise HTTPException(status_code=404, detail="Reseller not found")
        
        return dashboard_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")

@reseller_router.put(
    "/{reseller_id}/metrics",
    summary="Update reseller performance metrics"
)
async def update_reseller_metrics(
    reseller_id: str,
    metrics: ResellerMetricsUpdate,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Update reseller performance metrics."""
    
    try:
        service = ResellerService(db)
        
        # Convert to dict and filter None values
        metrics_data = {k: v for k, v in metrics.dict().items() if v is not None}
        
        if not metrics_data:
            raise HTTPException(status_code=400, detail="No metrics provided for update")
        
        updated_reseller = await service.update_metrics(reseller_id, metrics_data)
        
        if not updated_reseller:
            raise HTTPException(status_code=404, detail="Reseller not found")
        
        return {
            "message": "Metrics updated successfully",
            "reseller_id": updated_reseller.reseller_id,
            "updated_metrics": metrics_data,
            "updated_at": datetime.utcnow()
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update metrics")

# === CUSTOMER ASSIGNMENT ENDPOINTS ===

@reseller_router.post(
    "/{reseller_id}/customers",
    summary="Assign customer to reseller"
)
async def assign_customer_to_reseller(
    reseller_id: str,
    assignment: CustomerAssignmentRequest,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Assign a customer to a reseller."""
    
    try:
        service = ResellerCustomerService(db)
        reseller_service = ResellerService(db)
        
        # Verify reseller exists
        reseller = await reseller_service.get_reseller(reseller_id)
        if not reseller:
            raise HTTPException(status_code=404, detail="Reseller not found")
        
        # Prepare service details
        service_details = {}
        if assignment.service_type:
            service_details['primary_service_type'] = assignment.service_type
        if assignment.monthly_value:
            service_details['monthly_recurring_revenue'] = assignment.monthly_value
        
        # Create assignment
        assignment_record = await service.assign_customer_to_reseller(
            customer_id=assignment.customer_id,
            reseller_id=reseller.id,
            assignment_type=assignment.assignment_type,
            service_details=service_details
        )
        
        return {
            "message": "Customer assigned successfully",
            "customer_id": str(assignment.customer_id),
            "reseller_id": reseller_id,
            "assignment_type": assignment.assignment_type,
            "assignment_date": assignment_record.relationship_start_date
        }
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to assign customer")

@reseller_router.get(
    "/{reseller_id}/customers",
    summary="Get customers assigned to reseller"
)
async def get_reseller_customers(
    reseller_id: str,
    db: AsyncSession = Depends(get_async_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Get customers assigned to a reseller."""
    
    try:
        reseller_service = ResellerService(db)
        customer_service = ResellerCustomerService(db)
        
        # Verify reseller exists
        reseller = await reseller_service.get_reseller(reseller_id)
        if not reseller:
            raise HTTPException(status_code=404, detail="Reseller not found")
        
        # Get customers
        customers = await customer_service.get_reseller_customers(
            reseller.id, limit, offset
        )
        
        return {
            "reseller_id": reseller_id,
            "total_customers": len(customers),
            "customers": [
                {
                    "customer_id": str(c.customer_id),
                    "relationship_start_date": c.relationship_start_date,
                    "relationship_status": c.relationship_status,
                    "assignment_type": c.assignment_type,
                    "primary_service_type": c.primary_service_type,
                    "monthly_recurring_revenue": float(c.monthly_recurring_revenue or 0),
                    "lifetime_value": float(c.lifetime_value or 0)
                }
                for c in customers
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve customers")

# === ONBOARDING ENDPOINTS ===

@reseller_router.get(
    "/{reseller_id}/onboarding",
    summary="Get reseller onboarding status"
)
async def get_reseller_onboarding_status(
    reseller_id: str,
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Get reseller onboarding checklist and progress."""
    
    try:
        onboarding_service = ResellerOnboardingService(db)
        checklist = await onboarding_service.create_onboarding_checklist(reseller_id)
        
        return checklist
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to retrieve onboarding status")

@reseller_router.put(
    "/{reseller_id}/onboarding/{task_id}",
    summary="Update onboarding task status"
)
async def update_onboarding_task(
    reseller_id: str,
    task_id: str,
    task_status: str = Query(..., description="New task status"),
    notes: Optional[str] = Query(None, description="Task completion notes"),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """Update onboarding task status."""
    
    try:
        onboarding_service = ResellerOnboardingService(db)
        result = await onboarding_service.update_onboarding_task(
            reseller_id, task_id, task_status, notes
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update onboarding task")

# Include portal router as subrouter
reseller_router.include_router(portal_router)

# Export router
__all__ = ["reseller_router"]