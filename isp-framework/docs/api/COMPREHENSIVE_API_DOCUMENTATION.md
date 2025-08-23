# DotMac ISP Framework - Comprehensive API Documentation

**Version:** 1.0.0  
**Last Updated:** 2024-08-22  
**Quality Sprint:** Week 4 - Standards & Documentation  

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Core Modules](#core-modules)
4. [Service APIs](#service-apis)
5. [SDK Documentation](#sdk-documentation)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Security Considerations](#security-considerations)
9. [Examples and Use Cases](#examples-and-use-cases)

## Overview

The DotMac ISP Framework provides a comprehensive REST API for managing telecommunications services, customer relationships, billing, network infrastructure, and analytics. All APIs follow RESTful principles and return JSON responses.

### Base URLs

```
Production:    https://api.dotmac.com/v1
Staging:       https://staging-api.dotmac.com/v1
Development:   http://localhost:8000/api/v1
```

### API Versioning

- **Current Version**: v1
- **Version Header**: `API-Version: v1`
- **URL Versioning**: `/api/v1/`

### Content Types

- **Request**: `application/json`
- **Response**: `application/json`
- **File Uploads**: `multipart/form-data`

## Authentication

### JWT Authentication

All API endpoints require JWT authentication unless otherwise specified.

```http
Authorization: Bearer <jwt_token>
```

#### Obtaining Tokens

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password",
  "tenant_id": "tenant_123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "user_uuid",
    "username": "user@example.com",
    "roles": ["admin", "technician"]
  }
}
```

#### Token Refresh

```http
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>
```

### Multi-Tenant Architecture

All requests must include tenant identification:

```http
X-Tenant-ID: tenant_123
```

## Core Modules

### Identity Management

#### Customer Management

**Create Customer**
```http
POST /api/v1/identity/customers
Content-Type: application/json
Authorization: Bearer <token>
X-Tenant-ID: <tenant_id>

{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "organization_type": "residential",
  "customer_type": "individual",
  "billing_address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "postal_code": "12345",
    "country": "USA"
  }
}
```

**Response:**
```json
{
  "id": "customer_uuid",
  "portal_id": "CUST-2024-001234",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "status": "active",
  "created_at": "2024-08-22T10:30:00Z",
  "billing_address": {
    "id": "address_uuid",
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "postal_code": "12345",
    "country": "USA"
  }
}
```

**Get Customer**
```http
GET /api/v1/identity/customers/{customer_id}
Authorization: Bearer <token>
X-Tenant-ID: <tenant_id>
```

**List Customers**
```http
GET /api/v1/identity/customers?page=1&size=50&status=active
Authorization: Bearer <token>
X-Tenant-ID: <tenant_id>
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `size`: Page size (default: 50, max: 100)
- `status`: Filter by status (`active`, `inactive`, `suspended`)
- `customer_type`: Filter by type (`individual`, `business`)
- `search`: Search by name or email

#### User Management

**Create User**
```http
POST /api/v1/identity/users
Content-Type: application/json

{
  "username": "tech.user@company.com",
  "email": "tech.user@company.com",
  "first_name": "Tech",
  "last_name": "User",
  "password": "SecurePassword123!",
  "roles": ["technician"],
  "is_active": true
}
```

### Billing System

#### Invoice Management

**Create Invoice**
```http
POST /api/v1/billing/invoices
Content-Type: application/json

{
  "customer_id": "customer_uuid",
  "billing_period_start": "2024-08-01",
  "billing_period_end": "2024-08-31",
  "due_date": "2024-09-15",
  "line_items": [
    {
      "service_id": "service_uuid",
      "description": "Internet Service - 100Mbps",
      "quantity": 1,
      "unit_price": 59.99,
      "tax_rate": 0.08
    }
  ]
}
```

**Response:**
```json
{
  "id": "invoice_uuid",
  "invoice_number": "INV-2024-001234",
  "customer_id": "customer_uuid",
  "status": "draft",
  "subtotal": 59.99,
  "tax_amount": 4.80,
  "total_amount": 64.79,
  "due_date": "2024-09-15",
  "line_items": [
    {
      "id": "line_item_uuid",
      "description": "Internet Service - 100Mbps",
      "quantity": 1,
      "unit_price": 59.99,
      "total_price": 59.99,
      "tax_amount": 4.80
    }
  ],
  "created_at": "2024-08-22T10:30:00Z"
}
```

**Process Payment**
```http
POST /api/v1/billing/invoices/{invoice_id}/payments
Content-Type: application/json

{
  "payment_method": "credit_card",
  "amount": 64.79,
  "payment_source": {
    "card_number": "****-****-****-1234",
    "payment_token": "payment_token_from_gateway"
  }
}
```

### Service Management

#### Service Provisioning

**Create Service Order**
```http
POST /api/v1/services/orders
Content-Type: application/json

{
  "customer_id": "customer_uuid",
  "service_type": "internet",
  "plan_id": "plan_uuid",
  "installation_address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "postal_code": "12345"
  },
  "installation_date": "2024-08-30",
  "technical_specifications": {
    "bandwidth_down": "100Mbps",
    "bandwidth_up": "10Mbps",
    "technology": "fiber"
  }
}
```

**Response:**
```json
{
  "id": "order_uuid",
  "order_number": "ORD-2024-001234",
  "customer_id": "customer_uuid",
  "status": "pending",
  "service_type": "internet",
  "estimated_completion": "2024-08-30T16:00:00Z",
  "workflow_steps": [
    {
      "step": "technical_survey",
      "status": "pending",
      "estimated_duration": "2 hours"
    },
    {
      "step": "equipment_installation",
      "status": "pending",
      "estimated_duration": "4 hours"
    }
  ],
  "created_at": "2024-08-22T10:30:00Z"
}
```

### Network Management

#### Device Management

**Register Network Device**
```http
POST /api/v1/network/devices
Content-Type: application/json

{
  "device_type": "router",
  "manufacturer": "Cisco",
  "model": "ISR4331",
  "serial_number": "ABC123456789",
  "ip_address": "192.168.1.1",
  "location": "Main Office",
  "snmp_community": "public",
  "management_credentials": {
    "username": "admin",
    "password_secret_id": "device_admin_password"
  }
}
```

**Get Device Status**
```http
GET /api/v1/network/devices/{device_id}/status
Authorization: Bearer <token>
X-Tenant-ID: <tenant_id>
```

**Response:**
```json
{
  "device_id": "device_uuid",
  "status": "online",
  "uptime": "15 days, 8 hours",
  "cpu_utilization": 15.2,
  "memory_utilization": 42.8,
  "interface_status": [
    {
      "interface": "GigabitEthernet0/0/0",
      "status": "up",
      "speed": "1000Mbps",
      "utilization": {
        "in": 125.5,
        "out": 89.2
      }
    }
  ],
  "last_updated": "2024-08-22T10:29:45Z"
}
```

### Omnichannel Communications

#### Customer Interactions

**Create Interaction**
```http
POST /api/v1/omnichannel/interactions
Content-Type: application/json

{
  "customer_id": "customer_uuid",
  "contact_id": "contact_uuid",
  "interaction_type": "email",
  "channel": "support_email",
  "subject": "Internet Service Issue",
  "content": "Customer is experiencing intermittent connectivity issues.",
  "priority": "high",
  "metadata": {
    "source_email": "customer@example.com",
    "category": "technical_support"
  }
}
```

**Response:**
```json
{
  "id": "interaction_uuid",
  "interaction_number": "INT-2024-001234",
  "customer_id": "customer_uuid",
  "status": "open",
  "assigned_agent": null,
  "created_at": "2024-08-22T10:30:00Z",
  "estimated_response_time": "2 hours",
  "sla_deadline": "2024-08-22T18:30:00Z"
}
```

**Assign Agent**
```http
PUT /api/v1/omnichannel/interactions/{interaction_id}/assign
Content-Type: application/json

{
  "agent_id": "agent_uuid",
  "assignment_reason": "routing_algorithm",
  "priority_override": false
}
```

#### Agent Management

**Create Agent**
```http
POST /api/v1/omnichannel/agents
Content-Type: application/json

{
  "user_id": "user_uuid",
  "employee_id": "EMP001",
  "display_name": "John Smith",
  "skills": ["email", "chat", "phone", "technical_support"],
  "languages": ["en", "es"],
  "max_concurrent_interactions": 5,
  "working_hours": {
    "timezone": "America/New_York",
    "schedule": {
      "monday": {"start": "09:00", "end": "17:00"},
      "tuesday": {"start": "09:00", "end": "17:00"}
    }
  }
}
```

### Analytics and Reporting

#### Dashboard Metrics

**Get Dashboard Summary**
```http
GET /api/v1/analytics/dashboard/summary?period=last_30_days
Authorization: Bearer <token>
X-Tenant-ID: <tenant_id>
```

**Response:**
```json
{
  "period": "last_30_days",
  "metrics": {
    "total_customers": 1250,
    "new_customers": 45,
    "churn_rate": 2.3,
    "revenue": {
      "total": 125000.00,
      "recurring": 118000.00,
      "one_time": 7000.00
    },
    "service_metrics": {
      "active_services": 1180,
      "service_availability": 99.8,
      "average_response_time": "12 minutes"
    },
    "support_metrics": {
      "total_interactions": 342,
      "resolved_interactions": 318,
      "average_resolution_time": "2.4 hours",
      "customer_satisfaction": 4.2
    }
  },
  "generated_at": "2024-08-22T10:30:00Z"
}
```

**Generate Custom Report**
```http
POST /api/v1/analytics/reports
Content-Type: application/json

{
  "report_type": "customer_analytics",
  "date_range": {
    "start": "2024-08-01",
    "end": "2024-08-31"
  },
  "filters": {
    "customer_type": "business",
    "service_status": "active"
  },
  "metrics": [
    "revenue_per_customer",
    "service_utilization",
    "support_ticket_volume"
  ],
  "format": "json"
}
```

## SDK Documentation

### Core SDK Usage

```python
from dotmac_isp.sdks.core import DotMacClient

# Initialize client
client = DotMacClient(
    base_url="https://api.dotmac.com",
    api_key="your_api_key",
    tenant_id="tenant_123"
)

# Customer operations
customer = await client.identity.customers.create({
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com"
})

# Service provisioning
service_order = await client.services.orders.create({
    "customer_id": customer.id,
    "service_type": "internet",
    "plan_id": "plan_uuid"
})

# Network monitoring
device_status = await client.networking.devices.get_status("device_uuid")
```

### Billing SDK

```python
from dotmac_isp.sdks.billing import BillingClient

billing = BillingClient(client)

# Create invoice
invoice = await billing.invoices.create({
    "customer_id": "customer_uuid",
    "line_items": [
        {
            "description": "Internet Service",
            "amount": 59.99
        }
    ]
})

# Process payment
payment = await billing.payments.process({
    "invoice_id": invoice.id,
    "payment_method": "credit_card",
    "amount": 59.99
})
```

### Analytics SDK

```python
from dotmac_isp.sdks.analytics import AnalyticsClient

analytics = AnalyticsClient(client)

# Get dashboard metrics
dashboard = await analytics.dashboard.get_summary(period="last_30_days")

# Create custom report
report = await analytics.reports.generate({
    "report_type": "revenue_analysis",
    "date_range": {"start": "2024-08-01", "end": "2024-08-31"}
})
```

## Error Handling

### Standard Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format",
        "code": "INVALID_FORMAT"
      }
    ],
    "request_id": "req_uuid",
    "timestamp": "2024-08-22T10:30:00Z"
  }
}
```

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|-------|
| 200 | OK | Successful GET, PUT, PATCH requests |
| 201 | Created | Successful POST requests |
| 204 | No Content | Successful DELETE requests |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource conflict (duplicate) |
| 422 | Unprocessable Entity | Validation errors |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_ERROR` | Authentication failed |
| `AUTHORIZATION_ERROR` | Insufficient permissions |
| `VALIDATION_ERROR` | Input validation failed |
| `NOT_FOUND` | Resource not found |
| `DUPLICATE_RESOURCE` | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | API rate limit exceeded |
| `SERVICE_UNAVAILABLE` | External service unavailable |
| `INTERNAL_ERROR` | Internal server error |

## Rate Limiting

### Rate Limit Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1692705600
```

### Rate Limit Tiers

| Tier | Requests/Hour | Burst |
|------|---------------|-------|
| Basic | 1,000 | 100 |
| Professional | 10,000 | 500 |
| Enterprise | 100,000 | 2,000 |

### Rate Limit Exceeded Response

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1692705600

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "retry_after": 3600
  }
}
```

## Security Considerations

### Request Signing (Optional)

For high-security environments, requests can be signed using HMAC-SHA256:

```http
X-Signature: sha256=<signature>
X-Timestamp: 1692705600
```

### IP Whitelisting

Configure IP restrictions in tenant settings:

```json
{
  "allowed_ips": [
    "192.168.1.0/24",
    "10.0.0.100"
  ]
}
```

### Audit Logging

All API requests are logged for security and compliance:

```json
{
  "timestamp": "2024-08-22T10:30:00Z",
  "request_id": "req_uuid",
  "user_id": "user_uuid",
  "tenant_id": "tenant_123",
  "method": "POST",
  "endpoint": "/api/v1/customers",
  "ip_address": "192.168.1.100",
  "user_agent": "DotMac-SDK/1.0.0",
  "response_status": 201
}
```

## Examples and Use Cases

### Complete Customer Onboarding Workflow

```python
# 1. Create customer
customer = await client.identity.customers.create({
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane.smith@example.com",
    "phone": "+1234567890"
})

# 2. Create service order
service_order = await client.services.orders.create({
    "customer_id": customer.id,
    "service_type": "internet",
    "plan_id": "high_speed_plan"
})

# 3. Schedule installation
installation = await client.services.installations.schedule({
    "service_order_id": service_order.id,
    "installation_date": "2024-08-30T14:00:00Z",
    "technician_id": "tech_uuid"
})

# 4. Generate welcome materials
welcome_packet = await client.communications.send_welcome({
    "customer_id": customer.id,
    "service_details": service_order
})
```

### Network Monitoring and Alerting

```python
# Monitor device health
async def monitor_device_health(device_id):
    status = await client.networking.devices.get_status(device_id)
    
    if status.cpu_utilization > 80:
        await client.alerts.create({
            "type": "high_cpu_usage",
            "device_id": device_id,
            "severity": "warning",
            "message": f"CPU usage is {status.cpu_utilization}%"
        })
    
    if status.status == "offline":
        await client.alerts.create({
            "type": "device_offline",
            "device_id": device_id,
            "severity": "critical",
            "message": "Device is offline"
        })

# Bulk monitoring
devices = await client.networking.devices.list()
for device in devices:
    await monitor_device_health(device.id)
```

### Revenue Analytics and Reporting

```python
# Generate monthly revenue report
report = await client.analytics.reports.generate({
    "report_type": "revenue_summary",
    "date_range": {
        "start": "2024-08-01",
        "end": "2024-08-31"
    },
    "breakdown": ["service_type", "customer_segment"],
    "format": "json"
})

# Export customer churn analysis
churn_data = await client.analytics.churn.analyze({
    "period": "last_6_months",
    "include_predictions": True,
    "export_format": "csv"
})
```

### Support Ticket Automation

```python
# Auto-route support tickets
async def handle_new_interaction(interaction_data):
    interaction = await client.omnichannel.interactions.create(interaction_data)
    
    # Apply routing rules
    if "billing" in interaction.subject.lower():
        agent = await client.omnichannel.agents.find_available(
            skills=["billing"], 
            department="finance"
        )
    elif "technical" in interaction.content.lower():
        agent = await client.omnichannel.agents.find_available(
            skills=["technical_support"],
            certifications=["network_specialist"]
        )
    
    if agent:
        await client.omnichannel.interactions.assign(
            interaction.id, 
            agent.id
        )
    
    return interaction
```

This comprehensive API documentation provides developers with everything needed to integrate with the DotMac ISP Framework. For additional examples and advanced use cases, see the SDK documentation and developer guides.