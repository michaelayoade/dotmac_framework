"""
DotMac Shared Inventory Management System

Comprehensive inventory management for equipment, assets, stock control,
and warehouse operations across ISP and Management Platform systems.
"""

__version__ = "1.0.0"

from .core.inventory_manager import InventoryManager

# Core exports
from .core.models import (  # Enums; Models
    Item,
    ItemCondition,
    ItemStatus,
    ItemType,
    MovementType,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    StockCount,
    StockCountLine,
    StockItem,
    StockMovement,
    Warehouse,
    WarehouseType,
)
from .core.schemas import (  # Item schemas; Warehouse schemas; Stock schemas; Purchase Order schemas; Stock Count schemas
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
    PurchaseOrderLineResponse,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    StockCountCreate,
    StockCountLineResponse,
    StockCountResponse,
    StockItemResponse,
    StockMovementCreate,
    StockMovementResponse,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)
from .services.inventory_service import InventoryService

# Conditional exports for optional components
_workflow_available = False
_adapters_available = False

try:
    from .workflows.inventory_workflows import (
        InventoryWorkflowManager,
        WorkflowAction,
        WorkflowTrigger,
        setup_inventory_workflows,
    )

    _workflow_available = True
except ImportError:
    pass

try:
    from .adapters.platform_adapter import (
        InventoryPlatformAdapter,
        ISPInventoryAdapter,
        ManagementInventoryAdapter,
    )

    _adapters_available = True
except ImportError:
    pass

# Build exports list
core_exports = [
    # Enums
    "ItemType",
    "ItemCondition",
    "ItemStatus",
    "MovementType",
    "WarehouseType",
    "PurchaseOrderStatus",
    # Models
    "Item",
    "Warehouse",
    "StockItem",
    "StockMovement",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "StockCount",
    "StockCountLine",
    # Manager
    "InventoryManager",
    # Schemas
    "ItemCreate",
    "ItemUpdate",
    "ItemResponse",
    "WarehouseCreate",
    "WarehouseUpdate",
    "WarehouseResponse",
    "StockItemResponse",
    "StockMovementCreate",
    "StockMovementResponse",
    "PurchaseOrderCreate",
    "PurchaseOrderUpdate",
    "PurchaseOrderResponse",
    "PurchaseOrderLineCreate",
    "PurchaseOrderLineResponse",
    "StockCountCreate",
    "StockCountResponse",
    "StockCountLineResponse",
    # Service
    "InventoryService",
]

workflow_exports = []
if _workflow_available:
    workflow_exports = [
        "InventoryWorkflowManager",
        "setup_inventory_workflows",
        "WorkflowTrigger",
        "WorkflowAction",
    ]

adapter_exports = []
if _adapters_available:
    adapter_exports = [
        "InventoryPlatformAdapter",
        "ISPInventoryAdapter",
        "ManagementInventoryAdapter",
    ]

__all__ = core_exports + workflow_exports + adapter_exports
