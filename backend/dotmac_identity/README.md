# DotMac Identity

**Identity & Customer Management Platform for ISP Operations**

DotMac Identity provides a comprehensive set of small, composable SDKs for managing user accounts, customer lifecycles, verification, consent, and portal access in Internet Service Provider (ISP) operations.

## Features

### 🔐 Core Directory & Profiles
- **Identity Account SDK** - User accounts (create/disable), credentials, MFA factors
- **User Profile SDK** - Display name, avatar, locale, timezone management
- **Organizations SDK** - Tenants/companies with billing owner links
- **Contacts SDK** - People management across CRM, orders, support
- **Addresses SDK** - Postal and geographic address management

### ✅ Verification & Consent
- **Email SDK** - Email verification with OTP and deliverability tracking
- **Phone SDK** - SMS verification with OTP delivery
- **Consent Preferences SDK** - Communication preferences (email/SMS/WhatsApp), GDPR/CCPA compliance

### 👥 Customer Entity & Lifecycle
- **Customer Management SDK** - Subscriber/customer objects with lifecycle states (prospect → active → churned)

### 🌐 Portals
- **Portal Management SDK** - Creates and manages portal_id and settings per tenant
- **Customer Portal SDK** - Binds customers/contacts to portal accounts with login policies
- **Reseller Portal SDK** - Supports reseller access with scoped permissions

## Architecture

### Small & Composable
Each SDK is designed to be small, focused, and composable. You can use individual SDKs independently or combine them as needed.

### Multi-Tenant
All components support multi-tenancy with complete data isolation per tenant.

### In-Memory Services
Built with in-memory services for fast development and testing, with clear interfaces for database integration.

## Quick Start

### Installation

```bash
pip install dotmac-identity
```

### Basic Usage

```python
from dotmac_identity.sdks import (
    IdentityAccountSDK,
    UserProfileSDK,
    CustomerManagementSDK,
    EmailSDK
)

# Initialize SDKs for your tenant
tenant_id = "your_tenant_id"
accounts = IdentityAccountSDK(tenant_id)
profiles = UserProfileSDK(tenant_id)
customers = CustomerManagementSDK(tenant_id)
email = EmailSDK(tenant_id)

# Create user account
account = await accounts.create_account(
    username="john_doe",
    email="john@example.com",
    password="secure_password"
)

# Create user profile
profile = await profiles.create_profile(
    account_id=account["account_id"],
    display_name="John Doe",
    first_name="John",
    last_name="Doe",
    timezone="America/New_York"
)

# Create customer
customer = await customers.create_customer(
    customer_number="CUST-001",
    display_name="John Doe",
    customer_type="residential"
)

# Send email verification
verification = await email.send_verification_email(
    email="john@example.com",
    account_id=account["account_id"]
)
```

## SDK Reference

### Identity Account SDK

Manages user accounts, credentials, and MFA factors.

```python
from dotmac_identity.sdks import IdentityAccountSDK

accounts = IdentityAccountSDK("tenant_id")

# Create account
account = await accounts.create_account(
    username="user123",
    email="user@example.com",
    password="password"
)

# Authenticate
auth_result = await accounts.authenticate("user123", "password")

# Add MFA factor
mfa = await accounts.add_mfa_factor(
    account_id=account["account_id"],
    factor_type="totp",
    factor_data={"secret": "JBSWY3DPEHPK3PXP"}
)

# Disable account
await accounts.disable_account(account["account_id"])
```

### User Profile SDK

Manages display information, localization, and preferences.

```python
from dotmac_identity.sdks import UserProfileSDK

profiles = UserProfileSDK("tenant_id")

# Create profile
profile = await profiles.create_profile(
    account_id="account_id",
    display_name="Jane Smith",
    first_name="Jane",
    last_name="Smith",
    locale="en_US",
    timezone="UTC"
)

# Update avatar
await profiles.update_avatar(
    profile_id=profile["profile_id"],
    avatar_url="https://example.com/avatar.jpg"
)

# Update locale
await profiles.update_locale(
    profile_id=profile["profile_id"],
    locale="es_ES",
    timezone="Europe/Madrid"
)
```

### Organizations SDK

Manages tenants, companies, and organizational relationships.

```python
from dotmac_identity.sdks import OrganizationsSDK

orgs = OrganizationsSDK("tenant_id")

# Create organization
org = await orgs.create_organization(
    name="acme_corp",
    display_name="ACME Corporation",
    organization_type="company",
    billing_owner_id="account_id"
)

# Add member
member = await orgs.add_member(
    organization_id=org["organization_id"],
    account_id="account_id",
    role="admin",
    permissions=["manage_users", "manage_billing"]
)
```

### Customer Management SDK

Manages customer lifecycle with state transitions and event emission.

```python
from dotmac_identity.sdks import CustomerManagementSDK

customers = CustomerManagementSDK("tenant_id")

# Create customer
customer = await customers.create_customer(
    customer_number="CUST-12345",
    display_name="ACME Corp Customer",
    customer_type="business"
)

# Lifecycle transitions
await customers.activate_customer(customer["customer_id"])
await customers.suspend_customer(customer["customer_id"])
await customers.churn_customer(customer["customer_id"])

# Query customers
active_customers = await customers.get_active_customers()
prospects = await customers.get_prospects()
```

### Email SDK

Handles email verification with OTP and deliverability tracking.

```python
from dotmac_identity.sdks import EmailSDK

email = EmailSDK("tenant_id")

# Send verification
verification = await email.send_verification_email(
    email="user@example.com",
    contact_id="contact_id"
)

# Verify code
result = await email.verify_email_code(
    verification_id=verification["verification_id"],
    code="123456"
)

# Check deliverability
deliverability = await email.check_email_deliverability("user@example.com")
```

### Phone SDK

Handles SMS verification with OTP delivery.

```python
from dotmac_identity.sdks import PhoneSDK

phone = PhoneSDK("tenant_id")

# Send SMS verification
verification = await phone.send_verification_sms(
    phone_number="+1234567890",
    contact_id="contact_id"
)

# Verify code
result = await phone.verify_phone_code(
    verification_id=verification["verification_id"],
    code="123456"
)
```

### Consent Preferences SDK

Manages communication preferences and GDPR/CCPA compliance.

```python
from dotmac_identity.sdks import ConsentPreferencesSDK

consent = ConsentPreferencesSDK("tenant_id")

# Grant marketing consent
marketing_consent = await consent.grant_consent(
    consent_type="marketing_email",
    contact_id="contact_id",
    compliance_regions=["gdpr"]
)

# Set email preferences
email_prefs = await consent.set_email_preferences(
    contact_id="contact_id",
    marketing_email=True,
    transactional_email=True
)

# GDPR compliance
gdpr_prefs = await consent.set_gdpr_compliance(
    contact_id="contact_id",
    data_processing=True,
    third_party_sharing=False
)

# Withdraw consent
await consent.withdraw_consent(marketing_consent["preference_id"])
```

### Portal Management SDK

Creates and manages portal instances and settings.

```python
from dotmac_identity.sdks import PortalManagementSDK

portals = PortalManagementSDK("tenant_id")

# Create portal
portal = await portals.create_portal(
    portal_id="customer_portal_v1",
    name="customer_portal",
    display_name="Customer Portal",
    portal_type="customer"
)

# Configure settings
settings = await portals.configure_portal_settings(
    portal_id="customer_portal_v1",
    session_timeout=7200,
    require_mfa=True,
    max_login_attempts=3
)
```

### Customer Portal SDK

Binds customers to portal accounts with login policies.

```python
from dotmac_identity.sdks import CustomerPortalSDK

customer_portal = CustomerPortalSDK("tenant_id")

# Bind customer to portal
binding = await customer_portal.bind_customer_to_portal(
    portal_id="portal_uuid",
    customer_id="customer_id",
    portal_username="customer123",
    portal_email="customer@example.com"
)

# Publish credentials for ISP networking
await customer_portal.publish_credentials_for_networking(
    binding_id=binding["binding_id"],
    credentials={
        "radius_username": "customer123",
        "radius_password": "network_password",
        "vlan_id": 100
    }
)

# Set login policies
await customer_portal.update_login_policies(
    binding_id=binding["binding_id"],
    login_policies={
        "require_password_change": False,
        "session_timeout": 3600,
        "allowed_ip_ranges": ["192.168.1.0/24"]
    }
)
```

### Reseller Portal SDK

Manages reseller access with scoped permissions.

```python
from dotmac_identity.sdks import ResellerPortalSDK

reseller_portal = ResellerPortalSDK("tenant_id")

# Grant reseller access
access = await reseller_portal.grant_reseller_access(
    portal_id="portal_uuid",
    reseller_organization_id="reseller_org_id",
    access_level="read_write",
    permissions=["view_customers", "create_orders"]
)

# Set customer access scope
await reseller_portal.set_customer_access_scope(
    access_id=access["access_id"],
    accessible_customers=["customer1", "customer2"]
)

# Set commission rate
await reseller_portal.set_commission_rate(
    access_id=access["access_id"],
    commission_rate=0.15
)
```

## Configuration

### Environment Variables

```bash
# Basic configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key
JWT_SECRET=jwt-secret
PASSWORD_MIN_LENGTH=8

# MFA
ENABLE_MFA=true
MFA_ISSUER="Your ISP Name"

# Verification
EMAIL_VERIFICATION_TTL=3600
PHONE_VERIFICATION_TTL=300
OTP_LENGTH=6
MAX_VERIFICATION_ATTEMPTS=3

# Notifications
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password

SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token

# Compliance
GDPR_ENABLED=true
CCPA_ENABLED=true
DATA_RETENTION_DAYS=2555
ENABLE_AUDIT_LOGGING=true

# Portal settings
PORTAL_SESSION_TIMEOUT=3600
PORTAL_MAX_LOGIN_ATTEMPTS=5
PORTAL_LOCKOUT_DURATION=900
```

### Programmatic Configuration

```python
from dotmac_identity.core.config import IdentityConfig, update_config

# Update configuration
update_config(
    debug=True,
    enable_mfa=True,
    enable_email_verification=True
)

# Get current configuration
config = IdentityConfig()
print(f"Environment: {config.environment}")
print(f"MFA Enabled: {config.enable_mfa}")
```

## Customer Lifecycle States

The Customer Management SDK supports the following lifecycle states:

- **prospect** - Potential customer, not yet active
- **lead** - Qualified prospect
- **active** - Active paying customer
- **suspended** - Temporarily suspended service
- **churned** - Customer who has left
- **inactive** - Inactive account
- **cancelled** - Formally cancelled service

State transitions emit `customer.*` events for integration with other systems.

## Portal Integration

### ISP Networking Integration

The Customer Portal SDK publishes credentials and attributes that can be consumed by ISP networking equipment:

```python
# Publish RADIUS credentials
await customer_portal.publish_credentials_for_networking(
    binding_id="binding_id",
    credentials={
        "radius_username": "customer@isp.com",
        "radius_password": "network_secret",
        "nas_port_type": "ethernet",
        "service_type": "framed"
    }
)

# Publish network attributes
await customer_portal.publish_attributes_for_networking(
    binding_id="binding_id",
    attributes={
        "vlan_id": 100,
        "bandwidth_up": "100Mbps",
        "bandwidth_down": "1Gbps",
        "static_ip": "192.168.100.50",
        "dns_servers": ["8.8.8.8", "8.8.4.4"]
    }
)
```

## Compliance Features

### GDPR Compliance
- Explicit consent collection and management
- Right to withdraw consent
- Data retention policies
- Audit logging for compliance reporting

### CCPA Compliance
- Consumer privacy rights management
- Data processing consent
- Third-party sharing controls

### Audit Trail
All consent changes are automatically logged with:
- Timestamp and user context
- Legal basis and compliance regions
- Evidence data (IP address, user agent)
- Action history for regulatory reporting

## Development

### Setup Development Environment

```bash
git clone https://github.com/dotmac/isp-framework.git
cd isp-framework/dotmac_identity

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dotmac_identity --cov-report=html

# Run specific test categories
pytest tests/test_sdks/ -v
```

### Code Quality

```bash
# Format code
black dotmac_identity/
isort dotmac_identity/

# Lint code
flake8 dotmac_identity/
mypy dotmac_identity/

# Run all checks
pre-commit run --all-files
```

## Integration Examples

### CRM Integration

```python
# Create contact for CRM
contact = await contacts.create_contact(
    first_name="John",
    last_name="Doe",
    contact_type="person"
)

# Add contact information
await contacts.add_email(
    contact_id=contact["contact_id"],
    email="john@example.com",
    email_type="primary",
    is_primary=True
)

await contacts.add_phone(
    contact_id=contact["contact_id"],
    phone_number="+1234567890",
    phone_type="mobile",
    is_primary=True
)

# Add address
await addresses.create_address(
    contact_id=contact["contact_id"],
    line1="123 Main St",
    city="Anytown",
    state_province="CA",
    postal_code="12345",
    country="US",
    address_type="billing"
)
```

### Order Processing Integration

```python
# Link customer to contact and organization
customer = await customers.create_customer(
    customer_number="CUST-12345",
    display_name="John Doe",
    primary_contact_id=contact["contact_id"],
    organization_id=org["organization_id"]
)

# Activate customer when order is processed
await customers.activate_customer(
    customer_id=customer["customer_id"],
    changed_by="order_system"
)
```

### Support System Integration

```python
# Get customer information for support
customer_info = await customers.get_customer(customer_id)
contact_info = await contacts.get_contact(customer_info["primary_contact_id"])
contact_emails = await contacts.get_contact_emails(contact_info["contact_id"])
contact_phones = await contacts.get_contact_phones(contact_info["contact_id"])

# Customer support can access all contact methods and history
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Provide detailed reproduction steps
- Include relevant configuration and logs

### Pull Requests

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [https://docs.dotmac.com/identity](https://docs.dotmac.com/identity)
- **Issues**: [GitHub Issues](https://github.com/dotmac/isp-framework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dotmac/isp-framework/discussions)
- **Email**: support@dotmac.com

## Changelog

### v1.0.0 (2024-01-XX)

**Initial Release**

- ✨ Complete Identity & Customer Management Platform
- 🔐 Small, composable SDKs for all identity operations
- 👥 Customer lifecycle management with state transitions
- ✅ Email and SMS verification with OTP
- 📋 GDPR/CCPA compliant consent management
- 🌐 Portal management for customer and reseller access
- 🏢 Organization and contact management
- 📍 Address management with geo support
- 🔒 Multi-factor authentication support
- 🏗️ Multi-tenant architecture with data isolation
- 📊 Comprehensive audit logging
- 🧪 In-memory services for fast development
- 📚 Complete documentation and examples

---

**Built with ❤️ by the DotMac Team**
