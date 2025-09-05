# DotMac Networking

Comprehensive ISP networking package providing IP address management, device automation, SNMP monitoring, RADIUS authentication, and advanced network protocols.

## 🚀 Features

### 🌐 **IP Address Management (IPAM)**
- Automatic IP allocation and subnet management
- DHCP range planning and validation  
- DNS integration with PTR record management
- Network topology discovery and visualization
- Conflict detection and resolution

### 🔧 **Network Device Automation** 
- SSH-based device provisioning and configuration
- Bulk configuration deployment with rollback support
- Device inventory and lifecycle management
- Template-based configuration with Jinja2
- Multi-vendor support (Cisco, Juniper, Mikrotik)

### 📊 **SNMP Monitoring & Telemetry**
- Real-time device performance monitoring
- Interface statistics and utilization tracking
- Comprehensive SNMP OID library for major vendors
- Automated alerting with configurable thresholds
- Historical data collection and trending

### 🔐 **RADIUS Authentication**
- Centralized network authentication and authorization
- Change of Authorization (CoA) and disconnect support
- Session management and accounting integration
- Customer billing system integration
- Multi-realm support

### 🚀 **Advanced Protocols**
- VOLTHA (Virtual OLT Hardware Abstraction) integration
- Fiber network management and ONU provisioning
- Network topology mapping and discovery
- Protocol abstraction for multi-vendor environments

## 📦 Installation

```bash
pip install dotmac-networking

# With optional VOLTHA support
pip install dotmac-networking[voltha]

# All optional features
pip install dotmac-networking[all]
```

## 🏗️ Quick Start

### IPAM - IP Management
```python
from dotmac.networking import IPAMService, NetworkingService

# Create networking service
networking = NetworkingService()

# Allocate a subnet for a customer
subnet = await networking.ipam.allocate_subnet(
    network="192.168.0.0/24",
    customer_id="cust_123",
    purpose="customer_lan"
)

# Allocate IP for device
ip = await networking.ipam.allocate_ip(
    subnet_id=subnet.id,
    device_mac="aa:bb:cc:dd:ee:ff",
    hostname="customer-router"
)

print(f"Allocated IP: {ip.address}")
```

### Device Automation
```python
from dotmac.networking import DeviceManager

device_manager = DeviceManager()

# Configure customer router
result = await device_manager.configure_device(
    host="192.168.1.1",
    template="customer_router_basic",
    variables={
        "customer_vlan": 100,
        "bandwidth_limit": "100M",
        "customer_name": "John Doe"
    }
)

if result.success:
    print("Device configured successfully")
```

### SNMP Monitoring
```python
from dotmac.networking import NetworkMonitor, MonitoringTarget

monitor = NetworkMonitor()

# Add device to monitoring
target = MonitoringTarget(
    host="192.168.1.1",
    name="Customer Router",
    device_type="cisco",
    snmp_community="public"
)
monitor.add_target(target)

# Start monitoring
await monitor.start_monitoring(interval=60)

# Get device status
status = await monitor.get_device_status("192.168.1.1")
print(f"Device status: {status}")
```

### RADIUS Authentication
```python
from dotmac.networking import RADIUSServer, AuthManager

auth = AuthManager()

# Authenticate customer
result = await auth.authenticate_user(
    username="customer@isp.com",
    password="secret",
    nas_ip="192.168.1.1"
)

if result.success:
    # Send CoA to update session
    await auth.send_coa_update(
        session_id=result.session_id,
        attributes={"Mikrotik-Rate-Limit": "10M/10M"}
    )
```

## 🏗️ Architecture

Built with DRY principles using `dotmac-core` foundation:

```
dotmac-networking/
├── ipam/              # IP Address Management
│   ├── services/      # IPAM business logic
│   ├── repositories/  # Data access layer  
│   └── models/        # Domain models
├── automation/        # Device Automation
│   ├── ssh/          # SSH provisioning
│   ├── templates/    # Configuration templates
│   └── inventory/    # Device management
├── monitoring/        # SNMP Monitoring
│   ├── collectors/   # SNMP data collection
│   ├── alerts/       # Alerting system
│   └── storage/      # Metrics storage
├── radius/           # RADIUS Authentication
│   ├── server/       # RADIUS protocol
│   ├── auth/         # Authentication logic
│   └── accounting/   # Session accounting
└── protocols/        # Advanced Protocols
    ├── voltha/       # VOLTHA integration
    └── discovery/    # Topology discovery
```

## 🔧 Configuration

```python
from dotmac.networking import NetworkingService

config = {
    "ipam": {
        "default_subnet_size": 24,
        "dhcp_lease_time": 86400,
        "enable_ptr_records": True,
    },
    "automation": {
        "ssh_timeout": 30,
        "config_backup_enabled": True,
        "rollback_on_failure": True,
    },
    "monitoring": {
        "snmp_timeout": 10,
        "collection_interval": 60,
        "alert_thresholds": {
            "cpu_utilization": 80,
            "memory_utilization": 85,
        }
    },
    "radius": {
        "auth_port": 1812,
        "acct_port": 1813,
        "session_timeout": 3600,
    }
}

networking = NetworkingService(config)
```

## 🏢 Production Features

- ✅ **Multi-vendor Support**: Cisco, Juniper, Mikrotik, generic SNMP
- ✅ **High Availability**: Connection pooling, automatic failover
- ✅ **Scalability**: Async operations, concurrent device management
- ✅ **Security**: Encrypted credentials, audit logging, RBAC
- ✅ **Monitoring**: Built-in health checks and performance metrics
- ✅ **Integration**: REST APIs, webhook notifications, event streaming

## 📊 Monitoring & Observability

Integrates with observability stack:
- Prometheus metrics export
- Structured logging with correlation IDs
- Distributed tracing support
- Health check endpoints
- Performance monitoring

## 🔒 Security

- Encrypted credential storage
- Audit logging for all operations
- Role-based access control (RBAC)
- Network security best practices
- Compliance reporting

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=dotmac.networking

# Integration tests (requires test infrastructure)
pytest tests/integration/
```

## 📚 Documentation

- [API Reference](docs/api.md)
- [Configuration Guide](docs/configuration.md)
- [Device Support Matrix](docs/devices.md)
- [SNMP OID Reference](docs/snmp-oids.md)
- [RADIUS Integration](docs/radius.md)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.