"""
Onboarding API endpoints
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, EmailStr

from app.database import get_db
from app.core.auth import get_current_active_user
from app.core.deps import CurrentUser

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Onboarding Models (temporary - should be moved to proper models)
class OnboardingRequest(BaseModel):
    id: str = Field(..., description="Onboarding request ID")
    partner_name: str = Field(..., description="Partner name")
    contact_email: EmailStr = Field(..., description="Contact email")
    contact_phone: Optional[str] = Field(None, description="Contact phone")
    company_name: str = Field(..., description="Company name")
    business_type: str = Field(..., description="Business type")
    territory: Optional[str] = Field(None, description="Requested territory")
    estimated_monthly_sales: Optional[float] = Field(None, description="Estimated monthly sales")
    previous_experience: bool = Field(False, description="Previous ISP experience")
    referral_source: Optional[str] = Field(None, description="How they heard about us")
    status: str = Field(..., description="Request status")
    priority: str = Field("MEDIUM", description="Request priority")
    submitted_at: datetime = Field(..., description="Submission date")
    processed_at: Optional[datetime] = Field(None, description="Processing date")
    processed_by: Optional[str] = Field(None, description="Processed by user")
    notes: Optional[str] = Field(None, description="Processing notes")
    documents: List[str] = Field(default_factory=list, description="Uploaded documents")
    requirements_met: Dict[str, bool] = Field(default_factory=dict, description="Requirements checklist")

class OnboardingRequestCreate(BaseModel):
    partner_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    company_name: str
    business_type: str
    territory: Optional[str] = None
    estimated_monthly_sales: Optional[float] = None
    previous_experience: bool = False
    referral_source: Optional[str] = None

class OnboardingRequestUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    requirements_met: Optional[Dict[str, bool]] = None

class OnboardingApproval(BaseModel):
    tier: str = Field(..., description="Partner tier to assign")
    territory: Optional[str] = Field(None, description="Territory to assign")
    notes: Optional[str] = Field(None, description="Approval notes")

class OnboardingRejection(BaseModel):
    reason: str = Field(..., description="Rejection reason")
    feedback: Optional[str] = Field(None, description="Feedback for applicant")

class OnboardingListResponse(BaseModel):
    success: bool = True
    data: List[OnboardingRequest]
    total: int
    page: int = 1
    per_page: int = 50

class OnboardingResponse(BaseModel):
    success: bool = True
    data: OnboardingRequest

class OnboardingSummary(BaseModel):
    total_requests: int
    pending_review: int
    in_review: int
    approved: int
    rejected: int
    average_processing_time: float  # in days
    approval_rate: float

class OnboardingSummaryResponse(BaseModel):
    success: bool = True
    data: OnboardingSummary

# Mock data for development/testing
MOCK_ONBOARDING_REQUESTS = [
    OnboardingRequest(
        id="onb-001",
        partner_name="Test Partner 001",
        contact_email="partner001@dev.local",
        contact_phone="[REDACTED]",
        company_name="New Connect Solutions",
        business_type="WISP",
        territory="Southwest",
        estimated_monthly_sales=25000.0,
        previous_experience=True,
        referral_source="Partner referral",
        status="PENDING_REVIEW",
        priority="HIGH",
        submitted_at=datetime.now() - timedelta(days=2),
        documents=["business_license.pdf", "insurance_cert.pdf"],
        requirements_met={
            "business_license": True,
            "insurance": True,
            "tax_id": True,
            "bank_account": False,
            "references": True
        }
    ),
    OnboardingRequest(
        id="onb-002",
        partner_name="Test Partner 002",
        contact_email="partner002@dev.local",
        contact_phone="[REDACTED]",
        company_name="FastNet ISP",
        business_type="Fiber ISP",
        territory="Northeast",
        estimated_monthly_sales=45000.0,
        previous_experience=True,
        referral_source="Web search",
        status="IN_REVIEW",
        priority="MEDIUM",
        submitted_at=datetime.now() - timedelta(days=5),
        processed_at=datetime.now() - timedelta(days=1),
        processed_by="admin@dotmac.app",
        notes="Strong application, reviewing technical capabilities",
        documents=["business_license.pdf", "insurance_cert.pdf", "network_diagram.pdf"],
        requirements_met={
            "business_license": True,
            "insurance": True,
            "tax_id": True,
            "bank_account": True,
            "references": True
        }
    ),
    OnboardingRequest(
        id="onb-003",
        partner_name="Test Partner 003",
        contact_email="partner003@dev.local"
        contact_phone="[REDACTED]",
        company_name="Rural WiFi Networks",
        business_type="WISP",
        territory="Midwest",
        estimated_monthly_sales=15000.0,
        previous_experience=False,
        referral_source="Trade show",
        status="APPROVED",
        priority="MEDIUM",
        submitted_at=datetime.now() - timedelta(days=10),
        processed_at=datetime.now() - timedelta(days=3),
        processed_by="admin@dotmac.app",
        notes="Approved for Bronze tier, good growth potential",
        documents=["business_license.pdf", "insurance_cert.pdf"],
        requirements_met={
            "business_license": True,
            "insurance": True,
            "tax_id": True,
            "bank_account": True,
            "references": True
        }
    ),
    OnboardingRequest(
        id="onb-004",
        partner_name="Test Partner 004"
        contact_email="lisa@incomplete.com",
        company_name="Incomplete Application Corp",
        business_type="Cable ISP",
        status="REJECTED",
        priority="LOW",
        submitted_at=datetime.now() - timedelta(days=15),
        processed_at=datetime.now() - timedelta(days=8),
        processed_by="admin@dotmac.app",
        notes="Incomplete application, missing required documents",
        documents=[],
        requirements_met={
            "business_license": False,
            "insurance": False,
            "tax_id": False,
            "bank_account": False,
            "references": False
        }
    )
]

@router.get("/", response_model=OnboardingListResponse)
async def list_onboarding_requests(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    business_type: Optional[str] = Query(None),
    territory: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """List all onboarding requests with filtering and pagination."""
    
    # Filter requests based on query parameters
    filtered_requests = MOCK_ONBOARDING_REQUESTS.copy()
    
    if status:
        filtered_requests = [r for r in filtered_requests if r.status == status]
    
    if priority:
        filtered_requests = [r for r in filtered_requests if r.priority == priority]
    
    if business_type:
        filtered_requests = [r for r in filtered_requests if r.business_type == business_type]
    
    if territory:
        filtered_requests = [r for r in filtered_requests if r.territory == territory]
    
    if search:
        search_lower = search.lower()
        filtered_requests = [
            r for r in filtered_requests 
            if search_lower in r.partner_name.lower() 
            or search_lower in r.company_name.lower()
            or search_lower in r.contact_email.lower()
        ]
    
    # Pagination
    total = len(filtered_requests)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_requests = filtered_requests[start_idx:end_idx]
    
    return OnboardingListResponse(
        data=paginated_requests,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/{request_id}", response_model=OnboardingResponse)
async def get_onboarding_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get a specific onboarding request by ID."""
    
    request = next((r for r in MOCK_ONBOARDING_REQUESTS if r.id == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    
    return OnboardingResponse(data=request)

@router.post("/", response_model=OnboardingResponse)
async def create_onboarding_request(
    request_data: OnboardingRequestCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new onboarding request."""
    
    # Check if request with email already exists
    existing_request = next((r for r in MOCK_ONBOARDING_REQUESTS if r.contact_email == request_data.contact_email), None)
    if existing_request:
        raise HTTPException(status_code=400, detail="An onboarding request with this email already exists")
    
    # Create new request
    new_request = OnboardingRequest(
        id=f"onb-{str(uuid4())[:8]}",
        partner_name=request_data.partner_name,
        contact_email=request_data.contact_email,
        contact_phone=request_data.contact_phone,
        company_name=request_data.company_name,
        business_type=request_data.business_type,
        territory=request_data.territory,
        estimated_monthly_sales=request_data.estimated_monthly_sales,
        previous_experience=request_data.previous_experience,
        referral_source=request_data.referral_source,
        status="PENDING_REVIEW",
        priority="MEDIUM",
        submitted_at=datetime.now(),
        documents=[],
        requirements_met={
            "business_license": False,
            "insurance": False,
            "tax_id": False,
            "bank_account": False,
            "references": False
        }
    )
    
    MOCK_ONBOARDING_REQUESTS.append(new_request)
    return OnboardingResponse(data=new_request)

@router.put("/{request_id}", response_model=OnboardingResponse)
async def update_onboarding_request(
    request_id: str,
    request_update: OnboardingRequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Update an onboarding request."""
    
    request_idx = next((i for i, r in enumerate(MOCK_ONBOARDING_REQUESTS) if r.id == request_id), None)
    if request_idx is None:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    
    request = MOCK_ONBOARDING_REQUESTS[request_idx]
    
    # Update request fields
    if request_update.status is not None:
        request.status = request_update.status
    if request_update.priority is not None:
        request.priority = request_update.priority
    if request_update.notes is not None:
        request.notes = request_update.notes
    if request_update.requirements_met is not None:
        request.requirements_met.update(request_update.requirements_met)
    
    MOCK_ONBOARDING_REQUESTS[request_idx] = request
    return OnboardingResponse(data=request)

@router.post("/{request_id}/approve", response_model=OnboardingResponse)
async def approve_onboarding_request(
    request_id: str,
    approval_data: OnboardingApproval,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Approve an onboarding request."""
    
    request_idx = next((i for i, r in enumerate(MOCK_ONBOARDING_REQUESTS) if r.id == request_id), None)
    if request_idx is None:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    
    request = MOCK_ONBOARDING_REQUESTS[request_idx]
    
    if request.status not in ["PENDING_REVIEW", "IN_REVIEW"]:
        raise HTTPException(status_code=400, detail="Request cannot be approved from current status")
    
    request.status = "APPROVED"
    request.processed_at = datetime.now()
    request.processed_by = current_user.email
    request.notes = approval_data.notes or "Application approved"
    
    # Here we would normally create the partner record
    # For now, we'll just update the request
    
    MOCK_ONBOARDING_REQUESTS[request_idx] = request
    return OnboardingResponse(data=request)

@router.post("/{request_id}/reject", response_model=OnboardingResponse)
async def reject_onboarding_request(
    request_id: str,
    rejection_data: OnboardingRejection,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Reject an onboarding request."""
    
    request_idx = next((i for i, r in enumerate(MOCK_ONBOARDING_REQUESTS) if r.id == request_id), None)
    if request_idx is None:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    
    request = MOCK_ONBOARDING_REQUESTS[request_idx]
    
    if request.status not in ["PENDING_REVIEW", "IN_REVIEW"]:
        raise HTTPException(status_code=400, detail="Request cannot be rejected from current status")
    
    request.status = "REJECTED"
    request.processed_at = datetime.now()
    request.processed_by = current_user.email
    request.notes = f"REJECTED: {rejection_data.reason}"
    if rejection_data.feedback:
        request.notes += f"\nFeedback: {rejection_data.feedback}"
    
    MOCK_ONBOARDING_REQUESTS[request_idx] = request
    return OnboardingResponse(data=request)

@router.post("/{request_id}/review", response_model=OnboardingResponse)
async def start_review(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Start reviewing an onboarding request."""
    
    request_idx = next((i for i, r in enumerate(MOCK_ONBOARDING_REQUESTS) if r.id == request_id), None)
    if request_idx is None:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    
    request = MOCK_ONBOARDING_REQUESTS[request_idx]
    
    if request.status != "PENDING_REVIEW":
        raise HTTPException(status_code=400, detail="Request is not in pending review status")
    
    request.status = "IN_REVIEW"
    request.processed_by = current_user.email
    request.notes = f"Review started by {current_user.email}"
    
    MOCK_ONBOARDING_REQUESTS[request_idx] = request
    return OnboardingResponse(data=request)

@router.get("/summary", response_model=OnboardingSummaryResponse)
async def get_onboarding_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get onboarding summary statistics."""
    
    total_requests = len(MOCK_ONBOARDING_REQUESTS)
    pending_review = len([r for r in MOCK_ONBOARDING_REQUESTS if r.status == "PENDING_REVIEW"])
    in_review = len([r for r in MOCK_ONBOARDING_REQUESTS if r.status == "IN_REVIEW"])
    approved = len([r for r in MOCK_ONBOARDING_REQUESTS if r.status == "APPROVED"])
    rejected = len([r for r in MOCK_ONBOARDING_REQUESTS if r.status == "REJECTED"])
    
    # Calculate average processing time for completed requests
    completed_requests = [r for r in MOCK_ONBOARDING_REQUESTS 
                         if r.status in ["APPROVED", "REJECTED"] and r.processed_at]
    
    if completed_requests:
        processing_times = [(r.processed_at - r.submitted_at).days for r in completed_requests]
        average_processing_time = sum(processing_times) / len(processing_times)
    else:
        average_processing_time = 0
    
    approval_rate = approved / (approved + rejected) if (approved + rejected) > 0 else 0
    
    summary = OnboardingSummary(
        total_requests=total_requests,
        pending_review=pending_review,
        in_review=in_review,
        approved=approved,
        rejected=rejected,
        average_processing_time=average_processing_time,
        approval_rate=approval_rate
    )
    
    return OnboardingSummaryResponse(data=summary)

@router.delete("/{request_id}")
async def delete_onboarding_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Delete an onboarding request."""
    
    request_idx = next((i for i, r in enumerate(MOCK_ONBOARDING_REQUESTS) if r.id == request_id), None)
    if request_idx is None:
        raise HTTPException(status_code=404, detail="Onboarding request not found")
    
    MOCK_ONBOARDING_REQUESTS.pop(request_idx)
    return {"success": True, "message": "Onboarding request deleted successfully"}