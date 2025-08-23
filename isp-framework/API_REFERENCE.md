# DotMac ISP Framework - Complete API Reference

## Table of Contents
1. [API Overview](#api-overview)
2. [Portal ID APIs](#portal-id-apis)
3. [Module APIs](#module-apis)
4. [Authentication](#authentication)
5. [Response Formats](#response-formats)
6. [Error Handling](#error-handling)
7. [Rate Limiting](#rate-limiting)
8. [Webhooks](#webhooks)

## API Overview

The DotMac ISP Framework provides comprehensive REST APIs for all business operations. APIs are organized into two main categories:

- **Admin APIs**: For system administration and back-office operations
- **Portal APIs**: For customer-facing portal operations using Portal ID authentication

### Base URLs

```
Admin API:  https://api.yourisp.com/api/v1/
Portal API: https://api.yourisp.com/api/portal/v1/
```

### API Versioning

APIs use path-based versioning with backward compatibility guarantees:
- Current version: `v1`
- Deprecation notice: 6 months before removal
- Migration guides provided for breaking changes

## Portal ID APIs

The Portal ID APIs provide customer-facing functionality using Portal ID authentication.

### Portal Authentication

#### POST /api/portal/v1/auth/login
Authenticate using Portal ID and password.

**Request:**
```json
{
    "portal_id": "ABC12345",
    "password": "customer_password",
    "two_factor_code": "123456",
    "device_fingerprint": "unique_device_id",
    "remember_me": false
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
        "expires_in": 3600,
        "token_type": "bearer",
        "portal_id": "ABC12345",
        "account_type": "customer",
        "require_password_change": false,
        "require_two_factor": false,
        "two_factor_methods": ["totp"]
    },
    "message": "Login successful"
}
```

**Error Responses:**
- `400`: Invalid credentials
- `423`: Account locked
- `428`: Two-factor authentication required

#### POST /api/portal/v1/auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "expires_in": 3600,
        "token_type": "bearer"
    }
}
```

#### POST /api/portal/v1/auth/logout
Logout and invalidate current session.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "success": true,
    "message": "Logged out successfully"
}
```

### Portal Account Management

#### GET /api/portal/v1/account/profile
Get current customer's profile information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "success": true,
    "data": {
        "portal_id": "ABC12345",
        "customer": {
            "id": "uuid-customer-id",
            "customer_number": "CUST-001",
            "display_name": "John Smith",
            "customer_type": "residential",
            "account_status": "active",
            "email": "john@example.com",
            "phone": "+1-555-0123"
        },
        "account_settings": {
            "two_factor_enabled": true,
            "email_notifications": true,
            "sms_notifications": false,
            "theme_preference": "light",
            "language_preference": "en",
            "timezone_preference": "America/New_York"
        }
    }
}
```

#### PUT /api/portal/v1/account/profile
Update customer profile information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "email": "newemail@example.com",
    "phone": "+1-555-9876",
    "email_notifications": false,
    "theme_preference": "dark"
}
```

#### POST /api/portal/v1/account/change-password
Change Portal ID account password.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "current_password": "old_password",
    "new_password": "new_secure_password",
    "confirm_password": "new_secure_password"
}
```

### Portal Services

#### GET /api/portal/v1/services
Get customer's active services.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `status`: Filter by service status (active, suspended, pending)
- `type`: Filter by service type (internet, phone, tv, bundle)

**Response:**
```json
{
    "success": true,
    "data": {
        "services": [
            {
                "id": "uuid-service-id",
                "service_type": "internet",
                "plan_name": "High-Speed Internet 100Mbps",
                "status": "active",
                "monthly_price": 59.99,
                "installation_date": "2024-01-01T00:00:00Z",
                "next_billing_date": "2024-02-01T00:00:00Z",
                "bandwidth": {
                    "download": 100,
                    "upload": 20,
                    "unit": "mbps"
                },
                "data_usage": {
                    "current_month": 850.5,
                    "limit": null,
                    "unit": "gb"
                }
            }
        ],
        "total": 1
    }
}
```

#### GET /api/portal/v1/services/{service_id}/usage
Get detailed usage statistics for a service.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `period`: Usage period (daily, weekly, monthly)
- `start_date`: Start date for usage query
- `end_date`: End date for usage query

**Response:**
```json
{
    "success": true,
    "data": {
        "service_id": "uuid-service-id",
        "period": "monthly",
        "usage_data": [
            {
                "date": "2024-01-01",
                "download": 25.6,
                "upload": 5.2,
                "total": 30.8,
                "unit": "gb"
            }
        ],
        "summary": {
            "total_download": 850.5,
            "total_upload": 180.2,
            "total_usage": 1030.7,
            "average_daily": 33.25,
            "peak_usage": 45.8,
            "unit": "gb"
        }
    }
}
```

### Portal Billing

#### GET /api/portal/v1/billing/invoices
Get customer's invoices.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `status`: Filter by invoice status (pending, paid, overdue)
- `start_date`: Filter invoices from date
- `end_date`: Filter invoices to date
- `limit`: Number of invoices to return (default: 20)
- `offset`: Pagination offset

**Response:**
```json
{
    "success": true,
    "data": {
        "invoices": [
            {
                "id": "uuid-invoice-id",
                "invoice_number": "INV-2024-001",
                "status": "paid",
                "issue_date": "2024-01-01T00:00:00Z",
                "due_date": "2024-01-31T00:00:00Z",
                "paid_date": "2024-01-15T10:30:00Z",
                "subtotal": 59.99,
                "tax": 4.80,
                "total": 64.79,
                "line_items": [
                    {
                        "description": "High-Speed Internet 100Mbps",
                        "service_period": "2024-01-01 to 2024-01-31",
                        "quantity": 1,
                        "unit_price": 59.99,
                        "total": 59.99
                    }
                ]
            }
        ],
        "total": 12,
        "summary": {
            "total_outstanding": 0.00,
            "next_due_date": "2024-02-01T00:00:00Z",
            "average_monthly": 64.79
        }
    }
}
```

#### GET /api/portal/v1/billing/invoices/{invoice_id}/pdf
Download invoice as PDF.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="invoice-INV-2024-001.pdf"`

#### GET /api/portal/v1/billing/payments
Get payment history.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "success": true,
    "data": {
        "payments": [
            {
                "id": "uuid-payment-id",
                "invoice_number": "INV-2024-001",
                "amount": 64.79,
                "payment_method": "credit_card",
                "payment_date": "2024-01-15T10:30:00Z",
                "status": "completed",
                "transaction_id": "txn_abc123",
                "last_four": "4242"
            }
        ],
        "total": 12,
        "payment_methods": [
            {
                "id": "pm_card123",
                "type": "credit_card",
                "last_four": "4242",
                "brand": "visa",
                "expires": "12/25",
                "is_default": true
            }
        ]
    }
}
```

#### POST /api/portal/v1/billing/payments
Make a payment.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "invoice_id": "uuid-invoice-id",
    "amount": 64.79,
    "payment_method_id": "pm_card123",
    "save_payment_method": false
}
```

### Portal Support

#### GET /api/portal/v1/support/tickets
Get customer's support tickets.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `status`: Filter by ticket status (open, in_progress, resolved, closed)
- `priority`: Filter by priority (low, medium, high, critical)

**Response:**
```json
{
    "success": true,
    "data": {
        "tickets": [
            {
                "id": "uuid-ticket-id",
                "ticket_number": "TKT-2024-001",
                "subject": "Internet Connection Issues",
                "status": "in_progress",
                "priority": "high",
                "category": "technical",
                "created_date": "2024-01-15T09:00:00Z",
                "last_update": "2024-01-15T14:30:00Z",
                "assigned_technician": "Tech Support",
                "sla_due_date": "2024-01-16T09:00:00Z"
            }
        ],
        "total": 5
    }
}
```

#### POST /api/portal/v1/support/tickets
Create a new support ticket.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "subject": "Internet Speed Issues",
    "category": "technical",
    "priority": "medium",
    "description": "My internet speed is much slower than expected...",
    "service_id": "uuid-service-id"
}
```

#### GET /api/portal/v1/support/tickets/{ticket_id}
Get ticket details with comments.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "success": true,
    "data": {
        "ticket": {
            "id": "uuid-ticket-id",
            "ticket_number": "TKT-2024-001",
            "subject": "Internet Connection Issues",
            "status": "in_progress",
            "priority": "high",
            "category": "technical",
            "description": "Detailed issue description...",
            "created_date": "2024-01-15T09:00:00Z",
            "service_affected": {
                "id": "uuid-service-id",
                "type": "internet",
                "plan_name": "High-Speed Internet 100Mbps"
            },
            "comments": [
                {
                    "id": "uuid-comment-id",
                    "author": "customer",
                    "author_name": "John Smith",
                    "message": "The issue started yesterday morning...",
                    "timestamp": "2024-01-15T09:00:00Z",
                    "is_internal": false
                },
                {
                    "id": "uuid-comment-id-2",
                    "author": "technician",
                    "author_name": "Tech Support",
                    "message": "We're investigating the issue in your area.",
                    "timestamp": "2024-01-15T14:30:00Z",
                    "is_internal": false
                }
            ]
        }
    }
}
```

#### POST /api/portal/v1/support/tickets/{ticket_id}/comments
Add comment to ticket.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "message": "The issue is still occurring as of this morning."
}
```

## Module APIs

The Admin APIs provide comprehensive access to all system functionality for back-office operations.

### Identity Module APIs

#### Users Management

**GET /api/v1/identity/users**
List system users with pagination and filtering.

**Query Parameters:**
- `role`: Filter by user role
- `active`: Filter by active status
- `search`: Search in name/email
- `limit`: Items per page (default: 20)
- `offset`: Pagination offset

**Response:**
```json
{
    "success": true,
    "data": {
        "users": [
            {
                "id": "uuid-user-id",
                "username": "admin",
                "email": "admin@isp.com",
                "first_name": "Admin",
                "last_name": "User",
                "roles": ["tenant_admin"],
                "is_active": true,
                "last_login": "2024-01-15T10:30:00Z",
                "created_at": "2024-01-01T00:00:00Z"
            }
        ],
        "total": 25,
        "limit": 20,
        "offset": 0
    }
}
```

**POST /api/v1/identity/users**
Create new system user.

**Request:**
```json
{
    "username": "new_user",
    "email": "user@isp.com",
    "password": "secure_password",
    "first_name": "John",
    "last_name": "Doe",
    "roles": ["support"],
    "phone": "+1-555-0123",
    "timezone": "America/New_York"
}
```

#### Customers Management

**GET /api/v1/identity/customers**
List customers with advanced filtering.

**Query Parameters:**
- `customer_type`: residential, business, enterprise
- `status`: active, suspended, pending, cancelled
- `search`: Search in name/email/customer_number
- `limit`: Items per page
- `offset`: Pagination offset

**POST /api/v1/identity/customers**
Create new customer with automatic Portal ID.

**Request:**
```json
{
    "customer_type": "residential",
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane@example.com",
    "phone": "+1-555-0124",
    "address": {
        "street": "123 Main St",
        "city": "Anytown",
        "state": "ST",
        "postal_code": "12345",
        "country": "US"
    },
    "service_address": "Same as billing",
    "create_portal_account": true,
    "portal_password": "temp_password123"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "customer": {
            "id": "uuid-customer-id",
            "customer_number": "CUST-002",
            "display_name": "Jane Smith",
            "customer_type": "residential",
            "account_status": "pending",
            "email": "jane@example.com",
            "phone": "+1-555-0124"
        },
        "portal_account": {
            "portal_id": "DEF67890",
            "status": "pending_activation",
            "activation_required": true
        }
    },
    "message": "Customer created successfully with Portal ID: DEF67890"
}
```

### Billing Module APIs

#### Invoices Management

**GET /api/v1/billing/invoices**
List all invoices with filtering and search.

**Query Parameters:**
- `customer_id`: Filter by customer
- `status`: pending, paid, overdue, cancelled
- `date_from`: Invoice issue date from
- `date_to`: Invoice issue date to
- `amount_min`: Minimum invoice amount
- `amount_max`: Maximum invoice amount

**POST /api/v1/billing/invoices**
Create new invoice.

**Request:**
```json
{
    "customer_id": "uuid-customer-id",
    "due_date": "2024-02-01",
    "line_items": [
        {
            "service_id": "uuid-service-id",
            "description": "High-Speed Internet 100Mbps",
            "quantity": 1,
            "unit_price": 59.99,
            "tax_rate": 0.08
        }
    ],
    "notes": "Monthly service charge"
}
```

**POST /api/v1/billing/invoices/{invoice_id}/send**
Send invoice to customer via email.

**POST /api/v1/billing/invoices/{invoice_id}/void**
Void an invoice (admin only).

#### Payments Management

**GET /api/v1/billing/payments**
List all payments with filtering.

**POST /api/v1/billing/payments/{payment_id}/refund**
Process payment refund.

**Request:**
```json
{
    "amount": 30.00,
    "reason": "Service downtime credit",
    "refund_method": "original_payment_method"
}
```

### Services Module APIs

#### Service Catalog Management

**GET /api/v1/services/catalog**
Get complete service catalog.

**Response:**
```json
{
    "success": true,
    "data": {
        "services": [
            {
                "id": "uuid-service-id",
                "name": "High-Speed Internet 100Mbps",
                "service_type": "internet",
                "description": "Residential high-speed internet service",
                "monthly_price": 59.99,
                "setup_fee": 99.00,
                "features": {
                    "download_speed": 100,
                    "upload_speed": 20,
                    "data_limit": null,
                    "static_ip": false
                },
                "availability": {
                    "residential": true,
                    "business": true,
                    "enterprise": false
                }
            }
        ]
    }
}
```

**POST /api/v1/services/catalog**
Add new service to catalog.

#### Service Instances Management

**GET /api/v1/services/instances**
List active service instances.

**POST /api/v1/services/instances**
Provision new service for customer.

**Request:**
```json
{
    "customer_id": "uuid-customer-id",
    "service_id": "uuid-service-id",
    "installation_date": "2024-02-01",
    "configuration": {
        "static_ip": true,
        "additional_emails": 5
    },
    "notes": "Customer requested static IP"
}
```

**PUT /api/v1/services/instances/{instance_id}/status**
Update service status (activate, suspend, terminate).

**Request:**
```json
{
    "status": "suspended",
    "reason": "Non-payment",
    "notes": "Account 30 days overdue",
    "effective_date": "2024-01-16T00:00:00Z"
}
```

### Support Module APIs

#### Tickets Management

**GET /api/v1/support/tickets**
List all support tickets with advanced filtering.

**Query Parameters:**
- `status`: open, in_progress, resolved, closed
- `priority`: low, medium, high, critical
- `category`: technical, billing, sales, general
- `assigned_to`: Filter by assigned technician
- `created_from`: Ticket creation date from
- `created_to`: Ticket creation date to
- `sla_breach`: true/false for SLA breached tickets

**POST /api/v1/support/tickets**
Create ticket (admin/support staff).

**PUT /api/v1/support/tickets/{ticket_id}/assign**
Assign ticket to technician.

**Request:**
```json
{
    "assigned_to": "uuid-user-id",
    "priority": "high",
    "sla_hours": 24,
    "notes": "Escalating due to service impact"
}
```

**POST /api/v1/support/tickets/{ticket_id}/close**
Close ticket with resolution.

**Request:**
```json
{
    "resolution": "Issue resolved by replacing network equipment",
    "resolution_category": "hardware_replacement",
    "customer_satisfaction": 5,
    "follow_up_required": false
}
```

#### Knowledge Base Management

**GET /api/v1/support/knowledge-base**
Get knowledge base articles.

**POST /api/v1/support/knowledge-base**
Create new knowledge base article.

### Analytics Module APIs

#### Dashboards

**GET /api/v1/analytics/dashboards/overview**
Get business overview dashboard data.

**Response:**
```json
{
    "success": true,
    "data": {
        "kpis": {
            "total_customers": 1250,
            "active_services": 1450,
            "monthly_revenue": 87500.00,
            "customer_satisfaction": 4.2,
            "network_uptime": 99.95
        },
        "trends": {
            "customer_growth": {
                "period": "12_months",
                "data": [
                    {"month": "2023-02", "customers": 1100},
                    {"month": "2023-03", "customers": 1125}
                ]
            },
            "revenue_trend": {
                "period": "12_months",
                "data": [
                    {"month": "2023-02", "revenue": 82000.00},
                    {"month": "2023-03", "revenue": 84500.00}
                ]
            }
        }
    }
}
```

**GET /api/v1/analytics/reports/custom**
Generate custom reports.

**Query Parameters:**
- `report_type`: revenue, customers, services, support
- `date_from`: Report period start
- `date_to`: Report period end
- `group_by`: day, week, month, quarter
- `filters`: JSON object with report filters

## Authentication

### JWT Token Authentication

All API requests require authentication using JWT tokens in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Token Payload Structure

**Access Token:**
```json
{
    "sub": "uuid-user-id",
    "tenant_id": "uuid-tenant-id",
    "roles": ["tenant_admin"],
    "permissions": ["customers:read", "invoices:create"],
    "exp": 1705315200,
    "iat": 1705311600,
    "type": "access"
}
```

**Portal Token:**
```json
{
    "sub": "uuid-portal-account-id",
    "portal_id": "ABC12345",
    "tenant_id": "uuid-tenant-id",
    "session_id": "uuid-session-id",
    "account_type": "customer",
    "exp": 1705315200,
    "type": "access"
}
```

### Token Refresh

When access token expires, use refresh token to obtain new access token:

```bash
curl -X POST \
  https://api.yourisp.com/api/v1/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token": "your-refresh-token"}'
```

## Response Formats

### Success Response

All successful API responses follow this format:

```json
{
    "success": true,
    "data": { ... },
    "message": "Operation completed successfully",
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-request-id",
    "pagination": {
        "total": 100,
        "limit": 20,
        "offset": 0,
        "has_more": true
    }
}
```

### Error Response

All error responses follow this format:

```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input data",
        "details": {
            "field": "email",
            "issue": "Invalid email format",
            "provided": "invalid-email"
        }
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-request-id"
}
```

### Pagination

Paginated responses include pagination metadata:

```json
{
    "data": [...],
    "pagination": {
        "total": 250,
        "limit": 20,
        "offset": 40,
        "has_more": true,
        "next_offset": 60,
        "prev_offset": 20
    }
}
```

## Error Handling

### HTTP Status Codes

- `200`: OK - Request successful
- `201`: Created - Resource created successfully
- `204`: No Content - Request successful, no content returned
- `400`: Bad Request - Invalid request data
- `401`: Unauthorized - Authentication required
- `403`: Forbidden - Access denied
- `404`: Not Found - Resource not found
- `409`: Conflict - Resource conflict (duplicate, constraint violation)
- `422`: Unprocessable Entity - Validation errors
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - System error

### Error Codes

| Code | Description |
|------|-------------|
| VALIDATION_ERROR | Invalid input data |
| AUTHENTICATION_REQUIRED | Valid authentication required |
| ACCESS_DENIED | Insufficient permissions |
| RESOURCE_NOT_FOUND | Requested resource not found |
| DUPLICATE_RESOURCE | Resource already exists |
| RATE_LIMIT_EXCEEDED | Too many requests |
| PORTAL_ID_NOT_FOUND | Portal ID does not exist |
| ACCOUNT_LOCKED | Portal account is locked |
| PAYMENT_FAILED | Payment processing failed |
| SERVICE_UNAVAILABLE | External service unavailable |

## Rate Limiting

API rate limits are enforced per user/IP combination:

### Rate Limit Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1705315200
```

### Rate Limits by Endpoint Type

- **Portal Authentication**: 10 requests/minute per IP
- **Portal APIs**: 100 requests/minute per Portal ID
- **Admin APIs**: 1000 requests/minute per user
- **File Uploads**: 10 requests/minute per user
- **Report Generation**: 5 requests/minute per user

### Rate Limit Exceeded Response

```json
{
    "success": false,
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Rate limit exceeded. Try again later.",
        "details": {
            "limit": 100,
            "reset_time": "2024-01-15T10:31:00Z"
        }
    }
}
```

## Webhooks

The system supports webhooks for real-time event notifications.

### Webhook Events

- `customer.created` - New customer account created
- `customer.updated` - Customer information updated
- `service.activated` - Service activated for customer
- `service.suspended` - Service suspended
- `invoice.created` - New invoice generated
- `invoice.paid` - Invoice payment received
- `ticket.created` - New support ticket created
- `ticket.resolved` - Support ticket resolved
- `payment.failed` - Payment processing failed

### Webhook Payload Format

```json
{
    "event": "customer.created",
    "timestamp": "2024-01-15T10:30:00Z",
    "tenant_id": "uuid-tenant-id",
    "data": {
        "customer": {
            "id": "uuid-customer-id",
            "customer_number": "CUST-002",
            "portal_id": "DEF67890",
            "display_name": "Jane Smith",
            "customer_type": "residential"
        }
    },
    "webhook_id": "uuid-webhook-id"
}
```

### Webhook Configuration

**POST /api/v1/webhooks**
Create webhook endpoint.

**Request:**
```json
{
    "url": "https://your-system.com/webhooks/dotmac",
    "events": ["customer.created", "invoice.paid"],
    "secret": "webhook_secret_key",
    "active": true
}
```

This API reference provides comprehensive access to all DotMac ISP Framework functionality, enabling integration with existing business systems and custom applications.