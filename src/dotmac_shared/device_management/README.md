# DotMac Device Management Framework

Comprehensive device management system providing device inventory, monitoring, network topology management, and hardware lifecycle automation.

## Features

### Core Components

- **Device Inventory Management** - Complete asset tracking with modules, interfaces, and hardware lifecycle
- **SNMP Monitoring & Telemetry** - Real-time metrics collection and device health monitoring
- **Network Topology Management** - Graph-based network modeling with path analysis
- **MAC Address Registry** - Centralized MAC address tracking with OUI vendor identification
- **Hardware Lifecycle Management** - Automated provisioning, deployment, maintenance, and decommissioning workflows

### Advanced Capabilities

- **SNMP Client & Collector** - Production-ready SNMP query capabilities with async support
- **Topology Analyzer** - Advanced network analysis including centrality metrics, redundancy detection, and optimal placement
- **Platform Adapters** - Seamless integration with ISP Framework and Management Platform
- **Workflow Engine** - Complete device lifecycle automation with validation and rollback

## Quick Start

### Installation

```bash
# Install the package
pip install dotmac-device-management

# Or with optional dependencies
pip install dotmac-device-management[snmp,topology,monitoring]
```

### Basic Usage

```python
from sqlalchemy.orm import Session
from dotmac_device_management import DeviceService

# Initialize service
service = DeviceService(session, tenant_id="your-tenant")

# Create a device
device = await service.create_device(
    device_id="switch-001",
    hostname="core-switch-01",
    device_type="switch",
    site_id="datacenter-1",
    management_ip="192.168.1.10"
)

# Set up monitoring
monitor = await service.setup_device_monitoring(
    device_id="switch-001",
    monitor_type="snmp",
    metrics=["system", "interfaces", "cpu", "memory"]
)

# Get device health
health = await service.get_device_health("switch-001")
print(f"Device health: {health['health_status']}")
```

### Network Topology

```python
# Add device to topology
node = await service.add_device_to_topology(
    device_id="switch-001",
    name="Core Switch 01",
    site_id="datacenter-1",
    x_coordinate=100,
    y_coordinate=200
)

# Create connections
connection = await service.create_device_connection(
    source_device="switch-001",
    target_device="switch-002",
    link_type="physical",
    bandwidth="10G"
)

# Analyze topology
analysis = await service.analyze_network_topology()
print(f"Network has {analysis['topology_summary']['total_nodes']} nodes")
```

### Device Lifecycle

```python
# Provision new device
result = await service.provision_device(
    device_id="router-001",
    hostname="edge-router-01",
    device_type="router",
    site_id="branch-office-1",
    vendor="Cisco",
    model="ISR4331",
    interfaces=[
        {"name": "GigabitEthernet0/0/0", "type": "ethernet"},
        {"name": "GigabitEthernet0/0/1", "type": "ethernet"}
    ]
)

# Deploy device
deployment = await service.deploy_device(
    device_id="router-001",
    interface_macs={
        "GigabitEthernet0/0/0": "00:1a:2b:3c:4d:5e",
        "GigabitEthernet0/0/1": "00:1a:2b:3c:4d:5f"
    },
    connections=[
        {
            "target_device": "switch-001",
            "source_port": "GigabitEthernet0/0/0",
            "target_port": "GigabitEthernet1/0/1"
        }
    ]
)
```

## Architecture

### Core Models

The framework uses SQLAlchemy ORM models for persistence:

- `Device` - Main device inventory with hardware details
- `DeviceInterface` - Network interfaces with stable port IDs (`{device_id}:{interface_name}`)
- `DeviceModule` - Hardware modules and cards
- `MacAddress` - MAC address registry with OUI vendor lookup
- `NetworkNode` - Topology nodes for graph management
- `NetworkLink` - Network connections between nodes
- `MonitoringRecord` - SNMP/telemetry metrics storage

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   DeviceService │    │ Platform        │    │ SNMP/Topology  │
│   (Unified API) │◄───┤ Adapters        │    │ Utilities       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Inventory       │    │ Monitoring      │    │ Lifecycle       │
│ Service         │    │ Service         │    │ Manager         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ MAC Registry    │    │ Network         │    │ SQLAlchemy      │
│ Service         │    │ Topology Svc    │    │ Models          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Integration

### ISP Framework Integration

```python
from dotmac_device_management.adapters import ISPDeviceAdapter

# Create adapter
adapter = ISPDeviceAdapter(session, tenant_id)

# Import device from ISP framework
isp_device_data = {
    "device_id": "ont-customer-123",
    "hostname": "customer-ont-123",
    "device_type": "ont",
    "customer_id": "cust_123",
    "service_tier": "residential_100mb"
}

device = await adapter.create_device_from_platform(isp_device_data)
```

### Management Platform Integration

```python
from dotmac_device_management.adapters import ManagementDeviceAdapter

# Create adapter
adapter = ManagementDeviceAdapter(session, tenant_id)

# Export device to management platform
mgmt_data = await adapter.sync_device_to_platform("switch-001")
```

## Advanced Features

### SNMP Monitoring

```python
from dotmac_device_management.utils import SNMPClient, SNMPConfig, SNMPCollector

# Configure SNMP client
config = SNMPConfig(
    host="192.168.1.10",
    community="public",
    version="2c"
)

client = SNMPClient(config)
collector = SNMPCollector(client)

# Collect comprehensive metrics
metrics = await collector.collect_comprehensive_metrics()
```

### Topology Analysis

```python
from dotmac_device_management.utils import TopologyAnalyzer

analyzer = TopologyAnalyzer()

# Build graph from nodes and links
analyzer.build_graph(nodes_data, links_data)

# Analyze redundancy for critical devices
redundancy = analyzer.analyze_redundancy(["core-switch-01", "core-switch-02"])

# Generate comprehensive report
report = analyzer.generate_topology_report()
```

### Workflow Automation

```python
from dotmac_device_management.workflows import DeviceLifecycleManager

lifecycle = DeviceLifecycleManager(session, tenant_id)

# Execute maintenance workflow
maintenance = await lifecycle.execute_lifecycle_action(
    device_id="switch-001",
    action="maintain",
    parameters={
        "maintenance_type": "firmware_update",
        "tasks": [
            {"type": "config_backup"},
            {"type": "firmware_update", "version": "15.2.7"},
            {"type": "health_check"}
        ]
    }
)
```

## Configuration

### Database Setup

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotmac_device_management.core.models import Base

# Create database engine
engine = create_engine("postgresql://user:pass@localhost/devices")

# Create tables
Base.metadata.create_all(engine)

# Create session factory
SessionLocal = sessionmaker(bind=engine)
```

### Environment Variables

- `DEVICE_MGMT_DB_URL` - Database connection URL
- `DEVICE_MGMT_SNMP_TIMEOUT` - Default SNMP timeout (seconds)
- `DEVICE_MGMT_MONITORING_INTERVAL` - Default monitoring interval (seconds)
- `DEVICE_MGMT_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## Testing

```bash
# Install development dependencies
pip install dotmac-device-management[dev]

# Run tests
pytest

# Run with coverage
pytest --cov=dotmac_device_management --cov-report=html

# Run specific test categories
pytest -m "unit"  # Unit tests only
pytest -m "integration"  # Integration tests only
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Documentation: <https://docs.dotmac.com/device-management>
- Issues: <https://github.com/dotmac/device-management/issues>
- Discussions: <https://github.com/dotmac/device-management/discussions>
