# DotMac Captive Portal Package

A comprehensive, production-ready captive portal solution for WiFi hotspots and guest networks. This package consolidates and unifies captive portal functionality across the DotMac ecosystem, providing enterprise-grade features with simple integration.

## 🚀 Features

### Core Functionality

- **Multi-Authentication Methods**: Email, SMS, social media, vouchers, RADIUS, and free access
- **Guest Network Management**: VLAN isolation, bandwidth control, access policies, device tracking
- **Billing Integration**: Usage tracking, payment processing, subscription management
- **Portal Customization**: Themes, branding, multi-language support, custom HTML/CSS
- **Session Management**: Real-time monitoring, automatic cleanup, concurrent session limits
- **Security**: Rate limiting, input validation, CSRF protection, device isolation

### Advanced Features

- **Usage Analytics**: Comprehensive tracking with Prometheus metrics
- **Payment Processing**: Stripe and PayPal integration with billing plans
- **Network Isolation**: VLAN-based guest segmentation with firewall rules
- **Asset Management**: Logo uploads, background images, document hosting
- **Template System**: Jinja2-powered customizable portal pages
- **RADIUS Integration**: Enterprise authentication with attribute support
- **API-First Design**: RESTful APIs for all operations with comprehensive documentation

## 📦 Installation

### Using Poetry (Recommended)

```bash
# Install the package
cd /path/to/dotmac_framework/src/dotmac_shared/captive_portal
poetry install

# For development
poetry install --with dev
```

### Using pip

```bash
pip install -e /path/to/dotmac_framework/src/dotmac_shared/captive_portal
```

## 🏗️ Package Structure

```
dotmac_captive_portal/
├── __init__.py              # Main package exports
├── core.py                  # Core portal functionality and configuration
├── models.py                # SQLAlchemy database models
├── guest_manager.py         # Guest network management and device control
├── auth.py                  # Authentication methods (email, SMS, social, vouchers, RADIUS)
├── billing.py               # Billing integration and usage tracking
└── customization.py         # Portal theming and customization system
```

## 🚀 Quick Start

### 1. Basic Portal Setup

```python
from dotmac_captive_portal import CaptivePortal, CaptivePortalConfig
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# Configure the portal
config = CaptivePortalConfig(
    database_url="postgresql://user:pass@localhost/captive_portal",
    redis_url="redis://localhost:6379",
    default_session_timeout=3600,  # 1 hour
    require_email_verification=True
)

# Create portal instance
portal = CaptivePortal(config)

# Set up database session
engine = create_async_engine(config.database_url)
async_session = AsyncSession(engine)
portal.set_database_session(async_session)

# Create a new portal
new_portal = await portal.create_portal(
    tenant_id="your-tenant-id",
    name="Hotel Guest WiFi",
    ssid="Hotel_Guest",
    location="Main Lobby",
    auth_methods=["email", "social", "voucher"],
    session_timeout=7200,  # 2 hours
    max_concurrent_sessions=50
)

print(f"Portal created: {new_portal.id}")
```

### 2. Guest Network Management

```python
from dotmac_captive_portal import GuestNetworkManager, NetworkRange, VLANConfig

# Create guest network manager
network_manager = GuestNetworkManager(async_session)

# Define network configuration
network_range = NetworkRange(
    network="192.168.100.0/24",
    gateway="192.168.100.1",
    dns_servers=["8.8.8.8", "8.8.4.4"],
    dhcp_start="192.168.100.10",
    dhcp_end="192.168.100.250"
)

# Create guest network with VLAN isolation
guest_network = await network_manager.create_guest_network(
    tenant_id="your-tenant-id",
    name="Hotel Guest Network",
    network_cidr="192.168.100.0/24",
    gateway_ip="192.168.100.1",
    vlan_id=100,
    internet_access=True,
    lan_access=False,  # Isolate from main network
    guest_to_guest=False,  # Prevent device communication
    bandwidth_limit_down=5000,  # 5 Mbps download
    bandwidth_limit_up=1000     # 1 Mbps upload
)

# Assign IP to device
assigned_ip = await network_manager.assign_ip_address(
    network_id=guest_network.network_id,
    mac_address="aa:bb:cc:dd:ee:ff"
)

print(f"Device assigned IP: {assigned_ip}")
```

### 3. Authentication Setup

```python
from dotmac_captive_portal import AuthenticationManager, SocialAuth, VoucherAuth, RADIUSAuth

# Create authentication manager
auth_manager = AuthenticationManager(async_session)

# Configure social authentication
social_config = {
    "providers": {
        "google": {
            "client_id": "your-google-client-id",
            "client_secret": "your-google-client-secret",
            "redirect_uri": "https://your-portal.com/auth/google/callback"
        }
    }
}
auth_manager.register_auth_method("social", SocialAuth(social_config))

# Configure RADIUS authentication
radius_config = {
    "servers": [
        {
            "host": "radius.example.com",
            "port": 1812,
            "secret": "shared-secret"
        }
    ],
    "timeout": 30,
    "retries": 3
}
auth_manager.register_auth_method("radius", RADIUSAuth(radius_config))

# Configure voucher authentication
voucher_auth = VoucherAuth({"allow_multi_use": False})
auth_manager.register_auth_method("voucher", voucher_auth)

# Authenticate user
auth_result = await auth_manager.authenticate(
    method_name="email",
    credentials={
        "verification_id": "verification-uuid",
        "verification_code": "123456"
    },
    portal_id=str(new_portal.id),
    client_ip="192.168.100.100",
    client_mac="aa:bb:cc:dd:ee:ff"
)

if auth_result.success:
    print(f"User authenticated: {auth_result.session_data}")
```

### 4. Billing and Usage Tracking

```python
from dotmac_captive_portal import BillingIntegration, UsageTracker
from decimal import Decimal

# Configure payment processing
payment_config = {
    "providers": ["stripe", "paypal"],
    "stripe": {
        "secret_key": "sk_test_...",
        "webhook_secret": "whsec_..."
    },
    "default_currency": "USD"
}

# Create billing integration
billing = BillingIntegration(async_session, payment_config)

# Create a billing plan
billing_plan = await billing.create_billing_plan(
    tenant_id="your-tenant-id",
    name="1 Hour Internet Access",
    price=Decimal("5.00"),
    billing_type="one_time",
    duration_minutes=60,
    data_limit_mb=500,  # 500 MB limit
    bandwidth_limit_down=10000,  # 10 Mbps
    bandwidth_limit_up=2000      # 2 Mbps
)

# Start billing session
billing_session = await billing.initiate_billing_session(
    user_id="user-uuid",
    session_id="session-uuid",
    portal_id=str(new_portal.id),
    billing_plan_id=str(billing_plan.id)
)

if billing_session["payment_required"]:
    print(f"Payment required: {billing_session['payment_intent']}")
```

### 5. Portal Customization

```python
from dotmac_captive_portal import PortalCustomizer, BrandingConfig, ColorScheme, Theme

# Create portal customizer
customizer_config = {
    "template_dir": "portal_templates",
    "asset_dir": "portal_assets"
}
customizer = PortalCustomizer(customizer_config)

# Configure branding
branding = BrandingConfig(
    company_name="Luxury Hotel & Resort",
    logo_url="/assets/images/hotel-logo.png",
    website_url="https://luxuryhotel.com",
    support_email="support@luxuryhotel.com",
    support_phone="+1-800-LUXURY",
    terms_url="https://luxuryhotel.com/terms",
    privacy_url="https://luxuryhotel.com/privacy"
)

# Create custom theme
custom_colors = ColorScheme(
    primary="#d4af37",  # Gold
    secondary="#8b4513",  # Saddle brown
    background="#f8f5f0",  # Warm white
    text="#2c2c2c"  # Dark gray
)

hotel_theme = customizer.create_theme(
    name="Luxury Hotel Theme",
    colors=custom_colors,
    description="Elegant gold and brown hotel theme"
)

# Generate portal HTML
portal_html = customizer.generate_portal_html(
    template_name="welcome.html",
    theme_id=hotel_theme.theme_id,
    branding=branding,
    context={
        "portal_name": "Hotel Guest WiFi",
        "welcome_message": "Welcome to our complimentary WiFi service",
        "auth_methods": ["email", "social"]
    },
    language="en"
)

print("Custom portal HTML generated")
```

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/captive_portal
REDIS_URL=redis://localhost:6379

# Social OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Payment Processing
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret

# Security
JWT_SECRET_KEY=your-jwt-secret-key
CSRF_SECRET_KEY=your-csrf-secret-key

# Asset Storage
ASSET_STORAGE_PATH=/var/lib/captive-portal/assets
MAX_ASSET_SIZE_MB=50
```

### Configuration Class

```python
from dotmac_captive_portal import CaptivePortalConfig

config = CaptivePortalConfig(
    # Database settings
    database_url="postgresql://localhost/captive_portal",
    redis_url="redis://localhost:6379",

    # Portal defaults
    default_session_timeout=3600,
    default_idle_timeout=1800,
    default_data_limit_mb=0,  # unlimited

    # Authentication
    require_email_verification=True,
    verification_expires_minutes=15,
    max_login_attempts=5,

    # Session management
    cleanup_expired_sessions=True,
    cleanup_interval_minutes=15,
    max_concurrent_sessions_per_user=3,

    # Security
    enable_captcha=True,
    session_token_length=32,

    # Billing
    billing_enabled=True,
    payment_providers=["stripe", "paypal"],

    # Customization
    allow_custom_css=True,
    allow_custom_html=True,
    max_logo_size_mb=5
)
```

## 🏛️ Architecture

### Core Components

1. **CaptivePortal**: Main orchestrator class that manages portal operations
2. **GuestNetworkManager**: Handles network configuration, VLAN management, and device control
3. **AuthenticationManager**: Supports multiple authentication methods with pluggable providers
4. **BillingIntegration**: Complete billing system with usage tracking and payment processing
5. **PortalCustomizer**: Theme engine with branding, templates, and asset management

### Database Schema

The package uses SQLAlchemy models with the following main entities:

- **Portal**: Portal configuration and settings
- **GuestUser**: Guest user accounts and authentication data
- **Session**: Active user sessions with usage tracking
- **Voucher**: Access vouchers with limits and redemption tracking
- **BillingPlan**: Billing plans and pricing structures
- **UsageLog**: Detailed usage analytics and metrics

### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant Portal
    participant AuthManager
    participant Provider

    Client->>Portal: Access request
    Portal->>AuthManager: Initiate auth
    AuthManager->>Provider: Send verification
    Provider->>Client: Verification code
    Client->>Portal: Submit code
    Portal->>AuthManager: Validate code
    AuthManager->>Portal: Auth success
    Portal->>Client: Grant access
```

## 🔌 Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, HTTPException
from dotmac_captive_portal import CaptivePortal, CaptivePortalConfig

app = FastAPI(title="Captive Portal API")

# Configure portal
config = CaptivePortalConfig()
portal = CaptivePortal(config)

@app.post("/auth/email/prepare")
    result = await portal.service.auth_manager.prepare_authentication(
        method_name="email",
        user_data=request.model_dump(),
        portal_id=request.portal_id
    )
    return result

@app.post("/auth/email/verify")
    result = await portal.service.auth_manager.authenticate(
        method_name="email",
        credentials=request.model_dump(),
        portal_id=request.portal_id,
        client_ip=request.client_ip
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error_message)

    return {"success": True, "session_data": result.session_data}
```

### Django Integration

```python
# django_app/captive_portal.py
from django.conf import settings
from dotmac_captive_portal import CaptivePortal, CaptivePortalConfig

# Configure in settings.py
CAPTIVE_PORTAL_CONFIG = {
    'database_url': 'postgresql://...',
    'redis_url': 'redis://...',
    'billing_enabled': True,
    'payment_providers': ['stripe']
}

# In views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

portal = CaptivePortal(CaptivePortalConfig(**settings.CAPTIVE_PORTAL_CONFIG))

@csrf_exempt
    if request.method == 'POST':
        data = json.loads(request.body)
        result = await portal.service.auth_manager.prepare_authentication(
            method_name="email",
            user_data=data,
            portal_id=data['portal_id']
        )
        return JsonResponse(result)
```

## 📊 Monitoring and Analytics

### Prometheus Metrics

The package exports comprehensive metrics:

```python
from dotmac_captive_portal.metrics import setup_metrics

# Setup Prometheus metrics
metrics = setup_metrics()

# Metrics available:
# - captive_portal_active_sessions
# - captive_portal_authentication_attempts_total
# - captive_portal_authentication_success_rate
# - captive_portal_data_usage_bytes_total
# - captive_portal_session_duration_seconds
# - captive_portal_payment_transactions_total
```

### Usage Analytics

```python
# Get comprehensive usage analytics
analytics = await portal.service.usage_tracker.get_user_usage_summary(
    user_id="user-uuid",
    start_date=datetime.utcnow() - timedelta(days=30)
)

print(f"Total sessions: {analytics['usage']['total_sessions']}")
print(f"Data usage: {analytics['usage']['total_gb']:.2f} GB")
print(f"Duration: {analytics['usage']['total_duration_hours']:.1f} hours")
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=dotmac_captive_portal --cov-report=html

# Run specific test categories
poetry run pytest tests/test_auth.py
poetry run pytest tests/test_billing.py
poetry run pytest tests/test_network.py
```

### Integration Tests

```python
# tests/test_integration.py
import pytest
from dotmac_captive_portal import CaptivePortal, CaptivePortalConfig

@pytest.mark.asyncio
async def test_full_authentication_flow():
    config = CaptivePortalConfig(database_url="sqlite:///:memory:")
    portal = CaptivePortal(config)

    # Create portal
    test_portal = await portal.create_portal(
        tenant_id="test-tenant",
        name="Test Portal",
        ssid="Test_WiFi"
    )

    # ... test implementation

    assert test_portal.name == "Test Portal"
```

## 🔒 Security Considerations

### Best Practices

1. **Network Isolation**: Always use VLAN isolation for guest networks
2. **Rate Limiting**: Configure appropriate rate limits to prevent abuse
3. **Input Validation**: All user inputs are sanitized and validated
4. **Session Security**: Sessions use cryptographically secure tokens
5. **Payment Security**: PCI DSS compliant payment processing
6. **Data Privacy**: GDPR/CCPA compliant data handling

### Security Features

```python
# Configure security settings
config = CaptivePortalConfig(
    enable_captcha=True,
    max_login_attempts=5,
    lockout_duration_minutes=30,
    session_token_length=32,
    require_email_verification=True,
    csrf_protection=True
)
```

## 🌍 Multi-Language Support

```python
# Load translations
customizer.content_manager.load_translations_from_file(
    "translations/spanish.json",
    "es"
)

# Generate portal in Spanish
spanish_html = customizer.generate_portal_html(
    template_name="welcome.html",
    theme_id="default",
    branding=branding,
    context=context,
    language="es"
)
```

## 📚 API Reference

### Core Classes

- **CaptivePortal**: Main portal management class
- **GuestNetworkManager**: Network configuration and device management
- **AuthenticationManager**: Multi-method authentication handling
- **BillingIntegration**: Payment processing and usage tracking
- **PortalCustomizer**: Theme and branding management

### Authentication Methods

- **SocialAuth**: OAuth social media authentication
- **VoucherAuth**: Pre-paid voucher access
- **RADIUSAuth**: Enterprise RADIUS integration

### Models

- **Portal**: Portal configuration
- **GuestUser**: User account information
- **Session**: Active session tracking
- **Voucher**: Access voucher management
- **BillingPlan**: Pricing and limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Install development dependencies: `poetry install --with dev`
4. Make your changes and add tests
5. Run tests: `poetry run pytest`
6. Run linting: `poetry run ruff check`
7. Submit a pull request

## 📄 License

This software is proprietary and confidential to DotMac. All rights reserved.

## 🆘 Support

- **Email**: <support@dotmac.com>
- **Documentation**: <https://docs.dotmac.com/captive-portal>
- **Issues**: <https://github.com/dotmac/captive-portal/issues>

---

**Built with ❤️ by the DotMac Development Team**
