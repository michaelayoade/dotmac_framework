# @dotmac/inventory

Equipment and asset management components for the DotMac Framework. This package provides comprehensive inventory management functionality including asset tracking, stock management, equipment provisioning, and warehouse operations.

## Features

### 🏷️ Asset Tracking

- Real-time asset location tracking
- Serial number management
- Maintenance scheduling and tracking
- Customer deployment tracking
- Technician assignment

### 📦 Stock Management

- Multi-warehouse inventory control
- Stock level monitoring and alerts
- Automated reorder point calculations
- Stock transfers and adjustments
- Inventory valuation

### 🚚 Equipment Provisioning

- Customer equipment provisioning workflows
- Technician dispatch management
- Installation tracking
- Equipment kit templates
- Return processing

### 🏭 Warehouse Management

- Multi-location inventory
- Bin location tracking
- Zone and aisle management
- Warehouse capacity planning

### 📋 Purchase Order Management

- PO creation and approval workflows
- Vendor management integration
- Receipt processing
- Cost tracking and analysis

## Installation

```bash
# Using npm
npm install @dotmac/inventory

# Using yarn
yarn add @dotmac/inventory

# Using pnpm
pnpm add @dotmac/inventory
```

## Quick Start

```tsx
import React from 'react';
import {
  InventoryDashboard,
  AssetTracker,
  useInventory,
  useAssetTracking
} from '@dotmac/inventory';

function InventoryApp() {
  const { items, loading } = useInventory();
  const { assets } = useAssetTracking();

  return (
    <div>
      <h1>Inventory Management</h1>

      {/* Dashboard Overview */}
      <InventoryDashboard
        showLowStockAlerts={true}
        showRecentMovements={true}
      />

      {/* Asset Tracking */}
      <AssetTracker
        defaultView="list"
        showFilters={true}
      />
    </div>
  );
}
```

## Hooks

### useInventory

Manage inventory items with full CRUD operations.

```tsx
const {
  items,
  loading,
  error,
  createItem,
  updateItem,
  deleteItem,
  getItemWithStock,
  searchItems,
  getLowStockItems
} = useInventory();
```

### useAssetTracking

Track assets across locations and lifecycle stages.

```tsx
const {
  getAssetDetails,
  getAssetHistory,
  trackAssetMovement,
  assignAssetToTechnician,
  deployAssetToCustomer,
  searchAssetsBySerial
} = useAssetTracking();
```

### useStock

Manage stock levels, adjustments, and movements.

```tsx
const {
  stockLevels,
  adjustStock,
  reserveStock,
  transferStock,
  getLowStockAlerts,
  performStockCount
} = useStock();
```

### useEquipmentProvisioning

Handle equipment provisioning workflows.

```tsx
const {
  provisioningRequests,
  createProvisioningRequest,
  allocateEquipment,
  dispatchEquipment,
  confirmInstallation,
  getAvailableEquipment
} = useEquipmentProvisioning();
```

## Components

### Dashboard Components

- `InventoryDashboard` - Complete inventory overview
- `StockOverview` - Stock levels summary
- `LowStockAlerts` - Critical stock alerts

### Asset Management

- `AssetTracker` - Asset search and tracking
- `AssetDetails` - Detailed asset information
- `AssetHistory` - Movement and maintenance history
- `AssetLocationMap` - Geographic asset visualization

### Stock Management

- `StockLevels` - Current stock status
- `StockAdjustments` - Stock adjustment forms
- `MovementHistory` - Stock movement tracking

### Provisioning

- `ProvisioningDashboard` - Provisioning overview
- `ProvisioningRequest` - Request creation and management
- `EquipmentAllocation` - Equipment assignment
- `TechnicianDispatch` - Dispatch management

### Common Components

- `ItemStatusBadge` - Status indicators
- `StockLevelIndicator` - Visual stock levels
- `WarehouseSelector` - Warehouse selection
- `ItemSelector` - Item search and selection

## Utilities

### Calculations

```tsx
import {
  calculateStockStatus,
  calculateReorderPoint,
  calculateEOQ,
  calculateInventoryValue,
  calculateABCClassification
} from '@dotmac/inventory';

// Calculate optimal reorder point
const reorderPoint = calculateReorderPoint(
  averageDemand,
  leadTimeDays,
  safetyStockDays
);

// ABC classification for inventory optimization
const classification = calculateABCClassification(items);
```

### Validators

```tsx
import {
  validateItemCreate,
  validateStockAdjustment,
  validateSerialNumber
} from '@dotmac/inventory';

// Validate item creation data
const validation = validateItemCreate(itemData);
if (!validation.isValid) {
  console.log('Errors:', validation.errors);
}
```

### Formatters

```tsx
import {
  formatCurrency,
  formatQuantity,
  formatItemType,
  formatSerialNumber
} from '@dotmac/inventory';

// Format display values
const price = formatCurrency(19.99, 'USD');
const qty = formatQuantity(150, 'each');
const serial = formatSerialNumber('ABC123DEF456');
```

## Types

The package exports comprehensive TypeScript types:

```tsx
import type {
  Item,
  ItemCreate,
  ItemUpdate,
  StockItem,
  StockMovement,
  Warehouse,
  PurchaseOrder,
  AssetDetails,
  ProvisioningRequest
} from '@dotmac/inventory';
```

## Integration

### Portal Integration

The package integrates seamlessly with DotMac portals:

```tsx
// Admin Portal
import { InventoryDashboard } from '@dotmac/inventory';

// Technician Portal
import { AssetTracker, EquipmentAllocation } from '@dotmac/inventory';

// Customer Portal
import { AssetDetails } from '@dotmac/inventory';
```

### Backend Integration

Works with the existing DotMac backend inventory system:

- Uses standard DRY patterns with `@standard_exception_handler`
- Leverages RouterFactory for consistent API endpoints
- Integrates with existing tenant isolation
- Supports all portal types (Admin, Customer, Technician, Reseller)

## Configuration

### API Endpoints

Configure base API endpoints in your app:

```tsx
import { API_ENDPOINTS } from '@dotmac/inventory';

// Endpoints are pre-configured for DotMac backend
// /api/inventory/items
// /api/inventory/warehouses
// /api/inventory/stock
// /api/inventory/movements
// /api/inventory/assets
```

### Theming

Components use the DotMac design system and can be customized via CSS:

```css
.inventory-dashboard {
  --inventory-primary: #007bff;
  --inventory-success: #28a745;
  --inventory-warning: #ffc107;
  --inventory-danger: #dc3545;
}
```

## Testing

The package includes comprehensive tests:

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

## Dependencies

- `@dotmac/ui` - UI components
- `@dotmac/headless` - API client and state management
- `@dotmac/auth` - Authentication
- `@dotmac/primitives` - Base components
- `react` ^18.0.0
- `date-fns` - Date utilities
- `recharts` - Charts and visualizations

## License

MIT License - see LICENSE file for details.

## Support

For support and questions:

- GitHub Issues: [dotmac-framework/frontend](https://github.com/dotmac-framework/frontend/issues)
- Documentation: [DotMac Docs](https://docs.dotmac.com)
- Community: [DotMac Discord](https://discord.gg/dotmac)
