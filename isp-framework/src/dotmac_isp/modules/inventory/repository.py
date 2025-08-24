"""Repository pattern for inventory database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func

from dotmac_isp.modules.inventory.models import (
    Equipment,
    EquipmentType,
    Warehouse,
    Vendor,
    StockMovement,
    EquipmentStatus,
    MovementType,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class EquipmentRepository:
    """Repository for equipment database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, equipment_data: Dict[str, Any]) -> Equipment:
        """Create new equipment."""
        try:
            # Generate equipment number if not provided
            if not equipment_data.get("equipment_number"):
                equipment_data["equipment_number"] = self._generate_equipment_number()

            equipment = Equipment(
                id=uuid4(), tenant_id=self.tenant_id, **equipment_data
            )

            self.db.add(equipment)
            self.db.commit()
            self.db.refresh(equipment)
            return equipment

        except IntegrityError as e:
            self.db.rollback()
            if "equipment_number" in str(e):
                raise ConflictError(
                    f"Equipment number {equipment_data.get('equipment_number')} already exists"
                )
            if "serial_number" in str(e):
                raise ConflictError(
                    f"Serial number {equipment_data.get('serial_number')} already exists"
                )
            raise ConflictError("Equipment creation failed due to data conflict")

    def get_by_id(self, equipment_id: UUID) -> Optional[Equipment]:
        """Get equipment by ID."""
        return (
            self.db.query(Equipment)
            .filter(
                and_(
                    Equipment.id == equipment_id, Equipment.tenant_id == self.tenant_id
                )
            )
            .first()
        )

    def get_by_equipment_number(self, equipment_number: str) -> Optional[Equipment]:
        """Get equipment by equipment number."""
        return (
            self.db.query(Equipment)
            .filter(
                and_(
                    Equipment.equipment_number == equipment_number,
                    Equipment.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def get_by_serial_number(self, serial_number: str) -> Optional[Equipment]:
        """Get equipment by serial number."""
        return (
            self.db.query(Equipment)
            .filter(
                and_(
                    Equipment.serial_number == serial_number,
                    Equipment.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_equipment(
        self,
        equipment_type_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
        status: Optional[EquipmentStatus] = None,
        vendor_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Equipment]:
        """List equipment with filtering."""
        query = self.db.query(Equipment).filter(Equipment.tenant_id == self.tenant_id)

        if equipment_type_id:
            query = query.filter(Equipment.equipment_type_id == equipment_type_id)
        if warehouse_id:
            query = query.filter(Equipment.current_warehouse_id == warehouse_id)
        if status:
            query = query.filter(Equipment.status == status)
        if vendor_id:
            query = query.filter(Equipment.vendor_id == vendor_id)

        return (
            query.order_by(Equipment.created_at.desc()).offset(skip).limit(limit).all()
        )

    def update_status(
        self, equipment_id: UUID, status: EquipmentStatus, notes: Optional[str] = None
    ) -> Optional[Equipment]:
        """Update equipment status."""
        equipment = self.get_by_id(equipment_id)
        if not equipment:
            return None

        equipment.status = status
        equipment.updated_at = datetime.utcnow()

        if status == EquipmentStatus.DEPLOYED and not equipment.deployment_date:
            equipment.deployment_date = datetime.utcnow()
        elif (
            status == EquipmentStatus.DECOMMISSIONED and not equipment.decommission_date
        ):
            equipment.decommission_date = datetime.utcnow()

        if notes:
            equipment.notes = f"{equipment.notes or ''}\n{datetime.utcnow().isoformat()}: {notes}".strip()

        self.db.commit()
        self.db.refresh(equipment)
        return equipment

    def assign_to_customer(
        self,
        equipment_id: UUID,
        customer_id: UUID,
        service_instance_id: Optional[UUID] = None,
    ) -> Optional[Equipment]:
        """Assign equipment to customer."""
        equipment = self.get_by_id(equipment_id)
        if not equipment:
            return None

        equipment.assigned_customer_id = customer_id
        equipment.assigned_service_id = service_instance_id
        equipment.status = EquipmentStatus.DEPLOYED
        equipment.deployment_date = datetime.utcnow()
        equipment.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(equipment)
        return equipment

    def move_to_warehouse(
        self, equipment_id: UUID, warehouse_id: UUID
    ) -> Optional[Equipment]:
        """Move equipment to warehouse."""
        equipment = self.get_by_id(equipment_id)
        if not equipment:
            return None

        old_warehouse_id = equipment.current_warehouse_id
        equipment.current_warehouse_id = warehouse_id
        equipment.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(equipment)
        return equipment

    def _generate_equipment_number(self) -> str:
        """Generate unique equipment number."""
        today = date.today()
        count = (
            self.db.query(func.count(Equipment.id))
            .filter(
                and_(
                    Equipment.tenant_id == self.tenant_id,
                    func.date(Equipment.created_at) == today,
                )
            )
            .scalar()
        )

        return f"EQP-{today.strftime('%Y%m%d')}-{count + 1:04d}"


class EquipmentTypeRepository:
    """Repository for equipment type database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, equipment_type_data: Dict[str, Any]) -> EquipmentType:
        """Create new equipment type."""
        try:
            equipment_type = EquipmentType(
                id=uuid4(), tenant_id=self.tenant_id, **equipment_type_data
            )

            self.db.add(equipment_type)
            self.db.commit()
            self.db.refresh(equipment_type)
            return equipment_type

        except IntegrityError as e:
            self.db.rollback()
            if "name" in str(e):
                raise ConflictError(
                    f"Equipment type name {equipment_type_data.get('name')} already exists"
                )
            raise ConflictError("Equipment type creation failed due to data conflict")

    def get_by_id(self, equipment_type_id: UUID) -> Optional[EquipmentType]:
        """Get equipment type by ID."""
        return (
            self.db.query(EquipmentType)
            .filter(
                and_(
                    EquipmentType.id == equipment_type_id,
                    EquipmentType.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_equipment_types(
        self, is_active: Optional[bool] = None
    ) -> List[EquipmentType]:
        """List equipment types."""
        query = self.db.query(EquipmentType).filter(
            EquipmentType.tenant_id == self.tenant_id
        )

        if is_active is not None:
            query = query.filter(EquipmentType.is_active == is_active)

        return query.order_by(EquipmentType.name).all()


class WarehouseRepository:
    """Repository for warehouse database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, warehouse_data: Dict[str, Any]) -> Warehouse:
        """Create new warehouse."""
        try:
            warehouse = Warehouse(
                id=uuid4(), tenant_id=self.tenant_id, **warehouse_data
            )

            self.db.add(warehouse)
            self.db.commit()
            self.db.refresh(warehouse)
            return warehouse

        except IntegrityError as e:
            self.db.rollback()
            if "name" in str(e):
                raise ConflictError(
                    f"Warehouse name {warehouse_data.get('name')} already exists"
                )
            raise ConflictError("Warehouse creation failed due to data conflict")

    def get_by_id(self, warehouse_id: UUID) -> Optional[Warehouse]:
        """Get warehouse by ID."""
        return (
            self.db.query(Warehouse)
            .filter(
                and_(
                    Warehouse.id == warehouse_id, Warehouse.tenant_id == self.tenant_id
                )
            )
            .first()
        )

    def list_warehouses(self, is_active: Optional[bool] = None) -> List[Warehouse]:
        """List warehouses."""
        query = self.db.query(Warehouse).filter(Warehouse.tenant_id == self.tenant_id)

        if is_active is not None:
            query = query.filter(Warehouse.is_active == is_active)

        return query.order_by(Warehouse.name).all()


class VendorRepository:
    """Repository for vendor database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, vendor_data: Dict[str, Any]) -> Vendor:
        """Create new vendor."""
        try:
            vendor = Vendor(id=uuid4(), tenant_id=self.tenant_id, **vendor_data)

            self.db.add(vendor)
            self.db.commit()
            self.db.refresh(vendor)
            return vendor

        except IntegrityError as e:
            self.db.rollback()
            if "name" in str(e):
                raise ConflictError(
                    f"Vendor name {vendor_data.get('name')} already exists"
                )
            raise ConflictError("Vendor creation failed due to data conflict")

    def get_by_id(self, vendor_id: UUID) -> Optional[Vendor]:
        """Get vendor by ID."""
        return (
            self.db.query(Vendor)
            .filter(and_(Vendor.id == vendor_id, Vendor.tenant_id == self.tenant_id))
            .first()
        )

    def list_vendors(self, is_active: Optional[bool] = None) -> List[Vendor]:
        """List vendors."""
        query = self.db.query(Vendor).filter(Vendor.tenant_id == self.tenant_id)

        if is_active is not None:
            query = query.filter(Vendor.is_active == is_active)

        return query.order_by(Vendor.name).all()


class StockMovementRepository:
    """Repository for stock movement database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, movement_data: Dict[str, Any]) -> StockMovement:
        """Create new stock movement."""
        movement = StockMovement(id=uuid4(), tenant_id=self.tenant_id, **movement_data)

        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def get_by_id(self, movement_id: UUID) -> Optional[StockMovement]:
        """Get stock movement by ID."""
        return (
            self.db.query(StockMovement)
            .filter(
                and_(
                    StockMovement.id == movement_id,
                    StockMovement.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    def list_movements(
        self,
        equipment_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
        movement_type: Optional[MovementType] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[StockMovement]:
        """List stock movements with filtering."""
        query = self.db.query(StockMovement).filter(
            StockMovement.tenant_id == self.tenant_id
        )

        if equipment_id:
            query = query.filter(StockMovement.equipment_id == equipment_id)
        if warehouse_id:
            query = query.filter(
                or_(
                    StockMovement.from_warehouse_id == warehouse_id,
                    StockMovement.to_warehouse_id == warehouse_id,
                )
            )
        if movement_type:
            query = query.filter(StockMovement.movement_type == movement_type)

        return (
            query.order_by(StockMovement.movement_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_equipment_history(self, equipment_id: UUID) -> List[StockMovement]:
        """Get movement history for equipment."""
        return (
            self.db.query(StockMovement)
            .filter(
                and_(
                    StockMovement.equipment_id == equipment_id,
                    StockMovement.tenant_id == self.tenant_id,
                )
            )
            .order_by(StockMovement.movement_date.desc())
            .all()
        )
