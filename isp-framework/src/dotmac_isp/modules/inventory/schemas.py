"""Inventory schemas for API request/response models."""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel

from .models import (
    ItemType,
    ItemCondition,
    ItemStatus,
    MovementType,
    WarehouseType,
    PurchaseOrderStatus,
)


# Item schemas
class ItemCreate(BaseModel):
    """Schema for creating a new item."""

    name: str
    sku: str
    item_type: ItemType
    category: Optional[str] = None
    description: Optional[str] = None
    unit_cost: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    minimum_stock_level: Optional[int] = None
    maximum_stock_level: Optional[int] = None


class ItemUpdate(BaseModel):
    """Schema for updating an item."""

    name: Optional[str] = None
    description: Optional[str] = None
    unit_cost: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    minimum_stock_level: Optional[int] = None
    maximum_stock_level: Optional[int] = None
    status: Optional[ItemStatus] = None


class ItemResponse(BaseModel):
    """Schema for item responses."""

    id: str
    tenant_id: str
    name: str
    sku: str
    item_type: ItemType
    category: Optional[str] = None
    description: Optional[str] = None
    unit_cost: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    minimum_stock_level: Optional[int] = None
    maximum_stock_level: Optional[int] = None
    status: ItemStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True


# Warehouse schemas
class WarehouseCreate(BaseModel):
    """Schema for creating a new warehouse."""

    name: str
    code: str
    warehouse_type: WarehouseType
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: str = "US"
    description: Optional[str] = None


class WarehouseUpdate(BaseModel):
    """Schema for updating a warehouse."""

    name: Optional[str] = None
    description: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None


class WarehouseResponse(BaseModel):
    """Schema for warehouse responses."""

    id: str
    tenant_id: str
    name: str
    code: str
    warehouse_type: WarehouseType
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True


# Stock Item schemas
class StockItemResponse(BaseModel):
    """Schema for stock item responses."""

    id: str
    tenant_id: str
    item_id: str
    warehouse_id: str
    quantity: int
    condition: ItemCondition
    location: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    last_counted: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True


# Stock Movement schemas
class StockMovementCreate(BaseModel):
    """Schema for creating a stock movement."""

    item_id: str
    warehouse_id: str
    movement_type: MovementType
    quantity: int
    unit_cost: Optional[Decimal] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class StockMovementResponse(BaseModel):
    """Schema for stock movement responses."""

    id: str
    tenant_id: str
    item_id: str
    warehouse_id: str
    movement_type: MovementType
    quantity: int
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    movement_date: datetime
    created_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True


# Purchase Order schemas
class PurchaseOrderCreate(BaseModel):
    """Schema for creating a purchase order."""

    supplier_id: str
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None


class PurchaseOrderUpdate(BaseModel):
    """Schema for updating a purchase order."""

    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    status: Optional[PurchaseOrderStatus] = None
    notes: Optional[str] = None


class PurchaseOrderResponse(BaseModel):
    """Schema for purchase order responses."""

    id: str
    tenant_id: str
    order_number: str
    supplier_id: str
    order_date: date
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    status: PurchaseOrderStatus
    total_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True


# Stock Count schemas
class StockCountCreate(BaseModel):
    """Schema for creating a stock count."""

    warehouse_id: str
    count_type: str
    scheduled_date: date
    notes: Optional[str] = None


class StockCountResponse(BaseModel):
    """Schema for stock count responses."""

    id: str
    tenant_id: str
    count_number: str
    warehouse_id: str
    count_type: str
    scheduled_date: date
    actual_date: Optional[date] = None
    count_status: str
    variance_count: int
    variance_value: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Class for Config operations."""
        from_attributes = True
