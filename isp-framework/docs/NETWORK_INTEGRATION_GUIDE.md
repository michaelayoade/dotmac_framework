# Network Integration Guide for DotMac ISP Framework

## Overview

The DotMac ISP Framework provides comprehensive network integration capabilities designed specifically for Internet Service Providers. This guide covers the complete network operations platform that enables ISPs to manage their entire network infrastructure through a single, integrated system with complete geographic visualization and automation capabilities.

## Architecture Overview

The network integration system is built around several core modules:

### 1. Network Integration Module (`dotmac_isp.modules.network_integration`)
- **Network Device Management**: Complete lifecycle management for routers, switches, access points, and other network equipment
- **Interface Monitoring**: Real-time monitoring of network interfaces with traffic statistics and performance metrics
- **Location Management**: Geographic location tracking for all network infrastructure
- **Topology Discovery**: Automatic discovery and mapping of network connections
- **Configuration Management**: Version control and deployment of device configurations
- **Alert Management**: Intelligent alerting system with customizable rules and notifications

### 2. Ansible Integration (`dotmac_isp.integrations.ansible`)
- **Playbook Management**: Create, manage, and execute Ansible playbooks for network automation
- **Device Provisioning**: Automated setup and configuration of new network devices
- **Configuration Deployment**: Standardized deployment of device configurations
- **Inventory Management**: Dynamic inventory generation from network database
- **Automation Workflows**: Scheduled and event-driven automation tasks

### 3. VOLTHA GPON Integration (`dotmac_isp.integrations.voltha`)
- **OLT Management**: Complete management of Optical Line Terminals
- **ONU Provisioning**: Automatic discovery and provisioning of Optical Network Units
- **Service Provisioning**: GPON service activation and management
- **Performance Monitoring**: Real-time GPON network performance monitoring
- **Fault Management**: Automated fault detection and resolution

### 4. FreeRADIUS AAA Integration (`dotmac_isp.integrations.freeradius`)
- **Customer Authentication**: ISP customer login validation and session management
- **Device Authentication**: Network device access control
- **Accounting Records**: Usage tracking for billing integration
- **Policy Enforcement**: Dynamic bandwidth and access control policies

### 5. GIS Location System (`dotmac_isp.modules.gis`)
- **Device Location Tracking**: GPS coordinates for all network equipment
- **Fiber Network Mapping**: Complete fiber infrastructure visualization
- **Service Coverage Maps**: Real-time service area visualization
- **Field Operations**: GPS-enabled technician dispatch and routing

### 6. Network Monitoring (`dotmac_isp.modules.network_monitoring`)
- **SNMP Monitoring**: Real-time device health and performance metrics
- **Alerting System**: Customizable alert rules and escalation
- **Performance Analytics**: Historical analysis and capacity planning
- **Dashboard Visualization**: Network operations center (NOC) dashboards

### 7. Network Visualization (`dotmac_isp.modules.network_visualization`)
- **Topology Visualization**: Interactive network topology diagrams
- **Geographic Mapping**: Network infrastructure on interactive maps
- **Real-time Dashboards**: Live network status and performance visualization
- **Custom Dashboards**: Configurable dashboards for different roles

## Key Features

### Multi-Vendor Network Support
- **Cisco**: Full support for Cisco IOS/IOS-XE devices via SNMP and CLI
- **Juniper**: JunOS device management and monitoring
- **MikroTik**: RouterOS integration for wireless and routing equipment
- **Huawei**: Support for Huawei networking equipment
- **ZTE**: GPON and access equipment support
- **Generic SNMP**: Universal SNMP monitoring for any SNMP-capable device

### Protocol Support
- **SNMP v1/v2c/v3**: Complete SNMP support with authentication and encryption
- **NETCONF**: Network configuration protocol support
- **SSH/Telnet**: Direct CLI access for configuration and troubleshooting
- **REST APIs**: Modern API integration with vendor-specific endpoints

### Real-time Monitoring
- **Sub-second Updates**: WebSocket connections for live data updates
- **High Performance**: Support for 10,000+ network devices per ISP instance
- **Scalable Architecture**: Distributed monitoring with automatic load balancing
- **99.9% Uptime**: Automatic failover and redundancy

### Advanced Analytics
- **Machine Learning**: Anomaly detection for network performance
- **Predictive Analytics**: Capacity planning and failure prediction
- **Business Intelligence**: Comprehensive reporting and analytics
- **Custom Metrics**: Define and track custom network metrics

## Getting Started

### Prerequisites
- PostgreSQL 12+ with PostGIS extension (for geographic features)
- Redis 6+ for caching and real-time data
- Python 3.11+ with required packages
- Optional: Ansible 2.9+ for automation features
- Optional: VOLTHA deployment for GPON management

### Installation

1. **Install the Network Integration Module**:
```bash
cd /path/to/dotmac_isp_framework
pip install -e .
```

2. **Configure Database**:
```bash
# Run database migrations
alembic upgrade head
```

3. **Configure Environment Variables**:
```env
# Network Monitoring
SNMP_DEFAULT_COMMUNITY=public
SNMP_DEFAULT_PORT=161
SNMP_TIMEOUT=5
SNMP_RETRIES=3

# Ansible Integration
ANSIBLE_HOST_KEY_CHECKING=False
ANSIBLE_STDOUT_CALLBACK=json
ANSIBLE_GATHERING=smart

# VOLTHA Integration
VOLTHA_HOST=localhost
VOLTHA_PORT=50057

# FreeRADIUS Integration
RADIUS_HOST=localhost
RADIUS_SECRET=testing123
RADIUS_AUTH_PORT=1812
RADIUS_ACCT_PORT=1813

# GIS Configuration
GIS_DEFAULT_MAP_PROVIDER=openstreetmap
GIS_GEOCODING_PROVIDER=nominatim
```

4. **Start Services**:
```bash
# Start the main application
uvicorn dotmac_isp.main:app --host 0.0.0.0 --port 8000

# Start background workers for monitoring
celery -A dotmac_isp.core.celery worker --loglevel=info
```

## API Documentation

### Network Device Management

#### Create Network Device
```http
POST /api/v1/network/devices
Content-Type: application/json

{
  "name": "core-router-01",
  "hostname": "cr01.example.com",
  "device_type": "router",
  "vendor": "cisco",
  "model": "ASR1001-X",
  "management_ip": "192.168.1.1",
  "snmp_community": "public",
  "snmp_version": "v2c",
  "location": {
    "street_address": "123 Main St",
    "city": "Downtown",
    "state_province": "CA",
    "country_code": "US",
    "latitude": 37.7749,
    "longitude": -122.4194
  }
}
```

#### Get Device Topology
```http
GET /api/v1/visualization/topology/data?device_types=router,switch&include_interfaces=true
```

#### Execute Ansible Playbook
```http
POST /api/v1/ansible/playbooks/{playbook_id}/execute
Content-Type: application/json

{
  "inventory_content": "[routers]\ncr01.example.com ansible_host=192.168.1.1",
  "extra_variables": {
    "backup_location": "/backups/",
    "config_template": "ios_base_config.j2"
  },
  "limit_hosts": ["cr01.example.com"]
}
```

### VOLTHA GPON Management

#### Provision ONU Service
```http
POST /api/v1/voltha/services
Content-Type: application/json

{
  "olt_device_id": "olt_001",
  "onu_device_id": "onu_12345",
  "service_name": "residential_internet",
  "service_type": "internet",
  "c_tag": 100,
  "s_tag": 1000,
  "upstream_bandwidth_kbps": 10000,
  "downstream_bandwidth_kbps": 100000,
  "customer_id": "cust_001"
}
```

### RADIUS Authentication

#### Create RADIUS User
```http
POST /api/v1/radius/users
Content-Type: application/json

{
  "username": "customer001",
  "password": "secure_password",
  "user_type": "customer",
  "customer_id": "cust_001",
  "max_bandwidth_kbps": 100000,
  "max_sessions": 1,
  "enabled": true
}
```

### Network Monitoring

#### Get Real-time Metrics
```http
GET /api/v1/visualization/realtime/network-metrics?metric_names=cpu_usage,memory_usage&device_ids=dev_001,dev_002&time_range=3600
```

#### Create Alert Rule
```http
POST /api/v1/monitoring/alert-rules
Content-Type: application/json

{
  "rule_name": "High CPU Usage",
  "metric_name": "cpu_usage_percent",
  "condition_operator": ">",
  "threshold_value": 80,
  "alert_severity": "high",
  "evaluation_window": 300,
  "consecutive_violations": 2,
  "notification_channels": ["email", "slack"]
}
```

### Geographic Visualization

#### Get Network Map Data
```http
GET /api/v1/visualization/maps/{map_id}/data?include_devices=true&include_locations=true&include_coverage=true
```

## Configuration Examples

### Device Monitoring Profile
```json
{
  "profile_name": "Standard Router Monitoring",
  "profile_type": "system",
  "snmp_version": "v2c",
  "snmp_community": "public",
  "monitoring_interval": 300,
  "oids_to_monitor": [
    {
      "oid": "1.3.6.1.2.1.1.3.0",
      "name": "sysUpTime",
      "description": "System uptime"
    },
    {
      "oid": "1.3.6.1.2.1.2.2.1.10",
      "name": "ifInOctets",
      "description": "Interface input octets",
      "table": true
    }
  ],
  "data_retention_days": 30
}
```

### Ansible Playbook Example
```yaml
---
- name: Cisco Router Configuration Backup
  hosts: cisco_routers
  gather_facts: yes
  vars:
    backup_dir: "/var/backups/network"
    timestamp: "{{ ansible_date_time.epoch }}"
  
  tasks:
    - name: Create backup directory
      file:
        path: "{{ backup_dir }}/{{ inventory_hostname }}"
        state: directory
        mode: '0755'
      delegate_to: localhost
      
    - name: Backup running configuration
      cisco.ios.ios_command:
        commands:
          - show running-config
      register: config_output
      
    - name: Save configuration to file
      copy:
        content: "{{ config_output.stdout[0] }}"
        dest: "{{ backup_dir }}/{{ inventory_hostname }}/config_{{ timestamp }}.txt"
      delegate_to: localhost
      
    - name: Update device status in database
      uri:
        url: "http://localhost:8000/api/v1/network/devices/{{ device_id }}"
        method: PATCH
        body_format: json
        body:
          last_config_backup: "{{ ansible_date_time.iso8601 }}"
      delegate_to: localhost
```

### Dashboard Configuration
```json
{
  "dashboard_name": "Network Operations Center",
  "dashboard_type": "network_overview",
  "layout_config": {
    "columns": 12,
    "row_height": 60,
    "margin": [10, 10]
  },
  "widgets": [
    {
      "widget_name": "Total Devices",
      "widget_type": "counter",
      "position": {"x": 0, "y": 0, "width": 3, "height": 2},
      "data_source": "network_devices",
      "data_query": {"status": "active"},
      "display_config": {
        "show_trend": true,
        "trend_period": "24h"
      }
    },
    {
      "widget_name": "Network Topology",
      "widget_type": "topology",
      "position": {"x": 0, "y": 2, "width": 8, "height": 6},
      "data_source": "topology_data",
      "chart_config": {
        "layout_algorithm": "force_directed",
        "show_labels": true,
        "node_color_by": "status"
      }
    }
  ]
}
```

## Best Practices

### Network Device Management
1. **Consistent Naming**: Use consistent hostname patterns (site-role-number)
2. **SNMP Security**: Use SNMPv3 with encryption for production environments
3. **Regular Backups**: Schedule automated configuration backups
4. **Change Management**: Use configuration version control
5. **Monitoring Coverage**: Ensure all critical devices are monitored

### Automation Guidelines
1. **Idempotent Playbooks**: Ensure playbooks can be run multiple times safely
2. **Error Handling**: Include comprehensive error handling and rollback procedures
3. **Testing**: Test playbooks in staging environment before production
4. **Documentation**: Document all automation workflows and dependencies
5. **Security**: Use encrypted variables for sensitive data

### Performance Optimization
1. **Monitoring Intervals**: Adjust based on device criticality and network load
2. **Data Retention**: Configure appropriate retention periods for different metrics
3. **Alert Tuning**: Fine-tune alert thresholds to reduce false positives
4. **Indexing**: Ensure database indexes are optimized for query patterns
5. **Caching**: Use Redis caching for frequently accessed data

### Security Best Practices
1. **Authentication**: Use strong authentication for all network access
2. **Encryption**: Encrypt all management traffic (HTTPS, SSH, SNMPv3)
3. **Access Control**: Implement role-based access control
4. **Audit Logging**: Enable comprehensive audit logging
5. **Regular Updates**: Keep all components updated with security patches

## Troubleshooting

### Common Issues

#### SNMP Connectivity Issues
```bash
# Test SNMP connectivity
snmpwalk -v2c -c public 192.168.1.1 1.3.6.1.2.1.1.1.0

# Check SNMP configuration in device
show snmp community
```

#### Ansible Execution Failures
```bash
# Test Ansible connectivity
ansible -i inventory.ini all -m ping

# Run playbook with verbose output
ansible-playbook -i inventory.ini playbook.yml -vvv
```

#### Database Connection Issues
```sql
-- Check database connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Performance Monitoring
```bash
# Check API response times
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:8000/api/v1/network/devices"

# Monitor database performance
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

# Check Redis performance
redis-cli info stats
```

## Integration Examples

### SignOz Observability Integration
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure tracing
tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("network_device_discovery")
async def discover_network_devices():
    with tracer.start_as_current_span("snmp_walk") as span:
        span.set_attribute("device.ip", "192.168.1.1")
        # SNMP discovery logic
```

### External Monitoring System Integration
```python
# Prometheus metrics export
from prometheus_client import Counter, Histogram, generate_latest

device_discovery_counter = Counter('network_device_discovery_total', 'Total device discoveries')
snmp_request_duration = Histogram('snmp_request_duration_seconds', 'SNMP request duration')

@app.get("/metrics")
async def get_metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Webhook Integration
```python
@app.post("/webhooks/device-status")
async def handle_device_status_webhook(request: DeviceStatusWebhook):
    """Handle device status updates from external monitoring systems."""
    device = await get_device_by_ip(request.device_ip)
    if device:
        device.status = request.status
        await db.commit()
        
        # Trigger alerts if necessary
        await check_alert_conditions(device)
```

## API Reference

For complete API documentation, visit the interactive API docs at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Support and Contributing

### Getting Help
- Review the API documentation at `/docs`
- Check the troubleshooting section above
- Examine test files for usage examples
- Review Docker Compose configuration for deployment

### Contributing
- Follow code quality standards with complexity limits
- Include comprehensive test coverage (80% minimum)
- Document all public APIs
- Use type hints throughout the codebase

### Development Setup
```bash
# Install development dependencies
make install-dev

# Run quality checks
make check

# Run tests
make test-docker

# Start development environment
docker-compose up -d
```

This comprehensive network integration system provides ISPs with a complete solution for managing their network infrastructure, from device provisioning and monitoring to customer service delivery and geographic visualization. The modular architecture ensures scalability and flexibility while maintaining the performance and reliability required for production ISP operations.