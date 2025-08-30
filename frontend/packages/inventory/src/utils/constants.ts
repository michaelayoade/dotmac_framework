import { ItemType, ItemStatus, MovementType, WarehouseType, PurchaseOrderStatus } from '../types';

/**
 * Default values for inventory items
 */
export const ITEM_DEFAULTS = {
  UNIT_OF_MEASURE: 'each',
  REORDER_POINT: 0,
  REORDER_QUANTITY: 0,
  ZONE_COUNT: 1,
  STAFF_COUNT: 1,
  SECURITY_LEVEL: 'standard',
  CURRENCY: 'USD',
  VALUATION_METHOD: 'FIFO'
} as const;

/**
 * Validation limits
 */
export const VALIDATION_LIMITS = {
  ITEM_NAME_MAX_LENGTH: 300,
  ITEM_CODE_MAX_LENGTH: 100,
  BARCODE_MAX_LENGTH: 100,
  WAREHOUSE_CODE_MAX_LENGTH: 50,
  WAREHOUSE_NAME_MAX_LENGTH: 200,
  DESCRIPTION_MAX_LENGTH: 1000,
  NOTES_MAX_LENGTH: 2000,
  SERIAL_NUMBER_MAX_LENGTH: 50,
  SERIAL_NUMBER_MIN_LENGTH: 3,
  MAX_QUANTITY: 1000000,
  MAX_CURRENCY_AMOUNT: 999999999.99,
  MAX_DATE_RANGE_YEARS: 10
} as const;

/**
 * Common item categories by type
 */
export const ITEM_CATEGORIES = {
  [ItemType.HARDWARE]: [
    'Computer Hardware',
    'Server Hardware',
    'Storage Hardware',
    'Memory',
    'Processors',
    'Motherboards',
    'Power Supplies',
    'Cases & Enclosures'
  ],
  [ItemType.SOFTWARE]: [
    'Operating Systems',
    'Applications',
    'Licenses',
    'Utilities',
    'Security Software',
    'Development Tools'
  ],
  [ItemType.NETWORK_EQUIPMENT]: [
    'Routers',
    'Switches',
    'Firewalls',
    'Access Points',
    'Load Balancers',
    'Network Cables',
    'Transceivers',
    'Patch Panels'
  ],
  [ItemType.CUSTOMER_PREMISES_EQUIPMENT]: [
    'Modems',
    'ONTs',
    'Set-Top Boxes',
    'Wi-Fi Routers',
    'Voice Adapters',
    'Antennas',
    'Coaxial Equipment'
  ],
  [ItemType.CONSUMABLE]: [
    'Cables',
    'Connectors',
    'Batteries',
    'Adhesives',
    'Cleaning Supplies',
    'Labels',
    'Packaging Materials'
  ],
  [ItemType.TOOL]: [
    'Hand Tools',
    'Power Tools',
    'Test Equipment',
    'Measuring Tools',
    'Safety Equipment',
    'Installation Tools'
  ],
  [ItemType.SPARE_PART]: [
    'Replacement Parts',
    'Circuit Boards',
    'Sensors',
    'Actuators',
    'Mechanical Parts',
    'Electronic Components'
  ]
} as const;

/**
 * Standard warehouse configurations
 */
export const STANDARD_WAREHOUSES = [
  {
    warehouse_code: 'MAIN-01',
    name: 'Main Warehouse',
    warehouse_type: WarehouseType.MAIN,
    description: 'Primary inventory storage facility'
  },
  {
    warehouse_code: 'FIELD-01',
    name: 'Field Operations',
    warehouse_type: WarehouseType.FIELD,
    description: 'Field technician inventory'
  },
  {
    warehouse_code: 'REPAIR-01',
    name: 'Repair Workshop',
    warehouse_type: WarehouseType.REPAIR,
    description: 'Equipment repair and refurbishment'
  }
] as const;

/**
 * Status progression rules
 */
export const STATUS_TRANSITIONS = {
  [ItemStatus.AVAILABLE]: [
    ItemStatus.RESERVED,
    ItemStatus.ALLOCATED,
    ItemStatus.IN_REPAIR,
    ItemStatus.QUARANTINED,
    ItemStatus.RETIRED
  ],
  [ItemStatus.RESERVED]: [
    ItemStatus.AVAILABLE,
    ItemStatus.ALLOCATED,
    ItemStatus.IN_REPAIR
  ],
  [ItemStatus.ALLOCATED]: [
    ItemStatus.IN_USE,
    ItemStatus.AVAILABLE,
    ItemStatus.IN_REPAIR
  ],
  [ItemStatus.IN_USE]: [
    ItemStatus.AVAILABLE,
    ItemStatus.IN_REPAIR,
    ItemStatus.LOST,
    ItemStatus.RETIRED
  ],
  [ItemStatus.IN_REPAIR]: [
    ItemStatus.AVAILABLE,
    ItemStatus.RETIRED,
    ItemStatus.QUARANTINED
  ],
  [ItemStatus.QUARANTINED]: [
    ItemStatus.AVAILABLE,
    ItemStatus.RETIRED,
    ItemStatus.IN_REPAIR
  ],
  [ItemStatus.RETIRED]: [],
  [ItemStatus.LOST]: [ItemStatus.AVAILABLE] // If found
} as const;

/**
 * Movement type configurations
 */
export const MOVEMENT_CONFIGS = {
  [MovementType.RECEIPT]: {
    isInbound: true,
    requiresApproval: false,
    affectsAvailable: true,
    icon: 'ArrowRight',
    color: 'green'
  },
  [MovementType.ISSUE]: {
    isInbound: false,
    requiresApproval: false,
    affectsAvailable: true,
    icon: 'ArrowLeft',
    color: 'blue'
  },
  [MovementType.TRANSFER]: {
    isInbound: null, // Depends on direction
    requiresApproval: true,
    affectsAvailable: true,
    icon: 'RotateCcw',
    color: 'orange'
  },
  [MovementType.ADJUSTMENT]: {
    isInbound: null, // Can be positive or negative
    requiresApproval: true,
    affectsAvailable: true,
    icon: 'AlertCircle',
    color: 'yellow'
  },
  [MovementType.RETURN]: {
    isInbound: true,
    requiresApproval: false,
    affectsAvailable: true,
    icon: 'ArrowRight',
    color: 'green'
  },
  [MovementType.WRITE_OFF]: {
    isInbound: false,
    requiresApproval: true,
    affectsAvailable: true,
    icon: 'X',
    color: 'red'
  },
  [MovementType.FOUND]: {
    isInbound: true,
    requiresApproval: true,
    affectsAvailable: true,
    icon: 'Package',
    color: 'green'
  },
  [MovementType.INSTALLATION]: {
    isInbound: false,
    requiresApproval: false,
    affectsAvailable: true,
    icon: 'ArrowLeft',
    color: 'blue'
  },
  [MovementType.REPLACEMENT]: {
    isInbound: null, // Both in and out
    requiresApproval: false,
    affectsAvailable: true,
    icon: 'RotateCcw',
    color: 'orange'
  }
} as const;

/**
 * Purchase order workflow stages
 */
export const PO_WORKFLOW_STAGES = {
  [PurchaseOrderStatus.DRAFT]: {
    next: [PurchaseOrderStatus.PENDING_APPROVAL, PurchaseOrderStatus.CANCELLED],
    canEdit: true,
    canDelete: true
  },
  [PurchaseOrderStatus.PENDING_APPROVAL]: {
    next: [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.CANCELLED],
    canEdit: false,
    canDelete: false
  },
  [PurchaseOrderStatus.APPROVED]: {
    next: [PurchaseOrderStatus.SENT_TO_VENDOR],
    canEdit: false,
    canDelete: false
  },
  [PurchaseOrderStatus.SENT_TO_VENDOR]: {
    next: [PurchaseOrderStatus.PARTIALLY_RECEIVED, PurchaseOrderStatus.RECEIVED],
    canEdit: false,
    canDelete: false
  },
  [PurchaseOrderStatus.PARTIALLY_RECEIVED]: {
    next: [PurchaseOrderStatus.RECEIVED],
    canEdit: false,
    canDelete: false
  },
  [PurchaseOrderStatus.RECEIVED]: {
    next: [PurchaseOrderStatus.CLOSED],
    canEdit: false,
    canDelete: false
  },
  [PurchaseOrderStatus.CANCELLED]: {
    next: [],
    canEdit: false,
    canDelete: false
  },
  [PurchaseOrderStatus.CLOSED]: {
    next: [],
    canEdit: false,
    canDelete: false
  }
} as const;

/**
 * Inventory classification thresholds
 */
export const CLASSIFICATION_THRESHOLDS = {
  ABC: {
    A: 80, // Top 80% of value
    B: 95, // Next 15% of value
    C: 100 // Remaining 5% of value
  },
  STOCK_STATUS: {
    CRITICAL: 0,
    LOW: 0.5, // Below 50% of reorder point
    HEALTHY: 1.0, // Above reorder point
    OVERSTOCK: 1.5 // Above 150% of max stock
  }
} as const;

/**
 * Default calculation parameters
 */
export const CALCULATION_DEFAULTS = {
  CARRYING_COST_RATE: 0.20, // 20%
  ORDERING_COST: 50, // $50 per order
  SERVICE_LEVEL: 0.95, // 95%
  SAFETY_STOCK_DAYS: 7,
  FORECAST_PERIODS: 12, // months
  SEASONAL_CYCLES: 12, // months
  EOQ_MIN_QUANTITY: 1,
  EOQ_MAX_QUANTITY: 10000
} as const;

/**
 * API endpoints
 */
export const API_ENDPOINTS = {
  ITEMS: '/api/inventory/items',
  WAREHOUSES: '/api/inventory/warehouses',
  STOCK: '/api/inventory/stock',
  MOVEMENTS: '/api/inventory/movements',
  PURCHASE_ORDERS: '/api/inventory/purchase-orders',
  ASSETS: '/api/inventory/assets',
  PROVISIONING: '/api/inventory/provisioning',
  ANALYTICS: '/api/inventory/analytics'
} as const;

/**
 * Common search filters
 */
export const SEARCH_FILTERS = {
  ITEMS: {
    item_type: 'Item Type',
    category: 'Category',
    manufacturer: 'Manufacturer',
    status: 'Status',
    is_active: 'Active Only',
    low_stock: 'Low Stock Only'
  },
  WAREHOUSES: {
    warehouse_type: 'Warehouse Type',
    city: 'City',
    country: 'Country',
    is_active: 'Active Only'
  },
  MOVEMENTS: {
    movement_type: 'Movement Type',
    date_range: 'Date Range',
    reference_number: 'Reference Number'
  },
  PURCHASE_ORDERS: {
    po_status: 'Status',
    vendor_id: 'Vendor',
    date_range: 'Date Range'
  }
} as const;

/**
 * Export formats
 */
export const EXPORT_FORMATS = {
  CSV: 'text/csv',
  XLSX: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  PDF: 'application/pdf',
  JSON: 'application/json'
} as const;

/**
 * Notification types
 */
export const NOTIFICATION_TYPES = {
  LOW_STOCK: 'low_stock',
  STOCK_OUT: 'stock_out',
  REORDER_REQUIRED: 'reorder_required',
  MAINTENANCE_DUE: 'maintenance_due',
  PO_APPROVAL_REQUIRED: 'po_approval_required',
  MOVEMENT_APPROVED: 'movement_approved',
  ASSET_ASSIGNED: 'asset_assigned'
} as const;
