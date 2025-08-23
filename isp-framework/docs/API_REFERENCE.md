# Network Integration API Reference

This document provides comprehensive API reference for all network integration endpoints in the DotMac ISP Framework.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All API endpoints require authentication via JWT tokens. Include the token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## Content Type
All requests and responses use JSON format:
```
Content-Type: application/json
```

## Error Responses
All endpoints return consistent error responses:
```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Network Integration Endpoints

### Network Devices

#### Create Network Device
Creates a new network device in the system.

**Endpoint**: `POST /network/devices`

**Request Body**:
```json
{
  "name": "string (required, max 255 chars)",
  "hostname": "string (optional, unique, max 255 chars)",
  "device_type": "router|switch|access_point|firewall|load_balancer|olt|onu|modem|cpe|server|ups|pdu|optical_amplifier|splitter|patch_panel",
  "model": "string (optional, max 100 chars)",
  "vendor": "string (optional, max 100 chars)",
  "serial_number": "string (optional, unique, max 100 chars)",
  "asset_tag": "string (optional, unique, max 100 chars)",
  "management_ip": "string (optional, valid IP address)",
  "subnet_mask": "string (optional, max 18 chars)",
  "gateway": "string (optional, valid IP address)",
  "dns_servers": ["string"] (optional, array of IP addresses),
  "snmp_community": "string (optional, max 100 chars)",
  "snmp_version": "v1|v2c|v3 (default: v2c)",
  "snmp_port": "integer (default: 161, range: 1-65535)",
  "snmp_enabled": "boolean (default: true)",
  "cpu_count": "integer (optional, min: 1)",
  "memory_total_mb": "integer (optional, min: 1)",
  "storage_total_gb": "integer (optional, min: 1)",
  "power_consumption_watts": "integer (optional, min: 1)",
  "os_version": "string (optional, max 100 chars)",
  "firmware_version": "string (optional, max 100 chars)",
  "street_address": "string (optional, max 255 chars)",
  "city": "string (optional, max 100 chars)",
  "state_province": "string (optional, max 100 chars)",
  "postal_code": "string (optional, max 20 chars)",
  "country_code": "string (default: US, max 2 chars)",
  "rack_location": "string (optional, max 100 chars)",
  "rack_unit": "string (optional, max 10 chars)",
  "datacenter": "string (optional, max 100 chars)",
  "monitoring_enabled": "boolean (default: true)",
  "monitoring_interval": "integer (default: 300, range: 30-3600)",
  "warranty_expires": "string (optional, ISO 8601 datetime)",
  "next_maintenance": "string (optional, ISO 8601 datetime)",
  "description": "string (optional)",
  "tags": ["string"] (optional),
  "custom_fields": "object (optional)"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "string",
  "hostname": "string",
  "device_type": "string",
  "status": "string",
  "management_ip": "string",
  "snmp_enabled": "boolean",
  "monitoring_enabled": "boolean",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "full_address": "string"
}
```

#### List Network Devices
Retrieves a paginated list of network devices with filtering options.

**Endpoint**: `GET /network/devices`

**Query Parameters**:
- `page`: integer (default: 1, min: 1) - Page number
- `per_page`: integer (default: 50, range: 1-100) - Items per page
- `device_type`: string (optional) - Filter by device type
- `status`: string (optional) - Filter by status
- `vendor`: string (optional) - Filter by vendor
- `search`: string (optional) - Search in name, hostname, serial number

**Response**: `200 OK`
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "device_type": "string",
      "status": "string",
      "management_ip": "string",
      "vendor": "string",
      "model": "string",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": "integer",
  "page": "integer",
  "per_page": "integer",
  "total_pages": "integer"
}
```

#### Get Network Device
Retrieves details of a specific network device.

**Endpoint**: `GET /network/devices/{device_id}`

**Path Parameters**:
- `device_id`: string (required) - Device UUID

**Response**: `200 OK`
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "string",
  "hostname": "string",
  "device_type": "string",
  "vendor": "string",
  "model": "string",
  "serial_number": "string",
  "management_ip": "string",
  "status": "string",
  "snmp_enabled": "boolean",
  "monitoring_enabled": "boolean",
  "cpu_count": "integer",
  "memory_total_mb": "integer",
  "os_version": "string",
  "firmware_version": "string",
  "last_config_backup": "2024-01-01T00:00:00Z",
  "full_address": "string",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Update Network Device
Updates an existing network device.

**Endpoint**: `PUT /network/devices/{device_id}`

**Request Body**: Same as create request, all fields optional

**Response**: `200 OK` - Same as get device response

#### Delete Network Device
Deletes a network device from the system.

**Endpoint**: `DELETE /network/devices/{device_id}`

**Response**: `200 OK`
```json
{
  "message": "Network device deleted successfully"
}
```

### Network Locations

#### Create Network Location
Creates a new network location.

**Endpoint**: `POST /network/locations`

**Request Body**:
```json
{
  "name": "string (required, max 255 chars)",
  "location_type": "string (required, max 50 chars)",
  "code": "string (optional, unique, max 20 chars)",
  "latitude": "number (optional, decimal degrees)",
  "longitude": "number (optional, decimal degrees)",
  "elevation_meters": "number (optional)",
  "street_address": "string (optional, max 255 chars)",
  "city": "string (optional, max 100 chars)",
  "state_province": "string (optional, max 100 chars)",
  "postal_code": "string (optional, max 20 chars)",
  "country_code": "string (default: US, max 2 chars)",
  "facility_size_sqm": "number (optional, min: 0)",
  "power_capacity_kw": "number (optional, min: 0)",
  "cooling_capacity_tons": "number (optional, min: 0)",
  "rack_count": "integer (optional, min: 0)",
  "contact_person": "string (optional, max 255 chars)",
  "contact_phone": "string (optional, max 20 chars)",
  "contact_email": "string (optional, max 255 chars)",
  "service_area_radius_km": "number (optional, min: 0)",
  "population_served": "integer (optional, min: 0)",
  "description": "string (optional)",
  "tags": ["string"] (optional)
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "name": "string",
  "location_type": "string",
  "coordinates": {
    "lat": "number",
    "lon": "number"
  },
  "full_address": "string",
  "contact_person": "string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### List Network Locations
Retrieves a paginated list of network locations.

**Endpoint**: `GET /network/locations`

**Query Parameters**:
- `page`: integer (default: 1, min: 1)
- `per_page`: integer (default: 50, range: 1-100)
- `location_type`: string (optional)
- `search`: string (optional)

**Response**: `200 OK` - Paginated location list

### Network Metrics

#### Get Device Metrics
Retrieves metrics for a specific device.

**Endpoint**: `GET /network/devices/{device_id}/metrics`

**Query Parameters**:
- `metric_name`: string (optional) - Filter by metric name
- `start_time`: string (optional) - ISO 8601 datetime
- `end_time`: string (optional) - ISO 8601 datetime  
- `limit`: integer (default: 100, range: 1-1000)

**Response**: `200 OK`
```json
[
  {
    "id": "uuid",
    "device_id": "uuid",
    "interface_id": "uuid",
    "metric_name": "string",
    "metric_type": "string",
    "value": "number",
    "unit": "string",
    "timestamp": "2024-01-01T00:00:00Z",
    "tags": "object"
  }
]
```

#### Get Aggregated Metrics
Retrieves aggregated metrics data.

**Endpoint**: `GET /network/metrics/aggregated`

**Query Parameters**:
- `metric_name`: string (required)
- `aggregation`: string (required) - avg|sum|min|max|count
- `interval`: string (required) - 5m|15m|1h|6h|24h
- `start_time`: string (required) - ISO 8601 datetime
- `end_time`: string (required) - ISO 8601 datetime
- `device_ids`: array of strings (optional)

**Response**: `200 OK`
```json
{
  "metric_name": "string",
  "aggregation": "string",
  "interval": "string",
  "data_points": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "value": "number"
    }
  ],
  "start_time": "2024-01-01T00:00:00Z",
  "end_time": "2024-01-01T00:00:00Z"
}
```

### Network Topology

#### Get Network Topology
Retrieves network topology information.

**Endpoint**: `GET /network/topology`

**Query Parameters**:
- `device_id`: string (optional) - Filter by device involvement
- `connection_type`: string (optional) - Filter by connection type

**Response**: `200 OK`
```json
[
  {
    "id": "uuid",
    "parent_device_id": "uuid",
    "child_device_id": "uuid",
    "connection_type": "string",
    "bandwidth_mbps": "integer",
    "distance_meters": "number",
    "description": "string"
  }
]
```

### Device Configuration

#### Create Device Configuration
Creates a new device configuration.

**Endpoint**: `POST /network/devices/{device_id}/configurations`

**Request Body**:
```json
{
  "name": "string (required, max 255 chars)",
  "version": "string (required, max 50 chars)",
  "configuration_data": "string (required)",
  "source": "string (optional, max 50 chars)",
  "description": "string (optional)",
  "tags": ["string"] (optional)
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "device_id": "uuid",
  "name": "string",
  "version": "string",
  "is_active": "boolean",
  "is_backup": "boolean",
  "deployment_status": "string",
  "syntax_validated": "boolean",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### List Device Configurations
Lists configurations for a device.

**Endpoint**: `GET /network/devices/{device_id}/configurations`

**Query Parameters**:
- `active_only`: boolean (default: false)

**Response**: `200 OK` - Array of configuration objects

### Network Alerts

#### List Network Alerts
Retrieves network alerts with filtering and pagination.

**Endpoint**: `GET /network/alerts`

**Query Parameters**:
- `page`: integer (default: 1, min: 1)
- `per_page`: integer (default: 50, range: 1-100)
- `severity`: string (optional) - critical|high|medium|low|info
- `is_active`: boolean (optional)
- `device_id`: string (optional)

**Response**: `200 OK`
```json
{
  "items": [
    {
      "id": "uuid",
      "device_id": "uuid",
      "alert_type": "string",
      "severity": "string",
      "title": "string",
      "message": "string",
      "is_active": "boolean",
      "is_acknowledged": "boolean",
      "metric_name": "string",
      "threshold_value": "number",
      "current_value": "number",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": "integer",
  "page": "integer",
  "per_page": "integer",
  "total_pages": "integer"
}
```

#### Acknowledge Alert
Acknowledges a network alert.

**Endpoint**: `POST /network/alerts/{alert_id}/acknowledge`

**Query Parameters**:
- `user_id`: string (required)

**Response**: `200 OK`
```json
{
  "message": "Alert acknowledged successfully"
}
```

#### Resolve Alert
Resolves a network alert.

**Endpoint**: `POST /network/alerts/{alert_id}/resolve`

**Query Parameters**:
- `user_id`: string (required)

**Response**: `200 OK`
```json
{
  "message": "Alert resolved successfully"
}
```

## Ansible Integration Endpoints

### Playbook Management

#### Create Playbook
Creates a new Ansible playbook.

**Endpoint**: `POST /ansible/playbooks`

**Request Body**:
```json
{
  "name": "string (required, max 255 chars)",
  "playbook_type": "device_provisioning|configuration_deployment|firmware_update|backup_configuration|health_check|security_audit|troubleshooting|maintenance|custom",
  "version": "string (default: 1.0, max 50 chars)",
  "playbook_content": "string (required, YAML content)",
  "playbook_variables": "object (optional)",
  "requirements": "array (optional, Ansible collections/roles)",
  "target_device_types": "array (optional)",
  "target_vendors": "array (optional)",
  "timeout_minutes": "integer (default: 30)",
  "max_parallel_hosts": "integer (default: 10)",
  "description": "string (optional)"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "name": "string",
  "playbook_type": "string",
  "version": "string",
  "syntax_validated": "boolean",
  "execution_count": "integer",
  "success_rate": "integer",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Execute Playbook
Executes an Ansible playbook.

**Endpoint**: `POST /ansible/playbooks/{playbook_id}/execute`

**Request Body**:
```json
{
  "inventory_content": "string (required, Ansible inventory)",
  "extra_variables": "object (optional)",
  "limit_hosts": "array (optional, hostnames)",
  "tags": "array (optional, playbook tags)",
  "skip_tags": "array (optional, tags to skip)",
  "job_name": "string (optional)"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "execution_id": "string",
  "playbook_id": "uuid",
  "status": "pending|running|success|failed|cancelled",
  "started_at": "2024-01-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Inventory Management

#### Create Inventory
Creates a device inventory.

**Endpoint**: `POST /ansible/inventories`

**Request Body**:
```json
{
  "name": "string (required, max 255 chars)",
  "inventory_type": "static|dynamic|database|custom_script",
  "inventory_content": "string (optional, static inventory)",
  "inventory_script": "string (optional, dynamic script)",
  "group_variables": "object (optional)",
  "host_variables": "object (optional)",
  "auto_discovery_enabled": "boolean (default: false)",
  "description": "string (optional)"
}
```

#### Validate Inventory
Validates an inventory configuration.

**Endpoint**: `POST /ansible/inventories/{inventory_id}/validate`

**Response**: `200 OK`
```json
{
  "inventory_id": "uuid",
  "is_valid": "boolean",
  "errors": ["string"],
  "validated_at": "2024-01-01T00:00:00Z"
}
```

## VOLTHA Integration Endpoints

### OLT Management

#### List OLTs
Retrieves VOLTHA OLT devices.

**Endpoint**: `GET /voltha/olts`

**Response**: `200 OK`
```json
[
  {
    "id": "uuid",
    "voltha_device_id": "string",
    "name": "string",
    "device_type": "string",
    "vendor": "string",
    "model": "string",
    "serial_number": "string",
    "management_ip": "string",
    "connection_status": "reachable|unreachable|discovered|disabled|unknown",
    "operational_status": "active|activating|inactive|failed|testing|unknown",
    "admin_state": "enabled|disabled|preprovisioned|downloading_image|deleted",
    "max_pon_ports": "integer",
    "active_pon_ports": "integer",
    "total_active_onus": "integer"
  }
]
```

#### Get OLT Details
Retrieves details of a specific OLT.

**Endpoint**: `GET /voltha/olts/{olt_id}`

### ONU Management

#### List ONUs
Retrieves ONU devices for an OLT.

**Endpoint**: `GET /voltha/olts/{olt_id}/onus`

**Response**: `200 OK`
```json
[
  {
    "id": "uuid",
    "voltha_device_id": "string",
    "name": "string",
    "serial_number": "string",
    "onu_id": "integer",
    "connection_status": "string",
    "operational_status": "string",
    "onu_state": "discovered|activating|active|disabled|failed|rebooting|deleting",
    "customer_id": "uuid",
    "rx_power_dbm": "number",
    "tx_power_dbm": "number",
    "signal_quality": "excellent|good|fair|poor|critical"
  }
]
```

#### Provision ONU Service
Provisions a service on an ONU.

**Endpoint**: `POST /voltha/services`

**Request Body**:
```json
{
  "olt_id": "uuid (required)",
  "onu_id": "uuid (required)",
  "service_name": "string (required)",
  "service_type": "internet|voice|video|enterprise|multicast",
  "c_tag": "integer (optional, VLAN C-tag)",
  "s_tag": "integer (optional, VLAN S-tag)",
  "upstream_bandwidth_kbps": "integer (optional)",
  "downstream_bandwidth_kbps": "integer (optional)",
  "customer_id": "uuid (optional)"
}
```

## FreeRADIUS Integration Endpoints

### User Management

#### Create RADIUS User
Creates a new RADIUS user.

**Endpoint**: `POST /radius/users`

**Request Body**:
```json
{
  "username": "string (required, max 100 chars)",
  "password": "string (required)",
  "user_type": "customer|device|admin|service",
  "full_name": "string (optional)",
  "email": "string (optional)",
  "phone": "string (optional)",
  "customer_id": "uuid (optional)",
  "enabled": "boolean (default: true)",
  "max_sessions": "integer (default: 1)",
  "max_bandwidth_kbps": "integer (optional)",
  "max_time_limit": "integer (optional, seconds)",
  "valid_from": "string (optional, ISO 8601 datetime)",
  "valid_until": "string (optional, ISO 8601 datetime)"
}
```

**Response**: `201 Created`
```json
{
  "id": "uuid",
  "username": "string",
  "user_type": "string",
  "enabled": "boolean",
  "is_active": "boolean",
  "max_sessions": "integer",
  "total_sessions": "integer",
  "last_login": "2024-01-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### List RADIUS Users
Retrieves RADIUS users with filtering.

**Endpoint**: `GET /radius/users`

**Query Parameters**:
- `user_type`: string (optional)
- `enabled`: boolean (optional)
- `search`: string (optional, search username/email)

### Session Management

#### Get Active Sessions
Retrieves active RADIUS sessions.

**Endpoint**: `GET /radius/sessions`

**Query Parameters**:
- `username`: string (optional)
- `nas_ip`: string (optional)
- `status`: string (optional)

**Response**: `200 OK`
```json
[
  {
    "id": "uuid",
    "username": "string",
    "unique_session_id": "string",
    "nas_ip_address": "string",
    "framed_ip_address": "string",
    "session_start_time": "2024-01-01T00:00:00Z",
    "session_duration": "integer",
    "bytes_in": "integer",
    "bytes_out": "integer",
    "status": "active|stopped|interim|unknown"
  }
]
```

## Visualization Endpoints

### Dashboard Management

#### Create Dashboard
Creates a visualization dashboard.

**Endpoint**: `POST /visualization/dashboards`

**Request Body**:
```json
{
  "name": "string (required, max 255 chars)",
  "dashboard_type": "network_overview|device_monitoring|topology_view|geographic_view|performance_metrics|alerts_incidents|capacity_planning|custom",
  "layout_config": "object (optional, grid layout)",
  "refresh_interval": "integer (default: 30, seconds)",
  "theme": "string (default: light)",
  "show_toolbar": "boolean (default: true)",
  "is_public": "boolean (default: false)",
  "description": "string (optional)"
}
```

#### Get Topology Data
Retrieves network topology data for visualization.

**Endpoint**: `GET /visualization/topology/data`

**Query Parameters**:
- `device_types`: array of strings (optional)
- `location_ids`: array of strings (optional)
- `include_interfaces`: boolean (default: false)

**Response**: `200 OK`
```json
{
  "nodes": [
    {
      "id": "string",
      "name": "string",
      "type": "string",
      "vendor": "string",
      "status": "string",
      "coordinates": {"x": 0, "y": 0},
      "interfaces": [
        {
          "id": "string",
          "name": "string",
          "type": "string",
          "status": "string"
        }
      ]
    }
  ],
  "edges": [
    {
      "id": "string",
      "source": "string",
      "target": "string",
      "type": "string",
      "bandwidth": "integer"
    }
  ],
  "metadata": {
    "total_nodes": "integer",
    "total_edges": "integer",
    "generated_at": "2024-01-01T00:00:00Z"
  }
}
```

#### Get Real-time Device Status
Retrieves real-time device status.

**Endpoint**: `GET /visualization/realtime/device-status`

**Query Parameters**:
- `device_ids`: array of strings (optional)

**Response**: `200 OK`
```json
{
  "devices": [
    {
      "device_id": "uuid",
      "name": "string",
      "status": "string",
      "uptime": "integer",
      "last_seen": "2024-01-01T00:00:00Z",
      "cpu_usage": "number",
      "memory_usage": "number"
    }
  ],
  "timestamp": "2024-01-01T00:00:00Z",
  "total_devices": "integer"
}
```

### Geographic Visualization

#### Get Network Map Data
Retrieves data for geographic network visualization.

**Endpoint**: `GET /visualization/maps/{map_id}/data`

**Query Parameters**:
- `include_devices`: boolean (default: true)
- `include_locations`: boolean (default: true)
- `include_coverage`: boolean (default: false)

**Response**: `200 OK`
```json
{
  "map_config": {
    "center": {"lat": 37.7749, "lon": -122.4194},
    "zoom": 10,
    "base_map": "openstreetmap"
  },
  "layers": [
    {
      "type": "markers",
      "name": "Network Devices",
      "data": [
        {
          "id": "uuid",
          "name": "string",
          "type": "string",
          "coordinates": {"lat": 37.7749, "lon": -122.4194},
          "popup_data": {
            "title": "string",
            "status": "string"
          }
        }
      ]
    }
  ]
}
```

## Error Codes

### HTTP Status Codes
- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., duplicate)
- `422 Unprocessable Entity` - Validation errors
- `500 Internal Server Error` - Server error

### Application Error Codes
- `DEVICE_NOT_FOUND` - Network device not found
- `INVALID_IP_ADDRESS` - Invalid IP address format
- `SNMP_CONNECTION_FAILED` - SNMP connection failure
- `PLAYBOOK_EXECUTION_FAILED` - Ansible playbook execution failed
- `VOLTHA_CONNECTION_ERROR` - VOLTHA API connection error
- `RADIUS_AUTH_FAILED` - RADIUS authentication failed
- `INVALID_COORDINATES` - Invalid geographic coordinates
- `DASHBOARD_ACCESS_DENIED` - Dashboard access denied

## Rate Limiting

API endpoints are rate limited to prevent abuse:
- **Standard endpoints**: 1000 requests per hour per user
- **Real-time endpoints**: 100 requests per minute per user
- **Bulk operations**: 10 requests per minute per user

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Pagination

List endpoints support pagination with the following parameters:
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 50, max: 100)

Pagination info is included in response:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "per_page": 50,
  "total_pages": 3
}
```

## WebSocket Endpoints

Real-time updates are available via WebSocket connections:

### Device Status Updates
```
ws://localhost:8000/ws/device-status
```

### Network Metrics Stream
```
ws://localhost:8000/ws/metrics
```

### Alert Notifications
```
ws://localhost:8000/ws/alerts
```

## SDKs and Libraries

Official SDKs are available for:
- **Python**: `pip install dotmac-isp-sdk`
- **JavaScript/TypeScript**: `npm install @dotmac/isp-sdk`
- **Go**: `go get github.com/dotmac/isp-sdk-go`

Example usage (Python):
```python
from dotmac_isp_sdk import NetworkClient

client = NetworkClient(
    base_url="http://localhost:8000",
    api_token="your-jwt-token"
)

# Create a device
device = client.devices.create({
    "name": "router-01",
    "device_type": "router",
    "management_ip": "192.168.1.1"
})

# Get topology data
topology = client.visualization.get_topology_data()
```