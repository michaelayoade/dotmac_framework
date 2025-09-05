"""
Core inventory management operations and business logic.

Handles CRUD operations, stock movements, purchase orders, and warehouse management
with full audit trail and business rule validation.
"""

import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from .models import (
    Item,
    ItemType,
    MovementType,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    StockItem,
    StockMovement,
    Warehouse,
    WarehouseType,
)
from .schemas import (
    ItemCreate,
    ItemUpdate,
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
    StockMovementCreate,
    WarehouseCreate,
)

logger = logging.getLogger(__name__)


class InventoryManager:
    """Core inventory management system."""

    def __init__(self):
        self.logger = logger

    # Item Management
    async def create_item(
        self,
        db: AsyncSession,
        tenant_id: str,
        item_data: ItemCreate,
        created_by: Optional[str] = None,
    ) -> Item:
        """Create a new inventory item."""

        # Generate item code if not provided
        if not item_data.item_code:
            item_data.item_code = await self._generate_item_code(
                db, tenant_id, item_data.item_type
            )

        # Check for duplicate item codes
        existing = await db.scalar(
            select(Item).where(
                and_(Item.tenant_id == tenant_id, Item.item_code == item_data.item_code)
            )
        )
        if existing:
            raise ValueError(f"Item with code '{item_data.item_code}' already exists")

        # Create item
        item = Item(
            tenant_id=tenant_id,
            created_by=created_by,
            **item_data.model_dump(exclude_unset=True),
        )

        db.add(item)
        await db.commit()
        await db.refresh(item)

        logger.info(f"Created item: {item.item_code} ({item.name})")
        return item

    async def get_item(
        self,
        db: AsyncSession,
        tenant_id: str,
        item_id: str,
        include_stock: bool = False,
    ) -> Optional[Item]:
        """Get item by ID."""

        query = select(Item).where(
            and_(Item.tenant_id == tenant_id, Item.id == item_id)
        )

        if include_stock:
            query = query.options(selectinload(Item.stock_items))

        return await db.scalar(query)

    async def get_item_by_code(
        self,
        db: AsyncSession,
        tenant_id: str,
        item_code: str,
        include_stock: bool = False,
    ) -> Optional[Item]:
        """Get item by item code."""

        query = select(Item).where(
            and_(Item.tenant_id == tenant_id, Item.item_code == item_code)
        )

        if include_stock:
            query = query.options(selectinload(Item.stock_items))

        return await db.scalar(query)

    async def list_items(
        self,
        db: AsyncSession,
        tenant_id: str,
        filters: Optional[dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Item], int]:
        """List items with filtering and pagination."""

        query = select(Item).where(Item.tenant_id == tenant_id)

        # Apply filters
        if filters:
            if "item_type" in filters:
                if isinstance(filters["item_type"], list):
                    query = query.where(Item.item_type.in_(filters["item_type"]))
                else:
                    query = query.where(Item.item_type == filters["item_type"])

            if "category" in filters:
                query = query.where(Item.category == filters["category"])

            if "manufacturer" in filters:
                query = query.where(
                    Item.manufacturer.ilike(f"%{filters['manufacturer']}%")
                )

            if "is_active" in filters:
                query = query.where(Item.is_active == filters["is_active"])

            if "is_discontinued" in filters:
                query = query.where(Item.is_discontinued == filters["is_discontinued"])

            if "search" in filters and filters["search"]:
                search_term = f"%{filters['search']}%"
                query = query.where(
                    or_(
                        Item.name.ilike(search_term),
                        Item.item_code.ilike(search_term),
                        Item.description.ilike(search_term),
                        Item.manufacturer.ilike(search_term),
                        Item.model.ilike(search_term),
                    )
                )

            if "low_stock" in filters and filters["low_stock"]:
                # Items below reorder point
                query = query.join(Item.stock_items).where(
                    StockItem.available_quantity < Item.reorder_point
                )

        # Get total count
        count_query = select(func.count(Item.id)).where(Item.tenant_id == tenant_id)
        if filters:
            # Apply same filters to count query
            count_query = count_query.where(query.whereclause)

        total = await db.scalar(count_query) or 0

        # Apply pagination and ordering
        query = (
            query.order_by(Item.name).offset((page - 1) * page_size).limit(page_size)
        )

        result = await db.execute(query)
        items = result.scalars().all()

        return items, total

    async def update_item(
        self,
        db: AsyncSession,
        tenant_id: str,
        item_id: str,
        item_data: ItemUpdate,
        updated_by: Optional[str] = None,
    ) -> Optional[Item]:
        """Update an existing item."""

        item = await self.get_item(db, tenant_id, item_id)
        if not item:
            return None

        # Update fields
        for field, value in item_data.model_dump(exclude_unset=True).items():
            if hasattr(item, field):
                setattr(item, field, value)

        item.updated_by = updated_by
        item.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(item)

        logger.info(f"Updated item: {item.item_code}")
        return item

    # Warehouse Management
    async def create_warehouse(
        self,
        db: AsyncSession,
        tenant_id: str,
        warehouse_data: WarehouseCreate,
        created_by: Optional[str] = None,
    ) -> Warehouse:
        """Create a new warehouse."""

        # Check for duplicate warehouse codes
        existing = await db.scalar(
            select(Warehouse).where(
                and_(
                    Warehouse.tenant_id == tenant_id,
                    Warehouse.warehouse_code == warehouse_data.warehouse_code,
                )
            )
        )
        if existing:
            raise ValueError(
                f"Warehouse with code '{warehouse_data.warehouse_code}' already exists"
            )

        warehouse = Warehouse(
            tenant_id=tenant_id,
            created_by=created_by,
            **warehouse_data.model_dump(exclude_unset=True),
        )

        db.add(warehouse)
        await db.commit()
        await db.refresh(warehouse)

        logger.info(f"Created warehouse: {warehouse.warehouse_code} ({warehouse.name})")
        return warehouse

    async def get_warehouse(
        self, db: AsyncSession, tenant_id: str, warehouse_id: str
    ) -> Optional[Warehouse]:
        """Get warehouse by ID."""

        return await db.scalar(
            select(Warehouse).where(
                and_(Warehouse.tenant_id == tenant_id, Warehouse.id == warehouse_id)
            )
        )

    async def list_warehouses(
        self,
        db: AsyncSession,
        tenant_id: str,
        warehouse_type: WarehouseType = None,
        is_active: Optional[bool] = None,
    ) -> list[Warehouse]:
        """List warehouses with optional filtering."""

        query = select(Warehouse).where(Warehouse.tenant_id == tenant_id)

        if warehouse_type:
            query = query.where(Warehouse.warehouse_type == warehouse_type)

        if is_active is not None:
            query = query.where(Warehouse.is_active == is_active)

        query = query.order_by(Warehouse.name)

        result = await db.execute(query)
        return result.scalars().all()

    # Stock Management
    async def get_stock_item(
        self, db: AsyncSession, tenant_id: str, item_id: str, warehouse_id: str
    ) -> Optional[StockItem]:
        """Get stock item for specific item and warehouse."""

        return await db.scalar(
            select(StockItem).where(
                and_(
                    StockItem.tenant_id == tenant_id,
                    StockItem.item_id == item_id,
                    StockItem.warehouse_id == warehouse_id,
                )
            )
        )

    async def get_item_stock_summary(
        self, db: AsyncSession, tenant_id: str, item_id: str
    ) -> dict[str, Any]:
        """Get stock summary for an item across all warehouses."""

        stock_items = await db.execute(
            select(StockItem, Warehouse)
            .join(Warehouse, StockItem.warehouse_id == Warehouse.id)
            .where(
                and_(
                    StockItem.tenant_id == tenant_id,
                    StockItem.item_id == item_id,
                    StockItem.quantity > 0,
                )
            )
            .order_by(Warehouse.name)
        )

        stock_locations = []
        total_quantity = 0
        total_available = 0
        total_reserved = 0
        total_value = Decimal("0.00")

        for stock_item, warehouse in stock_items:
            stock_locations.append(
                {
                    "warehouse_id": str(warehouse.id),
                    "warehouse_name": warehouse.name,
                    "warehouse_type": warehouse.warehouse_type,
                    "quantity": stock_item.quantity,
                    "available_quantity": stock_item.available_quantity,
                    "reserved_quantity": stock_item.reserved_quantity,
                    "condition": stock_item.condition,
                    "bin_location": stock_item.bin_location,
                    "last_movement_date": stock_item.last_movement_date,
                }
            )

            total_quantity += stock_item.quantity
            total_available += stock_item.available_quantity
            total_reserved += stock_item.reserved_quantity
            if stock_item.total_value:
                total_value += stock_item.total_value

        return {
            "total_quantity": total_quantity,
            "total_available": total_available,
            "total_reserved": total_reserved,
            "total_value": total_value,
            "stock_locations": stock_locations,
        }

    async def create_stock_movement(
        self,
        db: AsyncSession,
        tenant_id: str,
        movement_data: StockMovementCreate,
        processed_by: str,
    ) -> StockMovement:
        """Create a stock movement and update stock levels."""

        # Generate movement ID
        movement_id = (
            f"MOV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        )

        # Create movement record
        movement = StockMovement(
            tenant_id=tenant_id,
            movement_id=movement_id,
            processed_by=processed_by,
            **movement_data.model_dump(exclude_unset=True),
        )

        if not movement.movement_date:
            movement.movement_date = datetime.now(timezone.utc)

        # Calculate total cost
        if movement.unit_cost and movement.quantity:
            movement.total_cost = movement.unit_cost * abs(movement.quantity)

        db.add(movement)

        # Update stock levels
        await self._update_stock_levels(db, movement)

        await db.commit()
        await db.refresh(movement)

        logger.info(f"Created stock movement: {movement_id} - {movement.movement_type}")
        return movement

    async def get_stock_movements(
        self,
        db: AsyncSession,
        tenant_id: str,
        item_id: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        movement_type: MovementType = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[StockMovement], int]:
        """Get stock movements with filtering."""

        query = select(StockMovement).where(StockMovement.tenant_id == tenant_id)

        # Apply filters
        if item_id:
            query = query.where(StockMovement.item_id == item_id)

        if warehouse_id:
            query = query.where(StockMovement.warehouse_id == warehouse_id)

        if movement_type:
            query = query.where(StockMovement.movement_type == movement_type)

        if start_date:
            query = query.where(StockMovement.movement_date >= start_date)

        if end_date:
            query = query.where(StockMovement.movement_date < end_date)

        # Get total count
        total = (
            await db.scalar(
                select(func.count(StockMovement.id)).where(query.whereclause)
            )
            or 0
        )

        # Apply pagination and ordering
        query = (
            query.options(
                joinedload(StockMovement.item), joinedload(StockMovement.warehouse)
            )
            .order_by(desc(StockMovement.movement_date))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await db.execute(query)
        movements = result.scalars().unique().all()

        return movements, total

    # Purchase Order Management
    async def create_purchase_order(
        self,
        db: AsyncSession,
        tenant_id: str,
        po_data: PurchaseOrderCreate,
        line_items: list[PurchaseOrderLineCreate],
        created_by: Optional[str] = None,
    ) -> PurchaseOrder:
        """Create a purchase order with line items."""

        # Generate PO number
        po_number = await self._generate_po_number(db, tenant_id)

        # Create purchase order
        po = PurchaseOrder(
            tenant_id=tenant_id,
            po_number=po_number,
            created_by=created_by,
            **po_data.model_dump(exclude_unset=True),
        )

        if not po.order_date:
            po.order_date = date.today()

        db.add(po)
        await db.flush()  # Get the PO ID

        # Add line items
        subtotal = Decimal("0.00")
        for line_data in line_items:
            line = PurchaseOrderLine(
                tenant_id=tenant_id,
                purchase_order_id=po.id,
                quantity_remaining=line_data.quantity_ordered,
                line_total=line_data.unit_price
                * line_data.quantity_ordered
                * (1 - line_data.discount_percent / 100),
                **line_data.model_dump(exclude_unset=True),
            )
            db.add(line)
            subtotal += line.line_total

        # Update totals
        po.subtotal = subtotal
        po.total_amount = po.subtotal + po.tax_amount + po.shipping_cost

        await db.commit()
        await db.refresh(po)

        logger.info(f"Created purchase order: {po_number}")
        return po

    async def get_purchase_order(
        self, db: AsyncSession, tenant_id: str, po_id: str, include_lines: bool = False
    ) -> Optional[PurchaseOrder]:
        """Get purchase order by ID."""

        query = select(PurchaseOrder).where(
            and_(PurchaseOrder.tenant_id == tenant_id, PurchaseOrder.id == po_id)
        )

        if include_lines:
            query = query.options(selectinload(PurchaseOrder.line_items))

        return await db.scalar(query)

    # Analytics and Reporting
    async def get_inventory_analytics(
        self, db: AsyncSession, tenant_id: str, filters: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Get inventory analytics and KPIs."""

        # Base queries
        select(Item).where(Item.tenant_id == tenant_id)
        select(StockItem).where(StockItem.tenant_id == tenant_id)

        # Apply date filter if provided
        if filters and "date_range" in filters:
            start_date, end_date = filters["date_range"]
            # Additional filtering can be added here

        # Total items
        total_items = (
            await db.scalar(
                select(func.count(Item.id)).where(Item.tenant_id == tenant_id)
            )
            or 0
        )
        active_items = (
            await db.scalar(
                select(func.count(Item.id)).where(
                    and_(Item.tenant_id == tenant_id, Item.is_active is True)
                )
            )
            or 0
        )

        # Stock value
        stock_value = await db.scalar(
            select(func.coalesce(func.sum(StockItem.total_value), 0)).where(
                StockItem.tenant_id == tenant_id
            )
        ) or Decimal("0.00")

        # Low stock items (below reorder point)
        low_stock_items = (
            await db.scalar(
                select(func.count(StockItem.id))
                .join(Item, StockItem.item_id == Item.id)
                .where(
                    and_(
                        StockItem.tenant_id == tenant_id,
                        StockItem.available_quantity < Item.reorder_point,
                        Item.reorder_point > 0,
                    )
                )
            )
            or 0
        )

        # Out of stock items
        out_of_stock_items = (
            await db.scalar(
                select(func.count(StockItem.id)).where(
                    and_(
                        StockItem.tenant_id == tenant_id,
                        StockItem.available_quantity == 0,
                    )
                )
            )
            or 0
        )

        # Items by type
        items_by_type = {}
        type_result = await db.execute(
            select(Item.item_type, func.count(Item.id))
            .where(Item.tenant_id == tenant_id)
            .group_by(Item.item_type)
        )
        for item_type, count in type_result:
            items_by_type[item_type.value] = count

        # Pending purchase orders
        pending_pos = (
            await db.scalar(
                select(func.count(PurchaseOrder.id)).where(
                    and_(
                        PurchaseOrder.tenant_id == tenant_id,
                        PurchaseOrder.po_status.in_(
                            [
                                PurchaseOrderStatus.DRAFT,
                                PurchaseOrderStatus.PENDING_APPROVAL,
                                PurchaseOrderStatus.APPROVED,
                                PurchaseOrderStatus.SENT_TO_VENDOR,
                            ]
                        ),
                    )
                )
            )
            or 0
        )

        return {
            "total_items": total_items,
            "active_items": active_items,
            "total_stock_value": float(stock_value),
            "low_stock_items": low_stock_items,
            "out_of_stock_items": out_of_stock_items,
            "items_by_type": items_by_type,
            "pending_purchase_orders": pending_pos,
        }

    # Helper methods
    async def _generate_item_code(
        self, db: AsyncSession, tenant_id: str, item_type: ItemType
    ) -> str:
        """Generate unique item code."""

        # Get type prefix
        type_prefixes = {
            ItemType.HARDWARE: "HW",
            ItemType.SOFTWARE: "SW",
            ItemType.CONSUMABLE: "CN",
            ItemType.TOOL: "TL",
            ItemType.SPARE_PART: "SP",
            ItemType.KIT: "KT",
            ItemType.ACCESSORY: "AC",
            ItemType.NETWORK_EQUIPMENT: "NE",
            ItemType.CUSTOMER_PREMISES_EQUIPMENT: "CPE",
        }

        prefix = type_prefixes.get(item_type, "IT")

        # Find next sequence number
        existing = await db.execute(
            select(Item.item_code)
            .where(
                and_(Item.tenant_id == tenant_id, Item.item_code.like(f"{prefix}-%"))
            )
            .order_by(desc(Item.item_code))
        )

        max_code = existing.scalar()
        if max_code:
            try:
                sequence = int(max_code.split("-")[1]) + 1
            except (IndexError, ValueError):
                sequence = 1
        else:
            sequence = 1

        return f"{prefix}-{sequence:06d}"

    async def _generate_po_number(self, db: AsyncSession, tenant_id: str) -> str:
        """Generate unique purchase order number."""

        current_date = datetime.now().strftime("%Y%m")
        prefix = f"PO-{current_date}"

        # Find next sequence number
        existing = await db.execute(
            select(PurchaseOrder.po_number)
            .where(
                and_(
                    PurchaseOrder.tenant_id == tenant_id,
                    PurchaseOrder.po_number.like(f"{prefix}-%"),
                )
            )
            .order_by(desc(PurchaseOrder.po_number))
        )

        max_po = existing.scalar()
        if max_po:
            try:
                sequence = int(max_po.split("-")[2]) + 1
            except (IndexError, ValueError):
                sequence = 1
        else:
            sequence = 1

        return f"{prefix}-{sequence:04d}"

    async def _update_stock_levels(self, db: AsyncSession, movement: StockMovement):
        """Update stock levels based on movement."""

        # Get or create stock item record
        stock_item = await db.scalar(
            select(StockItem).where(
                and_(
                    StockItem.tenant_id == movement.tenant_id,
                    StockItem.item_id == movement.item_id,
                    StockItem.warehouse_id == movement.warehouse_id,
                )
            )
        )

        if not stock_item:
            stock_item = StockItem(
                tenant_id=movement.tenant_id,
                item_id=movement.item_id,
                warehouse_id=movement.warehouse_id,
                quantity=0,
                available_quantity=0,
                reserved_quantity=0,
            )
            db.add(stock_item)

        # Update quantities based on movement type
        quantity_change = movement.quantity

        if movement.movement_type in [MovementType.ISSUE, MovementType.WRITE_OFF]:
            quantity_change = -abs(quantity_change)
        elif movement.movement_type in [
            MovementType.RECEIPT,
            MovementType.RETURN,
            MovementType.FOUND,
        ]:
            quantity_change = abs(quantity_change)
        elif movement.movement_type == MovementType.ADJUSTMENT:
            # For adjustments, quantity can be positive or negative
            pass

        # Update stock levels
        stock_item.quantity += quantity_change
        stock_item.available_quantity = max(
            0, stock_item.quantity - stock_item.reserved_quantity
        )
        stock_item.last_movement_date = movement.movement_date

        # Update cost information
        if movement.unit_cost:
            # Simple average costing - can be enhanced with FIFO/LIFO
            if stock_item.quantity > 0:
                if stock_item.unit_cost:
                    # Weighted average
                    total_cost = stock_item.unit_cost * (
                        stock_item.quantity - quantity_change
                    ) + movement.unit_cost * abs(quantity_change)
                    stock_item.unit_cost = total_cost / stock_item.quantity
                else:
                    stock_item.unit_cost = movement.unit_cost

                stock_item.total_value = stock_item.unit_cost * stock_item.quantity
            else:
                stock_item.unit_cost = None
                stock_item.total_value = Decimal("0.00")

        logger.debug(
            f"Updated stock for item {movement.item_id} in warehouse {movement.warehouse_id}: "
            f"quantity={stock_item.quantity}, available={stock_item.available_quantity}"
        )
