# Vendor Plugin Architecture

## Overview

The DotMac ISP Framework uses a comprehensive plugin architecture to handle vendor-specific integrations. This approach solves the missing SDK modules (VolthaSDK and AnalyticsEventsSDK) identified in the system analysis by providing a clean, modular, and secure way to integrate with external vendor systems.

## Problem Solved

**Before**: Missing SDK modules caused import errors:
- `dotmac_isp.sdks.networking.voltha_integration.VolthaSDK` (missing)
- `dotmac_isp.sdks.analytics.events.AnalyticsEventsSDK` (missing)

**After**: Vendor-specific plugins provide the functionality:
- `VolthaIntegrationPlugin` - Fiber network management via VOLTHA
- `AnalyticsEventsPlugin` - Comprehensive event tracking and analytics

## Architecture Components

### 1. Plugin Base Classes (`plugins/core/base.py`)

```python
# Base plugin interface
class BasePlugin(ABC):
    async def initialize() -> None
    async def activate() -> None  
    async def deactivate() -> None
    async def cleanup() -> None

# Specialized plugin types
class NetworkAutomationPlugin(BasePlugin):
    async def discover_devices() -> List[Dict]
    async def configure_device() -> bool
    async def get_device_status() -> Dict

class MonitoringPlugin(BasePlugin):
    async def collect_metrics() -> Dict
    async def create_alert() -> str
    async def get_alert_status() -> Dict
```

### 2. Plugin Manager (`plugins/core/manager.py`)

- **Plugin Lifecycle Management**: Load, start, stop, unload plugins
- **Multi-tenant Support**: Tenant-specific plugin configurations
- **Security Integration**: License validation and permission checks
- **Health Monitoring**: Background health checks and metrics collection
- **Dependency Management**: Automatic dependency resolution

### 3. Vendor Integration Plugins

#### VOLTHA Integration Plugin
**File**: `plugins/network_automation/voltha_integration_plugin.py`

**Features**:
- OLT (Optical Line Terminal) device provisioning
- ONU (Optical Network Unit) subscriber management
- Flow configuration for subscriber services
- Real-time device monitoring and alarms
- Performance metrics and statistics
- Fiber network topology management

**Configuration**:
```json
{
  "voltha_host": "voltha.fiber.local",
  "voltha_port": 50057,
  "voltha_rest_port": 8881,
  "device_monitoring_interval": 30
}
```

#### Analytics Events Plugin
**File**: `plugins/monitoring/analytics_events_plugin.py`

**Features**:
- Comprehensive event tracking (page views, conversions, transactions)
- Batch event processing with configurable buffer sizes
- Real-time analytics and custom dashboards
- Business intelligence reporting
- Alert rules and automated notifications
- Schema validation for event data
- Multi-category event support (business, technical, security, etc.)

**Configuration**:
```json
{
  "analytics_host": "localhost",
  "analytics_port": 8080,
  "batch_size": 100,
  "flush_interval": 30
}
```

### 4. Plugin Loader Utility (`plugins/utils/vendor_plugin_loader.py`)

**Features**:
- Environment-specific plugin loading (development, production)
- Automatic secret validation and management
- Configuration merging and overrides
- Bulk plugin operations (start/stop/restart)
- Health monitoring and status reporting
- Plugin discovery and registration

## Usage Examples

### 1. Loading Vendor Integrations

```python
from dotmac_isp.plugins.core.manager import PluginManager
from dotmac_isp.plugins.utils.vendor_plugin_loader import VendorPluginLoader

# Set up plugin manager
plugin_manager = PluginManager()
await plugin_manager.start()

# Load vendor plugins for production environment
loader = VendorPluginLoader(plugin_manager)
results = await loader.load_vendor_integrations("production", tenant_id="tenant_123")

print(f"Loaded plugins: {results['loaded_plugins']}")
# Output: ['voltha_integration', 'analytics_events']
```

### 2. Using VOLTHA Integration

```python
# Start VOLTHA plugin
await loader.start_vendor_plugin("voltha_integration", tenant_id="tenant_123")

# Plugin provides VOLTHA functionality that was missing from SDK
# - OLT provisioning: provision_olt(host_and_port, device_type)
# - ONU management: provision_onu(parent_device_id, pon_port, onu_id, serial_number)
# - Device monitoring: get_device_status(device_id)
# - Flow configuration: add_subscriber_flow(device_id, subscriber_id, service_config)
```

### 3. Using Analytics Events

```python
# Start Analytics Events plugin
await loader.start_vendor_plugin("analytics_events", tenant_id="tenant_123")

# Plugin provides analytics functionality that was missing from SDK
# - Event tracking: track_event(event, context)
# - Batch processing: track_events_batch(events, context)
# - Report generation: generate_report(report_type, parameters)
# - Dashboard creation: create_dashboard(dashboard_config)
```

### 4. Health Monitoring

```python
# Check health of all vendor plugins
health_status = await loader.health_check_all_plugins()

print(f"Healthy plugins: {health_status['healthy_plugins']}")
print(f"Total plugins: {health_status['total_plugins']}")

# Individual plugin status
status = await loader.get_vendor_plugin_status()
voltha_health = status["plugins"]["voltha_integration"]["health"]
```

## Configuration Management

### Plugin Configuration File
**File**: `plugins/config/vendor_integrations.json`

```json
{
  "vendor_integrations": {
    "voltha_integration": {
      "plugin_id": "voltha_integration",
      "name": "VOLTHA Integration",
      "module_path": "dotmac_isp.plugins.network_automation.voltha_integration_plugin",
      "class_name": "VolthaIntegrationPlugin",
      "enabled": true,
      "configuration": { ... },
      "security": {
        "required_permissions": ["network.fiber.manage"],
        "secrets_required": ["voltha-username", "voltha-password"]
      }
    }
  },
  "deployment_scenarios": {
    "development": { ... },
    "production": { ... }
  }
}
```

### Environment Variables

**VOLTHA Integration**:
- `VOLTHA_HOST` - VOLTHA server hostname
- `VOLTHA_PORT` - VOLTHA gRPC port (default: 50057)
- `VOLTHA_USERNAME` - Authentication username
- `VOLTHA_PASSWORD` - Authentication password

**Analytics Events**:
- `ANALYTICS_HOST` - Analytics service hostname  
- `ANALYTICS_PORT` - Analytics service port (default: 8080)
- `ANALYTICS_API_KEY` - API authentication key
- `ANALYTICS_DB_CONNECTION` - Optional database connection string

## Security Features

### 1. Secrets Management
- Integration with enterprise secrets manager (Vault/OpenBao)
- Automatic secret rotation support
- Environment variable fallback
- Required vs optional secret validation

### 2. Permission-Based Access Control
- Granular permissions per plugin feature
- Tenant-specific permission validation
- Security level classification (minimal, standard, elevated, system)

### 3. Sandboxing and Resource Limits
- Plugin sandboxing for isolation
- Configurable resource limits (CPU, memory, network)
- License validation for commercial plugins

## Benefits

### ✅ **Modular Architecture**
- Vendor integrations are isolated and optional
- Core SDK remains clean and focused
- Easy to add/remove vendor-specific features

### ✅ **Multi-Tenant Support**  
- Tenant-specific plugin configurations
- Isolated execution contexts
- Per-tenant credential management

### ✅ **Development Experience**
- Hot-reload support for development
- Comprehensive health monitoring
- Rich metrics and observability

### ✅ **Production Ready**
- License validation and compliance
- Background monitoring and alerting
- Graceful degradation on failures
- Performance metrics collection

### ✅ **Security First**
- Enterprise secrets management
- Permission-based access control
- Plugin sandboxing and resource limits
- Audit trail and compliance reporting

## Migration Guide

### From Missing SDKs to Plugins

**Old Code (would fail)**:
```python
# These imports would fail
from dotmac_isp.sdks.networking.voltha_integration import VolthaSDK
from dotmac_isp.sdks.analytics.events import AnalyticsEventsSDK
```

**New Code (plugin-based)**:
```python
# Load and use plugins instead
from dotmac_isp.plugins.utils import load_voltha_integration, load_analytics_events

# Load vendor integrations
await load_voltha_integration(plugin_manager, "production", tenant_id)
await load_analytics_events(plugin_manager, "production", tenant_id) 

# Plugins provide the same functionality through the plugin manager
```

## Deployment

### Development Environment
```bash
# Set development credentials
export VOLTHA_USERNAME="dev_user"
export VOLTHA_PASSWORD="dev_pass" 
export ANALYTICS_API_KEY="dev_analytics_key"

# Run demo
python examples/vendor_plugin_demo.py
```

### Production Environment
```bash
# Configure production secrets in vault/environment
# Load plugins with production configuration
# Monitor plugin health and performance
```

## Conclusion

The vendor plugin architecture successfully solves the missing SDK integration issues while providing:

- **Clean separation** between core framework and vendor integrations
- **Flexible deployment** with environment-specific configurations  
- **Enterprise security** with secrets management and permissions
- **Operational excellence** with monitoring and health checks
- **Developer experience** with hot-reload and comprehensive tooling

This architecture ensures that vendor integrations don't pollute the core SDK while providing all the functionality that would have been in the missing VolthaSDK and AnalyticsEventsSDK modules.