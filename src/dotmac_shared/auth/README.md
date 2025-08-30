# DotMac Authentication Service

A comprehensive, secure authentication and authorization service for the DotMac framework, implementing enterprise-grade security features with modern best practices.

## 🔐 Security Features

### JWT Token Management (RS256)

- **Algorithm**: RS256 (2048-bit RSA keys) following 2024 security standards
- **Token Types**: Access tokens (15 min) and refresh tokens (30 days)
- **Key Rotation**: Automatic key rotation support with 90-day cycles
- **Token Blacklisting**: Secure logout with distributed revocation
- **JWKS Support**: Standards-compliant public key distribution

### Role-Based Access Control (RBAC)

- **Hierarchical Permissions**: Resource:action pattern (e.g., `billing:read`)
- **Multi-Tenant Support**: Tenant-scoped permissions and isolation
- **Role Inheritance**: Admin roles imply sub-permissions
- **Dynamic Checking**: Runtime permission evaluation
- **15+ Roles**: From super admin to read-only access

### Session Management

- **Distributed Storage**: Redis-backed with encryption at rest
- **Security Features**: Hijacking detection, concurrent session limits
- **Device Tracking**: Browser/OS detection and trusted devices
- **Timeout Management**: Configurable idle and absolute timeouts
- **Cleanup**: Automatic expired session removal

### Multi-Factor Authentication (MFA)

- **TOTP Support**: Authenticator apps with QR code generation
- **SMS Authentication**: Time-limited numeric codes
- **Backup Codes**: Recovery codes for lost devices
- **Rate Limiting**: Brute force protection with lockout
- **Multiple Methods**: Flexible authentication options

## 🏗️ Architecture

```
dotmac_shared/auth/
├── core/                    # Core authentication components
│   ├── tokens.py           # JWT token management (RS256)
│   ├── permissions.py      # RBAC system with 60+ permissions
│   ├── sessions.py         # Distributed session management
│   └── multi_factor.py     # MFA with TOTP/SMS/backup codes
├── providers/              # Authentication providers
│   ├── local_provider.py   # Database authentication
│   ├── oauth_provider.py   # OAuth2/OIDC integration
│   └── ldap_provider.py    # LDAP/Active Directory
├── middleware/             # Web framework integration
│   ├── fastapi_middleware.py    # FastAPI middleware
│   ├── rate_limiting.py    # Brute force protection
│   └── audit_logging.py    # Authentication audit trail
├── adapters/               # Platform integration
│   ├── isp_adapter.py      # ISP Framework integration
│   └── management_adapter.py    # Management Platform
└── tests/                  # Comprehensive test suite
```

## 🚀 Quick Start

### Installation

```bash
cd /home/dotmac_framework/src/dotmac_shared/auth
pip install -e .
```

### Basic Usage

```python
from dotmac_shared.auth import (
    JWTTokenManager,
    PermissionManager,
    SessionManager,
    MFAManager
)

# Initialize components
jwt_manager = JWTTokenManager(
    issuer="dotmac-auth-service",
    access_token_expire_minutes=15,
    refresh_token_expire_days=30
)

permission_manager = PermissionManager()
session_manager = SessionManager(session_store)
mfa_manager = MFAManager(mfa_provider)
```

### Token Generation

```python
# Generate access token
access_token = jwt_manager.generate_access_token(
    user_id="user123",
    tenant_id="tenant456",
    permissions=["billing:read", "customer:update"]
)

# Generate token pair
token_pair = jwt_manager.generate_token_pair(
    user_id="user123",
    tenant_id="tenant456",
    permissions=["billing:read", "customer:update"]
)
```

### Permission Checking

```python
from dotmac_shared.auth.core.permissions import Permission, Role

# Check specific permission
user_permissions = UserPermissions(
    user_id="user123",
    tenant_id="tenant456",
    roles=[Role.BILLING_MANAGER],
    explicit_permissions=set()
)

can_read_billing = permission_manager.check_permission(
    user_permissions,
    Permission.BILLING_READ
)
```

### Session Management

```python
# Create session
session = await session_manager.create_session(
    user_id="user123",
    tenant_id="tenant456",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0...",
    device_fingerprint="device123"
)

# Validate session security
is_secure = await session_manager.validate_session_security(
    session.session_id,
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0..."
)
```

### Multi-Factor Authentication

```python
# Setup TOTP
secret, qr_code = await mfa_manager.setup_totp(
    user_id="user123",
    tenant_id="tenant456",
    user_email="user@example.com"
)

# Validate TOTP
is_valid = await mfa_manager.validate_totp(
    user_id="user123",
    tenant_id="tenant456",
    token="123456"
)

# Generate backup codes
backup_codes = await mfa_manager.setup_backup_codes(
    user_id="user123",
    tenant_id="tenant456"
)
```

## 🔧 Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY="your-rsa-private-key"
JWT_ALGORITHM="RS256"
JWT_ACCESS_TOKEN_EXPIRE=900     # 15 minutes
JWT_REFRESH_TOKEN_EXPIRE=2592000 # 30 days

# Session Configuration
SESSION_TIMEOUT=28800           # 8 hours
MAX_CONCURRENT_SESSIONS=5

# MFA Configuration
MFA_REQUIRED=false
RATE_LIMIT_ATTEMPTS=5
LOCKOUT_DURATION=900           # 15 minutes

# Security
ENABLE_DEVICE_TRACKING=true
SUSPICIOUS_ACTIVITY_THRESHOLD=3
```

### Cache Service Integration

The authentication service integrates with Developer A's cache service for:

```python
# Session storage
session_store = CacheServiceSessionStore(cache_service, "auth_sessions")
session_manager = SessionManager(session_store)

# Token blacklisting
jwt_manager = JWTTokenManager(blacklist_provider=cache_service)
```

## 🎯 Permission System

### Available Permissions

The system includes 60+ permissions organized by resource:

- **System**: `system:admin`, `system:read`, `system:monitor`
- **Tenant**: `tenant:admin`, `tenant:create`, `tenant:update`, `tenant:delete`
- **User**: `user:admin`, `user:create`, `user:update`, `user:delete`, `user:impersonate`
- **Customer**: `customer:admin`, `customer:create`, `customer:update`, `customer:billing`
- **Billing**: `billing:admin`, `billing:invoice`, `billing:payment`, `billing:refund`
- **Network**: `network:admin`, `network:config`, `network:provision`, `network:monitor`
- **Service**: `service:admin`, `service:provision`, `service:update`
- **Support**: `support:admin`, `support:create`, `support:assign`
- **Analytics**: `analytics:admin`, `analytics:read`, `analytics:export`

### Role Hierarchy

```
SUPER_ADMIN              # Platform-wide access
├── PLATFORM_ADMIN       # Platform management
├── PLATFORM_SUPPORT     # Platform support
└── TENANT_ADMIN         # Full tenant access
    ├── TENANT_MANAGER    # Tenant operations
    ├── BILLING_MANAGER   # Billing operations
    ├── NETWORK_ADMIN     # Network management
    ├── CUSTOMER_SERVICE  # Customer support
    └── FIELD_TECHNICIAN  # Field operations
```

## 🔒 Security Standards

### JWT Security

- **Algorithm**: RS256 (asymmetric signing)
- **Key Size**: 2048-bit RSA keys
- **Key Rotation**: 90-day automatic rotation
- **Claims**: Minimal necessary claims only
- **Expiry**: Short-lived access tokens (15 min)

### Session Security

- **Storage**: Redis with encryption at rest
- **Timeout**: 8 hours idle, 24 hours absolute
- **Protection**: CSRF tokens, session binding
- **Monitoring**: Real-time session tracking
- **Cleanup**: Automatic expired session removal

### Password Security

- **Hashing**: bcrypt with work factor 12
- **Complexity**: 12+ chars, mixed case, numbers, symbols
- **History**: Cannot reuse last 5 passwords
- **Expiry**: Optional 90-day expiry for high-security tenants

### MFA Security

- **TOTP**: RFC 6238 compliant with 30-second windows
- **SMS**: 5-minute expiry with rate limiting
- **Backup Codes**: 8 single-use recovery codes
- **Rate Limiting**: 5 attempts per 15 minutes
- **Lockout**: Temporary account lockout on abuse

## 🧪 Testing

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=dotmac_shared.auth --cov-report=html

# Security tests
pytest tests/ -m security

# Performance tests
pytest tests/ -m performance
```

## 🔗 Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from dotmac_shared.auth.middleware import AuthenticationMiddleware
from dotmac_shared.auth.core.permissions import Permission

app = FastAPI()
app.add_middleware(AuthenticationMiddleware)

@app.get("/billing/invoices")
async def get_invoices(
    user: dict = Depends(require_permissions([Permission.BILLING_READ]))
):
    return {"invoices": []}
```

### ISP Framework Integration

```python
from dotmac_shared.auth.adapters import ISPAuthAdapter

# Initialize adapter
auth_adapter = ISPAuthAdapter(jwt_manager, permission_manager)

# Use in ISP Framework routes
@router.get("/customers")
async def get_customers(user=Depends(auth_adapter.get_current_user)):
    return await customer_service.get_customers(user.tenant_id)
```

### Management Platform Integration

```python
from dotmac_shared.auth.adapters import ManagementAuthAdapter

# Initialize adapter
auth_adapter = ManagementAuthAdapter(jwt_manager, permission_manager)

# Use in Management Platform
@router.post("/tenants")
async def create_tenant(
    user=Depends(auth_adapter.require_platform_admin)
):
    return await tenant_service.create_tenant()
```

## 📊 Monitoring & Analytics

The authentication service provides comprehensive monitoring:

- **Authentication Metrics**: Success/failure rates, response times
- **Session Analytics**: Active sessions, device types, locations
- **Security Events**: Failed attempts, suspicious activity, lockouts
- **MFA Usage**: Method adoption, backup code usage
- **Performance**: Token generation/validation times

## 🛡️ Security Considerations

### Production Deployment

1. **Key Management**: Use secure key storage (HSM, Key Vault)
2. **Secret Rotation**: Implement automated key rotation
3. **Rate Limiting**: Deploy Redis for distributed rate limiting
4. **Monitoring**: Set up security event alerting
5. **Backup**: Regular backup of MFA secrets and sessions

### Security Hardening

1. **Network Security**: TLS 1.3 for all communications
2. **Input Validation**: Comprehensive input sanitization
3. **Audit Logging**: Complete audit trail of auth events
4. **Penetration Testing**: Regular security assessments
5. **Compliance**: GDPR, SOC 2, ISO 27001 considerations

## 📞 Support

For issues and questions:

- GitHub Issues: [auth-service/issues](https://github.com/dotmac-framework/auth-service/issues)
- Documentation: [docs.dotmac-framework.com/auth-service](https://docs.dotmac-framework.com/auth-service)
- Email: <security@dotmac-framework.com>

## 📜 License

MIT License - see LICENSE file for details.

---

**Built with security in mind for the DotMac Framework** 🚀
