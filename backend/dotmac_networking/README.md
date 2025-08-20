# DotMac Networking SDKs

Minimal, reusable SDKs for ISP networking plane operations. This package provides composable SDKs for managing networking resources, identity & access, configuration & execution, and monitoring & assurance in ISP environments.

## Features

### Resource & Topology Management
- **Device Inventory**: Manage devices, modules, and interfaces with stable port IDs
- **Site/POP Management**: Organize sites, racks, and rooms
- **IPAM**: IP address allocation, reservation, and conflict detection
- **VLAN Management**: VLAN creation, assignment, and auto-assignment
- **MAC Registry**: MAC address normalization and vendor lookup
- **Network Topology**: Graph-based network topology with path finding

### Identity & Access
- **RADIUS Server Management**: FreeRADIUS configuration and policy management
- **RADIUS AAA**: Authentication, authorization, accounting, and CoA
- **NAS Management**: BNG/BRAS endpoint and session management
- **OLT/ONU**: Optical network device management
- **TR-069 CWMP**: CPE device management via TR-069 protocol

### Configuration & Execution
- **Device Configuration**: Template-based config management with drift detection
- **Network Automation**: Ansible, NETCONF, and SSH automation adapters
- **Device Provisioning**: Orchestrated thin provisioning workflows

### Monitoring & Assurance
- **Device Monitoring**: SNMP/telemetry collection and health checks
- **Alarm & Events**: SNMP trap and syslog processing with alarm management
- **Service Assurance**: ICMP/DNS/HTTP probes with SLA monitoring
- **Flow Analytics**: NetFlow/sFlow/IPFIX ingestion and traffic analysis

## Installation

```bash
pip install dotmac-networking
```

For development:
```bash
pip install dotmac-networking[dev]
```

## Quick Start

```python
import asyncio
from dotmac_networking import (
    DeviceInventorySDK,
    IPAMSDK,
    VLANSDK,
    DeviceMonitoringSDK
)

async def main():
    tenant_id = "isp-tenant-1"
    
    # Initialize SDKs
    device_sdk = DeviceInventorySDK(tenant_id)
    ipam_sdk = IPAMSDK(tenant_id)
    vlan_sdk = VLANSDK(tenant_id)
    monitoring_sdk = DeviceMonitoringSDK(tenant_id)
    
    # Register a device
    device = await device_sdk.register_device(
        device_id="sw-core-01",
        device_type="switch",
        vendor="Cisco",
        model="Catalyst 9300",
        site_id="pop-downtown"
    )
    
    # Create IP network
    network = await ipam_sdk.create_network(
        network="192.168.1.0/24",
        name="management-network",
        vrf="default"
    )
    
    # Allocate IP address
    allocation = await ipam_sdk.allocate_ip(
        network_id=network["network_id"],
        purpose="device-mgmt",
        device_id="sw-core-01"
    )
    
    # Create VLAN
    vlan = await vlan_sdk.create_vlan(
        vlan_id=100,
        name="management",
        site_id="pop-downtown"
    )
    
    # Start monitoring
    monitor = await monitoring_sdk.create_snmp_monitor(
        device_id="sw-core-01",
        community="public",
        oids=["1.3.6.1.2.1.1.3.0"]  # sysUpTime
    )
    
    print(f"Device: {device['device_id']}")
    print(f"IP: {allocation['ip_address']}")
    print(f"VLAN: {vlan['vlan_id']}")
    print(f"Monitor: {monitor['monitor_id']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

Configure via environment variables:

```bash
# Database
DOTMAC_DB_HOST=localhost
DOTMAC_DB_PORT=5432
DOTMAC_DB_NAME=dotmac_networking
DOTMAC_DB_USER=dotmac
DOTMAC_DB_PASSWORD=secret

# Cache
DOTMAC_CACHE_TYPE=redis
DOTMAC_CACHE_HOST=localhost
DOTMAC_CACHE_PORT=6379

# IPAM
DOTMAC_IPAM_DEFAULT_VRF=default
DOTMAC_IPAM_ENABLE_IPV6=true

# VLAN
DOTMAC_VLAN_RANGE_START=100
DOTMAC_VLAN_RANGE_END=4094

# RADIUS
DOTMAC_RADIUS_SERVER_HOST=localhost
DOTMAC_RADIUS_SERVER_PORT=1812
DOTMAC_RADIUS_SECRET=radiussecret

# Monitoring
DOTMAC_MONITORING_SCRAPE_INTERVAL=30
DOTMAC_MONITORING_RETENTION_DAYS=30
```

## Architecture

The package follows a modular, composable design:

- **Core**: Configuration management and custom exceptions
- **SDKs**: Small, focused SDKs for specific networking domains
- **Services**: In-memory service implementations for rapid prototyping
- **Multi-tenant**: All SDKs require `tenant_id` for isolation

## SDK Categories

### Primitives
Core networking resource management SDKs that form the foundation.

### DDI + RADIUS
DNS, DHCP, IPAM integration with RADIUS authentication services.

### Config & Automation
Configuration management and network automation capabilities.

### Monitoring
Device monitoring, alarm processing, service assurance, and flow analytics.

### Access Technologies
Specialized SDKs for access network technologies like PON and TR-069.

## Development

```bash
# Clone repository
git clone https://github.com/dotmac/dotmac-networking.git
cd dotmac-networking

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Format code
black dotmac_networking/
isort dotmac_networking/

# Type checking
mypy dotmac_networking/
```

## Examples

See the `examples/` directory for complete usage examples:

- `basic_provisioning.py` - Device provisioning workflow
- `radius_integration.py` - RADIUS authentication setup
- `monitoring_setup.py` - Comprehensive monitoring configuration
- `flow_analytics.py` - Traffic analysis and reporting

## Integration

### External Dependencies

- **Kea DHCP**: DHCP server integration
- **PowerDNS**: DNS server management
- **FreeRADIUS**: RADIUS server configuration
- **Ansible Runner/AWX**: Network automation
- **SNMP/Telemetry**: Device monitoring
- **Vendor APIs**: Device-specific integrations

### Event Integration

SDKs support event publishing for integration with event-driven architectures:

```python
# Event topics
DEVICE_REGISTERED = "networking.device.registered"
IP_ALLOCATED = "networking.ipam.allocated"
ALARM_RAISED = "networking.alarm.raised"
CONFIG_APPLIED = "networking.config.applied"
```

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://docs.dotmac.com/networking
- Issues: https://github.com/dotmac/dotmac-networking/issues
- Email: support@dotmac.com

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

Please ensure all tests pass and code follows the project style guidelines.
