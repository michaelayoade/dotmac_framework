"""Service layer for inventory management operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.orm import Session

from dotmac_isp.shared.base_service import BaseTenantService
from dotmac_isp.modules.inventory import schemas
from dotmac_isp.modules.inventory.models import (
    Equipment,
    EquipmentType,
    Warehouse,
    Vendor,
    StockMovement,
    EquipmentStatus,
    MovementType,
    ItemCondition,
, timezone)
from dotmac_isp.shared.exceptions import (
    ServiceError,
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
)


class EquipmentService(BaseTenantService[Equipment, schemas.EquipmentCreate, schemas.EquipmentUpdate, schemas.EquipmentResponse]):
    """Service for equipment management."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        super().__init__(
            db=db,
            model_class=Equipment,
            create_schema=schemas.EquipmentCreate,
            update_schema=schemas.EquipmentUpdate,
            response_schema=schemas.EquipmentResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.EquipmentCreate) -> None:
        """Validate business rules for equipment creation."""
        # Ensure serial number is unique if provided
        if data.serial_number and await self.repository.exists({'serial_number': data.serial_number}):
            raise BusinessRuleError(
                f"Equipment with serial number '{data.serial_number}' already exists",
                rule_name="unique_serial_number"
            )
        
        # Validate purchase price is positive
        if hasattr(data, 'purchase_price') and data.purchase_price and data.purchase_price <= 0:
            raise ValidationError("Purchase price must be positive")

    async def _validate_update_rules(self, entity: Equipment, data: schemas.EquipmentUpdate) -> None:
        """Validate business rules for equipment updates."""
        # Prevent status change to deployed if equipment has issues
        if data.status == EquipmentStatus.DEPLOYED and entity.condition != ItemCondition.NEW:
            # Allow with business justification, but log the decision
            pass
        
        # Validate serial number uniqueness if changing
        if data.serial_number and data.serial_number != entity.serial_number:
            if await self.repository.exists({'serial_number': data.serial_number}):
                raise BusinessRuleError(
                    f"Equipment with serial number '{data.serial_number}' already exists",
                    rule_name="unique_serial_number"
                )

    async def _post_create_hook(self, entity: Equipment, data: schemas.EquipmentCreate) -> None:
        """Create stock movement record after equipment creation."""
        try:
            # Create initial stock movement for equipment receipt
            movement_service = StockMovementService(self.db, self.tenant_id)
            await movement_service.create(schemas.StockMovementCreate(
                equipment_id=entity.id,
                movement_type=MovementType.RECEIVED,
                quantity=1,
                warehouse_id=data.warehouse_id,
                notes=f"Initial receipt of equipment {entity.model}"
            )
        except Exception as e:
            self._logger.error(f"Failed to create stock movement for equipment {entity.id}: {e}")


class WarehouseService(BaseTenantService[Warehouse, schemas.WarehouseCreate, schemas.WarehouseUpdate, schemas.WarehouseResponse]):
    """Service for warehouse management."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        super().__init__(
            db=db,
            model_class=Warehouse,
            create_schema=schemas.WarehouseCreate,
            update_schema=schemas.WarehouseUpdate,
            response_schema=schemas.WarehouseResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.WarehouseCreate) -> None:
        """Validate business rules for warehouse creation."""
        # Ensure warehouse name is unique for tenant
        if await self.repository.exists({'name': data.name}):
            raise BusinessRuleError(
                f"Warehouse with name '{data.name}' already exists",
                rule_name="unique_warehouse_name"
            )

    async def _validate_update_rules(self, entity: Warehouse, data: schemas.WarehouseUpdate) -> None:
        """Validate business rules for warehouse updates."""
        # Prevent deactivation if warehouse has active inventory
        if data.is_active == False and entity.is_active:
            # Check for active inventory (simplified check)
            equipment_count = await self.repository.count({'warehouse_id': entity.id, 'status': EquipmentStatus.IN_STOCK})
            if equipment_count > 0:
                raise BusinessRuleError(
                    "Cannot deactivate warehouse with active inventory",
                    rule_name="active_inventory_protection"
                )


class VendorService(BaseTenantService[Vendor, schemas.VendorCreate, schemas.VendorUpdate, schemas.VendorResponse]):
    """Service for vendor management."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        super().__init__(
            db=db,
            model_class=Vendor,
            create_schema=schemas.VendorCreate,
            update_schema=schemas.VendorUpdate,
            response_schema=schemas.VendorResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.VendorCreate) -> None:
        """Validate business rules for vendor creation."""
        # Ensure vendor name is unique for tenant
        if await self.repository.exists({'name': data.name}):
            raise BusinessRuleError(
                f"Vendor with name '{data.name}' already exists",
                rule_name="unique_vendor_name"
            )
        
        # Validate email format if provided
        if hasattr(data, 'email') and data.email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, data.email):
                raise ValidationError("Invalid email format")


class StockMovementService(BaseTenantService[StockMovement, schemas.StockMovementCreate, schemas.StockMovementUpdate, schemas.StockMovementResponse]):
    """Service for stock movement tracking."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        super().__init__(
            db=db,
            model_class=StockMovement,
            create_schema=schemas.StockMovementCreate,
            update_schema=schemas.StockMovementUpdate,
            response_schema=schemas.StockMovementResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.StockMovementCreate) -> None:
        """Validate business rules for stock movement creation."""
        if not data.equipment_id:
            raise ValidationError("Equipment ID is required for stock movement")
        
        # Validate quantity is positive
        if data.quantity <= 0:
            raise ValidationError("Movement quantity must be positive")

    async def _post_create_hook(self, entity: StockMovement, data: schemas.StockMovementCreate) -> None:
        """Update equipment status based on movement type."""
        try:
            equipment_service = EquipmentService(self.db, self.tenant_id)
            
            # Update equipment status based on movement type
            if entity.movement_type == MovementType.DEPLOYED:
                await equipment_service.update(entity.equipment_id, 
                    schemas.EquipmentUpdate(status=EquipmentStatus.DEPLOYED)
            elif entity.movement_type == MovementType.RETURNED:
                await equipment_service.update(entity.equipment_id, 
                    schemas.EquipmentUpdate(status=EquipmentStatus.IN_STOCK)
                
        except Exception as e:
            self._logger.error(f"Failed to update equipment status for movement {entity.id}: {e}")


# Legacy inventory service for backward compatibility
class InventoryService:
    """Legacy inventory service - use individual services instead."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id
        self.equipment_service = EquipmentService(db, tenant_id)
        self.warehouse_service = WarehouseService(db, tenant_id)
        self.vendor_service = VendorService(db, tenant_id)
        self.movement_service = StockMovementService(db, tenant_id)

    # Equipment Management
    async def create_equipment(
        self, equipment_data: schemas.EquipmentCreate
    ) -> Equipment:
        """Create new equipment."""
        try:
            # Validate equipment type exists
            equipment_type = self.equipment_type_repo.get_by_id(
                equipment_data.equipment_type_id
            )
            if not equipment_type:
                raise ValidationError(
                    f"Equipment type not found: {equipment_data.equipment_type_id}"
                )

            # Validate warehouse exists
            if equipment_data.current_warehouse_id:
                warehouse = self.warehouse_repo.get_by_id(
                    equipment_data.current_warehouse_id
                )
                if not warehouse:
                    raise ValidationError(
                        f"Warehouse not found: {equipment_data.current_warehouse_id}"
                    )

            # Validate vendor exists
            if equipment_data.vendor_id:
                vendor = self.vendor_repo.get_by_id(equipment_data.vendor_id)
                if not vendor:
                    raise ValidationError(
                        f"Vendor not found: {equipment_data.vendor_id}"
                    )

            # Create equipment
            equipment_dict = equipment_data.model_dump()
            equipment = self.equipment_repo.create(equipment_dict)

            # Create initial stock movement if in warehouse
            if equipment.current_warehouse_id:
                await self._create_stock_movement(
                    equipment_id=equipment.id,
                    movement_type=MovementType.RECEIPT,
                    to_warehouse_id=equipment.current_warehouse_id,
                    notes="Initial equipment receipt",
                )

            return equipment

        except Exception as e:
            raise ServiceError(f"Failed to create equipment: {str(e)}")

    async def get_equipment(self, equipment_id: UUID) -> Equipment:
        """Get equipment by ID."""
        equipment = self.equipment_repo.get_by_id(equipment_id)
        if not equipment:
            raise NotFoundError(f"Equipment not found: {equipment_id}")
        return equipment

    async def get_equipment_by_number(self, equipment_number: str) -> Equipment:
        """Get equipment by equipment number."""
        equipment = self.equipment_repo.get_by_equipment_number(equipment_number)
        if not equipment:
            raise NotFoundError(f"Equipment not found: {equipment_number}")
        return equipment

    async def get_equipment_by_serial(self, serial_number: str) -> Equipment:
        """Get equipment by serial number."""
        equipment = self.equipment_repo.get_by_serial_number(serial_number)
        if not equipment:
            raise NotFoundError(f"Equipment not found: {serial_number}")
        return equipment

    async def list_equipment(
        self,
        equipment_type_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
        status: Optional[EquipmentStatus] = None,
        vendor_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Equipment]:
        """List equipment with filtering."""
        return self.equipment_repo.list_equipment(
            equipment_type_id=equipment_type_id,
            warehouse_id=warehouse_id,
            status=status,
            vendor_id=vendor_id,
            skip=skip,
            limit=limit,
        )

    async def update_equipment_status(
        self, equipment_id: UUID, status: EquipmentStatus, notes: Optional[str] = None
    ) -> Equipment:
        """Update equipment status."""
        equipment = self.equipment_repo.update_status(equipment_id, status, notes)
        if not equipment:
            raise NotFoundError(f"Equipment not found: {equipment_id}")

        # Create stock movement for status changes
        movement_type = self._get_movement_type_for_status(status)
        if movement_type:
            await self._create_stock_movement(
                equipment_id=equipment_id,
                movement_type=movement_type,
                from_warehouse_id=equipment.current_warehouse_id,
                notes=f"Status changed to {status.value}: {notes or ''}",
            )

        return equipment

    async def assign_equipment_to_customer(
        self,
        equipment_id: UUID,
        customer_id: UUID,
        service_instance_id: Optional[UUID] = None,
    ) -> Equipment:
        """Assign equipment to customer."""
        equipment = await self.get_equipment(equipment_id)

        if equipment.status not in [
            EquipmentStatus.AVAILABLE,
            EquipmentStatus.IN_STOCK,
        ]:
            raise ValidationError(
                f"Equipment is not available for assignment. Current status: {equipment.status}"
            )

        # Assign equipment
        updated_equipment = self.equipment_repo.assign_to_customer(
            equipment_id, customer_id, service_instance_id
        )

        if not updated_equipment:
            raise ServiceError("Failed to assign equipment to customer")

        # Create deployment movement
        await self._create_stock_movement(
            equipment_id=equipment_id,
            movement_type=MovementType.DEPLOYMENT,
            from_warehouse_id=equipment.current_warehouse_id,
            notes=f"Deployed to customer {customer_id}",
        )

        return updated_equipment

    async def move_equipment(
        self, equipment_id: UUID, to_warehouse_id: UUID, notes: Optional[str] = None
    ) -> Equipment:
        """Move equipment between warehouses."""
        equipment = await self.get_equipment(equipment_id)

        # Validate target warehouse
        target_warehouse = self.warehouse_repo.get_by_id(to_warehouse_id)
        if not target_warehouse:
            raise ValidationError(f"Target warehouse not found: {to_warehouse_id}")

        if equipment.current_warehouse_id == to_warehouse_id:
            raise ValidationError("Equipment is already in the target warehouse")

        from_warehouse_id = equipment.current_warehouse_id

        # Move equipment
        updated_equipment = self.equipment_repo.move_to_warehouse(
            equipment_id, to_warehouse_id
        )
        if not updated_equipment:
            raise ServiceError("Failed to move equipment")

        # Create transfer movement
        await self._create_stock_movement(
            equipment_id=equipment_id,
            movement_type=MovementType.TRANSFER,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            notes=notes or f"Transferred to {target_warehouse.name}",
        )

        return updated_equipment

    # Equipment Type Management
    async def create_equipment_type(
        self, equipment_type_data: schemas.EquipmentTypeCreate
    ) -> EquipmentType:
        """Create new equipment type."""
        try:
            equipment_type_dict = equipment_type_data.model_dump()
            return self.equipment_type_repo.create(equipment_type_dict)
        except Exception as e:
            raise ServiceError(f"Failed to create equipment type: {str(e)}")

    async def get_equipment_type(self, equipment_type_id: UUID) -> EquipmentType:
        """Get equipment type by ID."""
        equipment_type = self.equipment_type_repo.get_by_id(equipment_type_id)
        if not equipment_type:
            raise NotFoundError(f"Equipment type not found: {equipment_type_id}")
        return equipment_type

    async def list_equipment_types(
        self, is_active: Optional[bool] = None
    ) -> List[EquipmentType]:
        """List equipment types."""
        return self.equipment_type_repo.list_equipment_types(is_active=is_active)

    # Warehouse Management
    async def create_warehouse(
        self, warehouse_data: schemas.WarehouseCreate
    ) -> Warehouse:
        """Create new warehouse."""
        try:
            warehouse_dict = warehouse_data.model_dump()
            return self.warehouse_repo.create(warehouse_dict)
        except Exception as e:
            raise ServiceError(f"Failed to create warehouse: {str(e)}")

    async def get_warehouse(self, warehouse_id: UUID) -> Warehouse:
        """Get warehouse by ID."""
        warehouse = self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse:
            raise NotFoundError(f"Warehouse not found: {warehouse_id}")
        return warehouse

    async def list_warehouses(
        self, is_active: Optional[bool] = None
    ) -> List[Warehouse]:
        """List warehouses."""
        return self.warehouse_repo.list_warehouses(is_active=is_active)

    # Vendor Management
    async def create_vendor(self, vendor_data: schemas.VendorCreate) -> Vendor:
        """Create new vendor."""
        try:
            vendor_dict = vendor_data.model_dump()
            return self.vendor_repo.create(vendor_dict)
        except Exception as e:
            raise ServiceError(f"Failed to create vendor: {str(e)}")

    async def get_vendor(self, vendor_id: UUID) -> Vendor:
        """Get vendor by ID."""
        vendor = self.vendor_repo.get_by_id(vendor_id)
        if not vendor:
            raise NotFoundError(f"Vendor not found: {vendor_id}")
        return vendor

    async def list_vendors(self, is_active: Optional[bool] = None) -> List[Vendor]:
        """List vendors."""
        return self.vendor_repo.list_vendors(is_active=is_active)

    # Stock Movement Management
    async def get_stock_movement(self, movement_id: UUID) -> StockMovement:
        """Get stock movement by ID."""
        movement = self.movement_repo.get_by_id(movement_id)
        if not movement:
            raise NotFoundError(f"Stock movement not found: {movement_id}")
        return movement

    async def list_stock_movements(
        self,
        equipment_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
        movement_type: Optional[MovementType] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[StockMovement]:
        """List stock movements with filtering."""
        return self.movement_repo.list_movements(
            equipment_id=equipment_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            skip=skip,
            limit=limit,
        )

    async def get_equipment_history(self, equipment_id: UUID) -> List[StockMovement]:
        """Get movement history for equipment."""
        return self.movement_repo.get_equipment_history(equipment_id)

    # Inventory Reports
    async def get_warehouse_inventory(self, warehouse_id: UUID) -> Dict[str, Any]:
        """Get inventory summary for a warehouse."""
        warehouse = await self.get_warehouse(warehouse_id)
        equipment_list = await self.list_equipment(warehouse_id=warehouse_id)

        # Group by equipment type and status
        summary = {}
        total_count = 0

        for equipment in equipment_list:
            type_name = (
                equipment.equipment_type.name if equipment.equipment_type else "Unknown"
            )
            status = equipment.status.value

            if type_name not in summary:
                summary[type_name] = {}

            if status not in summary[type_name]:
                summary[type_name][status] = 0

            summary[type_name][status] += 1
            total_count += 1

        return {
            "warehouse_id": warehouse_id,
            "warehouse_name": warehouse.name,
            "total_equipment": total_count,
            "summary_by_type": summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_equipment_availability(self) -> Dict[str, Any]:
        """Get equipment availability across all warehouses."""
        all_equipment = await self.list_equipment()

        availability = {
            "available": 0,
            "deployed": 0,
            "maintenance": 0,
            "decommissioned": 0,
            "total": len(all_equipment),
        }

        for equipment in all_equipment:
            if equipment.status in [
                EquipmentStatus.AVAILABLE,
                EquipmentStatus.IN_STOCK,
            ]:
                availability["available"] += 1
            elif equipment.status == EquipmentStatus.DEPLOYED:
                availability["deployed"] += 1
            elif equipment.status in [
                EquipmentStatus.MAINTENANCE,
                EquipmentStatus.REPAIR,
            ]:
                availability["maintenance"] += 1
            elif equipment.status == EquipmentStatus.DECOMMISSIONED:
                availability["decommissioned"] += 1

        return {
            "availability": availability,
            "utilization_rate": (
                (availability["deployed"] / availability["total"] * 100)
                if availability["total"] > 0
                else 0
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Private helper methods
    async def _create_stock_movement(
        self,
        equipment_id: UUID,
        movement_type: MovementType,
        from_warehouse_id: Optional[UUID] = None,
        to_warehouse_id: Optional[UUID] = None,
        notes: Optional[str] = None,
    ) -> StockMovement:
        """Create a stock movement record."""
        movement_data = {
            "equipment_id": equipment_id,
            "movement_type": movement_type,
            "movement_date": datetime.now(timezone.utc),
            "from_warehouse_id": from_warehouse_id,
            "to_warehouse_id": to_warehouse_id,
            "notes": notes,
        }

        return self.movement_repo.create(movement_data)

    def _get_movement_type_for_status(
        self, status: EquipmentStatus
    ) -> Optional[MovementType]:
        """Get movement type for status change."""
        status_movement_map = {
            EquipmentStatus.DEPLOYED: MovementType.DEPLOYMENT,
            EquipmentStatus.MAINTENANCE: MovementType.MAINTENANCE,
            EquipmentStatus.REPAIR: MovementType.MAINTENANCE,
            EquipmentStatus.RETURNED: MovementType.RETURN,
            EquipmentStatus.DECOMMISSIONED: MovementType.DISPOSAL,
        }

        return status_movement_map.get(status)


class EquipmentTrackingService:
    """Service for equipment tracking and lifecycle management."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize equipment tracking service."""
        self.db = db
        self.inventory_service = InventoryService(db, tenant_id)

    async def track_equipment_lifecycle(self, equipment_id: UUID) -> Dict[str, Any]:
        """Track complete equipment lifecycle."""
        equipment = await self.inventory_service.get_equipment(equipment_id)
        history = await self.inventory_service.get_equipment_history(equipment_id)

        lifecycle_events = []

        # Add creation event
        lifecycle_events.append(
            {
                "event": "created",
                "date": equipment.created_at,
                "details": f"Equipment created with serial number {equipment.serial_number}",
            }
        )

        # Add movement history
        for movement in history:
            event_details = {
                "event": movement.movement_type.value,
                "date": movement.movement_date,
                "details": movement.notes
                or f"{movement.movement_type.value} operation",
            }

            if movement.from_warehouse_id and movement.to_warehouse_id:
                event_details[
                    "details"
                ] += f" (from warehouse {movement.from_warehouse_id} to {movement.to_warehouse_id})"

            lifecycle_events.append(event_details)

        # Sort by date
        lifecycle_events.sort(key=lambda x: x["date"])

        return {
            "equipment_id": equipment_id,
            "equipment_number": equipment.equipment_number,
            "serial_number": equipment.serial_number,
            "current_status": equipment.status.value,
            "lifecycle_events": lifecycle_events,
            "total_events": len(lifecycle_events),
        }

    async def get_deployment_metrics(self) -> Dict[str, Any]:
        """Get equipment deployment metrics."""
        all_equipment = await self.inventory_service.list_equipment()

        metrics = {
            "total_equipment": len(all_equipment),
            "deployed_equipment": 0,
            "available_equipment": 0,
            "maintenance_equipment": 0,
            "average_deployment_age_days": 0,
            "equipment_by_type": {},
            "equipment_by_vendor": {},
        }

        deployment_ages = []

        for equipment in all_equipment:
            # Count by status
            if equipment.status == EquipmentStatus.DEPLOYED:
                metrics["deployed_equipment"] += 1
                if equipment.deployment_date:
                    age_days = (datetime.now(timezone.utc) - equipment.deployment_date).days
                    deployment_ages.append(age_days)
            elif equipment.status in [
                EquipmentStatus.AVAILABLE,
                EquipmentStatus.IN_STOCK,
            ]:
                metrics["available_equipment"] += 1
            elif equipment.status in [
                EquipmentStatus.MAINTENANCE,
                EquipmentStatus.REPAIR,
            ]:
                metrics["maintenance_equipment"] += 1

            # Count by type
            type_name = (
                equipment.equipment_type.name if equipment.equipment_type else "Unknown"
            )
            if type_name not in metrics["equipment_by_type"]:
                metrics["equipment_by_type"][type_name] = 0
            metrics["equipment_by_type"][type_name] += 1

            # Count by vendor
            vendor_name = equipment.vendor.name if equipment.vendor else "Unknown"
            if vendor_name not in metrics["equipment_by_vendor"]:
                metrics["equipment_by_vendor"][vendor_name] = 0
            metrics["equipment_by_vendor"][vendor_name] += 1

        # Calculate average deployment age
        if deployment_ages:
            metrics["average_deployment_age_days"] = sum(deployment_ages) / len(
                deployment_ages
            )

        return metrics
