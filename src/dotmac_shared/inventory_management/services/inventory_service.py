"""
High-level inventory management service with business logic.

Orchestrates inventory operations, workflows, and cross-platform integrations.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.inventory_manager import InventoryManager
from ..core.models import (
    Item,
    ItemStatus,
    ItemType,
    MovementType,
    PurchaseOrder,
    PurchaseOrderStatus,
    StockCount,
    StockItem,
    StockMovement,
    Warehouse,
    WarehouseType,
)
from ..core.schemas import (
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    StockCountCreate,
    StockCountResponse,
    StockItemResponse,
    StockMovementCreate,
    StockMovementResponse,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)

logger = logging.getLogger(__name__)


class InventoryService:
    """High-level inventory management service with business logic."""

    def __init__(self, inventory_manager: InventoryManager):
        """Initialize service."""
        self.inventory_manager = inventory_manager

    # Item Management with Business Logic
    async def create_equipment_item(
        self,
        db: AsyncSession,
        tenant_id: str,
        equipment_type: str,
        manufacturer: str,
        model: str,
        specifications: Dict[str, Any],
        created_by: str = None,
    ) -> ItemResponse:
        """Create equipment item with standard specifications."""

        item_data = ItemCreate(
            name=f"{manufacturer} {model}",
            item_type=(
                ItemType.NETWORK_EQUIPMENT
                if equipment_type in ["router", "switch", "ap"]
                else ItemType.CUSTOMER_PREMISES_EQUIPMENT
            ),
            category=equipment_type,
            manufacturer=manufacturer,
            model=model,
            technical_specs=specifications,
            track_serial_numbers=True,
            maintenance_required=True,
            platform_data={"equipment_type": equipment_type},
        )

        item = await self.inventory_manager.create_item(
            db, tenant_id, item_data, created_by
        )
        return ItemResponse.model_validate(item)

    async def create_consumable_item(
        self,
        db: AsyncSession,
        tenant_id: str,
        item_name: str,
        category: str,
        reorder_point: int = 10,
        reorder_quantity: int = 50,
        created_by: str = None,
    ) -> ItemResponse:
        """Create consumable item with inventory controls."""

        item_data = ItemCreate(
            name=item_name,
            item_type=ItemType.CONSUMABLE,
            category=category,
            reorder_point=reorder_point,
            reorder_quantity=reorder_quantity,
            track_expiry_dates=category in ["cable", "batteries", "adhesives"],
        )

        item = await self.inventory_manager.create_item(
            db, tenant_id, item_data, created_by
        )
        return ItemResponse.model_validate(item)

    async def get_item_with_stock_summary(
        self, db: AsyncSession, tenant_id: str, item_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get item with complete stock summary."""

        item = await self.inventory_manager.get_item(
            db, tenant_id, item_id, include_stock=True
        )
        if not item:
            return None

        stock_summary = await self.inventory_manager.get_item_stock_summary(
            db, tenant_id, item_id
        )

        return {
            "item": ItemResponse.model_validate(item),
            "stock_summary": stock_summary,
        }

    async def get_low_stock_items(
        self, db: AsyncSession, tenant_id: str
    ) -> List[Dict[str, Any]]:
        """Get items that are below reorder point."""

        items, _ = await self.inventory_manager.list_items(
            db, tenant_id, {"low_stock": True}
        )

        low_stock_items = []
        for item in items:
            stock_summary = await self.inventory_manager.get_item_stock_summary(
                db, tenant_id, str(item.id)
            )

            if stock_summary["total_available"] < item.reorder_point:
                low_stock_items.append(
                    {
                        "item": ItemResponse.model_validate(item),
                        "current_stock": stock_summary["total_available"],
                        "reorder_point": item.reorder_point,
                        "reorder_quantity": item.reorder_quantity,
                        "shortage": item.reorder_point
                        - stock_summary["total_available"],
                    }
                )

        return low_stock_items

    # Warehouse Operations
    async def setup_standard_warehouses(
        self, db: AsyncSession, tenant_id: str, created_by: str = None
    ) -> List[WarehouseResponse]:
        """Setup standard warehouse structure for ISP operations."""

        standard_warehouses = [
            {
                "warehouse_code": "MAIN-01",
                "name": "Main Warehouse",
                "warehouse_type": WarehouseType.MAIN,
                "description": "Primary inventory storage facility",
            },
            {
                "warehouse_code": "FIELD-01",
                "name": "Field Operations",
                "warehouse_type": WarehouseType.FIELD,
                "description": "Field technician inventory",
            },
            {
                "warehouse_code": "REPAIR-01",
                "name": "Repair Workshop",
                "warehouse_type": WarehouseType.REPAIR,
                "description": "Equipment repair and refurbishment",
            },
        ]

        created_warehouses = []
        for warehouse_data in standard_warehouses:
            warehouse = await self.inventory_manager.create_warehouse(
                db, tenant_id, WarehouseCreate(**warehouse_data), created_by
            )
            created_warehouses.append(WarehouseResponse.model_validate(warehouse))

        return created_warehouses

    # Stock Operations
    async def receive_equipment(
        self,
        db: AsyncSession,
        tenant_id: str,
        item_id: str,
        warehouse_id: str,
        quantity: int,
        serial_numbers: List[str] = None,
        purchase_order_id: str = None,
        received_by: str = None,
    ) -> StockMovementResponse:
        """Receive equipment into inventory with serial number tracking."""

        movement_data = StockMovementCreate(
            item_id=UUID(item_id),
            warehouse_id=UUID(warehouse_id),
            movement_type=MovementType.RECEIPT,
            quantity=quantity,
            reference_number=f"REC-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            purchase_order_id=purchase_order_id,
            serial_numbers=serial_numbers,
            reason_description="Equipment received into inventory",
        )

        movement = await self.inventory_manager.create_stock_movement(
            db, tenant_id, movement_data, received_by or "System"
        )

        return StockMovementResponse.model_validate(movement)

    async def issue_equipment_for_installation(
        self,
        db: AsyncSession,
        tenant_id: str,
        item_id: str,
        warehouse_id: str,
        quantity: int,
        project_id: str = None,
        technician: str = None,
        customer_location: str = None,
    ) -> StockMovementResponse:
        """Issue equipment for customer installation."""

        movement_data = StockMovementCreate(
            item_id=UUID(item_id),
            warehouse_id=UUID(warehouse_id),
            movement_type=MovementType.INSTALLATION,
            quantity=quantity,
            reference_number=f"INST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            project_id=project_id,
            to_location=customer_location,
            reason_description=f"Equipment issued for installation by {technician or 'technician'}",
        )

        movement = await self.inventory_manager.create_stock_movement(
            db, tenant_id, movement_data, technician or "System"
        )

        return StockMovementResponse.model_validate(movement)

    async def transfer_equipment(
        self,
        db: AsyncSession,
        tenant_id: str,
        item_id: str,
        from_warehouse_id: str,
        to_warehouse_id: str,
        quantity: int,
        reason: str,
        transferred_by: str,
    ) -> List[StockMovementResponse]:
        """Transfer equipment between warehouses."""

        # Create outbound movement
        outbound_data = StockMovementCreate(
            item_id=UUID(item_id),
            warehouse_id=UUID(from_warehouse_id),
            movement_type=MovementType.TRANSFER,
            quantity=-quantity,  # Negative for outbound
            reference_number=f"XFER-OUT-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            to_location=f"Transfer to warehouse {to_warehouse_id}",
            reason_description=reason,
        )

        # Create inbound movement
        inbound_data = StockMovementCreate(
            item_id=UUID(item_id),
            warehouse_id=UUID(to_warehouse_id),
            movement_type=MovementType.TRANSFER,
            quantity=quantity,  # Positive for inbound
            reference_number=f"XFER-IN-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            from_warehouse_id=UUID(from_warehouse_id),
            reason_description=reason,
        )

        outbound_movement = await self.inventory_manager.create_stock_movement(
            db, tenant_id, outbound_data, transferred_by
        )

        inbound_movement = await self.inventory_manager.create_stock_movement(
            db, tenant_id, inbound_data, transferred_by
        )

        return [
            StockMovementResponse.model_validate(outbound_movement),
            StockMovementResponse.model_validate(inbound_movement),
        ]

    # Purchase Order Management
    async def create_reorder_purchase_orders(
        self,
        db: AsyncSession,
        tenant_id: str,
        default_warehouse_id: str,
        created_by: str = None,
    ) -> List[PurchaseOrderResponse]:
        """Create purchase orders for items below reorder point."""

        low_stock_items = await self.get_low_stock_items(db, tenant_id)

        # Group by vendor
        vendors_items = {}
        for item_data in low_stock_items:
            item = item_data["item"]
            vendor_id = item.primary_vendor_id or "default_vendor"

            if vendor_id not in vendors_items:
                vendors_items[vendor_id] = []

            vendors_items[vendor_id].append(
                {"item": item, "quantity_needed": item_data["reorder_quantity"]}
            )

        created_pos = []
        for vendor_id, items in vendors_items.items():
            # Create PO for vendor
            po_data = PurchaseOrderCreate(
                title=f"Reorder - {datetime.now().strftime('%Y-%m-%d')}",
                description="Automatic reorder for low stock items",
                vendor_id=vendor_id,
                vendor_name=f"Vendor {vendor_id}",  # Would normally lookup from vendor master
                ship_to_warehouse_id=UUID(default_warehouse_id),
                required_date=date.today() + timedelta(days=14),
            )

            # Create line items
            line_items = []
            for i, item_data in enumerate(items, 1):
                item = item_data["item"]
                line_items.append(
                    PurchaseOrderLineCreate(
                        item_id=item.id,
                        line_number=i,
                        item_description=item.name,
                        quantity_ordered=item_data["quantity_needed"],
                        unit_price=item.standard_cost or Decimal("0.00"),
                        required_date=date.today() + timedelta(days=14),
                    )
                )

            po = await self.inventory_manager.create_purchase_order(
                db, tenant_id, po_data, line_items, created_by
            )

            created_pos.append(PurchaseOrderResponse.model_validate(po))

        return created_pos

    # Analytics and Reporting
    async def get_inventory_dashboard(
        self, db: AsyncSession, tenant_id: str, period_days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive inventory dashboard metrics."""

        # Get base analytics
        analytics = await self.inventory_manager.get_inventory_analytics(db, tenant_id)

        # Get movement trends
        start_date = date.today() - timedelta(days=period_days)
        movements, _ = await self.inventory_manager.get_stock_movements(
            db, tenant_id, start_date=start_date, page_size=1000
        )

        # Analyze movement patterns
        movement_trends = {
            "receipts": 0,
            "issues": 0,
            "installations": 0,
            "transfers": 0,
            "adjustments": 0,
        }

        for movement in movements:
            if movement.movement_type == MovementType.RECEIPT:
                movement_trends["receipts"] += movement.quantity
            elif movement.movement_type == MovementType.ISSUE:
                movement_trends["issues"] += abs(movement.quantity)
            elif movement.movement_type == MovementType.INSTALLATION:
                movement_trends["installations"] += abs(movement.quantity)
            elif movement.movement_type == MovementType.TRANSFER:
                movement_trends["transfers"] += abs(movement.quantity)
            elif movement.movement_type == MovementType.ADJUSTMENT:
                movement_trends["adjustments"] += abs(movement.quantity)

        # Get low stock alerts
        low_stock_items = await self.get_low_stock_items(db, tenant_id)

        analytics.update(
            {
                "period_days": period_days,
                "movement_trends": movement_trends,
                "low_stock_alerts": len(low_stock_items),
                "low_stock_items": low_stock_items[:10],  # Top 10 for dashboard
            }
        )

        return analytics

    async def get_equipment_utilization_report(
        self, db: AsyncSession, tenant_id: str
    ) -> Dict[str, Any]:
        """Get equipment utilization and deployment status."""

        # Get all equipment items
        equipment_items, _ = await self.inventory_manager.list_items(
            db,
            tenant_id,
            {
                "item_type": [
                    ItemType.NETWORK_EQUIPMENT,
                    ItemType.CUSTOMER_PREMISES_EQUIPMENT,
                ]
            },
            page_size=1000,
        )

        utilization_data = {
            "total_equipment": len(equipment_items),
            "in_use": 0,
            "available": 0,
            "in_repair": 0,
            "by_type": {},
            "equipment_details": [],
        }

        for item in equipment_items:
            stock_summary = await self.inventory_manager.get_item_stock_summary(
                db, tenant_id, str(item.id)
            )

            # Determine utilization status
            status = "available"
            if stock_summary["total_quantity"] == 0:
                status = "fully_deployed"
                utilization_data["in_use"] += 1
            elif stock_summary["total_available"] < stock_summary["total_quantity"]:
                status = "partially_deployed"
                utilization_data["in_use"] += 1
            else:
                utilization_data["available"] += 1

            # Count by type
            equipment_type = (
                item.platform_data.get("equipment_type", "unknown")
                if item.platform_data
                else "unknown"
            )
            if equipment_type not in utilization_data["by_type"]:
                utilization_data["by_type"][equipment_type] = {
                    "total": 0,
                    "in_use": 0,
                    "available": 0,
                }

            utilization_data["by_type"][equipment_type]["total"] += 1
            if status == "available":
                utilization_data["by_type"][equipment_type]["available"] += 1
            else:
                utilization_data["by_type"][equipment_type]["in_use"] += 1

            utilization_data["equipment_details"].append(
                {
                    "item_id": str(item.id),
                    "item_code": item.item_code,
                    "name": item.name,
                    "manufacturer": item.manufacturer,
                    "model": item.model,
                    "equipment_type": equipment_type,
                    "total_quantity": stock_summary["total_quantity"],
                    "available_quantity": stock_summary["total_available"],
                    "status": status,
                }
            )

        return utilization_data
