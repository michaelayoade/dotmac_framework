# @dotmac/network

Network management and monitoring components for ISP operations. This package provides comprehensive network infrastructure management capabilities built on DRY patterns and integrated with the DotMac shared services.

## Features

### 🌐 Network Topology Management

- Interactive network topology visualization
- Drag-and-drop topology editor
- Multiple layout algorithms (force-directed, hierarchical, grid, circular)
- Real-time topology updates
- Network discovery and auto-mapping

### 📱 Device Management

- Complete device lifecycle management
- Device inventory with filtering and search
- Real-time device status monitoring
- Configuration backup and restore
- SNMP operations and monitoring

### 📊 Network Monitoring

- Real-time performance metrics
- Network health dashboards
- Alert management system
- Custom monitoring rules
- Performance trend analysis

### 🔧 Core ISP Functionality

- Device discovery and provisioning
- Interface monitoring
- Bandwidth utilization tracking
- Network troubleshooting tools
- Configuration management

## Installation

```bash
pnpm add @dotmac/network
```

## Dependencies

This package relies on other DotMac packages:

- `@dotmac/primitives` - Core UI components
- `@dotmac/ui` - Higher-level UI components
- `@dotmac/headless` - Data management and API clients
- `@dotmac/auth` - Authentication and authorization

## Basic Usage

### Network Device Management

```tsx
import { DeviceList, useNetworkDevices } from '@dotmac/network';

function NetworkDevicesPage() {
  const { devices, loading, refresh } = useNetworkDevices();

  return (
    <DeviceList
      devices={devices}
      loading={loading}
      onRefresh={refresh}
      onDeviceSelect={(device) => console.log('Selected:', device)}
    />
  );
}
```

### Network Topology Visualization

```tsx
import { TopologyViewer } from '@dotmac/network';

function NetworkTopologyPage() {
  const topology = {
    id: '1',
    name: 'Main Network',
    nodes: [
      {
        id: 'router-1',
        device_id: 'dev-001',
        position: { x: 100, y: 100 },
        size: { width: 60, height: 60 },
        label: 'Core Router',
        type: 'device',
        status: 'online'
      }
    ],
    edges: [],
    layout: { type: 'force', settings: {} },
    metadata: {
      created_at: new Date(),
      updated_at: new Date(),
      created_by: 'admin',
      version: 1,
      auto_layout: false,
      show_labels: true,
      show_metrics: true
    }
  };

  return (
    <TopologyViewer
      topology={topology}
      showMetrics={true}
      onNodeSelect={(node) => console.log('Node selected:', node)}
    />
  );
}
```

### Network Monitoring Dashboard

```tsx
import { NetworkMonitoringDashboard, useNetworkDevices, useNetworkAlerts } from '@dotmac/network';

function MonitoringPage() {
  const { devices, loading: devicesLoading } = useNetworkDevices();
  const { alerts, loading: alertsLoading } = useNetworkAlerts();

  return (
    <NetworkMonitoringDashboard
      devices={devices}
      alerts={alerts}
      loading={devicesLoading || alertsLoading}
    />
  );
}
```

## Components

### Device Management

- `DeviceList` - Comprehensive device listing with filters
- `DeviceDetail` - Detailed device information view
- `DeviceForm` - Device creation and editing forms
- `DeviceStatusCard` - Status summary cards
- `DeviceMetricsChart` - Performance metrics visualization
- `InterfaceList` - Network interface management
- `DeviceConfiguration` - Configuration management

### Network Topology

- `TopologyViewer` - Interactive topology visualization
- `TopologyEditor` - Drag-and-drop topology editor
- `TopologyList` - Topology management interface
- `TopologyLayoutSelector` - Layout algorithm selection
- `TopologyMetricsOverlay` - Real-time metrics overlay

### Monitoring & Alerts

- `NetworkMonitoringDashboard` - Comprehensive monitoring overview
- `AlertsList` - Alert management and notifications
- `MetricsChart` - Customizable metrics visualization
- `MonitoringRulesList` - Alert rule configuration
- `PerformanceMetrics` - Performance trend analysis
- `NetworkHealthOverview` - Network health summary

## Hooks

### Data Management

- `useNetworkDevices` - Device CRUD operations
- `useNetworkTopology` - Topology management
- `useNetworkAlerts` - Alert handling
- `useDeviceMetrics` - Real-time metrics
- `useNetworkMonitoring` - Monitoring configuration

## API Integration

The package includes a comprehensive API client that follows DRY patterns and integrates with existing shared services:

```tsx
import { networkApiClient } from '@dotmac/network';

// Device operations
const devices = await networkApiClient.getDevices();
const device = await networkApiClient.createDevice({
  name: 'New Router',
  type: 'router',
  ip_address: '192.168.1.1',
  vendor: 'Cisco',
  model: 'ISR4431'
});

// Monitoring operations
const alerts = await networkApiClient.getAlerts();
await networkApiClient.acknowledgeAlert(alertId);

// SNMP operations
const result = await networkApiClient.snmpWalk(deviceId, '1.3.6.1.2.1.1');
```

## Configuration

### Network Configuration

```tsx
import { NetworkConfig } from '@dotmac/network';

const config: NetworkConfig = {
  api_endpoint: '/api/network',
  websocket_endpoint: '/ws/network',
  refresh_interval: 30000, // 30 seconds
  max_devices_per_topology: 1000,
  default_layout: 'force',
  enable_auto_discovery: true,
  snmp_timeout: 10000, // 10 seconds
  ssh_timeout: 30000 // 30 seconds
};
```

## Integration with Shared Services

This package leverages existing DRY patterns and shared services:

- **Exception Handling**: Uses `@standard_exception_handler` decorator
- **Authentication**: Integrates with `@dotmac/auth` for secure access
- **API Client**: Extends `BaseApiClient` from `@dotmac/headless`
- **UI Components**: Built on `@dotmac/primitives` and `@dotmac/ui`

## TypeScript Support

Comprehensive TypeScript definitions for all network management operations:

```tsx
import type {
  NetworkDevice,
  NetworkTopology,
  NetworkAlert,
  DeviceType,
  DeviceStatus,
  AlertSeverity
} from '@dotmac/network';
```

## Real-time Features

- WebSocket connections for live metrics
- Real-time topology updates
- Instant alert notifications
- Live device status monitoring

## Testing

The package includes comprehensive test coverage:

```bash
pnpm test
pnpm test:watch
```

## Development

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Build for production
pnpm build

# Run linting
pnpm lint
pnpm lint:fix

# Type checking
pnpm type-check
```

## License

MIT - See LICENSE file for details.

## Contributing

Please refer to the main DotMac Framework contributing guidelines.
