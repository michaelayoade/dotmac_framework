"""
Management Portal Licensing API - Contract Provisioning and Management.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.router_factory import Depends, Query, RouterFactory
from dotmac_shared.licensing.models import LicenseContract, LicenseStatus
from dotmac_shared.licensing.service import LicenseEnforcementService

from ..core.auth import get_current_user
from ..shared.database.base import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic schemas for API

class LicenseContractCreate(BaseModel):
    """License contract creation request."""
    subscription_id: str
    contract_type: str  # enterprise, professional, basic
    valid_from: datetime
    valid_until: datetime
    max_customers: Optional[int] = None
    max_concurrent_users: Optional[int] = None
    max_bandwidth_gbps: Optional[int] = None
    max_storage_gb: Optional[int] = None
    max_api_calls_per_hour: Optional[int] = None
    max_network_devices: Optional[int] = None
    enabled_features: List[str] = []
    disabled_features: List[str] = []
    feature_limits: dict = {}
    enforcement_mode: str = "strict"  # strict, warning, disabled
    target_isp_instance: str


class LicenseContractUpdate(BaseModel):
    """License contract update request."""
    status: Optional[LicenseStatus] = None
    valid_until: Optional[datetime] = None
    max_customers: Optional[int] = None
    max_concurrent_users: Optional[int] = None
    max_bandwidth_gbps: Optional[int] = None
    max_storage_gb: Optional[int] = None
    max_api_calls_per_hour: Optional[int] = None
    max_network_devices: Optional[int] = None
    enabled_features: Optional[List[str]] = None
    disabled_features: Optional[List[str]] = None
    feature_limits: Optional[dict] = None
    enforcement_mode: Optional[str] = None


class LicenseContractResponse(BaseModel):
    """License contract API response."""
    contract_id: str
    subscription_id: str
    status: str
    contract_type: str
    valid_from: datetime
    valid_until: datetime
    days_until_expiry: int
    enforcement_mode: str
    enabled_features: List[str]
    current_usage: dict
    violation_count: int
    target_isp_instance: str
    created_at: datetime
    updated_at: datetime


# Contract management endpoints

@router.post("/contracts", response_model=LicenseContractResponse)
@standard_exception_handler
async def create_license_contract(
    contract_data: LicenseContractCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a new license contract for ISP instance.
    
    This provisions licensing for an ISP portal based on a management portal subscription.
    """
    # Generate unique contract ID
    contract_id = f"LIC-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    
    # Calculate contract hash for integrity
    import hashlib
    contract_string = f"{contract_id}{contract_data.subscription_id}{contract_data.valid_from}{contract_data.valid_until}"
    contract_hash = hashlib.sha256(contract_string.encode()).hexdigest()
    
    # Create license contract
    license_contract = LicenseContract(
        tenant_id=current_user.tenant_id,
        contract_id=contract_id,
        subscription_id=contract_data.subscription_id,
        status=LicenseStatus.ACTIVE,
        contract_type=contract_data.contract_type,
        valid_from=contract_data.valid_from,
        valid_until=contract_data.valid_until,
        max_customers=contract_data.max_customers,
        max_concurrent_users=contract_data.max_concurrent_users,
        max_bandwidth_gbps=contract_data.max_bandwidth_gbps,
        max_storage_gb=contract_data.max_storage_gb,
        max_api_calls_per_hour=contract_data.max_api_calls_per_hour,
        max_network_devices=contract_data.max_network_devices,
        enabled_features=contract_data.enabled_features,
        disabled_features=contract_data.disabled_features,
        feature_limits=contract_data.feature_limits,
        enforcement_mode=contract_data.enforcement_mode,
        issuer_management_instance=f"mgmt-{current_user.tenant_id}",
        target_isp_instance=contract_data.target_isp_instance,
        contract_hash=contract_hash,
        current_usage={}
    )
    
    db.add(license_contract)
    
    try:
        db.commit()
        logger.info(f"Created license contract {contract_id} for subscription {contract_data.subscription_id}")
        
        return LicenseContractResponse(
            contract_id=license_contract.contract_id,
            subscription_id=license_contract.subscription_id,
            status=license_contract.status,
            contract_type=license_contract.contract_type,
            valid_from=license_contract.valid_from,
            valid_until=license_contract.valid_until,
            days_until_expiry=license_contract.days_until_expiry,
            enforcement_mode=license_contract.enforcement_mode,
            enabled_features=license_contract.enabled_features,
            current_usage=license_contract.current_usage,
            violation_count=license_contract.violation_count,
            target_isp_instance=license_contract.target_isp_instance,
            created_at=license_contract.created_at,
            updated_at=license_contract.updated_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create license contract: {e}")
        raise HTTPException(status_code=500, detail="Failed to create license contract")


@router.get("/contracts", response_model=List[LicenseContractResponse])
@standard_exception_handler
async def list_license_contracts(
    status: Optional[str] = Query(None, description="Filter by contract status"),
    contract_type: Optional[str] = Query(None, description="Filter by contract type"),
    expiring_in_days: Optional[int] = Query(None, description="Filter contracts expiring within N days"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List license contracts for current management tenant."""
    query = db.query(LicenseContract).filter(
        LicenseContract.tenant_id == current_user.tenant_id
    )
    
    # Apply filters
    if status:
        query = query.filter(LicenseContract.status == status)
    
    if contract_type:
        query = query.filter(LicenseContract.contract_type == contract_type)
    
    if expiring_in_days:
        expiry_threshold = datetime.utcnow() + timedelta(days=expiring_in_days)
        query = query.filter(LicenseContract.valid_until <= expiry_threshold)
    
    # Get paginated results
    contracts = query.offset(offset).limit(limit).all()
    
    return [
        LicenseContractResponse(
            contract_id=contract.contract_id,
            subscription_id=contract.subscription_id,
            status=contract.status,
            contract_type=contract.contract_type,
            valid_from=contract.valid_from,
            valid_until=contract.valid_until,
            days_until_expiry=contract.days_until_expiry,
            enforcement_mode=contract.enforcement_mode,
            enabled_features=contract.enabled_features,
            current_usage=contract.current_usage,
            violation_count=contract.violation_count,
            target_isp_instance=contract.target_isp_instance,
            created_at=contract.created_at,
            updated_at=contract.updated_at
        )
        for contract in contracts
    ]


@router.get("/contracts/{contract_id}", response_model=LicenseContractResponse)
@standard_exception_handler
async def get_license_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get specific license contract details."""
    contract = db.query(LicenseContract).filter(
        LicenseContract.contract_id == contract_id,
        LicenseContract.tenant_id == current_user.tenant_id
    ).first()
    
    if not contract:
        raise HTTPException(status_code=404, detail="License contract not found")
    
    return LicenseContractResponse(
        contract_id=contract.contract_id,
        subscription_id=contract.subscription_id,
        status=contract.status,
        contract_type=contract.contract_type,
        valid_from=contract.valid_from,
        valid_until=contract.valid_until,
        days_until_expiry=contract.days_until_expiry,
        enforcement_mode=contract.enforcement_mode,
        enabled_features=contract.enabled_features,
        current_usage=contract.current_usage,
        violation_count=contract.violation_count,
        target_isp_instance=contract.target_isp_instance,
        created_at=contract.created_at,
        updated_at=contract.updated_at
    )


@router.put("/contracts/{contract_id}", response_model=LicenseContractResponse)
@standard_exception_handler
async def update_license_contract(
    contract_id: str,
    update_data: LicenseContractUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update license contract parameters."""
    contract = db.query(LicenseContract).filter(
        LicenseContract.contract_id == contract_id,
        LicenseContract.tenant_id == current_user.tenant_id
    ).first()
    
    if not contract:
        raise HTTPException(status_code=404, detail="License contract not found")
    
    # Update provided fields
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(contract, field, value)
    
    contract.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        logger.info(f"Updated license contract {contract_id}")
        
        return LicenseContractResponse(
            contract_id=contract.contract_id,
            subscription_id=contract.subscription_id,
            status=contract.status,
            contract_type=contract.contract_type,
            valid_from=contract.valid_from,
            valid_until=contract.valid_until,
            days_until_expiry=contract.days_until_expiry,
            enforcement_mode=contract.enforcement_mode,
            enabled_features=contract.enabled_features,
            current_usage=contract.current_usage,
            violation_count=contract.violation_count,
            target_isp_instance=contract.target_isp_instance,
            created_at=contract.created_at,
            updated_at=contract.updated_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update license contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update license contract")


@router.post("/contracts/{contract_id}/suspend")
@standard_exception_handler
async def suspend_license_contract(
    contract_id: str,
    reason: str = Query(..., description="Reason for suspension"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Suspend a license contract."""
    contract = db.query(LicenseContract).filter(
        LicenseContract.contract_id == contract_id,
        LicenseContract.tenant_id == current_user.tenant_id
    ).first()
    
    if not contract:
        raise HTTPException(status_code=404, detail="License contract not found")
    
    contract.status = LicenseStatus.SUSPENDED
    contract.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        logger.warning(f"Suspended license contract {contract_id}: {reason}")
        return {"message": "License contract suspended", "contract_id": contract_id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to suspend license contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to suspend license contract")


@router.post("/contracts/{contract_id}/reactivate")
@standard_exception_handler
async def reactivate_license_contract(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Reactivate a suspended license contract."""
    contract = db.query(LicenseContract).filter(
        LicenseContract.contract_id == contract_id,
        LicenseContract.tenant_id == current_user.tenant_id
    ).first()
    
    if not contract:
        raise HTTPException(status_code=404, detail="License contract not found")
    
    if contract.is_expired:
        raise HTTPException(status_code=400, detail="Cannot reactivate expired contract")
    
    contract.status = LicenseStatus.ACTIVE
    contract.violation_count = 0  # Reset violation count on reactivation
    contract.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        logger.info(f"Reactivated license contract {contract_id}")
        return {"message": "License contract reactivated", "contract_id": contract_id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reactivate license contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reactivate license contract")


@router.get("/contracts/{contract_id}/status")
@standard_exception_handler
async def get_contract_status(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get comprehensive contract status including validation results."""
    # Use enforcement service for comprehensive status
    enforcement_service = LicenseEnforcementService(db, current_user.tenant_id)
    
    status = enforcement_service.get_contract_status(contract_id)
    if not status:
        raise HTTPException(status_code=404, detail="License contract not found")
    
    return status


# Export router
__all__ = ["router"]