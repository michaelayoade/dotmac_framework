"""Inventory models for equipment, assets, and stock management."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    Integer,
    Float,
    Numeric,
    JSON,
    ForeignKey,
    Index,
    Enum as SQLEnum,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin
from dotmac_isp.shared.models import AddressMixin


class ItemType(str, Enum):
    """Inventory item types."""

    HARDWARE = "hardware"
    SOFTWARE = "software"
    CONSUMABLE = "consumable"
    TOOL = "tool"
    SPARE_PART = "spare_part"
    KIT = "kit"
    ACCESSORY = "accessory"


class ItemCondition(str, Enum):
    """Item condition status."""

    NEW = "new"
    REFURBISHED = "refurbished"
    USED = "used"
    DAMAGED = "damaged"
    DEFECTIVE = "defective"
    OBSOLETE = "obsolete"


class ItemStatus(str, Enum):
    """Item availability status."""

    AVAILABLE = "available"
    RESERVED = "reserved"
    ALLOCATED = "allocated"
    IN_USE = "in_use"
    IN_REPAIR = "in_repair"
    RETIRED = "retired"
    LOST = "lost"


class MovementType(str, Enum):
    """Stock movement types."""

    RECEIPT = "receipt"
    ISSUE = "issue"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    RETURN = "return"
    WRITE_OFF = "write_off"
    FOUND = "found"


class WarehouseType(str, Enum):
    """Warehouse types."""

    MAIN = "main"
    REGIONAL = "regional"
    FIELD = "field"
    VENDOR = "vendor"
    CUSTOMER = "customer"
    REPAIR = "repair"
    QUARANTINE = "quarantine"


class PurchaseOrderStatus(str, Enum):
    """Purchase order status."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT_TO_VENDOR = "sent_to_vendor"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class Item(TenantModel, StatusMixin, AuditMixin):
    """Inventory items and products."""

    __tablename__ = "inventory_items"

    # Item identification
    item_code = Column(String(100), nullable=False, index=True)
    barcode = Column(String(100), nullable=True, index=True)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    item_type = Column(SQLEnum(ItemType), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)

    # Product details
    manufacturer = Column(String(200), nullable=True)
    model = Column(String(100), nullable=True)
    part_number = Column(String(100), nullable=True)
    manufacturer_part_number = Column(String(100), nullable=True)

    # Physical attributes
    weight_kg = Column(Float, nullable=True)
    dimensions = Column(JSON, nullable=True)  # length, width, height
    color = Column(String(50), nullable=True)

    # Specifications
    technical_specs = Column(JSON, nullable=True)
    compatibility = Column(JSON, nullable=True)
    operating_conditions = Column(JSON, nullable=True)

    # Stock management
    unit_of_measure = Column(String(20), nullable=False, default="each")
    reorder_point = Column(Integer, default=0, nullable=False)
    reorder_quantity = Column(Integer, default=0, nullable=False)
    max_stock_level = Column(Integer, nullable=True)

    # Costs and pricing
    standard_cost = Column(Numeric(10, 2), nullable=True)
    last_purchase_cost = Column(Numeric(10, 2), nullable=True)
    average_cost = Column(Numeric(10, 2), nullable=True)
    list_price = Column(Numeric(10, 2), nullable=True)

    # Lifecycle
    introduction_date = Column(Date, nullable=True)
    discontinue_date = Column(Date, nullable=True)
    end_of_life_date = Column(Date, nullable=True)

    # Quality and compliance
    quality_grade = Column(String(20), nullable=True)
    certifications = Column(JSON, nullable=True)
    regulatory_info = Column(JSON, nullable=True)

    # Vendor information
    primary_vendor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    vendor_item_code = Column(String(100), nullable=True)
    lead_time_days = Column(Integer, nullable=True)

    # Service and warranty
    warranty_period_days = Column(Integer, nullable=True)
    service_level = Column(String(50), nullable=True)
    maintenance_required = Column(Boolean, default=False, nullable=False)

    # Documentation
    documentation_links = Column(JSON, nullable=True)
    image_urls = Column(JSON, nullable=True)
    safety_data_sheet_url = Column(String(500), nullable=True)

    # Tracking preferences
    track_serial_numbers = Column(Boolean, default=False, nullable=False)
    track_lot_numbers = Column(Boolean, default=False, nullable=False)
    track_expiry_dates = Column(Boolean, default=False, nullable=False)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    stock_items = relationship(
        "StockItem", back_populates="item", cascade="all, delete-orphan"
    )
    movements = relationship("StockMovement", back_populates="item")

    __table_args__ = (
        Index("ix_items_tenant_code", "tenant_id", "item_code", unique=True),
        Index("ix_items_manufacturer_model", "manufacturer", "model"),
        Index("ix_items_category_type", "category", "item_type"),
    )

    @hybrid_property
    def is_discontinued(self) -> bool:
        """Check if item is discontinued."""
        return self.discontinue_date and date.today() >= self.discontinue_date

    @hybrid_property
    def total_stock_quantity(self) -> int:
        """Get total stock quantity across all locations."""
        return sum(stock.quantity for stock in self.stock_items if stock.quantity > 0)

    def __repr__(self):
        return f"<Item(code='{self.item_code}', name='{self.name}', type='{self.item_type}')>"


class Warehouse(TenantModel, StatusMixin, AuditMixin, AddressMixin):
    """Warehouses and storage locations."""

    __tablename__ = "inventory_warehouses"

    # Warehouse identification
    warehouse_code = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    warehouse_type = Column(SQLEnum(WarehouseType), nullable=False, index=True)

    # Capacity and layout
    total_area_sqm = Column(Float, nullable=True)
    storage_capacity = Column(Integer, nullable=True)
    zone_count = Column(Integer, default=1, nullable=False)
    bin_locations = Column(JSON, nullable=True)

    # Operations
    operating_hours = Column(JSON, nullable=True)
    manager_name = Column(String(200), nullable=True)
    staff_count = Column(Integer, default=1, nullable=False)

    # Environmental conditions
    temperature_controlled = Column(Boolean, default=False, nullable=False)
    humidity_controlled = Column(Boolean, default=False, nullable=False)
    security_level = Column(String(20), default="standard", nullable=False)

    # Systems integration
    wms_integrated = Column(
        Boolean, default=False, nullable=False
    )  # Warehouse Management System
    barcode_scanning = Column(Boolean, default=True, nullable=False)
    rfid_enabled = Column(Boolean, default=False, nullable=False)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    stock_items = relationship(
        "StockItem", back_populates="warehouse", cascade="all, delete-orphan"
    )
    movements = relationship(
        "StockMovement",
        foreign_keys="[StockMovement.warehouse_id]",
        back_populates="warehouse",
    )

    __table_args__ = (
        Index("ix_warehouses_tenant_code", "tenant_id", "warehouse_code", unique=True),
        Index("ix_warehouses_type", "warehouse_type"),
    )

    def __repr__(self):
        return f"<Warehouse(code='{self.warehouse_code}', name='{self.name}', type='{self.warehouse_type}')>"


class StockItem(TenantModel, AuditMixin):
    """Stock quantities per item per warehouse."""

    __tablename__ = "inventory_stock_items"

    # References
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_warehouses.id"),
        nullable=False,
        index=True,
    )

    # Stock quantities
    quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    available_quantity = Column(Integer, default=0, nullable=False)

    # Location within warehouse
    bin_location = Column(String(50), nullable=True)
    zone = Column(String(50), nullable=True)
    aisle = Column(String(20), nullable=True)
    shelf = Column(String(20), nullable=True)

    # Item condition and status
    condition = Column(
        SQLEnum(ItemCondition), default=ItemCondition.NEW, nullable=False
    )
    item_status = Column(
        SQLEnum(ItemStatus), default=ItemStatus.AVAILABLE, nullable=False, index=True
    )

    # Tracking information
    serial_numbers = Column(JSON, nullable=True)  # For serialized items
    lot_numbers = Column(JSON, nullable=True)  # For lot-tracked items
    expiry_dates = Column(JSON, nullable=True)  # For items with expiry

    # Stock valuation
    unit_cost = Column(Numeric(10, 2), nullable=True)
    total_value = Column(Numeric(12, 2), nullable=True)
    valuation_method = Column(
        String(20), default="FIFO", nullable=False
    )  # FIFO, LIFO, Average

    # Minimum stock levels
    min_quantity = Column(Integer, default=0, nullable=False)
    max_quantity = Column(Integer, nullable=True)

    # Last activity
    last_movement_date = Column(DateTime, nullable=True)
    last_counted_date = Column(Date, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    item = relationship("Item", back_populates="stock_items")
    warehouse = relationship("Warehouse", back_populates="stock_items")

    __table_args__ = (
        Index("ix_stock_items_item_warehouse", "item_id", "warehouse_id", unique=True),
        Index("ix_stock_items_status_quantity", "item_status", "quantity"),
        CheckConstraint("quantity >= 0", name="ck_stock_quantity_non_negative"),
        CheckConstraint(
            "reserved_quantity >= 0", name="ck_reserved_quantity_non_negative"
        ),
    )

    @hybrid_property
    def is_below_minimum(self) -> bool:
        """Check if stock is below minimum level."""
        return self.available_quantity < self.min_quantity

    @hybrid_property
    def turnover_days(self) -> Optional[int]:
        """Calculate days since last movement."""
        if self.last_movement_date:
            return (datetime.utcnow() - self.last_movement_date).days
        return None

    def __repr__(self):
        return f"<StockItem(item_id='{self.item_id}', warehouse_id='{self.warehouse_id}', quantity={self.quantity})>"


class StockMovement(TenantModel, AuditMixin):
    """Stock movement transactions."""

    __tablename__ = "inventory_stock_movements"

    # Movement identification
    movement_id = Column(String(100), nullable=False, unique=True, index=True)
    reference_number = Column(String(100), nullable=True, index=True)

    # Item and location
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_warehouses.id"),
        nullable=False,
        index=True,
    )

    # Movement details
    movement_type = Column(SQLEnum(MovementType), nullable=False, index=True)
    movement_date = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    # Quantities
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=True)
    total_cost = Column(Numeric(12, 2), nullable=True)

    # Source and destination (for transfers)
    from_warehouse_id = Column(
        UUID(as_uuid=True), ForeignKey("inventory_warehouses.id"), nullable=True
    )
    from_location = Column(String(100), nullable=True)
    to_location = Column(String(100), nullable=True)

    # Transaction details
    reason_code = Column(String(50), nullable=True)
    reason_description = Column(Text, nullable=True)

    # Document references
    purchase_order_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    work_order_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    invoice_number = Column(String(100), nullable=True)

    # Approval and processing
    approved_by = Column(String(200), nullable=True)
    approved_date = Column(DateTime, nullable=True)
    processed_by = Column(String(200), nullable=False)

    # Tracking information
    serial_numbers = Column(JSON, nullable=True)
    lot_numbers = Column(JSON, nullable=True)
    expiry_date = Column(Date, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    item = relationship("Item", back_populates="movements")
    warehouse = relationship(
        "Warehouse", foreign_keys=[warehouse_id], back_populates="movements"
    )
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])

    __table_args__ = (
        Index("ix_movements_item_date", "item_id", "movement_date"),
        Index("ix_movements_warehouse_type", "warehouse_id", "movement_type"),
        Index("ix_movements_reference", "reference_number"),
    )

    @hybrid_property
    def is_inbound(self) -> bool:
        """Check if movement increases stock."""
        return self.movement_type in [
            MovementType.RECEIPT,
            MovementType.RETURN,
            MovementType.ADJUSTMENT,
            MovementType.FOUND,
        ]

    def __repr__(self):
        return f"<StockMovement(id='{self.movement_id}', type='{self.movement_type}', quantity={self.quantity})>"


class PurchaseOrder(TenantModel, StatusMixin, AuditMixin):
    """Purchase orders for inventory replenishment."""

    __tablename__ = "inventory_purchase_orders"

    # Order identification
    po_number = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Vendor information
    vendor_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    vendor_name = Column(String(200), nullable=False)
    vendor_contact = Column(String(200), nullable=True)

    # Order details
    order_date = Column(Date, nullable=False, default=date.today)
    required_date = Column(Date, nullable=True)
    promised_date = Column(Date, nullable=True)

    # Status and approval
    po_status = Column(
        SQLEnum(PurchaseOrderStatus),
        default=PurchaseOrderStatus.DRAFT,
        nullable=False,
        index=True,
    )
    approved_by = Column(String(200), nullable=True)
    approval_date = Column(Date, nullable=True)

    # Financial details
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    shipping_cost = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)

    # Shipping information
    ship_to_warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_warehouses.id"),
        nullable=False,
        index=True,
    )
    shipping_method = Column(String(100), nullable=True)
    tracking_number = Column(String(100), nullable=True)

    # Payment terms
    payment_terms = Column(String(100), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)

    # Delivery tracking
    shipped_date = Column(Date, nullable=True)
    received_date = Column(Date, nullable=True)

    # Additional information
    terms_and_conditions = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    line_items = relationship(
        "PurchaseOrderLine",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )
    warehouse = relationship("Warehouse")

    __table_args__ = (
        Index("ix_purchase_orders_vendor_date", "vendor_id", "order_date"),
        Index("ix_purchase_orders_status", "po_status"),
    )

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if purchase order is overdue."""
        if self.po_status in [
            PurchaseOrderStatus.RECEIVED,
            PurchaseOrderStatus.CANCELLED,
            PurchaseOrderStatus.CLOSED,
        ]:
            return False
        return self.required_date and date.today() > self.required_date

    def __repr__(self):
        return f"<PurchaseOrder(number='{self.po_number}', vendor='{self.vendor_name}', status='{self.po_status}')>"


class PurchaseOrderLine(TenantModel, AuditMixin):
    """Individual line items in purchase orders."""

    __tablename__ = "inventory_purchase_order_lines"

    # References
    purchase_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_purchase_orders.id"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True
    )

    # Line details
    line_number = Column(Integer, nullable=False)
    item_description = Column(String(500), nullable=True)

    # Quantities and pricing
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0, nullable=False)
    quantity_remaining = Column(Integer, nullable=False)

    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_percent = Column(Numeric(5, 2), default=0, nullable=False)
    line_total = Column(Numeric(12, 2), nullable=False)

    # Delivery
    required_date = Column(Date, nullable=True)
    promised_date = Column(Date, nullable=True)

    # Status
    line_status = Column(String(50), default="pending", nullable=False)

    # Additional information
    vendor_item_code = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="line_items")
    item = relationship("Item")

    __table_args__ = (
        Index(
            "ix_po_lines_order_line", "purchase_order_id", "line_number", unique=True
        ),
        Index("ix_po_lines_item", "item_id"),
    )

    @hybrid_property
    def is_fully_received(self) -> bool:
        """Check if line item is fully received."""
        return self.quantity_received >= self.quantity_ordered

    def __repr__(self):
        return f"<PurchaseOrderLine(po_id='{self.purchase_order_id}', line={self.line_number}, qty={self.quantity_ordered})>"


class StockCount(TenantModel, AuditMixin):
    """Physical stock counts and cycle counts."""

    __tablename__ = "inventory_stock_counts"

    # Count identification
    count_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Count details
    count_date = Column(Date, nullable=False, default=date.today)
    count_type = Column(String(50), nullable=False)  # full, cycle, spot

    # Scope
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_warehouses.id"),
        nullable=False,
        index=True,
    )
    locations = Column(JSON, nullable=True)  # Specific locations to count
    items_filter = Column(JSON, nullable=True)  # Item criteria

    # Status and progress
    count_status = Column(String(50), default="planned", nullable=False, index=True)
    progress_percentage = Column(Integer, default=0, nullable=False)

    # Personnel
    count_supervisor = Column(String(200), nullable=False)
    counters = Column(JSON, nullable=True)

    # Results summary
    items_counted = Column(Integer, default=0, nullable=False)
    discrepancies_found = Column(Integer, default=0, nullable=False)
    total_variance_value = Column(Numeric(12, 2), default=0, nullable=False)

    # Approval and finalization
    approved_by = Column(String(200), nullable=True)
    approval_date = Column(Date, nullable=True)
    finalized_date = Column(Date, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    count_lines = relationship(
        "StockCountLine", back_populates="stock_count", cascade="all, delete-orphan"
    )
    warehouse = relationship("Warehouse")

    __table_args__ = (
        Index("ix_stock_counts_warehouse_date", "warehouse_id", "count_date"),
        Index("ix_stock_counts_status", "count_status"),
    )

    @hybrid_property
    def accuracy_percentage(self) -> float:
        """Calculate count accuracy percentage."""
        if self.items_counted == 0:
            return 0.0
        accurate_items = self.items_counted - self.discrepancies_found
        return round((accurate_items / self.items_counted) * 100, 2)

    def __repr__(self):
        return f"<StockCount(id='{self.count_id}', warehouse_id='{self.warehouse_id}', status='{self.count_status}')>"


class StockCountLine(TenantModel, AuditMixin):
    """Individual item counts within a stock count."""

    __tablename__ = "inventory_stock_count_lines"

    # References
    stock_count_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_stock_counts.id"),
        nullable=False,
        index=True,
    )
    item_id = Column(
        UUID(as_uuid=True), ForeignKey("inventory_items.id"), nullable=False, index=True
    )

    # Location
    location = Column(String(100), nullable=True)

    # Count quantities
    system_quantity = Column(Integer, nullable=False)
    counted_quantity = Column(Integer, nullable=True)
    variance_quantity = Column(Integer, default=0, nullable=False)

    # Valuation
    unit_cost = Column(Numeric(10, 2), nullable=True)
    variance_value = Column(Numeric(12, 2), default=0, nullable=False)

    # Count details
    counter_name = Column(String(200), nullable=True)
    count_timestamp = Column(DateTime, nullable=True)
    recount_required = Column(Boolean, default=False, nullable=False)

    # Resolution
    variance_reason = Column(String(200), nullable=True)
    adjustment_made = Column(Boolean, default=False, nullable=False)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    stock_count = relationship("StockCount", back_populates="count_lines")
    item = relationship("Item")

    __table_args__ = (
        Index("ix_count_lines_count_item", "stock_count_id", "item_id", unique=True),
        Index("ix_count_lines_variance", "variance_quantity"),
    )

    @hybrid_property
    def has_variance(self) -> bool:
        """Check if count has variance."""
        return self.variance_quantity != 0

    def __repr__(self):
        return f"<StockCountLine(count_id='{self.stock_count_id}', item_id='{self.item_id}', variance={self.variance_quantity})>"
