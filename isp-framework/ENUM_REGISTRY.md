# DotMac ISP Framework - Enum Registry

## Table of Contents
1. [Overview](#overview)
2. [Identity Module Enums](#identity-module-enums)
3. [Portal Management Enums](#portal-management-enums)
4. [Billing Module Enums](#billing-module-enums)
5. [Services Module Enums](#services-module-enums)
6. [Support Module Enums](#support-module-enums)
7. [Plugin System Enums](#plugin-system-enums)
8. [Usage Guidelines](#usage-guidelines)
9. [Migration Considerations](#migration-considerations)

## Overview

This document provides a comprehensive registry of all enumeration types used throughout the DotMac ISP Framework. Enums provide type safety, consistent data representation, and clear business logic boundaries.

### Enum Standards

All enums in the framework follow these conventions:
- **Snake case values**: `"active"`, `"pending_activation"`
- **Descriptive names**: Clear business meaning
- **Immutable**: Values should not change after deployment
- **Database storage**: Stored as string values for readability
- **API representation**: JSON strings matching enum values

## Identity Module Enums

Location: `/src/dotmac_isp/modules/identity/models.py`

### UserRole

**Purpose**: Defines system user roles and access levels
**Database Column**: `users.roles` (via junction table)

```python
class UserRole(enum.Enum):
    SUPER_ADMIN = "super_admin"      # System-wide administrative access
    TENANT_ADMIN = "tenant_admin"    # Full tenant administrative access  
    MANAGER = "manager"              # Management-level access
    TECHNICIAN = "technician"        # Technical operations access
    SUPPORT = "support"              # Customer support access
    SALES = "sales"                  # Sales operations access
    CUSTOMER = "customer"            # Customer portal access (deprecated - use Portal ID)
```

**Business Rules**:
- `SUPER_ADMIN`: Cross-tenant access, system configuration
- `TENANT_ADMIN`: Full access within tenant boundary
- `MANAGER`: Business operations, reporting access
- `TECHNICIAN`: Field operations, technical support
- `SUPPORT`: Customer service, ticket management
- `SALES`: Lead management, customer acquisition
- `CUSTOMER`: Legacy role, replaced by Portal ID system

**API Usage**:
```json
{
    "roles": ["tenant_admin", "manager"]
}
```

**Migration Notes**: 
- `CUSTOMER` role is deprecated in favor of Portal ID authentication
- New roles should be added carefully to maintain security boundaries

### CustomerType

**Purpose**: Categorizes customers for billing and service delivery
**Database Column**: `customers.customer_type`

```python
class CustomerType(enum.Enum):
    RESIDENTIAL = "residential"      # Individual/household customers
    BUSINESS = "business"            # Small to medium businesses
    ENTERPRISE = "enterprise"       # Large enterprise customers
```

**Business Rules**:
- `RESIDENTIAL`: Individual consumers, residential pricing
- `BUSINESS`: Commercial customers, business-grade SLAs
- `ENTERPRISE`: Large organizations, custom contracts

**Service Implications**:
- Different pricing tiers per customer type
- SLA requirements vary by type
- Support prioritization based on type
- Available services filtered by type

### AccountStatus

**Purpose**: Tracks customer account lifecycle status
**Database Column**: `customers.account_status`

```python
class AccountStatus(enum.Enum):
    ACTIVE = "active"           # Account in good standing
    SUSPENDED = "suspended"     # Temporarily suspended (payment, policy violation)
    PENDING = "pending"         # New account, pending activation
    CANCELLED = "cancelled"     # Account permanently closed
```

**Business Rules**:
- `ACTIVE`: Services operational, billing active
- `SUSPENDED`: Services restricted, account recoverable
- `PENDING`: Initial state, requires activation
- `CANCELLED`: Final state, services terminated

**State Transitions**:
```
PENDING → ACTIVE → SUSPENDED → ACTIVE
PENDING → CANCELLED
SUSPENDED → CANCELLED
```

## Portal Management Enums

Location: `/src/dotmac_isp/modules/portal_management/models.py`

### PortalAccountStatus

**Purpose**: Manages Portal ID account authentication status
**Database Column**: `portal_accounts.status`

```python
class PortalAccountStatus(enum.Enum):
    ACTIVE = "active"                    # Account can authenticate
    SUSPENDED = "suspended"              # Account temporarily disabled
    LOCKED = "locked"                    # Account locked due to security issues
    PENDING_ACTIVATION = "pending_activation"  # New account, requires activation
    DEACTIVATED = "deactivated"          # Account permanently disabled
```

**Business Rules**:
- `ACTIVE`: Normal portal access, all features available
- `SUSPENDED`: Login blocked, account recoverable
- `LOCKED`: Temporary security lock (failed attempts, suspicious activity)
- `PENDING_ACTIVATION`: New Portal ID, requires email verification
- `DEACTIVATED`: Permanent disable, account archived

**Security Implications**:
- `LOCKED` status automatically applied after 5 failed login attempts
- Lock duration configurable per tenant (default: 30 minutes)
- `SUSPENDED` and `DEACTIVATED` require admin intervention
- Status changes logged in security audit trail

### PortalAccountType

**Purpose**: Categorizes Portal ID account types for access control
**Database Column**: `portal_accounts.account_type`

```python
class PortalAccountType(enum.Enum):
    CUSTOMER = "customer"        # Customer portal access
    TECHNICIAN = "technician"    # Technician mobile app access
    RESELLER = "reseller"        # Reseller portal access
```

**Access Patterns**:
- `CUSTOMER`: Customer portal, service management, billing
- `TECHNICIAN`: Work order access, field operations
- `RESELLER`: Partner portal, commission tracking

**Portal Routing**:
- Different login forms per account type
- Type-specific dashboard and features
- Role-based menu and permissions

## Billing Module Enums

Location: `/src/dotmac_isp/modules/billing/models.py`

### InvoiceStatus

**Purpose**: Tracks invoice lifecycle and payment status
**Database Column**: `invoices.status`

```python
class InvoiceStatus(enum.Enum):
    DRAFT = "draft"              # Invoice created, not yet sent
    PENDING = "pending"          # Invoice sent, awaiting payment
    PAID = "paid"                # Invoice fully paid
    PARTIALLY_PAID = "partially_paid"  # Partial payment received
    OVERDUE = "overdue"          # Invoice past due date
    CANCELLED = "cancelled"      # Invoice voided/cancelled
    REFUNDED = "refunded"        # Invoice payment refunded
```

**Payment Workflow**:
```
DRAFT → PENDING → PAID
DRAFT → CANCELLED
PENDING → PARTIALLY_PAID → PAID
PENDING → OVERDUE → PAID
PAID → REFUNDED
```

**Business Rules**:
- `OVERDUE` automatically set by scheduled job after due date
- `PARTIALLY_PAID` when payment amount < invoice total
- Status changes trigger customer notifications
- Payment gateway webhooks update status

### PaymentStatus

**Purpose**: Tracks individual payment transaction status
**Database Column**: `payments.status`

```python
class PaymentStatus(enum.Enum):
    PENDING = "pending"          # Payment initiated, processing
    PROCESSING = "processing"    # Payment gateway processing
    COMPLETED = "completed"      # Payment successful
    FAILED = "failed"            # Payment failed
    CANCELLED = "cancelled"      # Payment cancelled by user
    REFUNDED = "refunded"        # Payment refunded
    DISPUTED = "disputed"        # Payment disputed/chargeback
```

**Integration Points**:
- Payment gateway status mapping
- Retry logic for `FAILED` payments
- Customer notifications on status changes
- Accounting system synchronization

### PaymentMethod

**Purpose**: Defines supported payment methods
**Database Column**: `payments.payment_method`

```python
class PaymentMethod(enum.Enum):
    CREDIT_CARD = "credit_card"      # Credit/debit card payments
    BANK_TRANSFER = "bank_transfer"   # ACH/bank transfer
    CHECK = "check"                  # Physical check payments
    CASH = "cash"                    # Cash payments (office)
    CRYPTO = "crypto"                # Cryptocurrency payments
    PAYPAL = "paypal"                # PayPal payments
    APPLE_PAY = "apple_pay"          # Apple Pay
    GOOGLE_PAY = "google_pay"        # Google Pay
```

**Gateway Integration**:
- Different payment processors per method
- Method availability varies by customer type
- Fee structures vary by method
- Compliance requirements per method

### BillingCycle

**Purpose**: Defines recurring billing frequencies
**Database Column**: `subscriptions.billing_cycle`

```python
class BillingCycle(enum.Enum):
    MONTHLY = "monthly"          # Bill every month
    QUARTERLY = "quarterly"      # Bill every 3 months
    SEMI_ANNUAL = "semi_annual"  # Bill every 6 months
    ANNUAL = "annual"            # Bill every 12 months
    WEEKLY = "weekly"            # Bill every week
    BIWEEKLY = "biweekly"        # Bill every 2 weeks
```

**Billing Logic**:
- Proration calculations based on cycle
- Discount structures per cycle length
- Payment processing schedules
- Customer communication timing

### TaxType

**Purpose**: Categorizes tax types for compliance
**Database Column**: `invoice_line_items.tax_type`

```python
class TaxType(enum.Enum):
    SALES_TAX = "sales_tax"      # State/local sales tax
    VAT = "vat"                  # Value-added tax
    GST = "gst"                  # Goods and services tax
    EXEMPT = "exempt"            # Tax-exempt items
    FEDERAL_TAX = "federal_tax"  # Federal excise tax
```

**Compliance Requirements**:
- Tax calculation rules per type
- Reporting obligations by jurisdiction
- Customer type tax exemptions
- Audit trail requirements

## Services Module Enums

Location: `/src/dotmac_isp/modules/services/models.py`

### ServiceType

**Purpose**: Categorizes ISP service offerings
**Database Column**: `services.service_type`

```python
class ServiceType(enum.Enum):
    INTERNET = "internet"        # Internet connectivity services
    PHONE = "phone"              # VoIP/telephony services
    TV = "tv"                    # Television/streaming services
    BUNDLE = "bundle"            # Combined service packages
    HOSTING = "hosting"          # Web hosting services
    COLOCATION = "colocation"    # Data center colocation
    MANAGED_SERVICES = "managed_services"  # Managed IT services
    SECURITY = "security"        # Security services
```

**Service Provisioning**:
- Different provisioning workflows per type
- Equipment requirements vary by type
- SLA definitions specific to type
- Pricing structures per type

### ServiceStatus

**Purpose**: Tracks service instance operational status
**Database Column**: `service_instances.status`

```python
class ServiceStatus(enum.Enum):
    ACTIVE = "active"            # Service operational
    SUSPENDED = "suspended"      # Service temporarily disabled
    PENDING = "pending"          # Service ordered, not yet active
    CANCELLED = "cancelled"      # Service permanently terminated
    MAINTENANCE = "maintenance"  # Service under maintenance
```

**Service Lifecycle**:
```
PENDING → ACTIVE → SUSPENDED → ACTIVE
PENDING → CANCELLED
ACTIVE → MAINTENANCE → ACTIVE
ACTIVE → CANCELLED
```

### ProvisioningStatus

**Purpose**: Tracks service provisioning progress
**Database Column**: `service_instances.provisioning_status`

```python
class ProvisioningStatus(enum.Enum):
    PENDING = "pending"          # Provisioning not started
    IN_PROGRESS = "in_progress"  # Provisioning underway
    COMPLETED = "completed"      # Provisioning successful
    FAILED = "failed"            # Provisioning failed
    ROLLED_BACK = "rolled_back"  # Provisioning reversed
```

**Automation Integration**:
- Workflow engine status tracking
- Error handling and retry logic
- Customer notifications per status
- SLA tracking for provisioning time

### BandwidthUnit

**Purpose**: Defines bandwidth measurement units
**Database Column**: `services.bandwidth_unit`

```python
class BandwidthUnit(enum.Enum):
    KBPS = "kbps"    # Kilobits per second
    MBPS = "mbps"    # Megabits per second  
    GBPS = "gbps"    # Gigabits per second
```

**Usage Tracking**:
- Unit conversions for reporting
- Data transfer calculations
- Billing unit standardization
- Performance monitoring metrics

## Support Module Enums

Location: `/src/dotmac_isp/modules/support/models.py`

### TicketPriority

**Purpose**: Defines support ticket urgency levels
**Database Column**: `tickets.priority`

```python
class TicketPriority(enum.Enum):
    LOW = "low"          # Non-urgent issues
    MEDIUM = "medium"    # Standard priority
    HIGH = "high"        # Urgent issues
    CRITICAL = "critical"  # Service-affecting issues
```

**SLA Implications**:
- Response time requirements per priority
- Escalation rules based on priority
- Assignment logic prioritization
- Customer communication frequency

**Business Rules**:
- `CRITICAL`: Service outages, security issues (1-hour response)
- `HIGH`: Service degradation (4-hour response)
- `MEDIUM`: General issues (24-hour response)
- `LOW`: Feature requests, information (72-hour response)

### TicketStatus

**Purpose**: Tracks ticket resolution workflow status
**Database Column**: `tickets.status`

```python
class TicketStatus(enum.Enum):
    OPEN = "open"                # New ticket, needs assignment
    IN_PROGRESS = "in_progress"  # Actively being worked
    PENDING_CUSTOMER = "pending_customer"  # Awaiting customer response
    PENDING_VENDOR = "pending_vendor"      # Awaiting vendor response
    RESOLVED = "resolved"        # Issue fixed, awaiting confirmation
    CLOSED = "closed"            # Ticket completed
    CANCELLED = "cancelled"      # Ticket cancelled
```

**Workflow States**:
```
OPEN → IN_PROGRESS → RESOLVED → CLOSED
IN_PROGRESS → PENDING_CUSTOMER → IN_PROGRESS
IN_PROGRESS → PENDING_VENDOR → IN_PROGRESS
OPEN → CANCELLED
```

### TicketCategory

**Purpose**: Categorizes tickets by issue type
**Database Column**: `tickets.category`

```python
class TicketCategory(enum.Enum):
    TECHNICAL = "technical"      # Technical issues
    BILLING = "billing"          # Billing inquiries
    SALES = "sales"              # Sales inquiries
    GENERAL = "general"          # General questions
    COMPLAINT = "complaint"      # Customer complaints
    FEATURE_REQUEST = "feature_request"  # Enhancement requests
```

**Routing Logic**:
- Automatic assignment based on category
- Specialized teams per category
- Knowledge base article suggestions
- Escalation paths per category

### TicketSource

**Purpose**: Tracks how tickets were created
**Database Column**: `tickets.source`

```python
class TicketSource(enum.Enum):
    CUSTOMER_PORTAL = "customer_portal"  # Customer portal submission
    PHONE = "phone"                      # Phone support
    EMAIL = "email"                      # Email support
    CHAT = "chat"                        # Live chat
    WALK_IN = "walk_in"                  # In-person visit
    SYSTEM = "system"                    # System-generated
    SOCIAL_MEDIA = "social_media"        # Social media platforms
```

**Analytics Usage**:
- Channel effectiveness metrics
- Customer preference tracking
- Resource allocation planning
- Communication strategy optimization

### SLAStatus

**Purpose**: Tracks SLA compliance for tickets
**Database Column**: `tickets.sla_status`

```python
class SLAStatus(enum.Enum):
    MET = "met"              # SLA requirements met
    BREACHED = "breached"    # SLA deadline missed
    AT_RISK = "at_risk"      # Approaching SLA deadline
    PAUSED = "paused"        # SLA timer paused (pending customer)
```

**SLA Management**:
- Automatic status calculation
- Escalation triggers on breach risk
- Management reporting on SLA performance
- Customer notification on breaches

## Plugin System Enums

Location: `/src/dotmac_isp/plugins/core/models.py` and `/src/dotmac_isp/plugins/core/base.py`

### PluginStatus / PluginStatusDB

**Purpose**: Manages plugin lifecycle status
**Database Column**: `plugins.status`

```python
class PluginStatus(Enum):
    ACTIVE = "active"        # Plugin loaded and operational
    INACTIVE = "inactive"    # Plugin installed but disabled
    ERROR = "error"          # Plugin failed to load
    LOADING = "loading"      # Plugin currently loading
    UNLOADING = "unloading"  # Plugin being disabled
```

**Plugin Management**:
- Runtime status tracking
- Error state handling
- Load/unload operation status
- System health monitoring

### PluginCategory / PluginCategoryDB

**Purpose**: Categorizes plugins by functionality
**Database Column**: `plugins.category`

```python
class PluginCategory(Enum):
    BILLING = "billing"              # Billing system integrations
    CRM = "crm"                      # CRM system integrations
    MONITORING = "monitoring"        # Network monitoring tools
    TICKETING = "ticketing"          # Support system integrations
    NETWORK_AUTOMATION = "network_automation"  # Network automation tools
    REPORTING = "reporting"          # Custom reporting plugins
    AUTHENTICATION = "authentication"  # Auth system integrations
```

**Plugin Organization**:
- Category-based loading order
- Permission scoping by category
- Configuration templates per category
- Resource allocation per category

## Usage Guidelines

### Enum Validation

Always validate enum values in API inputs:

```python
from pydantic import BaseModel, validator

class CustomerCreate(BaseModel):
    customer_type: CustomerType
    
    @validator('customer_type')
    def validate_customer_type(cls, v):
        if v not in CustomerType:
            raise ValueError(f"Invalid customer type: {v}")
        return v
```

### Database Queries

Use enum values in database queries:

```python
# Correct
customers = session.query(Customer).filter(
    Customer.customer_type == CustomerType.BUSINESS.value
)

# Also correct with enum comparison
customers = session.query(Customer).filter(
    Customer.customer_type == CustomerType.BUSINESS
)
```

### API Serialization

Enums serialize to string values in JSON:

```python
# Database model
customer.customer_type = CustomerType.BUSINESS

# JSON output
{
    "customer_type": "business"
}
```

### Frontend Integration

Frontend applications should use enum values as constants:

```javascript
const CustomerType = {
    RESIDENTIAL: 'residential',
    BUSINESS: 'business', 
    ENTERPRISE: 'enterprise'
};

// Form validation
if (!Object.values(CustomerType).includes(formData.customerType)) {
    throw new Error('Invalid customer type');
}
```

## Migration Considerations

### Adding New Enum Values

1. **Add to enum class**: Add new value to Python enum
2. **Database migration**: No migration needed (stored as strings)
3. **Update validators**: Update Pydantic models if needed
4. **Frontend update**: Update frontend constants
5. **Documentation**: Update API documentation

### Removing Enum Values

1. **Deprecation notice**: Mark as deprecated in documentation
2. **Migration path**: Provide migration for existing data
3. **Grace period**: Maintain support for deprecated values
4. **Remove**: Only remove after grace period

### Renaming Enum Values

1. **Add new value**: Add with new name
2. **Migration**: Update existing database records
3. **Deprecation**: Mark old value as deprecated
4. **Remove**: Remove old value after grace period

### Database Considerations

Enums are stored as strings in the database:
- **Readable**: Database values are human-readable
- **Flexible**: Easy to add/remove values
- **Consistent**: No foreign key constraints to manage
- **Performance**: String comparisons, consider indexing for frequently queried enums

### Best Practices

1. **Immutable Values**: Never change existing enum string values
2. **Clear Names**: Use descriptive, business-meaningful names
3. **Documentation**: Document business rules for each value
4. **Validation**: Always validate enum inputs
5. **Consistency**: Use consistent naming patterns across enums
6. **Migration**: Plan enum changes carefully with proper migrations

This enum registry provides a complete reference for all enumeration types used throughout the DotMac ISP Framework, ensuring consistent data representation and clear business logic implementation.