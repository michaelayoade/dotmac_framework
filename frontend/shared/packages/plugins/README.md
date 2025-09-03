# @dotmac/plugins

Plugin management system for the DotMac Framework. This package provides comprehensive plugin management functionality including plugin discovery, installation, lifecycle management, and marketplace integration.

## Features

### 🔌 Plugin Management

- Plugin discovery and installation
- Lifecycle management (initialization, shutdown, restart)
- Real-time health monitoring
- Configuration management
- Dependency resolution

### 🏪 Plugin Marketplace

- Browse available plugins
- Search and filtering capabilities
- Plugin ratings and reviews
- Installation from marketplace
- Update notifications

### 🛠️ Plugin Development

- Plugin validation utilities
- Configuration schema validation
- Status monitoring and reporting
- Error handling and logging

### 🔒 Security & Validation

- Plugin signature verification
- Configuration validation
- Dependency checking
- Security scanning

## Installation

```bash
# Using npm
npm install @dotmac/plugins

# Using yarn
yarn add @dotmac/plugins

# Using pnpm
pnpm add @dotmac/plugins
```

## Quick Start

```tsx
import React from 'react';
import { PluginDashboard, PluginManager, PluginMarketplace, usePlugins } from '@dotmac/plugins';

function PluginApp() {
  const { plugins, loading, error } = usePlugins();

  if (loading) return <div>Loading plugins...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h1>Plugin System</h1>

      {/* Dashboard Overview */}
      <PluginDashboard showSystemMetrics={true} showHealthAlerts={true} refreshInterval={30000} />

      {/* Plugin Management */}
      <PluginManager allowBulkOperations={true} showAdvancedFeatures={true} />

      {/* Marketplace */}
      <PluginMarketplace allowInstallation={true} showFilters={true} />
    </div>
  );
}
```

## Hooks

### usePlugins

Main hook for plugin management with full CRUD operations.

```tsx
const {
  plugins,
  loading,
  error,
  installPlugin,
  updatePlugin,
  uninstallPlugin,
  enablePlugin,
  disablePlugin,
  restartPlugin,
  getPlugin,
  getPluginHealth,
  findPlugins,
  getAvailableDomains,
  enableMultiplePlugins,
  disableMultiplePlugins,
  getSystemHealth,
  refreshPlugins,
} = usePlugins();
```

### usePluginMarketplace

Hook for marketplace functionality and plugin discovery.

```tsx
const {
  items,
  loading,
  error,
  searchPlugins,
  filterByCategory,
  filterByTag,
  clearFilters,
  installFromMarketplace,
  getPluginDetails,
  getCategories,
  getPopularTags,
  refreshMarketplace,
  checkForUpdates,
} = usePluginMarketplace();
```

### usePluginLifecycle

Hook for plugin lifecycle management and health monitoring.

```tsx
const {
  initializePlugin,
  shutdownPlugin,
  restartPlugin,
  performHealthCheck,
  startHealthMonitoring,
  stopHealthMonitoring,
  updatePluginConfig,
  validatePluginConfig,
  initializePluginsByDomain,
  shutdownPluginsByDomain,
  healthMonitoringActive,
  lastHealthCheck,
} = usePluginLifecycle();
```

## Components

### Dashboard Components

- `PluginDashboard` - Complete system overview with metrics
- System health monitoring
- Real-time status updates
- Error alerts and notifications

### Management Components

- `PluginManager` - Plugin management interface
- `PluginCard` - Individual plugin display card
- Bulk operations support
- Search and filtering

### Marketplace Components

- `PluginMarketplace` - Plugin discovery and installation
- Category and tag filtering
- Rating and review display
- Installation workflows

## Plugin Management

### Installation

```tsx
import { usePlugins } from '@dotmac/plugins';

function InstallPlugin() {
  const { installPlugin } = usePlugins();

  const handleInstall = async () => {
    await installPlugin({
      plugin_id: 'com.example.awesome-plugin',
      version: '1.0.0',
      enable_after_install: true,
      auto_update: true,
      config: {
        api_endpoint: 'https://api.example.com',
        timeout: 5000,
      },
    });
  };

  return <button onClick={handleInstall}>Install Plugin</button>;
}
```

### Lifecycle Management

```tsx
import { usePluginLifecycle } from '@dotmac/plugins';

function PluginControls({ pluginKey }: { pluginKey: string }) {
  const { initializePlugin, shutdownPlugin, restartPlugin, performHealthCheck } =
    usePluginLifecycle();

  const handleRestart = async () => {
    await shutdownPlugin(pluginKey);
    await initializePlugin(pluginKey);
  };

  const checkHealth = async () => {
    const health = await performHealthCheck(pluginKey);
    console.log('Plugin health:', health);
  };

  return (
    <div>
      <button onClick={handleRestart}>Restart</button>
      <button onClick={checkHealth}>Check Health</button>
    </div>
  );
}
```

### Health Monitoring

```tsx
import { usePluginLifecycle } from '@dotmac/plugins';

function HealthMonitoring() {
  const { startHealthMonitoring, stopHealthMonitoring, healthMonitoringActive } =
    usePluginLifecycle();

  return (
    <div>
      <p>Health monitoring: {healthMonitoringActive ? 'Active' : 'Inactive'}</p>
      <button onClick={healthMonitoringActive ? stopHealthMonitoring : startHealthMonitoring}>
        {healthMonitoringActive ? 'Stop' : 'Start'} Monitoring
      </button>
    </div>
  );
}
```

## Utilities

### Validation

```tsx
import {
  validatePluginName,
  validatePluginVersion,
  validatePluginMetadata,
  validatePluginConfig,
} from '@dotmac/plugins';

// Validate plugin metadata
const validation = validatePluginMetadata({
  name: 'my-plugin',
  version: '1.0.0',
  domain: 'com.example',
  description: 'A great plugin',
  dependencies: ['com.example.dependency'],
  tags: ['api', 'integration'],
  categories: ['network'],
});

if (!validation.isValid) {
  console.log('Validation errors:', validation.errors);
  console.log('Warnings:', validation.warnings);
}

// Validate configuration
const configValidation = validatePluginConfig(
  {
    apiUrl: 'https://api.example.com',
    timeout: 5000,
  },
  {
    apiUrl: { required: true, type: 'string' },
    timeout: { required: false, type: 'number', minimum: 1000 },
  }
);
```

### Formatting

```tsx
import {
  formatPluginStatus,
  formatPluginUptime,
  formatPluginSize,
  formatDownloadCount,
  formatPluginRating,
  getPluginStatusClasses,
} from '@dotmac/plugins';

// Format display values
const statusText = formatPluginStatus('active');
const uptime = formatPluginUptime(3665); // "1h 1m"
const size = formatPluginSize(1572864); // "1.5 MB"
const downloads = formatDownloadCount(1500000); // "1.5M"
const rating = formatPluginRating(4.67); // "4.7"

// Get CSS classes for status
const statusClasses = getPluginStatusClasses('active');
// Returns: "px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800"
```

## Types

The package exports comprehensive TypeScript types:

```tsx
import type {
  Plugin,
  PluginMetadata,
  PluginStatus,
  PluginHealth,
  PluginMarketplaceItem,
  PluginInstallRequest,
  PluginUpdateRequest,
  PluginUninstallRequest,
  PluginConfigValidation,
  PluginSearchFilters,
  PluginSystemHealth,
  UsePluginsResult,
  UsePluginMarketplaceResult,
  UsePluginLifecycleResult,
} from '@dotmac/plugins';
```

## Integration

### Portal Integration

The package integrates seamlessly with all DotMac portals:

```tsx
// Admin Portal - Full plugin management
import { PluginManager, PluginDashboard } from '@dotmac/plugins';

// Customer Portal - View installed plugins
import { PluginCard, usePlugins } from '@dotmac/plugins';

// Technician Portal - Plugin status monitoring
import { PluginDashboard, usePluginLifecycle } from '@dotmac/plugins';

// Reseller Portal - Plugin marketplace
import { PluginMarketplace } from '@dotmac/plugins';
```

### Backend Integration

The package works with the existing DotMac backend plugin system:

- Uses RouterFactory patterns for consistent API endpoints
- Integrates with existing tenant isolation
- Leverages `@standard_exception_handler` for error handling
- Supports all portal types with appropriate permissions

### API Endpoints

```tsx
import { API_ENDPOINTS } from '@dotmac/plugins';

// Pre-configured endpoints:
// /api/plugins - Plugin management
// /api/plugins/marketplace - Marketplace
// /api/plugins/lifecycle - Lifecycle management
// /api/plugins/health - Health monitoring
```

## Configuration

### Theming

Components use the DotMac design system and can be customized:

```css
.plugin-dashboard {
  --plugin-primary: #007bff;
  --plugin-success: #28a745;
  --plugin-warning: #ffc107;
  --plugin-danger: #dc3545;
}

.plugin-card {
  --card-border: #e5e7eb;
  --card-background: #ffffff;
  --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
```

### Health Monitoring

Configure health monitoring intervals:

```tsx
<PluginDashboard
  refreshInterval={30000} // 30 seconds
  showHealthAlerts={true}
/>;

// Or programmatically
const { startHealthMonitoring } = usePluginLifecycle();
await startHealthMonitoring();
```

## Error Handling

The package provides comprehensive error handling:

```tsx
import { usePlugins } from '@dotmac/plugins';

function PluginWithErrorHandling() {
  const { plugins, loading, error, installPlugin } = usePlugins();

  const handleInstall = async (pluginId: string) => {
    try {
      await installPlugin({
        plugin_id: pluginId,
        enable_after_install: true,
        auto_update: true,
      });
    } catch (err) {
      console.error('Installation failed:', err);
      // Handle error appropriately
    }
  };

  if (error) {
    return (
      <div className='error-state'>
        <h3>Plugin System Error</h3>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return <div>...</div>;
}
```

## Testing

The package includes comprehensive tests:

```bash
# Run all tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

### Test Utilities

The package provides test utilities for easier testing:

```tsx
// Mock plugin data for testing
import { createMockPlugin, createMockMarketplaceItem } from '@dotmac/plugins/testing';

const mockPlugin = createMockPlugin({
  name: 'test-plugin',
  domain: 'com.test',
  status: 'active',
});
```

## Security

The package includes security features:

- Plugin signature verification
- Configuration validation
- Dependency checking
- Sandbox execution support
- Permission management

```tsx
// Validate plugin before installation
const validation = validatePluginMetadata(pluginMetadata);
if (!validation.isValid) {
  throw new Error('Plugin validation failed');
}

// Check configuration security
const configValidation = validatePluginConfig(config, schema);
if (configValidation.warnings.some((w) => w.includes('sensitive'))) {
  console.warn('Plugin configuration contains sensitive data');
}
```

## Performance

The package is optimized for performance:

- Lazy loading of components
- Efficient state management
- Debounced search operations
- Virtual scrolling for large lists
- Caching of plugin data

## Dependencies

- `@dotmac/ui` - UI components
- `@dotmac/headless` - API client and state management
- `@dotmac/auth` - Authentication
- `@dotmac/primitives` - Base components
- `react` ^18.0.0
- `date-fns` - Date utilities
- `lucide-react` - Icons
- `js-yaml` - YAML parsing

## License

MIT License - see LICENSE file for details.

## Support

For support and questions:

- GitHub Issues: [dotmac-framework/frontend](https://github.com/dotmac-framework/frontend/issues)
- Documentation: [DotMac Docs](https://docs.dotmac.com)
- Community: [DotMac Discord](https://discord.gg/dotmac)
