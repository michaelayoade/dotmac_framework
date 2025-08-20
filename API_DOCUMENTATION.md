# DotMac ISP Platform - Complete API Documentation

## Overview

The DotMac Platform is a comprehensive microservices-based telecommunications management platform for Internet Service Providers. Currently, the platform is deployed with limited service exposure, but this documentation covers the complete API schema for all services.

## Current Deployment Status

**URL**: http://149.102.135.97:8000

**Current Status**: The deployment currently shows only the enhanced network services. The full platform with all services requires deployment using the unified API configuration.

## Complete Service Architecture

### 1. API Gateway Service (Port 8000)
**Base Path**: `/gateway`

Central API gateway providing:
- Request routing and load balancing
- Rate limiting (1000 req/min default)
- Authentication proxy
- API versioning
- Request/response transformation

**Key Endpoints**:
```
GET  /gateway/health              - Health check
GET  /gateway/routes              - List all routes
POST /gateway/auth/login          - Authenticate user
POST /gateway/auth/refresh        - Refresh token
GET  /gateway/metrics             - Gateway metrics
```

### 2. Identity Service (Port 8001)
**Base Path**: `/identity`

User authentication and customer management:
- Multi-tenant user management
- Customer profiles and organizations
- Role-based access control (RBAC)
- OAuth2/JWT authentication
- Password policies and MFA

**Key Endpoints**:
```
POST /identity/users              - Create user
GET  /identity/users/{id}         - Get user details
PUT  /identity/users/{id}         - Update user
POST /identity/auth/login         - User login
POST /identity/auth/logout        - User logout
GET  /identity/organizations      - List organizations
POST /identity/customers          - Create customer
GET  /identity/customers/{id}     - Get customer details
```

### 3. Billing Service (Port 8002)
**Base Path**: `/billing`

Financial management system:
- Invoice generation and management
- Payment processing
- Subscription management
- Usage-based billing
- Payment gateway integration
- Tax calculation

**Key Endpoints**:
```
POST /billing/invoices            - Create invoice
GET  /billing/invoices/{id}       - Get invoice
POST /billing/payments            - Process payment
GET  /billing/subscriptions       - List subscriptions
POST /billing/subscriptions       - Create subscription
PUT  /billing/subscriptions/{id}  - Update subscription
GET  /billing/usage/{customer_id} - Get usage data
POST /billing/charges             - Create charge
```

### 4. Services Provisioning (Port 8003)
**Base Path**: `/services`

Service lifecycle management:
- Service catalog management
- Automated provisioning
- Service activation/deactivation
- Service templates
- Dependency management

**Key Endpoints**:
```
GET  /services/catalog            - List service catalog
POST /services/provision          - Provision service
PUT  /services/{id}/activate      - Activate service
PUT  /services/{id}/suspend       - Suspend service
DELETE /services/{id}             - Terminate service
GET  /services/templates          - List service templates
POST /services/bundles            - Create service bundle
```

### 5. Network Management (Port 8004)
**Base Path**: `/network`

Network infrastructure management:
- Device inventory and monitoring
- SNMP monitoring
- SSH automation
- Network topology management
- VOLTHA fiber management
- RADIUS/AAA integration
- Captive portal management

**Key Endpoints**:
```
# Device Management
GET  /network/devices             - List network devices
POST /network/devices             - Add device
GET  /network/devices/{id}        - Get device details
PUT  /network/devices/{id}/config - Update device config

# SSH Automation
POST /network/ssh/deploy-configuration - Deploy UCI config
POST /network/ssh/network-discovery    - Discover devices
POST /network/ssh/firmware-upgrade     - Mass firmware upgrade

# Network Topology
POST /network/topology/add-device      - Add device to topology
POST /network/topology/add-link        - Add network link
GET  /network/topology/analysis        - Network analysis
GET  /network/topology/shortest-path   - Find shortest path

# VOLTHA Integration
GET  /network/voltha/network-status    - VOLTHA network status
POST /network/voltha/provision-subscriber - Provision fiber subscriber
POST /network/voltha/suspend-service   - Suspend fiber service

# Captive Portal
POST /network/captive-portal/create-hotspot - Create WiFi hotspot
POST /network/captive-portal/authenticate-user - Authenticate portal user
```

### 6. Analytics Service (Port 8005)
**Base Path**: `/analytics`

Business intelligence and reporting:
- Real-time metrics collection
- Custom dashboard creation
- Report generation
- Data aggregation
- Predictive analytics

**Key Endpoints**:
```
GET  /analytics/metrics           - Get real-time metrics
POST /analytics/reports           - Generate report
GET  /analytics/dashboards        - List dashboards
POST /analytics/dashboards        - Create dashboard
GET  /analytics/insights          - Get business insights
POST /analytics/queries           - Execute custom query
GET  /analytics/exports/{format}  - Export data
```

### 7. Platform Service (Port 8006)
**Base Path**: `/platform`

Core platform utilities:
- Tenant management
- RBAC enforcement
- Audit logging
- Configuration management
- Health monitoring

**Key Endpoints**:
```
GET  /platform/tenants            - List tenants
POST /platform/tenants            - Create tenant
GET  /platform/config             - Get configuration
PUT  /platform/config             - Update configuration
GET  /platform/audit-logs         - Get audit logs
GET  /platform/permissions        - List permissions
POST /platform/roles              - Create role
```

### 8. Event Bus (Port 8007)
**Base Path**: `/events`

Event-driven architecture:
- Event publishing and subscription
- Message queuing
- Event streaming
- Event replay
- Dead letter queues

**Key Endpoints**:
```
POST /events/publish              - Publish event
GET  /events/subscribe/{topic}    - Subscribe to topic
GET  /events/history              - Event history
POST /events/replay               - Replay events
GET  /events/schemas              - List event schemas
GET  /events/topics               - List topics
```

### 9. Core Ops (Port 8008)
**Base Path**: `/ops`

Workflow orchestration:
- Workflow engine
- Saga orchestration
- Job scheduling
- Task management
- State machines

**Key Endpoints**:
```
POST /ops/workflows               - Create workflow
GET  /ops/workflows/{id}          - Get workflow status
POST /ops/jobs                    - Schedule job
GET  /ops/jobs/{id}               - Get job status
POST /ops/sagas                   - Start saga
GET  /ops/tasks                   - List tasks
POST /ops/state-machines          - Create state machine
```

## Authentication

All API endpoints require authentication using either:

### JWT Bearer Token
```http
Authorization: Bearer <jwt-token>
```

### API Key
```http
X-API-Key: <api-key>
```

## Rate Limiting

Default rate limits:
- 1000 requests per minute per client
- Burst: 100 requests per second

Custom limits can be configured per tenant.

## Error Responses

Standard error response format:
```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional error details"
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error
- `503` - Service Unavailable

## Deployment Instructions

To deploy the complete platform with all services:

```bash
# 1. Clone the repository
git clone https://github.com/dotmac/platform.git
cd platform

# 2. Deploy unified API service
./scripts/deploy-unified-api.sh

# 3. Access the platform
# Documentation: http://localhost:8000/docs
# Health Check: http://localhost:8000/health
```

## Testing the API

### Quick Health Check
```bash
curl http://localhost:8000/health
```

### List All Services
```bash
curl http://localhost:8000/services
```

### Get Service Details
```bash
curl http://localhost:8000/services/networking
```

### Example: Create a Customer
```bash
curl -X POST http://localhost:8000/identity/customers \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890"
  }'
```

## WebSocket Support

Real-time features are available via WebSocket connections:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  console.log('Received:', event.data);
};
```

## SDK Support

SDKs are available for:
- Python: `pip install dotmac-sdk`
- JavaScript/TypeScript: `npm install @dotmac/sdk`
- Go: `go get github.com/dotmac/sdk-go`

## Support

- Documentation: https://docs.dotmac.io
- API Status: https://status.dotmac.io
- Support Email: support@dotmac.io
- GitHub: https://github.com/dotmac/platform

## License

MIT License - See LICENSE file for details.