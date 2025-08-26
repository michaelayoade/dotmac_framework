"""Inventory management API endpoints."""

from datetime import datetime, date, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.core.middleware import get_tenant_id_dependency
from .models import EquipmentStatus, MovementType
from .schemas import (
    EquipmentCreate,
    EquipmentUpdate,
    Equipment,
    EquipmentTypeCreate,
    EquipmentType,
    WarehouseCreate,
    WarehouseUpdate,
    Warehouse,
    VendorCreate,
    Vendor,
    StockMovementCreate,
    StockMovement,
)
from .service import InventoryService
from dotmac_isp.shared.exceptions import NotFoundError, ValidationError, ConflictError

router = APIRouter(tags=["inventory"])


# Equipment endpoints
@router.post(
    "/equipment", response_model=Equipment, status_code=status.HTTP_201_CREATED
)
async def create_equipment(
    equipment_data: EquipmentCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new equipment."""
    try:
        service = InventoryService(db, tenant_id)
        equipment = await service.create_equipment(equipment_data.model_dump())
        return equipment
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment", response_model=List[Equipment])
async def list_equipment(
    equipment_type_id: Optional[UUID] = Query(None),
    warehouse_id: Optional[UUID] = Query(None),
    status: Optional[EquipmentStatus] = Query(None),
    vendor_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List equipment with filtering."""
    try:
        service = InventoryService(db, tenant_id)
        equipment_list = await service.list_equipment(
            equipment_type_id=equipment_type_id,
            warehouse_id=warehouse_id,
            status=status,
            vendor_id=vendor_id,
            skip=skip,
            limit=limit,
        )
        return equipment_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment/{equipment_id}", response_model=Equipment)
async def get_equipment(
    equipment_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get equipment by ID."""
    try:
        service = InventoryService(db, tenant_id)
        equipment = await service.get_equipment(equipment_id)
        return equipment
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Equipment not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment/number/{equipment_number}", response_model=Equipment)
async def get_equipment_by_number(
    equipment_number: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get equipment by equipment number."""
    try:
        service = InventoryService(db, tenant_id)
        equipment = await service.get_equipment_by_number(equipment_number)
        return equipment
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Equipment not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/equipment/{equipment_id}/assign-customer")
async def assign_equipment_to_customer(
    equipment_id: UUID,
    customer_id: UUID = Query(...),
    service_instance_id: Optional[UUID] = Query(None),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Assign equipment to customer."""
    try:
        service = InventoryService(db, tenant_id)
        equipment = await service.assign_equipment_to_customer(
            equipment_id, customer_id, service_instance_id
        )
        return {"message": "Equipment assigned successfully", "equipment": equipment}
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Equipment not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/equipment/{equipment_id}/move")
async def move_equipment(
    equipment_id: UUID,
    warehouse_id: UUID = Query(...),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Move equipment to warehouse."""
    try:
        service = InventoryService(db, tenant_id)
        equipment = await service.move_equipment_to_warehouse(
            equipment_id, warehouse_id
        )
        return {"message": "Equipment moved successfully", "equipment": equipment}
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Equipment not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/equipment/{equipment_id}/status")
async def update_equipment_status(
    equipment_id: UUID,
    status: EquipmentStatus = Query(...),
    notes: Optional[str] = Query(None),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update equipment status."""
    try:
        service = InventoryService(db, tenant_id)
        equipment = await service.update_equipment_status(equipment_id, status, notes)
        return {"message": "Equipment status updated", "equipment": equipment}
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Equipment not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Equipment Type endpoints
@router.post(
    "/equipment-types",
    response_model=EquipmentType,
    status_code=status.HTTP_201_CREATED,
)
async def create_equipment_type(
    equipment_type_data: EquipmentTypeCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new equipment type."""
    try:
        service = InventoryService(db, tenant_id)
        equipment_type = await service.create_equipment_type(equipment_type_data.model_dump())
        return equipment_type
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment-types", response_model=List[EquipmentType])
async def list_equipment_types(
    is_active: Optional[bool] = Query(None),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List equipment types."""
    try:
        service = InventoryService(db, tenant_id)
        equipment_types = await service.list_equipment_types(is_active=is_active)
        return equipment_types
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Warehouse endpoints
@router.post(
    "/warehouses", response_model=Warehouse, status_code=status.HTTP_201_CREATED
)
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new warehouse."""
    try:
        service = InventoryService(db, tenant_id)
        warehouse = await service.create_warehouse(warehouse_data.model_dump())
        return warehouse
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/warehouses", response_model=List[Warehouse])
async def list_warehouses(
    is_active: Optional[bool] = Query(None),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List warehouses."""
    try:
        service = InventoryService(db, tenant_id)
        warehouses = await service.list_warehouses(is_active=is_active)
        return warehouses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Vendor endpoints
@router.post("/vendors", response_model=Vendor, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor_data: VendorCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create new vendor."""
    try:
        service = InventoryService(db, tenant_id)
        vendor = await service.create_vendor(vendor_data.model_dump())
        return vendor
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vendors", response_model=List[Vendor])
async def list_vendors(
    is_active: Optional[bool] = Query(None),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List vendors."""
    try:
        service = InventoryService(db, tenant_id)
        vendors = await service.list_vendors(is_active=is_active)
        return vendors
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Stock Movement endpoints
@router.post(
    "/stock-movements",
    response_model=StockMovement,
    status_code=status.HTTP_201_CREATED,
)
async def create_stock_movement(
    movement_data: StockMovementCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create stock movement."""
    try:
        service = InventoryService(db, tenant_id)
        movement = await service.create_stock_movement(movement_data.model_dump())
        return movement
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-movements", response_model=List[StockMovement])
async def list_stock_movements(
    equipment_id: Optional[UUID] = Query(None),
    warehouse_id: Optional[UUID] = Query(None),
    movement_type: Optional[MovementType] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List stock movements with filtering."""
    try:
        service = InventoryService(db, tenant_id)
        movements = await service.list_stock_movements(
            equipment_id=equipment_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            skip=skip,
            limit=limit,
        )
        return movements
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment/{equipment_id}/history", response_model=List[StockMovement])
async def get_equipment_history(
    equipment_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get movement history for equipment."""
    try:
        service = InventoryService(db, tenant_id)
        history = await service.get_equipment_history(equipment_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for inventory module."""
    return {
        "status": "healthy",
        "module": "inventory",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
