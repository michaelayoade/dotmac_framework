# DotMac Network Automation Toolkit

A comprehensive Python package for network automation, providing unified management of RADIUS servers, VOLTHA fiber networks, SSH device provisioning, and network monitoring.

## Features

### 🔐 RADIUS Server Management

- Complete RADIUS server implementation (Authentication, Authorization, Accounting)
- Change of Authorization (CoA) support
- Session management and tracking
- Client/NAS management
- Multi-protocol support (PAP, CHAP, EAP)

### 🌐 VOLTHA Integration

- Fiber network management through VOLTHA
- OLT (Optical Line Terminal) provisioning
- ONU (Optical Network Unit) management
- Flow configuration and management
- gRPC-based communication

### 🖥️ SSH Automation

- Paramiko-based SSH connections
- Device provisioning templates
- Connection pooling and reuse
- Command execution with retries
- TextFSM output parsing

### 📊 Network Monitoring

- Real-time device health checks
- SNMP metrics collection
- Alert management system
- Performance monitoring
- Historical data retention

## Installation

```bash
# Install from the DotMac Framework workspace
cd /home/dotmac_framework
poetry install

# Or install the package directly
pip install dotmac-network-automation
```

## Quick Start

### RADIUS Server

```python
from dotmac_network import RADIUSManager, RADIUSServerConfig, RADIUSClient, RADIUSUser

# Configure RADIUS server
config = RADIUSServerConfig(
    auth_port=1812,
    acct_port=1813,
    bind_address="0.0.0.0"
)

# Create and start RADIUS manager
radius_manager = RADIUSManager(config)

# Add RADIUS client (NAS)
client = RADIUSClient(
    name="switch01",
    ip_address="192.168.1.10",
    shared_secret="secret123"
)
radius_manager.add_client(client)

# Add RADIUS user
user = RADIUSUser(
    username="john.doe",
    password="userpass123",
    groups=["network_users"]
)
radius_manager.add_user(user)

# Start server
await radius_manager.start()
```

### VOLTHA Integration

```python
from dotmac_network import VOLTHAManager, VOLTHAConfig

# Configure VOLTHA connection
config = VOLTHAConfig(
    core_endpoint="localhost:50057",
    enable_tls=False
)

# Create VOLTHA manager
voltha_manager = VOLTHAManager(config)

# Connect to VOLTHA
await voltha_manager.connect()

# Create OLT device
olt_config = {
    "type": "openolt",
    "host_and_port": "192.168.1.100:9191",
    "device_type": "openolt"
}
response = await voltha_manager.create_olt(olt_config)

# Enable device
if response.success:
    await voltha_manager.enable_device(response.data.id)
```

### SSH Automation

```python
from dotmac_network import SSHAutomation, DeviceCredentials, SSHCommand

# Create SSH automation instance
ssh = SSHAutomation()

# Set up credentials
credentials = DeviceCredentials(
    username="admin",
    password="admin123"
)

# Connect to device
connection = await ssh.connect(
    host="192.168.1.50",
    credentials=credentials
)

# Execute commands
command = SSHCommand(
    command="show version",
    timeout=30
)
response = await ssh.execute_command(connection.connection_id, command)

if response.success:
    print(response.output)
```

### Network Monitoring

```python
from dotmac_network import NetworkMonitor, MonitoringConfig, MonitoringTarget, HealthCheck

# Configure monitoring
config = MonitoringConfig(
    check_interval=60,
    enable_alerting=True,
    enable_metrics=True
)

# Create network monitor
monitor = NetworkMonitor(config)

# Add monitoring target
target = MonitoringTarget(
    id="router01",
    name="Core Router 01",
    host="192.168.1.1",
    device_type="router"
)
monitor.add_target(target)

# Add health check
health_check = HealthCheck(
    name="ping_check",
    check_type=CheckType.PING,
    target="192.168.1.1",
    interval=30
)
monitor.add_health_check(health_check)

# Start monitoring
await monitor.start()
```

## Architecture

The package is organized into four main modules:

```
dotmac_network/
├── radius/           # RADIUS server components
│   ├── manager.py    # Main RADIUS orchestrator
│   ├── auth.py       # Authentication handler
│   ├── accounting.py # Accounting processor
│   ├── session.py    # Session management
│   ├── coa.py        # Change of Authorization
│   └── types.py      # Data structures
├── voltha/           # VOLTHA integration
│   ├── manager.py    # VOLTHA orchestrator
│   ├── olt.py        # OLT management
│   ├── onu.py        # ONU management
│   └── types.py      # VOLTHA data structures
├── ssh/              # SSH automation
│   ├── automation.py # SSH engine
│   ├── provisioner.py# Device provisioning
│   ├── pool.py       # Connection pooling
│   └── types.py      # SSH data structures
└── monitoring/       # Network monitoring
    ├── monitor.py    # Main monitoring system
    ├── health.py     # Health checking
    ├── snmp.py       # SNMP collector
    └── types.py      # Monitoring data structures
```

## Configuration

### RADIUS Server Configuration

```python
config = RADIUSServerConfig(
    auth_port=1812,          # Authentication port
    acct_port=1813,          # Accounting port
    coa_port=3799,           # CoA port
    bind_address="0.0.0.0",  # Bind address
    max_packet_size=4096,    # Max RADIUS packet size
    timeout=5,               # Request timeout
    retries=3,               # Retry count
    enable_coa=True,         # Enable CoA
    enable_accounting=True,   # Enable accounting
    log_level="INFO"         # Logging level
)
```

### VOLTHA Configuration

```python
config = VOLTHAConfig(
    core_endpoint="localhost:50057",     # VOLTHA core gRPC endpoint
    ofagent_endpoint="localhost:6653",   # OpenFlow agent endpoint
    kafka_endpoint="localhost:9092",     # Kafka endpoint
    etcd_endpoint="localhost:2379",      # etcd endpoint
    timeout=30,                          # Operation timeout
    retry_count=3,                       # Retry count
    enable_tls=False,                    # Enable TLS
    log_level="INFO"                     # Logging level
)
```

### SSH Configuration

```python
config = SSHConnectionConfig(
    host="192.168.1.10",    # Target host
    port=22,                # SSH port
    timeout=30,             # Connection timeout
    keepalive=60,           # Keepalive interval
    max_retries=3,          # Maximum retries
    retry_delay=5,          # Delay between retries
    use_agent=True,         # Use SSH agent
    compression=True        # Enable compression
)
```

### Monitoring Configuration

```python
config = MonitoringConfig(
    check_interval=60,           # Health check interval
    alert_check_interval=30,     # Alert evaluation interval
    metric_retention=86400,      # Metric retention (24h)
    max_concurrent_checks=50,    # Max concurrent checks
    enable_alerting=True,        # Enable alerting
    enable_metrics=True,         # Enable metrics
    enable_health_checks=True,   # Enable health checks
    log_level="INFO"            # Logging level
)
```

## Advanced Usage

### Device Provisioning with Templates

```python
from dotmac_network import DeviceProvisioner, ProvisioningTemplate, ProvisioningStep, SSHCommand

# Create provisioning template
template = ProvisioningTemplate(
    name="cisco_switch_base",
    device_type=DeviceType.SWITCH,
    description="Base configuration for Cisco switches"
)

# Add configuration steps
steps = [
    ProvisioningStep(
        name="set_hostname",
        command=SSHCommand(command="hostname {{ hostname }}"),
        required=True
    ),
    ProvisioningStep(
        name="configure_management",
        command=SSHCommand(command="interface vlan{{ mgmt_vlan }}\nip address {{ mgmt_ip }} {{ mgmt_mask }}"),
        required=True
    )
]

for step in steps:
    template.add_step(step)

# Create provisioner
provisioner = DeviceProvisioner()

# Provision device
job = await provisioner.provision_device(
    device_config=device_config,
    template=template,
    variables={
        "hostname": "switch01",
        "mgmt_vlan": "100",
        "mgmt_ip": "192.168.100.10",
        "mgmt_mask": "255.255.255.0"
    }
)
```

### Custom Alert Rules

```python
from dotmac_network import AlertRule, AlertSeverity

# Create custom alert rule
rule = AlertRule(
    name="high_cpu_usage",
    description="Alert when CPU usage exceeds 80%",
    condition="cpu_utilization > 80",
    severity=AlertSeverity.WARNING,
    evaluation_interval=60,
    evaluation_window=300,
    notification_channels=["email", "slack"]
)

monitor.add_alert_rule(rule)
```

### SNMP Metrics Collection

```python
from dotmac_network import SNMPCollector, SNMPConfig

# Configure SNMP
snmp_config = SNMPConfig(
    community="public",
    version="2c",
    port=161,
    timeout=5
)

# Collect metrics
collector = SNMPCollector(snmp_config)
metrics = await collector.collect_device_metrics("192.168.1.1")

print(f"CPU Usage: {metrics.cpu_utilization}%")
print(f"Memory Usage: {metrics.memory_utilization}%")
```

## Integration Examples

### ISP Framework Integration

```python
# This package integrates seamlessly with the DotMac ISP Framework
from dotmac_isp.modules.network_integration import NetworkIntegrationService
from dotmac_network import RADIUSManager, VOLTHAManager

class ISPNetworkService(NetworkIntegrationService):
    def __init__(self):
        self.radius_manager = RADIUSManager(radius_config)
        self.voltha_manager = VOLTHAManager(voltha_config)

    async def provision_customer(self, customer_data):
        # Create RADIUS user for customer
        radius_user = RADIUSUser(
            username=customer_data.username,
            password=customer_data.password
        )
        self.radius_manager.add_user(radius_user)

        # Provision ONU for fiber customers
        if customer_data.service_type == "fiber":
            onu_config = {
                "serial_number": customer_data.ont_serial,
                "olt_device_id": customer_data.olt_id
            }
            await self.voltha_manager.create_onu(onu_config)
```

### Kubernetes Deployment

```yaml
# radius-server.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotmac-radius-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: dotmac-radius-server
  template:
    metadata:
      labels:
        app: dotmac-radius-server
    spec:
      containers:
      - name: radius-server
        image: dotmac/network-automation:latest
        ports:
        - containerPort: 1812
          protocol: UDP
        - containerPort: 1813
          protocol: UDP
        env:
        - name: RADIUS_AUTH_PORT
          value: "1812"
        - name: RADIUS_ACCT_PORT
          value: "1813"
```

## Testing

```bash
# Run tests
poetry run pytest tests/

# Run with coverage
poetry run pytest tests/ --cov=dotmac_network --cov-report=html

# Run specific test module
poetry run pytest tests/test_radius.py -v
```

## Performance Considerations

- **RADIUS Server**: Can handle 1000+ authentication requests per second
- **SSH Connections**: Connection pooling reduces latency for repeated operations
- **VOLTHA Integration**: Async gRPC calls prevent blocking
- **Monitoring**: Configurable check intervals to balance accuracy vs load

## Security Features

- **RADIUS**: MD5 packet authentication, shared secrets
- **SSH**: Public key authentication, connection encryption
- **VOLTHA**: Optional TLS encryption for gRPC communications
- **Monitoring**: Secure SNMP v3 support

## Logging

All components support structured logging with configurable levels:

```python
import logging
import structlog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

# Component-specific loggers
radius_logger = structlog.get_logger("dotmac_network.radius")
voltha_logger = structlog.get_logger("dotmac_network.voltha")
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is part of the DotMac Framework and follows the same licensing terms.

## Support

For issues and questions:

- Create an issue in the DotMac Framework repository
- Check the documentation in `/docs/`
- Review example code in `/examples/`
