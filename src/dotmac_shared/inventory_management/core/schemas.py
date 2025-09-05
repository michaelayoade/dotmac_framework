"""
Pydantic schemas for inventory management API validation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    ItemCondition,
    ItemStatus,
    ItemType,
    MovementType,
    PurchaseOrderStatus,
    WarehouseType,
)


# Base schemas
class InventoryBase(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v) if v else None,
        },
    )


# Item schemas
class ItemBase(InventoryBase):
    """Base item schema."""

    item_code: str = Field(..., max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    name: str = Field(..., max_length=300)
    description: Optional[str] = None
    item_type: ItemType
    category: str = Field(..., max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)


class ItemCreate(ItemBase):
    """Schema for creating items."""

    # Product details
    manufacturer: Optional[str] = Field(None, max_length=200)
    model: Optional[str] = Field(None, max_length=100)
    part_number: Optional[str] = Field(None, max_length=100)
    manufacturer_part_number: Optional[str] = Field(None, max_length=100)

    # Physical attributes
    weight_kg: Optional[float] = Field(None, ge=0)
    dimensions: Optional[dict[str, float]] = None
    color: Optional[str] = Field(None, max_length=50)

    # Specifications
    technical_specs: Optional[dict[str, Any]] = None
    compatibility: Optional[list[str]] = None
    operating_conditions: Optional[dict[str, Any]] = None

    # Stock management
    unit_of_measure: str = Field("each", max_length=20)
    reorder_point: int = Field(0, ge=0)
    reorder_quantity: int = Field(0, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)

    # Costs and pricing
    standard_cost: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    list_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)

    # Lifecycle dates
    introduction_date: Optional[date] = None
    discontinue_date: Optional[date] = None
    end_of_life_date: Optional[date] = None

    # Quality and compliance
    quality_grade: Optional[str] = Field(None, max_length=20)
    certifications: Optional[list[str]] = None
    regulatory_info: Optional[dict[str, Any]] = None

    # Vendor information
    primary_vendor_id: Optional[str] = Field(None, max_length=255)
    vendor_item_code: Optional[str] = Field(None, max_length=100)
    lead_time_days: Optional[int] = Field(None, ge=0)

    # Service and warranty
    warranty_period_days: Optional[int] = Field(None, ge=0)
    service_level: Optional[str] = Field(None, max_length=50)
    maintenance_required: bool = False

    # Documentation
    documentation_links: Optional[list[str]] = None
    image_urls: Optional[list[str]] = None
    safety_data_sheet_url: Optional[str] = Field(None, max_length=500)

    # Tracking preferences
    track_serial_numbers: bool = False
    track_lot_numbers: bool = False
    track_expiry_dates: bool = False

    # Additional metadata
    tags: Optional[list[str]] = None
    platform_data: Optional[dict[str, Any]] = None


class ItemUpdate(InventoryBase):
    """Schema for updating items."""

    item_code: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None
    item_type: Optional[ItemType] = None
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)

    # All other fields as optional
    manufacturer: Optional[str] = Field(None, max_length=200)
    model: Optional[str] = Field(None, max_length=100)
    part_number: Optional[str] = Field(None, max_length=100)
    manufacturer_part_number: Optional[str] = Field(None, max_length=100)

    weight_kg: Optional[float] = Field(None, ge=0)
    dimensions: Optional[dict[str, float]] = None
    color: Optional[str] = Field(None, max_length=50)

    technical_specs: Optional[dict[str, Any]] = None
    compatibility: Optional[list[str]] = None
    operating_conditions: Optional[dict[str, Any]] = None

    unit_of_measure: Optional[str] = Field(None, max_length=20)
    reorder_point: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)
    max_stock_level: Optional[int] = Field(None, ge=0)

    standard_cost: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    list_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)

    introduction_date: Optional[date] = None
    discontinue_date: Optional[date] = None
    end_of_life_date: Optional[date] = None

    quality_grade: Optional[str] = Field(None, max_length=20)
    certifications: Optional[list[str]] = None
    regulatory_info: Optional[dict[str, Any]] = None

    primary_vendor_id: Optional[str] = Field(None, max_length=255)
    vendor_item_code: Optional[str] = Field(None, max_length=100)
    lead_time_days: Optional[int] = Field(None, ge=0)

    warranty_period_days: Optional[int] = Field(None, ge=0)
    service_level: Optional[str] = Field(None, max_length=50)
    maintenance_required: Optional[bool] = None

    documentation_links: Optional[list[str]] = None
    image_urls: Optional[list[str]] = None
    safety_data_sheet_url: Optional[str] = Field(None, max_length=500)

    track_serial_numbers: Optional[bool] = None
    track_lot_numbers: Optional[bool] = None
    track_expiry_dates: Optional[bool] = None

    is_active: Optional[bool] = None
    is_discontinued: Optional[bool] = None

    tags: Optional[list[str]] = None
    platform_data: Optional[dict[str, Any]] = None


class ItemResponse(ItemBase):
    """Schema for item responses."""

    id: UUID
    tenant_id: str

    # All fields from ItemCreate
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer_part_number: Optional[str] = None

    weight_kg: Optional[float] = None
    dimensions: Optional[dict[str, float]] = None
    color: Optional[str] = None

    technical_specs: Optional[dict[str, Any]] = None
    compatibility: Optional[list[str]] = None
    operating_conditions: Optional[dict[str, Any]] = None

    unit_of_measure: str = "each"
    reorder_point: int = 0
    reorder_quantity: int = 0
    max_stock_level: Optional[int] = None

    standard_cost: Optional[Decimal] = None
    last_purchase_cost: Optional[Decimal] = None
    average_cost: Optional[Decimal] = None
    list_price: Optional[Decimal] = None

    introduction_date: Optional[date] = None
    discontinue_date: Optional[date] = None
    end_of_life_date: Optional[date] = None

    quality_grade: Optional[str] = None
    certifications: Optional[list[str]] = None
    regulatory_info: Optional[dict[str, Any]] = None

    primary_vendor_id: Optional[str] = None
    vendor_item_code: Optional[str] = None
    lead_time_days: Optional[int] = None

    warranty_period_days: Optional[int] = None
    service_level: Optional[str] = None
    maintenance_required: bool = False

    documentation_links: Optional[list[str]] = None
    image_urls: Optional[list[str]] = None
    safety_data_sheet_url: Optional[str] = None

    track_serial_numbers: bool = False
    track_lot_numbers: bool = False
    track_expiry_dates: bool = False

    is_active: bool = True
    is_discontinued: bool = False

    tags: Optional[list[str]] = None
    platform_data: Optional[dict[str, Any]] = None

    # Audit fields
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    # Computed fields
    total_stock_quantity: Optional[int] = None
    available_stock_quantity: Optional[int] = None


# Warehouse schemas
class WarehouseBase(InventoryBase):
    """Base warehouse schema."""

    warehouse_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    warehouse_type: WarehouseType


class WarehouseCreate(WarehouseBase):
    """Schema for creating warehouses."""

    # Location information
    address_line1: Optional[str] = Field(None, max_length=300)
    address_line2: Optional[str] = Field(None, max_length=300)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)

    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    # Capacity and layout
    total_area_sqm: Optional[float] = Field(None, ge=0)
    storage_capacity: Optional[int] = Field(None, ge=0)
    zone_count: int = Field(1, ge=1)
    bin_locations: Optional[list[str]] = None

    # Operations
    operating_hours: Optional[dict[str, str]] = None
    manager_name: Optional[str] = Field(None, max_length=200)
    staff_count: int = Field(1, ge=1)

    # Environmental conditions
    temperature_controlled: bool = False
    humidity_controlled: bool = False
    security_level: str = Field("standard", max_length=20)

    # Systems integration
    wms_integrated: bool = False
    barcode_scanning: bool = True
    rfid_enabled: bool = False

    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None


class WarehouseUpdate(InventoryBase):
    """Schema for updating warehouses."""

    warehouse_code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    warehouse_type: Optional[WarehouseType] = None

    address_line1: Optional[str] = Field(None, max_length=300)
    address_line2: Optional[str] = Field(None, max_length=300)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)

    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    total_area_sqm: Optional[float] = Field(None, ge=0)
    storage_capacity: Optional[int] = Field(None, ge=0)
    zone_count: Optional[int] = Field(None, ge=1)
    bin_locations: Optional[list[str]] = None

    operating_hours: Optional[dict[str, str]] = None
    manager_name: Optional[str] = Field(None, max_length=200)
    staff_count: Optional[int] = Field(None, ge=1)

    temperature_controlled: Optional[bool] = None
    humidity_controlled: Optional[bool] = None
    security_level: Optional[str] = Field(None, max_length=20)

    wms_integrated: Optional[bool] = None
    barcode_scanning: Optional[bool] = None
    rfid_enabled: Optional[bool] = None

    is_active: Optional[bool] = None
    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None


class WarehouseResponse(WarehouseBase):
    """Schema for warehouse responses."""

    id: UUID
    tenant_id: str

    # Location information
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Capacity and layout
    total_area_sqm: Optional[float] = None
    storage_capacity: Optional[int] = None
    zone_count: int = 1
    bin_locations: Optional[list[str]] = None

    # Operations
    operating_hours: Optional[dict[str, str]] = None
    manager_name: Optional[str] = None
    staff_count: int = 1

    # Environmental conditions
    temperature_controlled: bool = False
    humidity_controlled: bool = False
    security_level: str = "standard"

    # Systems integration
    wms_integrated: bool = False
    barcode_scanning: bool = True
    rfid_enabled: bool = False

    is_active: bool = True
    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None

    # Audit fields
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


# Stock Item schemas
class StockItemResponse(InventoryBase):
    """Schema for stock item responses."""

    id: UUID
    tenant_id: str
    item_id: UUID
    warehouse_id: UUID

    quantity: int = 0
    reserved_quantity: int = 0
    available_quantity: int = 0

    bin_location: Optional[str] = None
    zone: Optional[str] = None
    aisle: Optional[str] = None
    shelf: Optional[str] = None

    condition: ItemCondition = ItemCondition.NEW
    item_status: ItemStatus = ItemStatus.AVAILABLE

    serial_numbers: Optional[list[str]] = None
    lot_numbers: Optional[list[str]] = None
    expiry_dates: Optional[list[date]] = None

    unit_cost: Optional[Decimal] = None
    total_value: Optional[Decimal] = None
    valuation_method: str = "FIFO"

    min_quantity: int = 0
    max_quantity: Optional[int] = None

    last_movement_date: Optional[datetime] = None
    last_counted_date: Optional[date] = None

    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    # Related data
    item: Optional["ItemResponse"] = None
    warehouse: Optional["WarehouseResponse"] = None


# Stock Movement schemas
class StockMovementCreate(InventoryBase):
    """Schema for creating stock movements."""

    item_id: UUID
    warehouse_id: UUID
    movement_type: MovementType
    quantity: int = Field(..., ne=0)

    # Optional fields
    reference_number: Optional[str] = Field(None, max_length=100)
    movement_date: Optional[datetime] = None

    unit_cost: Optional[Decimal] = Field(None, ge=0, decimal_places=2)

    from_warehouse_id: Optional[UUID] = None
    from_location: Optional[str] = Field(None, max_length=100)
    to_location: Optional[str] = Field(None, max_length=100)

    reason_code: Optional[str] = Field(None, max_length=50)
    reason_description: Optional[str] = None

    purchase_order_id: Optional[str] = Field(None, max_length=255)
    work_order_id: Optional[str] = Field(None, max_length=255)
    project_id: Optional[str] = Field(None, max_length=255)
    invoice_number: Optional[str] = Field(None, max_length=100)

    serial_numbers: Optional[list[str]] = None
    lot_numbers: Optional[list[str]] = None
    expiry_date: Optional[date] = None

    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None


class StockMovementResponse(InventoryBase):
    """Schema for stock movement responses."""

    id: UUID
    tenant_id: str
    movement_id: str
    reference_number: Optional[str] = None

    item_id: UUID
    warehouse_id: UUID
    movement_type: MovementType
    movement_date: datetime

    quantity: int
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None

    from_warehouse_id: Optional[UUID] = None
    from_location: Optional[str] = None
    to_location: Optional[str] = None

    reason_code: Optional[str] = None
    reason_description: Optional[str] = None

    purchase_order_id: Optional[str] = None
    work_order_id: Optional[str] = None
    project_id: Optional[str] = None
    invoice_number: Optional[str] = None

    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    processed_by: str

    serial_numbers: Optional[list[str]] = None
    lot_numbers: Optional[list[str]] = None
    expiry_date: Optional[date] = None

    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None

    created_at: datetime

    # Related data
    item: Optional["ItemResponse"] = None
    warehouse: Optional["WarehouseResponse"] = None
    from_warehouse: Optional["WarehouseResponse"] = None


# Purchase Order schemas
class PurchaseOrderCreate(InventoryBase):
    """Schema for creating purchase orders."""

    title: str = Field(..., max_length=300)
    description: Optional[str] = None

    vendor_id: str = Field(..., max_length=255)
    vendor_name: str = Field(..., max_length=200)
    vendor_contact: Optional[str] = Field(None, max_length=200)

    order_date: Optional[date] = None
    required_date: Optional[date] = None
    promised_date: Optional[date] = None

    ship_to_warehouse_id: UUID
    shipping_method: Optional[str] = Field(None, max_length=100)

    payment_terms: Optional[str] = Field(None, max_length=100)
    currency: str = Field("USD", max_length=3)

    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None


class PurchaseOrderUpdate(InventoryBase):
    """Schema for updating purchase orders."""

    title: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None

    vendor_contact: Optional[str] = Field(None, max_length=200)

    required_date: Optional[date] = None
    promised_date: Optional[date] = None

    po_status: Optional[PurchaseOrderStatus] = None

    shipping_method: Optional[str] = Field(None, max_length=100)
    tracking_number: Optional[str] = Field(None, max_length=100)

    shipped_date: Optional[date] = None
    received_date: Optional[date] = None

    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None


class PurchaseOrderResponse(InventoryBase):
    """Schema for purchase order responses."""

    id: UUID
    tenant_id: str
    po_number: str
    title: str
    description: Optional[str] = None

    vendor_id: str
    vendor_name: str
    vendor_contact: Optional[str] = None

    order_date: date
    required_date: Optional[date] = None
    promised_date: Optional[date] = None

    po_status: PurchaseOrderStatus
    approved_by: Optional[str] = None
    approval_date: Optional[date] = None

    subtotal: Decimal = 0
    tax_amount: Decimal = 0
    shipping_cost: Decimal = 0
    total_amount: Decimal = 0

    ship_to_warehouse_id: UUID
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None

    payment_terms: Optional[str] = None
    currency: str = "USD"

    shipped_date: Optional[date] = None
    received_date: Optional[date] = None

    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None

    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    # Related data
    warehouse: Optional["WarehouseResponse"] = None
    line_items: Optional[list["PurchaseOrderLineResponse"]] = None


class PurchaseOrderLineCreate(InventoryBase):
    """Schema for creating purchase order lines."""

    item_id: UUID
    line_number: int = Field(..., ge=1)
    item_description: Optional[str] = Field(None, max_length=500)

    quantity_ordered: int = Field(..., ge=1)
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)
    discount_percent: Decimal = Field(0, ge=0, le=100, decimal_places=2)

    required_date: Optional[date] = None
    promised_date: Optional[date] = None

    vendor_item_code: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None


class PurchaseOrderLineResponse(InventoryBase):
    """Schema for purchase order line responses."""

    id: UUID
    tenant_id: str
    purchase_order_id: UUID
    item_id: UUID

    line_number: int
    item_description: Optional[str] = None

    quantity_ordered: int
    quantity_received: int = 0
    quantity_remaining: int

    unit_price: Decimal
    discount_percent: Decimal = 0
    line_total: Decimal

    required_date: Optional[date] = None
    promised_date: Optional[date] = None

    line_status: str = "pending"

    vendor_item_code: Optional[str] = None
    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    # Related data
    item: Optional["ItemResponse"] = None


# Stock Count schemas
class StockCountCreate(InventoryBase):
    """Schema for creating stock counts."""

    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    count_type: str = Field(..., max_length=50)  # full, cycle, spot

    warehouse_id: UUID
    locations: Optional[list[str]] = None
    items_filter: Optional[dict[str, Any]] = None

    count_date: Optional[date] = None
    count_supervisor: str = Field(..., max_length=200)
    counters: Optional[list[str]] = None

    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None


class StockCountResponse(InventoryBase):
    """Schema for stock count responses."""

    id: UUID
    tenant_id: str
    count_id: str
    name: str
    description: Optional[str] = None

    count_date: date
    count_type: str

    warehouse_id: UUID
    locations: Optional[list[str]] = None
    items_filter: Optional[dict[str, Any]] = None

    count_status: str = "planned"
    progress_percentage: int = 0

    count_supervisor: str
    counters: Optional[list[str]] = None

    items_counted: int = 0
    discrepancies_found: int = 0
    total_variance_value: Decimal = 0

    approved_by: Optional[str] = None
    approval_date: Optional[date] = None
    finalized_date: Optional[date] = None

    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    # Related data
    warehouse: Optional["WarehouseResponse"] = None
    count_lines: Optional[list["StockCountLineResponse"]] = None

    # Computed fields
    accuracy_percentage: Optional[float] = None


class StockCountLineResponse(InventoryBase):
    """Schema for stock count line responses."""

    id: UUID
    tenant_id: str
    stock_count_id: UUID
    item_id: UUID

    location: Optional[str] = None

    system_quantity: int
    counted_quantity: Optional[int] = None
    variance_quantity: int = 0

    unit_cost: Optional[Decimal] = None
    variance_value: Decimal = 0

    counter_name: Optional[str] = None
    count_timestamp: Optional[datetime] = None
    recount_required: bool = False

    variance_reason: Optional[str] = None
    adjustment_made: bool = False

    notes: Optional[str] = None
    platform_data: Optional[dict[str, Any]] = None

    created_at: datetime

    # Related data
    item: Optional["ItemResponse"] = None
