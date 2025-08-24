# DotMac API Documentation

## API Overview

The DotMac API is a RESTful service built with FastAPI that provides comprehensive ISP management capabilities. All endpoints require authentication unless specified otherwise.

## Base URL
```
Production: https://api.dotmac.cloud
Staging: https://staging-api.dotmac.cloud
Development: http://localhost:8000
```

## Authentication

### OAuth 2.0 + JWT

The API uses OAuth 2.0 with JWT tokens for authentication.

#### Login Flow

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "tenant_id": "tenant_001"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_123",
    "email": "user@example.com",
    "roles": ["admin", "operator"]
  }
}
```

#### Token Refresh

```http
POST /api/v1/auth/refresh
Authorization: Bearer {refresh_token}
```

### Request Headers

All authenticated requests must include:
```http
Authorization: Bearer {access_token}
X-Tenant-ID: tenant_001
X-Request-ID: unique_request_id
```

## Rate Limiting

| Endpoint Type | Rate Limit | Window |
|--------------|------------|---------|
| Authentication | 5 requests | 1 minute |
| API (General) | 100 requests | 1 minute |
| Search | 30 requests | 1 minute |
| Bulk Operations | 10 requests | 1 hour |
| WebSocket | 1 connection | Per user |

Rate limit headers in response:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1629835200
```

## Error Responses

### Standard Error Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {},
    "request_id": "req_abc123",
    "timestamp": "2024-08-24T20:00:00Z"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request data |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

## Customer Management API

### List Customers

```http
GET /api/v1/customers
```

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 20, max: 100)
- `search` (string): Search term
- `status` (enum): `active`, `inactive`, `suspended`
- `sort` (string): Sort field (e.g., `created_at`, `-name`)

**Response:**
```json
{
  "data": [
    {
      "id": "cust_123",
      "account_number": "ACC-001234",
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890",
      "status": "active",
      "created_at": "2024-01-15T10:00:00Z",
      "services_count": 3,
      "balance": 0.00
    }
  ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

### Get Customer

```http
GET /api/v1/customers/{customer_id}
```

**Response:**
```json
{
  "data": {
    "id": "cust_123",
    "account_number": "ACC-001234",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "status": "active",
    "address": {
      "street": "123 Main St",
      "city": "Silicon Valley",
      "state": "CA",
      "zip": "94000",
      "country": "US"
    },
    "billing_address": {},
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-08-20T15:30:00Z",
    "metadata": {
      "source": "website",
      "referral": "partner_001"
    }
  }
}
```

### Create Customer

```http
POST /api/v1/customers
Content-Type: application/json

{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "phone": "+1234567890",
  "address": {
    "street": "456 Oak Ave",
    "city": "San Francisco",
    "state": "CA",
    "zip": "94102",
    "country": "US"
  },
  "metadata": {
    "source": "api",
    "notes": "Premium customer"
  }
}
```

### Update Customer

```http
PUT /api/v1/customers/{customer_id}
Content-Type: application/json

{
  "name": "Jane Smith-Updated",
  "email": "jane.new@example.com",
  "status": "active"
}
```

### Delete Customer

```http
DELETE /api/v1/customers/{customer_id}
```

## Service Management API

### List Services

```http
GET /api/v1/services
```

**Query Parameters:**
- `customer_id` (string): Filter by customer
- `type` (enum): `internet`, `voip`, `iptv`, `bundle`
- `status` (enum): `active`, `suspended`, `terminated`

### Create Service

```http
POST /api/v1/services
Content-Type: application/json

{
  "customer_id": "cust_123",
  "plan_id": "plan_fiber_100",
  "type": "internet",
  "installation_address": {
    "street": "123 Main St",
    "city": "Silicon Valley",
    "state": "CA",
    "zip": "94000"
  },
  "activation_date": "2024-09-01",
  "contract_months": 12
}
```

### Service Actions

#### Suspend Service
```http
POST /api/v1/services/{service_id}/suspend
Content-Type: application/json

{
  "reason": "non_payment",
  "notes": "3 months overdue"
}
```

#### Resume Service
```http
POST /api/v1/services/{service_id}/resume
```

#### Upgrade/Downgrade Service
```http
POST /api/v1/services/{service_id}/change-plan
Content-Type: application/json

{
  "new_plan_id": "plan_fiber_500",
  "effective_date": "2024-09-01"
}
```

## Billing API

### List Invoices

```http
GET /api/v1/invoices
```

**Query Parameters:**
- `customer_id` (string): Filter by customer
- `status` (enum): `draft`, `sent`, `paid`, `overdue`, `cancelled`
- `date_from` (date): Start date filter
- `date_to` (date): End date filter

### Create Invoice

```http
POST /api/v1/invoices
Content-Type: application/json

{
  "customer_id": "cust_123",
  "due_date": "2024-09-15",
  "items": [
    {
      "description": "Internet Service - September 2024",
      "quantity": 1,
      "unit_price": 49.99,
      "tax_rate": 0.08
    }
  ],
  "notes": "Thank you for your business"
}
```

### Process Payment

```http
POST /api/v1/payments
Content-Type: application/json

{
  "invoice_id": "inv_456",
  "amount": 53.99,
  "payment_method": "credit_card",
  "reference": "stripe_ch_123456"
}
```

### Payment Methods

```http
GET /api/v1/customers/{customer_id}/payment-methods
POST /api/v1/customers/{customer_id}/payment-methods
DELETE /api/v1/payment-methods/{method_id}
```

## Network Management API

### IP Address Management

#### List IP Pools
```http
GET /api/v1/network/ip-pools
```

#### Allocate IP Address
```http
POST /api/v1/network/ip-allocations
Content-Type: application/json

{
  "customer_id": "cust_123",
  "service_id": "svc_456",
  "pool_id": "pool_public_v4",
  "type": "static"
}
```

#### Release IP Address
```http
DELETE /api/v1/network/ip-allocations/{allocation_id}
```

### Equipment Management

#### List Equipment
```http
GET /api/v1/network/equipment
```

#### Register Equipment
```http
POST /api/v1/network/equipment
Content-Type: application/json

{
  "type": "router",
  "model": "MikroTik RB4011",
  "serial_number": "ABC123456",
  "mac_address": "00:11:22:33:44:55",
  "location": "POP-01",
  "customer_id": "cust_123"
}
```

### Circuit Management

```http
GET /api/v1/network/circuits
POST /api/v1/network/circuits
PUT /api/v1/network/circuits/{circuit_id}
DELETE /api/v1/network/circuits/{circuit_id}
```

## Support Ticket API

### List Tickets

```http
GET /api/v1/tickets
```

**Query Parameters:**
- `status` (enum): `open`, `in_progress`, `resolved`, `closed`
- `priority` (enum): `low`, `medium`, `high`, `critical`
- `assigned_to` (string): Filter by assigned user

### Create Ticket

```http
POST /api/v1/tickets
Content-Type: application/json

{
  "customer_id": "cust_123",
  "subject": "Internet connection issues",
  "description": "Intermittent disconnections since yesterday",
  "priority": "high",
  "category": "technical"
}
```

### Update Ticket

```http
PUT /api/v1/tickets/{ticket_id}
Content-Type: application/json

{
  "status": "in_progress",
  "assigned_to": "user_789",
  "notes": "Escalated to network team"
}
```

### Add Ticket Comment

```http
POST /api/v1/tickets/{ticket_id}/comments
Content-Type: application/json

{
  "message": "We've identified the issue and are working on a fix",
  "internal": false
}
```

## Reports API

### Generate Report

```http
POST /api/v1/reports/generate
Content-Type: application/json

{
  "type": "revenue",
  "period": "monthly",
  "date_from": "2024-01-01",
  "date_to": "2024-08-31",
  "format": "pdf",
  "email_to": "manager@example.com"
}
```

### List Available Reports

```http
GET /api/v1/reports/templates
```

### Download Report

```http
GET /api/v1/reports/{report_id}/download
```

## WebSocket API

### Real-time Updates

```javascript
const ws = new WebSocket('wss://api.dotmac.cloud/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your_jwt_token'
  }));
  
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['tickets', 'network_status']
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

### Event Types

| Event | Description | Payload |
|-------|-------------|---------|
| `ticket.created` | New ticket created | Ticket object |
| `ticket.updated` | Ticket status changed | Ticket object |
| `service.status` | Service status change | Service object |
| `network.alert` | Network issue detected | Alert details |
| `payment.received` | Payment processed | Payment object |

## Batch Operations

### Bulk Create

```http
POST /api/v1/batch/customers
Content-Type: application/json

{
  "operations": [
    {
      "method": "POST",
      "data": {
        "name": "Customer 1",
        "email": "cust1@example.com"
      }
    },
    {
      "method": "POST",
      "data": {
        "name": "Customer 2",
        "email": "cust2@example.com"
      }
    }
  ]
}
```

### Bulk Update

```http
PATCH /api/v1/batch/services
Content-Type: application/json

{
  "filter": {
    "status": "active",
    "plan_id": "plan_old"
  },
  "update": {
    "plan_id": "plan_new"
  }
}
```

## Pagination

All list endpoints support pagination:

```http
GET /api/v1/customers?page=2&limit=50
```

**Response Headers:**
```http
X-Total-Count: 500
X-Page-Count: 10
Link: <https://api.dotmac.cloud/api/v1/customers?page=3&limit=50>; rel="next",
      <https://api.dotmac.cloud/api/v1/customers?page=1&limit=50>; rel="prev"
```

## Filtering & Sorting

### Filter Syntax

```http
GET /api/v1/customers?filter[status]=active&filter[created_at][gte]=2024-01-01
```

### Sort Syntax

```http
GET /api/v1/customers?sort=-created_at,name
```
- Prefix with `-` for descending order
- Multiple fields separated by comma

## Webhooks

### Register Webhook

```http
POST /api/v1/webhooks
Content-Type: application/json

{
  "url": "https://your-app.com/webhook",
  "events": ["customer.created", "payment.received"],
  "secret": "webhook_secret_key"
}
```

### Webhook Payload

```json
{
  "id": "evt_123",
  "type": "customer.created",
  "timestamp": "2024-08-24T20:00:00Z",
  "data": {
    "customer_id": "cust_123",
    "email": "new@example.com"
  },
  "signature": "sha256=..."
}
```

### Verify Webhook Signature

```python
import hmac
import hashlib

def verify_webhook(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## API Versioning

The API uses URL versioning:
- Current: `/api/v1/`
- Previous: `/api/v0/` (deprecated)

Version sunset notice provided via:
```http
Sunset: Sat, 31 Dec 2024 23:59:59 GMT
Deprecation: true
Link: <https://docs.dotmac.cloud/api/migration>; rel="deprecation"
```

## SDK & Client Libraries

### Python

```python
from dotmac import Client

client = Client(
    api_key="your_api_key",
    tenant_id="tenant_001"
)

# List customers
customers = client.customers.list(status="active")

# Create invoice
invoice = client.invoices.create(
    customer_id="cust_123",
    amount=49.99
)
```

### JavaScript/TypeScript

```typescript
import { DotMacClient } from '@dotmac/sdk';

const client = new DotMacClient({
  apiKey: 'your_api_key',
  tenantId: 'tenant_001'
});

// Async/await
const customers = await client.customers.list({ status: 'active' });

// Promises
client.invoices.create({
  customerId: 'cust_123',
  amount: 49.99
}).then(invoice => {
  console.log(invoice);
});
```

## Testing

### Sandbox Environment

Test endpoint: `https://sandbox.dotmac.cloud`
- Full API functionality
- Data reset daily
- Test credit cards accepted
- Rate limits relaxed

### Test Credentials

```json
{
  "email": "test@dotmac.cloud",
  "password": "test123",
  "tenant_id": "sandbox_tenant",
  "api_key": "test_pk_1234567890"
}
```

---

*API Version: 1.0*
*Last Updated: August 2024*
*OpenAPI Spec: [Download](https://api.dotmac.cloud/openapi.json)*
