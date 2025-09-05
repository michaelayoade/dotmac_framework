"""
DotMac Networking - Comprehensive ISP Network Management

This package provides complete networking infrastructure for ISP operations:

🌐 **IP Address Management (IPAM)**
  - Automatic IP allocation and subnet management
  - DHCP range planning and validation
  - DNS integration and PTR record management
  - Network topology discovery and visualization

🔧 **Network Device Automation**
  - SSH-based device provisioning and configuration
  - Bulk configuration deployment and rollback
  - Device inventory and lifecycle management
  - Configuration templates and validation

📊 **SNMP Monitoring & Telemetry**
  - Real-time device performance monitoring
  - Interface statistics and utilization tracking
  - Comprehensive SNMP OID library (Cisco, Juniper, etc.)
  - Automated alert generation and thresholds

🔐 **RADIUS Authentication**
  - Centralized network authentication
  - Change of Authorization (CoA) support
  - Session management and accounting
  - Integration with customer billing systems

🚀 **Advanced Protocols**
  - VOLTHA (Virtual OLT Hardware Abstraction) support
  - Fiber network management and provisioning
  - Network topology mapping and discovery
  - Protocol abstraction for multi-vendor environments

## Quick Start

### IPAM - IP Address Management
```python
from dotmac.networking.ipam import IPAMService, SubnetPlanner

ipam = IPAMService()
subnet = await ipam.allocate_subnet("192.168.0.0/24", customer_id="cust_123")
ip = await ipam.allocate_ip(subnet.id, device_mac="aa:bb:cc:dd:ee:ff")
```

### Device Automation
```python
from dotmac.networking.automation import DeviceManager, SSHProvisioner

provisioner = SSHProvisioner()
result = await provisioner.configure_device(
    host="192.168.1.1",
    template="customer_router",
    variables={"customer_vlan": 100, "bandwidth_limit": "100M"}
)
```

### SNMP Monitoring
```python
from dotmac.networking.monitoring import SNMPCollector, NetworkMonitor

collector = SNMPCollector()
metrics = await collector.collect_interface_stats("192.168.1.1")
# Get CPU, memory, interface utilization
```

### RADIUS Authentication
```python
from dotmac.networking.radius import RADIUSServer, AuthManager

auth = AuthManager()
result = await auth.authenticate_user("customer@isp.com", "password")
await auth.send_coa_disconnect(session_id="sess_123")
```

## Architecture

Built on DRY principles with shared `dotmac-core` utilities:
- Unified logging and error handling
- Common configuration management
- Standardized retry and rate limiting
- Consistent authentication patterns

## Production Features

- ✅ **Multi-vendor support**: Cisco, Juniper, Mikrotik, generic SNMP
- ✅ **Scalability**: Async operations, connection pooling
- ✅ **Reliability**: Automatic retry, circuit breakers, health checks
- ✅ **Security**: Encrypted credentials, audit logging, access control
- ✅ **Integration**: REST APIs, webhook notifications, event streaming
"""
from typing import Optional

try:
    from .ipam import (
        DHCPManager,
        DNSManager,
        IPAllocationManager,
        IPAMService,
        NetworkPlanner,
        SubnetManager,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"IPAM not available: {e}")
    IPAMService = SubnetManager = IPAllocationManager = None
    DHCPManager = DNSManager = NetworkPlanner = None

# Device Automation
try:
    from .automation import (
        ConfigurationManager,
        DeviceInventory,
        DeviceManager,
        SSHProvisioner,
        TemplateEngine,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"Device automation not available: {e}")
    DeviceManager = SSHProvisioner = ConfigurationManager = None
    DeviceInventory = TemplateEngine = None

# SNMP Monitoring
try:
    from .monitoring import (
        DeviceHealthMonitor,
        InterfaceMonitor,
        MetricsCollector,
        NetworkMonitor,
        SNMPCollector,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"SNMP monitoring not available: {e}")
    SNMPCollector = NetworkMonitor = InterfaceMonitor = None
    DeviceHealthMonitor = MetricsCollector = None

# RADIUS Authentication
try:
    from .radius import (
        AccountingManager,
        AuthManager,
        CoAManager,
        RADIUSServer,
        SessionManager,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"RADIUS not available: {e}")
    RADIUSServer = AuthManager = SessionManager = None
    AccountingManager = CoAManager = None

# Advanced Protocols
try:
    from .protocols import (
        FiberManager,
        ProtocolAdapter,
        TopologyDiscovery,
        VOLTHAManager,
    )
except ImportError as e:
    import warnings

    warnings.warn(f"Advanced protocols not available: {e}")
    VOLTHAManager = FiberManager = TopologyDiscovery = None
    ProtocolAdapter = None

__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

__all__ = [
    # IPAM
    "IPAMService",
    "SubnetManager",
    "IPAllocationManager",
    "DHCPManager",
    "DNSManager",
    "NetworkPlanner",
    # Device Automation
    "DeviceManager",
    "SSHProvisioner",
    "ConfigurationManager",
    "DeviceInventory",
    "TemplateEngine",
    # SNMP Monitoring
    "SNMPCollector",
    "NetworkMonitor",
    "InterfaceMonitor",
    "DeviceHealthMonitor",
    "MetricsCollector",
    # RADIUS
    "RADIUSServer",
    "AuthManager",
    "SessionManager",
    "AccountingManager",
    "CoAManager",
    # Advanced Protocols
    "VOLTHAManager",
    "FiberManager",
    "TopologyDiscovery",
    "ProtocolAdapter",
    # Version
    "__version__",
]

# Configuration defaults for ISP networking
DEFAULT_CONFIG = {
    "ipam": {
        "default_subnet_size": 24,
        "dhcp_lease_time": 86400,  # 24 hours
        "dns_ttl": 300,  # 5 minutes
        "enable_ptr_records": True,
        "conflict_detection": True,
    },
    "automation": {
        "ssh_timeout": 30,
        "config_backup_enabled": True,
        "rollback_on_failure": True,
        "concurrent_operations": 10,
        "retry_attempts": 3,
    },
    "monitoring": {
        "snmp_timeout": 10,
        "collection_interval": 60,  # seconds
        "alert_thresholds": {
            "cpu_utilization": 80,
            "memory_utilization": 85,
            "interface_utilization": 90,
        },
        "community": "public",
    },
    "radius": {
        "auth_port": 1812,
        "acct_port": 1813,
        "coa_port": 3799,
        "session_timeout": 3600,  # 1 hour
        "enable_accounting": True,
    },
}


def get_default_config():
    """Get default networking configuration."""
    return DEFAULT_CONFIG.copy()


class NetworkingService:
    """Unified networking service providing IPAM, automation, monitoring, and RADIUS."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or get_default_config()
        self._ipam = None
        self._automation = None
        self._monitoring = None
        self._radius = None

    @property
    def ipam(self):
        """Get IPAM service."""
        if self._ipam is None and IPAMService:
            self._ipam = IPAMService(self.config.get("ipam", {}))
        return self._ipam

    @property
    def automation(self):
        """Get device automation service."""
        if self._automation is None and DeviceManager:
            self._automation = DeviceManager(self.config.get("automation", {}))
        return self._automation

    @property
    def monitoring(self):
        """Get SNMP monitoring service."""
        if self._monitoring is None and NetworkMonitor:
            self._monitoring = NetworkMonitor(self.config.get("monitoring", {}))
        return self._monitoring

    @property
    def radius(self):
        """Get RADIUS service."""
        if self._radius is None and RADIUSServer:
            self._radius = RADIUSServer(self.config.get("radius", {}))
        return self._radius


def create_networking_service(config: Optional[dict] = None) -> NetworkingService:
    """Create a configured networking service."""
    return NetworkingService(config)
