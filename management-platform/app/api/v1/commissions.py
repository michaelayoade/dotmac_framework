"""
Commissions API endpoints
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.core.auth import get_current_active_user
from app.core.deps import CurrentUser

router = APIRouter(prefix="/commissions", tags=["commissions"])

# Commission Models (temporary - should be moved to proper models)
class CommissionDeduction(BaseModel):
    id: str = Field(..., description="Deduction ID")
    type: str = Field(..., description="Deduction type")
    description: str = Field(..., description="Deduction description")
    amount: float = Field(..., description="Deduction amount")
    percentage: Optional[float] = Field(None, description="Deduction percentage")
    applied_at: datetime = Field(..., description="When deduction was applied")

class Commission(BaseModel):
    id: str = Field(..., description="Commission ID")
    payment_number: str = Field(..., description="Payment number")
    partner_id: str = Field(..., description="Partner ID")
    partner_name: str = Field(..., description="Partner name")
    partner_tier: str = Field(..., description="Partner tier")
    period_start: str = Field(..., description="Commission period start")
    period_end: str = Field(..., description="Commission period end")
    gross_amount: float = Field(..., description="Gross commission amount")
    deductions: List[CommissionDeduction] = Field(default_factory=list, description="Deductions")
    net_amount: float = Field(..., description="Net commission amount")
    payment_date: Optional[str] = Field(None, description="Payment date")
    payment_method: str = Field(..., description="Payment method")
    status: str = Field(..., description="Commission status")
    created_at: str = Field(..., description="Creation date")
    updated_at: str = Field(..., description="Last update date")
    sales_count: int = Field(..., description="Number of sales")
    approval_notes: Optional[str] = Field(None, description="Approval notes")
    approved_by: Optional[str] = Field(None, description="Approved by user")
    approved_at: Optional[str] = Field(None, description="Approval date")

class CommissionBulkApprove(BaseModel):
    ids: List[str] = Field(..., description="Commission IDs to approve")
    notes: Optional[str] = Field(None, description="Approval notes")

class CommissionBulkProcess(BaseModel):
    ids: List[str] = Field(..., description="Commission IDs to process")

class CommissionDispute(BaseModel):
    reason: str = Field(..., description="Dispute reason")

class CommissionListResponse(BaseModel):
    success: bool = True
    data: List[Commission]
    total: int
    page: int = 1
    per_page: int = 50

class CommissionResponse(BaseModel):
    success: bool = True
    data: Commission

class CommissionSummary(BaseModel):
    total_commissions: int
    pending_approval: int
    approved: int
    paid: int
    disputed: int
    total_gross_amount: float
    total_net_amount: float
    average_commission: float

class CommissionSummaryResponse(BaseModel):
    success: bool = True
    data: CommissionSummary

# Mock data for development/testing
MOCK_COMMISSIONS = [
    Commission(
        id="comm-001",
        payment_number="PAY-2024-001",
        partner_id="partner-001",
        partner_name="Acme ISP Solutions",
        partner_tier="GOLD",
        period_start="2024-01-01",
        period_end="2024-01-31",
        gross_amount=7500.0,
        deductions=[
            CommissionDeduction(
                id="deduct-001",
                type="TAX",
                description="Federal tax withholding",
                amount=1125.0,
                percentage=15.0,
                applied_at=datetime.now() - timedelta(days=5)
            )
        ],
        net_amount=6375.0,
        payment_date="2024-02-15",
        payment_method="ACH",
        status="PAID",
        created_at="2024-02-01T10:00:00Z",
        updated_at="2024-02-15T14:30:00Z",
        sales_count=15,
        approval_notes="All sales verified and approved",
        approved_by="admin@dotmac.app",
        approved_at="2024-02-05T09:00:00Z"
    ),
    Commission(
        id="comm-002",
        payment_number="PAY-2024-002",
        partner_id="partner-002",
        partner_name="TechNet Partners",
        partner_tier="SILVER",
        period_start="2024-01-01",
        period_end="2024-01-31",
        gross_amount=4200.0,
        deductions=[
            CommissionDeduction(
                id="deduct-002",
                type="FEE",
                description="Processing fee",
                amount=84.0,
                percentage=2.0,
                applied_at=datetime.now() - timedelta(days=3)
            )
        ],
        net_amount=4116.0,
        payment_method="CHECK",
        status="APPROVED",
        created_at="2024-02-01T10:00:00Z",
        updated_at="2024-02-10T11:00:00Z",
        sales_count=9,
        approval_notes="Standard approval",
        approved_by="admin@dotmac.app",
        approved_at="2024-02-10T11:00:00Z"
    ),
    Commission(
        id="comm-003",
        payment_number="PAY-2024-003",
        partner_id="partner-003",
        partner_name="Global Connect",
        partner_tier="BRONZE",
        period_start="2024-01-01",
        period_end="2024-01-31",
        gross_amount=1200.0,
        deductions=[],
        net_amount=1200.0,
        payment_method="ACH",
        status="CALCULATED",
        created_at="2024-02-01T10:00:00Z",
        updated_at="2024-02-01T10:00:00Z",
        sales_count=3
    )
]

@router.get("/", response_model=CommissionListResponse)
async def list_commissions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    partner_id: Optional[str] = Query(None),
    payment_method: Optional[str] = Query(None),
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """List all commissions with filtering and pagination."""
    
    # Filter commissions based on query parameters
    filtered_commissions = MOCK_COMMISSIONS.copy()
    
    if status:
        filtered_commissions = [c for c in filtered_commissions if c.status == status]
    
    if partner_id:
        filtered_commissions = [c for c in filtered_commissions if c.partner_id == partner_id]
    
    if payment_method:
        filtered_commissions = [c for c in filtered_commissions if c.payment_method == payment_method]
    
    # Pagination
    total = len(filtered_commissions)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_commissions = filtered_commissions[start_idx:end_idx]
    
    return CommissionListResponse(
        data=paginated_commissions,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/{commission_id}", response_model=CommissionResponse)
async def get_commission(
    commission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get a specific commission by ID."""
    
    commission = next((c for c in MOCK_COMMISSIONS if c.id == commission_id), None)
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    return CommissionResponse(data=commission)

@router.post("/{commission_id}/approve", response_model=CommissionResponse)
async def approve_commission(
    commission_id: str,
    approval_data: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Approve a commission."""
    
    commission_idx = next((i for i, c in enumerate(MOCK_COMMISSIONS) if c.id == commission_id), None)
    if commission_idx is None:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    commission = MOCK_COMMISSIONS[commission_idx]
    
    if commission.status != "CALCULATED":
        raise HTTPException(status_code=400, detail="Commission can only be approved from CALCULATED status")
    
    commission.status = "APPROVED"
    commission.approval_notes = approval_data.get("notes", "")
    commission.approved_by = current_user.email
    commission.approved_at = datetime.now().isoformat()
    commission.updated_at = datetime.now().isoformat()
    
    MOCK_COMMISSIONS[commission_idx] = commission
    return CommissionResponse(data=commission)

@router.post("/bulk-approve", response_model=Dict[str, List[Commission]])
async def bulk_approve_commissions(
    approval_data: CommissionBulkApprove,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Approve multiple commissions."""
    
    approved_commissions = []
    errors = []
    
    for commission_id in approval_data.ids:
        commission_idx = next((i for i, c in enumerate(MOCK_COMMISSIONS) if c.id == commission_id), None)
        if commission_idx is None:
            errors.append(f"Commission {commission_id} not found")
            continue
            
        commission = MOCK_COMMISSIONS[commission_idx]
        
        if commission.status != "CALCULATED":
            errors.append(f"Commission {commission_id} cannot be approved from {commission.status} status")
            continue
        
        commission.status = "APPROVED"
        commission.approval_notes = approval_data.notes or ""
        commission.approved_by = current_user.email
        commission.approved_at = datetime.now().isoformat()
        commission.updated_at = datetime.now().isoformat()
        
        MOCK_COMMISSIONS[commission_idx] = commission
        approved_commissions.append(commission)
    
    return {
        "success": True,
        "data": approved_commissions,
        "errors": errors
    }

@router.post("/{commission_id}/process", response_model=CommissionResponse)
async def process_commission(
    commission_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Process (pay) a commission."""
    
    commission_idx = next((i for i, c in enumerate(MOCK_COMMISSIONS) if c.id == commission_id), None)
    if commission_idx is None:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    commission = MOCK_COMMISSIONS[commission_idx]
    
    if commission.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Commission can only be processed from APPROVED status")
    
    commission.status = "PAID"
    commission.payment_date = datetime.now().date().isoformat()
    commission.updated_at = datetime.now().isoformat()
    
    MOCK_COMMISSIONS[commission_idx] = commission
    return CommissionResponse(data=commission)

@router.post("/bulk-process", response_model=Dict[str, List[Commission]])
async def bulk_process_commissions(
    process_data: CommissionBulkProcess,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Process (pay) multiple commissions."""
    
    processed_commissions = []
    errors = []
    
    for commission_id in process_data.ids:
        commission_idx = next((i for i, c in enumerate(MOCK_COMMISSIONS) if c.id == commission_id), None)
        if commission_idx is None:
            errors.append(f"Commission {commission_id} not found")
            continue
            
        commission = MOCK_COMMISSIONS[commission_idx]
        
        if commission.status != "APPROVED":
            errors.append(f"Commission {commission_id} cannot be processed from {commission.status} status")
            continue
        
        commission.status = "PAID"
        commission.payment_date = datetime.now().date().isoformat()
        commission.updated_at = datetime.now().isoformat()
        
        MOCK_COMMISSIONS[commission_idx] = commission
        processed_commissions.append(commission)
    
    return {
        "success": True,
        "data": processed_commissions,
        "errors": errors
    }

@router.post("/{commission_id}/dispute", response_model=CommissionResponse)
async def dispute_commission(
    commission_id: str,
    dispute_data: CommissionDispute,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Dispute a commission."""
    
    commission_idx = next((i for i, c in enumerate(MOCK_COMMISSIONS) if c.id == commission_id), None)
    if commission_idx is None:
        raise HTTPException(status_code=404, detail="Commission not found")
    
    commission = MOCK_COMMISSIONS[commission_idx]
    commission.status = "DISPUTED"
    commission.approval_notes = f"DISPUTED: {dispute_data.reason}"
    commission.updated_at = datetime.now().isoformat()
    
    MOCK_COMMISSIONS[commission_idx] = commission
    return CommissionResponse(data=commission)

@router.get("/summary", response_model=CommissionSummaryResponse)
async def get_commission_summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get commission summary statistics."""
    
    total_commissions = len(MOCK_COMMISSIONS)
    pending_approval = len([c for c in MOCK_COMMISSIONS if c.status == "CALCULATED"])
    approved = len([c for c in MOCK_COMMISSIONS if c.status == "APPROVED"])
    paid = len([c for c in MOCK_COMMISSIONS if c.status == "PAID"])
    disputed = len([c for c in MOCK_COMMISSIONS if c.status == "DISPUTED"])
    
    total_gross_amount = sum(c.gross_amount for c in MOCK_COMMISSIONS)
    total_net_amount = sum(c.net_amount for c in MOCK_COMMISSIONS)
    average_commission = total_net_amount / total_commissions if total_commissions > 0 else 0
    
    summary = CommissionSummary(
        total_commissions=total_commissions,
        pending_approval=pending_approval,
        approved=approved,
        paid=paid,
        disputed=disputed,
        total_gross_amount=total_gross_amount,
        total_net_amount=total_net_amount,
        average_commission=average_commission
    )
    
    return CommissionSummaryResponse(data=summary)

@router.get("/export", response_class=None)
async def export_commissions(
    format: str = Query("csv", regex="^(csv|xlsx|pdf)$"),
    status: Optional[str] = Query(None),
    partner_id: Optional[str] = Query(None),
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Export commissions data."""
    
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    # Filter commissions based on query parameters
    filtered_commissions = MOCK_COMMISSIONS.copy()
    
    if status:
        filtered_commissions = [c for c in filtered_commissions if c.status == status]
    
    if partner_id:
        filtered_commissions = [c for c in filtered_commissions if c.partner_id == partner_id]
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            "ID", "Payment Number", "Partner Name", "Partner Tier",
            "Period Start", "Period End", "Gross Amount", "Net Amount",
            "Payment Method", "Status", "Sales Count", "Created At"
        ])
        
        # Write data
        for commission in filtered_commissions:
            writer.writerow([
                commission.id,
                commission.payment_number,
                commission.partner_name,
                commission.partner_tier,
                commission.period_start,
                commission.period_end,
                commission.gross_amount,
                commission.net_amount,
                commission.payment_method,
                commission.status,
                commission.sales_count,
                commission.created_at
            ])
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=commissions_export.csv"}
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Export format '{format}' not supported")