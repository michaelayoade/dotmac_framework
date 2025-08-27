"""
Partners API endpoints
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

router = APIRouter(prefix="/partners", tags=["partners"])

# Partner Models (temporary - should be moved to proper models)
class Partner(BaseModel):
    id: str = Field(..., description="Partner ID")
    partner_code: str = Field(..., description="Unique partner code")
    name: str = Field(..., description="Partner name")
    email: str = Field(..., description="Partner email")
    status: str = Field(..., description="Partner status")
    tier: str = Field(..., description="Partner tier")
    join_date: datetime = Field(..., description="Date partner joined")
    territory: Optional[str] = Field(None, description="Partner territory")
    total_customers: int = Field(0, description="Total customers")
    monthly_revenue: float = Field(0.0, description="Monthly recurring revenue")

class PartnerCreate(BaseModel):
    name: str
    email: str
    territory: Optional[str] = None

class PartnerUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    tier: Optional[str] = None

class PartnerListResponse(BaseModel):
    success: bool = True
    data: List[Partner]
    total: int
    page: int = 1
    per_page: int = 50

class PartnerResponse(BaseModel):
    success: bool = True
    data: Partner

# Mock data for development/testing
MOCK_PARTNERS = [
    Partner(
        id="partner-001",
        partner_code="PART-001",
        name="Acme ISP Solutions",
        email="contact@acme-isp.com",
        status="ACTIVE",
        tier="GOLD",
        join_date=datetime.now() - timedelta(days=365),
        territory="North America",
        total_customers=150,
        monthly_revenue=75000.0
    ),
    Partner(
        id="partner-002",
        partner_code="PART-002", 
        name="TechNet Partners",
        email="info@technet.com",
        status="ACTIVE",
        tier="SILVER",
        join_date=datetime.now() - timedelta(days=180),
        territory="Europe",
        total_customers=89,
        monthly_revenue=42000.0
    ),
    Partner(
        id="partner-003",
        partner_code="PART-003",
        name="Global Connect",
        email="hello@globalconnect.com", 
        status="PENDING",
        tier="BRONZE",
        join_date=datetime.now() - timedelta(days=30),
        territory="Asia-Pacific",
        total_customers=23,
        monthly_revenue=12000.0
    )
]

@router.get("/", response_model=PartnerListResponse)
async def list_partners(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """List all partners with filtering and pagination."""
    
    # Filter partners based on query parameters
    filtered_partners = MOCK_PARTNERS.copy()
    
    if status:
        filtered_partners = [p for p in filtered_partners if p.status == status]
    
    if tier:
        filtered_partners = [p for p in filtered_partners if p.tier == tier]
    
    if search:
        search_lower = search.lower()
        filtered_partners = [
            p for p in filtered_partners 
            if search_lower in p.name.lower() or search_lower in p.email.lower()
        ]
    
    # Pagination
    total = len(filtered_partners)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_partners = filtered_partners[start_idx:end_idx]
    
    return PartnerListResponse(
        data=paginated_partners,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/{partner_id}", response_model=PartnerResponse)
async def get_partner(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Get a specific partner by ID."""
    
    partner = next((p for p in MOCK_PARTNERS if p.id == partner_id), None)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    return PartnerResponse(data=partner)

@router.post("/", response_model=PartnerResponse)
async def create_partner(
    partner_data: PartnerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Create a new partner."""
    
    # Check if partner with email already exists
    existing_partner = next((p for p in MOCK_PARTNERS if p.email == partner_data.email), None)
    if existing_partner:
        raise HTTPException(status_code=400, detail="Partner with this email already exists")
    
    # Create new partner
    new_partner = Partner(
        id=f"partner-{str(uuid4())[:8]}",
        partner_code=f"PART-{len(MOCK_PARTNERS) + 1:03d}",
        name=partner_data.name,
        email=partner_data.email,
        status="PENDING",
        tier="BRONZE",
        join_date=datetime.now(),
        territory=partner_data.territory,
        total_customers=0,
        monthly_revenue=0.0
    )
    
    MOCK_PARTNERS.append(new_partner)
    return PartnerResponse(data=new_partner)

@router.put("/{partner_id}", response_model=PartnerResponse)
async def update_partner(
    partner_id: str,
    partner_update: PartnerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Update an existing partner."""
    
    partner_idx = next((i for i, p in enumerate(MOCK_PARTNERS) if p.id == partner_id), None)
    if partner_idx is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = MOCK_PARTNERS[partner_idx]
    
    # Update partner fields
    if partner_update.name is not None:
        partner.name = partner_update.name
    if partner_update.status is not None:
        partner.status = partner_update.status
    if partner_update.tier is not None:
        partner.tier = partner_update.tier
    
    MOCK_PARTNERS[partner_idx] = partner
    return PartnerResponse(data=partner)

@router.delete("/{partner_id}")
async def delete_partner(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Delete a partner."""
    
    partner_idx = next((i for i, p in enumerate(MOCK_PARTNERS) if p.id == partner_id), None)
    if partner_idx is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    MOCK_PARTNERS.pop(partner_idx)
    return {"success": True, "message": "Partner deleted successfully"}

@router.post("/{partner_id}/approve", response_model=PartnerResponse)
async def approve_partner(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Approve a partner."""
    
    partner_idx = next((i for i, p in enumerate(MOCK_PARTNERS) if p.id == partner_id), None)
    if partner_idx is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = MOCK_PARTNERS[partner_idx]
    partner.status = "ACTIVE"
    
    MOCK_PARTNERS[partner_idx] = partner
    return PartnerResponse(data=partner)

@router.post("/{partner_id}/suspend", response_model=PartnerResponse)
async def suspend_partner(
    partner_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Suspend a partner."""
    
    partner_idx = next((i for i, p in enumerate(MOCK_PARTNERS) if p.id == partner_id), None)
    if partner_idx is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner = MOCK_PARTNERS[partner_idx]
    partner.status = "SUSPENDED"
    
    MOCK_PARTNERS[partner_idx] = partner
    return PartnerResponse(data=partner)

@router.put("/{partner_id}/tier", response_model=PartnerResponse)
async def update_partner_tier(
    partner_id: str,
    tier_data: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_active_user)
):
    """Update partner tier."""
    
    partner_idx = next((i for i, p in enumerate(MOCK_PARTNERS) if p.id == partner_id), None)
    if partner_idx is None:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    new_tier = tier_data.get("tier")
    if not new_tier:
        raise HTTPException(status_code=400, detail="Tier is required")
    
    valid_tiers = ["BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND"]
    if new_tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Must be one of: {valid_tiers}")
    
    partner = MOCK_PARTNERS[partner_idx]
    partner.tier = new_tier
    
    MOCK_PARTNERS[partner_idx] = partner
    return PartnerResponse(data=partner)