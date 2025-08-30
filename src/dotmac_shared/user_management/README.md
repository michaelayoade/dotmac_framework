# DotMac Unified User Management Service

A comprehensive user lifecycle management service that consolidates user operations across ISP Framework and Management Platform, built on top of the DotMac Auth service.

## 🎯 Consolidation Impact

This service **eliminates 8-10 duplicate user service classes** across both platforms:

### Before Consolidation

- **ISP Framework**: 3x UserService, 3x CustomerService, identity domain services
- **Management Platform**: UserManagementService, AuthService, user repositories
- **Result**: 12+ separate user management implementations

### After Consolidation

- **Single unified service** with platform-specific adapters
- **Consistent user lifecycle** across all platforms
- **Shared authentication** integration
- **Unified permission model**

## 🏗️ Architecture

```
dotmac_shared/user_management/
├── core/                           # Core user management logic
│   ├── user_lifecycle_service.py   # Main user lifecycle operations
│   ├── user_repository.py          # Unified user data access
│   ├── permission_manager.py       # Permission assignment & validation
│   └── profile_manager.py          # User profile & preferences
├── adapters/                       # Platform-specific integrations
│   ├── isp_user_adapter.py         # ISP Framework integration
│   ├── management_user_adapter.py  # Management Platform integration
│   └── base_adapter.py             # Common adapter interface
├── schemas/                        # Unified data models
│   ├── user_schemas.py             # Core user models
│   ├── profile_schemas.py          # User profile models
│   └── lifecycle_schemas.py        # User lifecycle events
├── integrations/                   # External service integrations
│   ├── auth_integration.py         # DotMac Auth service integration
│   ├── notification_integration.py # User notifications
│   └── audit_integration.py        # User activity auditing
└── tests/                          # Comprehensive test suite
```

## ✨ Key Features

### 🔄 User Lifecycle Management

- **Registration**: Multi-step user onboarding with verification
- **Activation**: Email/SMS verification with retry logic
- **Profile Management**: Comprehensive user profile handling
- **Deactivation**: Graceful account suspension and cleanup
- **Deletion**: GDPR-compliant user data removal

### 👤 User Types & Roles

**ISP Framework Users:**

- **Customers**: End-user ISP customers with service subscriptions
- **Technicians**: Field technicians with device access
- **Support**: Customer support representatives
- **ISP Admins**: ISP administrative users

**Management Platform Users:**

- **Super Admins**: Global platform administrators
- **Tenant Admins**: ISP tenant administrators
- **Tenant Users**: Regular ISP staff members
- **Support**: Platform support team

### 🔐 Authentication Integration

- **Seamless Auth Service Integration**: Built on `dotmac_shared/auth/`
- **JWT Token Management**: RS256 tokens with 15min/30day lifecycles
- **Multi-Factor Authentication**: TOTP, SMS, backup codes
- **Session Management**: Distributed Redis-backed sessions
- **Permission Validation**: 60+ granular permissions

### 🎯 Profile Management

- **Basic Profiles**: Name, email, phone, timezone, language
- **Extended Profiles**: Platform-specific attributes and preferences
- **Avatar Management**: Profile picture upload and processing
- **Preference Storage**: User settings and customizations
- **Activity Tracking**: Login history and usage analytics

### 🔄 Platform Adapters

- **ISP Adapter**: Maps to ISP customer and user models
- **Management Adapter**: Maps to platform user and tenant models
- **Consistent API**: Same user operations across all platforms
- **Data Translation**: Seamless model conversion between platforms

## 🚀 Usage Examples

### Basic User Operations

```python
from dotmac_shared.user_management import UserLifecycleService
from dotmac_shared.user_management.adapters import ISPUserAdapter

# Create service with ISP adapter
user_service = UserLifecycleService()
isp_adapter = ISPUserAdapter(db_session, tenant_id)

# Register new ISP customer
customer_data = {
    "email": "customer@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890",
    "user_type": "customer"
}

user = await isp_adapter.register_user(customer_data)
# Returns: Unified user model with ISP-specific attributes

# Activate user account
await user_service.activate_user(
    user.id,
    verification_code="123456",
    platform_context={"tenant_id": tenant_id}
)
```

### Advanced Profile Management

```python
# Update user profile with platform-specific data
profile_updates = {
    "timezone": "America/New_York",
    "language": "en-US",
    "notifications": {
        "email": True,
        "sms": False,
        "push": True
    },
    # ISP-specific profile data
    "service_preferences": {
        "billing_notifications": True,
        "outage_alerts": True,
        "usage_warnings": True
    }
}

await user_service.update_user_profile(user.id, profile_updates)
```

### Cross-Platform User Operations

```python
# Same user service works across platforms
from dotmac_shared.user_management.adapters import ManagementUserAdapter

mgmt_adapter = ManagementUserAdapter(db_session)

# Create Management Platform admin user
admin_data = {
    "email": "admin@platform.com",
    "first_name": "Platform",
    "last_name": "Admin",
    "user_type": "tenant_admin",
    "permissions": ["tenant:read", "tenant:write", "user:manage"]
}

admin_user = await mgmt_adapter.register_user(admin_data)
```

## 🔧 Configuration

```python
# User lifecycle configuration
USER_LIFECYCLE_CONFIG = {
    "registration": {
        "email_verification_required": True,
        "phone_verification_required": False,
        "approval_required": False,
        "password_requirements": {
            "min_length": 8,
            "require_uppercase": True,
            "require_numbers": True,
            "require_symbols": True
        }
    },
    "activation": {
        "verification_code_length": 6,
        "verification_code_expiry": 900,  # 15 minutes
        "max_verification_attempts": 5,
        "resend_cooldown": 60  # 1 minute
    },
    "profiles": {
        "avatar_max_size": 5242880,  # 5MB
        "avatar_formats": ["jpg", "png", "webp"],
        "extended_profiles_enabled": True
    },
    "cleanup": {
        "inactive_user_days": 365,
        "deleted_user_retention_days": 90
    }
}
```

## 🔌 Integration Points

### Auth Service Integration

- **Automatic sync** with `dotmac_shared/auth/`
- **Permission assignment** through RBAC system
- **Token management** for user sessions
- **MFA setup** and validation

### Notification Integration

- **Welcome emails** on registration
- **Verification codes** via email/SMS
- **Password reset** notifications
- **Account status changes**

### Audit Integration

- **User activity logging**
- **Permission changes** tracking
- **Login/logout** events
- **Profile modifications**

## 📊 Benefits

### For Developers

- **Single API** for all user operations across platforms
- **Consistent behavior** regardless of platform
- **Comprehensive testing** with shared test suite
- **Clear documentation** and examples

### For Operations

- **Unified user management** console
- **Consistent audit trails** across platforms
- **Centralized user lifecycle** policies
- **Simplified troubleshooting**

### For Users

- **Consistent experience** across platform interfaces
- **Unified profile management**
- **Single sign-on** capabilities
- **Standardized security features**

## 🧪 Testing

The service includes comprehensive tests covering:

- **Unit tests** for core user lifecycle operations
- **Integration tests** for platform adapters
- **Security tests** for authentication integration
- **Performance tests** for large user datasets
- **End-to-end tests** for complete user journeys

```bash
# Run user management service tests
pytest src/dotmac_shared/user_management/tests/ -v --cov=dotmac_shared.user_management
```

This unified user management service eliminates the complexity of managing multiple user systems while providing platform-specific functionality through clean adapter patterns.
