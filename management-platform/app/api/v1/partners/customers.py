"""
Partner Customer Management API endpoints
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.partner import Partner, PartnerCustomer
from app.schemas.partner import (
    CustomerResponse, 
    CreateCustomerRequest, 
    UpdateCustomerRequest,
    PaginatedCustomersResponse
)
from app.core.security import get_current_partner
from app.core.territory import TerritoryValidator
from app.core.commission import CommissionCalculator
from app.core.validation import validate_customer_data

router = APIRouter(prefix="/partners/{partner_id}/customers", tags=["partner-customers"])


@router.get("", response_model=PaginatedCustomersResponse)
async def get_partner_customers(
    partner_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, max_length=100, description="Search term"),
    status: Optional[str] = Query(None, regex="^(active|pending|suspended|cancelled)$"),
    db: Session = Depends(get_db),
    current_partner: Partner = Depends(get_current_partner)
) -> PaginatedCustomersResponse:
    """
    Get paginated list of partner customers with filtering
    """
    
    # Verify partner access
    if current_partner.id != partner_id:
        raise HTTPException(status_code=403, detail="Access denied to partner customers")
    
    # Build base query
    query = db.query(PartnerCustomer).filter(PartnerCustomer.partner_id == partner_id)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                PartnerCustomer.name.ilike(search_term),
                PartnerCustomer.email.ilike(search_term),
                PartnerCustomer.id.ilike(search_term)
            )
        )
    
    if status:
        query = query.filter(PartnerCustomer.status == status)
    
    # Get total count for pagination
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    customers = query.order_by(PartnerCustomer.created_at.desc()).offset(offset).limit(limit).all()
    
    # Calculate pagination info
    total_pages = (total + limit - 1) // limit
    
    # Convert to response format
    customer_responses = []
    commission_calculator = CommissionCalculator()
    
    for customer in customers:
        customer_responses.append(CustomerResponse(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            address=customer.address,
            plan=customer.service_plan,
            mrr=customer.mrr,
            status=customer.status,
            join_date=customer.created_at,
            last_payment=customer.last_payment_date,
            connection_status=customer.connection_status,
            usage=customer.usage_percentage or 0.0
        ))
    
    return PaginatedCustomersResponse(
        customers=customer_responses,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_partner_customer(
    partner_id: str,
    customer_id: str,
    db: Session = Depends(get_db),
    current_partner: Partner = Depends(get_current_partner)
) -> CustomerResponse:
    """
    Get specific customer details
    """
    
    if current_partner.id != partner_id:
        raise HTTPException(status_code=403, detail="Access denied to partner customers")
    
    customer = db.query(PartnerCustomer).filter(
        and_(
            PartnerCustomer.id == customer_id,
            PartnerCustomer.partner_id == partner_id
        )
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        plan=customer.service_plan,
        mrr=customer.mrr,
        status=customer.status,
        join_date=customer.created_at,
        last_payment=customer.last_payment_date,
        connection_status=customer.connection_status,
        usage=customer.usage_percentage or 0.0
    )


@router.post("", response_model=CustomerResponse, status_code=201)
async def create_customer(
    partner_id: str,
    customer_data: CreateCustomerRequest,
    db: Session = Depends(get_db),
    current_partner: Partner = Depends(get_current_partner)
) -> CustomerResponse:
    """
    Create new customer for partner
    """
    
    if current_partner.id != partner_id:
        raise HTTPException(status_code=403, detail="Access denied to partner customers")
    
    # Validate business rules
    validation_result = await validate_customer_data(customer_data, partner_id, db)
    if not validation_result.is_valid:
        raise HTTPException(
            status_code=422, 
            detail={
                "message": "Customer validation failed",
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            }
        )
    
    # Validate territory
    territory_validator = TerritoryValidator(db)
    territory_result = await territory_validator.validate_address(
        customer_data.address, partner_id
    )
    
    if not territory_result.is_valid or territory_result.assigned_partner_id != partner_id:
        raise HTTPException(
            status_code=422,
            detail="Customer address is not in your assigned territory"
        )
    
    # Check for duplicate email
    existing_customer = db.query(PartnerCustomer).filter(
        PartnerCustomer.email == customer_data.email
    ).first()
    
    if existing_customer:
        raise HTTPException(status_code=409, detail="Customer with this email already exists")
    
    # Create customer
    customer = PartnerCustomer(
        partner_id=partner_id,
        name=customer_data.name,
        email=customer_data.email,
        phone=customer_data.phone,
        address=customer_data.address,
        service_plan=customer_data.plan,
        mrr=customer_data.mrr,
        status="pending",  # New customers start as pending
        created_at=datetime.utcnow(),
        connection_status="offline",
        usage_percentage=0.0
    )
    
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Calculate and create initial commission record
    commission_calculator = CommissionCalculator()
    commission_result = commission_calculator.calculate_customer_commission(
        customer, current_partner, is_new_customer=True
    )
    
    # Log commission calculation
    commission_calculator.create_commission_record(
        db, customer.id, partner_id, commission_result
    )
    
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        plan=customer.service_plan,
        mrr=customer.mrr,
        status=customer.status,
        join_date=customer.created_at,
        last_payment=customer.last_payment_date,
        connection_status=customer.connection_status,
        usage=customer.usage_percentage or 0.0
    )


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    partner_id: str,
    customer_id: str,
    customer_data: UpdateCustomerRequest,
    db: Session = Depends(get_db),
    current_partner: Partner = Depends(get_current_partner)
) -> CustomerResponse:
    """
    Update existing customer
    """
    
    if current_partner.id != partner_id:
        raise HTTPException(status_code=403, detail="Access denied to partner customers")
    
    customer = db.query(PartnerCustomer).filter(
        and_(
            PartnerCustomer.id == customer_id,
            PartnerCustomer.partner_id == partner_id
        )
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Validate business rules for updates
    update_data = customer_data.dict(exclude_unset=True)
    if update_data:
        validation_result = await validate_customer_data(customer_data, partner_id, db)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Customer validation failed", 
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings
                }
            )
    
    # Validate territory if address is being updated
    if customer_data.address:
        territory_validator = TerritoryValidator(db)
        territory_result = await territory_validator.validate_address(
            customer_data.address, partner_id
        )
        
        if not territory_result.is_valid or territory_result.assigned_partner_id != partner_id:
            raise HTTPException(
                status_code=422,
                detail="New address is not in your assigned territory"
            )
    
    # Update customer fields
    for field, value in update_data.items():
        if hasattr(customer, field):
            setattr(customer, field, value)
    
    customer.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(customer)
    
    # Recalculate commission if MRR or plan changed
    if customer_data.mrr is not None or customer_data.plan is not None:
        commission_calculator = CommissionCalculator()
        commission_result = commission_calculator.calculate_customer_commission(
            customer, current_partner
        )
        
        # Update commission record
        commission_calculator.update_commission_record(
            db, customer.id, partner_id, commission_result
        )
    
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        plan=customer.service_plan,
        mrr=customer.mrr,
        status=customer.status,
        join_date=customer.created_at,
        last_payment=customer.last_payment_date,
        connection_status=customer.connection_status,
        usage=customer.usage_percentage or 0.0
    )


@router.delete("/{customer_id}", status_code=204)
async def delete_customer(
    partner_id: str,
    customer_id: str,
    db: Session = Depends(get_db),
    current_partner: Partner = Depends(get_current_partner)
):
    """
    Delete customer (mark as cancelled)
    """
    
    if current_partner.id != partner_id:
        raise HTTPException(status_code=403, detail="Access denied to partner customers")
    
    customer = db.query(PartnerCustomer).filter(
        and_(
            PartnerCustomer.id == customer_id,
            PartnerCustomer.partner_id == partner_id
        )
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Soft delete - mark as cancelled
    customer.status = "cancelled"
    customer.cancelled_at = datetime.utcnow()
    customer.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Customer cancelled successfully"}


@router.post("/{customer_id}/validate-territory")
async def validate_customer_territory(
    partner_id: str,
    customer_id: str,
    db: Session = Depends(get_db),
    current_partner: Partner = Depends(get_current_partner)
):
    """
    Validate that customer is in partner's territory
    """
    
    if current_partner.id != partner_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    customer = db.query(PartnerCustomer).filter(
        and_(
            PartnerCustomer.id == customer_id,
            PartnerCustomer.partner_id == partner_id
        )
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    territory_validator = TerritoryValidator(db)
    result = await territory_validator.validate_address(customer.address, partner_id)
    
    return {
        "customer_id": customer_id,
        "is_valid": result.is_valid,
        "assigned_partner_id": result.assigned_partner_id,
        "territory_name": result.territory_name,
        "confidence": result.confidence,
        "warnings": result.warnings
    }