# DotMac Security

Comprehensive security services for the DotMac Framework providing unified access control, audit logging, tenant isolation, plugin sandboxing, and enterprise security features.

## Features

### 🔐 Access Control & RBAC
- Fine-grained role-based access control (RBAC)
- Attribute-based access control (ABAC)
- Permission caching and performance optimization
- Hierarchical roles and inheritance
- Dynamic permission evaluation

### 📊 Audit Logging
- Comprehensive security event logging
- Structured audit events with context
- Multiple storage backends support
- Real-time audit streaming
- Compliance reporting integration

### 🏢 Tenant Isolation
- Multi-tenant security boundary enforcement
- Row-level security (RLS) for databases
- Cross-tenant access prevention
- Tenant context validation
- Gateway integration support

### 🔒 Plugin Security
- Secure plugin execution sandbox
- Resource limits and monitoring
- Code validation and scanning
- Permission-based plugin access
- Static analysis security checks

### 🏛️ Enterprise Features
- Single Sign-On (SSO) integration
- Compliance reporting (SOC2, GDPR, HIPAA, etc.)
- Advanced threat detection
- Enhanced audit logging
- Forensic investigation support

### ✅ Input Validation
- SQL injection prevention
- XSS attack detection
- Input sanitization
- Pattern validation
- Security rule engine

## Installation

```bash
# Install with Poetry
poetry add dotmac-security

# Install with pip
pip install dotmac-security

# Install with enterprise features
poetry add "dotmac-security[enterprise]"
```

## Quick Start

### Access Control

```python
from dotmac.security import (
    AccessControlManager, 
    Permission, 
    Role, 
    AccessRequest,
    ResourceType,
    ActionType
)

# Create access control manager
acm = AccessControlManager()

# Create permission
permission = Permission(
    permission_id="api_read",
    name="Read API",
    resource_type=ResourceType.API,
    action=ActionType.READ
)
await acm.create_permission(permission)

# Create role
role = Role(
    role_id="user",
    name="Basic User",
    permissions=["api_read"]
)
await acm.create_role(role)

# Grant permission to user
await acm.grant_permission(
    subject_type="user",
    subject_id="user123",
    resource_type=ResourceType.API,
    resource_id="my_api",
    roles=["user"]
)

# Check access
request = AccessRequest(
    subject_type="user",
    subject_id="user123",
    resource_type=ResourceType.API,
    resource_id="my_api",
    action=ActionType.READ
)
decision = await acm.check_permission(request)
print(f"Access: {decision.decision}")  # "allow" or "deny"
```

### Audit Logging

```python
from dotmac.security import AuditLogger, AuditEventType

# Create audit logger
audit = AuditLogger(service_name="my-service")

# Log authentication event
await audit.log_auth_event(
    event_type=AuditEventType.AUTH_LOGIN,
    actor_id="user123",
    outcome="success",
    message="User login successful",
    client_ip="192.168.1.1"
)

# Log data access
await audit.log_data_access(
    operation="read",
    resource_type="customer",
    resource_id="cust123",
    actor_id="user123"
)

# Query events
events = await audit.query_events(limit=10)
```

### Tenant Security

```python
from dotmac.security import TenantSecurityManager, TenantSecurityEnforcer
from fastapi import FastAPI

app = FastAPI()

# Add tenant security middleware
manager = TenantSecurityManager()
enforcer = TenantSecurityEnforcer(manager)

@app.middleware("http")
async def tenant_middleware(request, call_next):
    # Enforce tenant boundaries
    tenant_context = await enforcer.enforce_tenant_boundary(request)
    response = await call_next(request)
    return response
```

### Plugin Sandbox

```python
from dotmac.security import create_secure_environment
from uuid import uuid4

# Create secure plugin environment
async with create_secure_environment(
    plugin_id="my_plugin",
    tenant_id=uuid4(),
    security_level="default"
) as sandbox:
    
    # Check permissions
    if sandbox.check_permission("filesystem", "read_temp"):
        # Execute plugin code securely
        result = await sandbox.execute_with_timeout(
            my_plugin_function,
            timeout=30.0
        )
```

### Input Validation

```python
from dotmac.security import validate_input, sanitize_data

# Validate user input
result = validate_input(
    data=user_input,
    rules={
        "check_sql_injection": True,
        "check_xss": True,
        "max_length": 1000,
        "sanitize": True
    }
)

if result["valid"]:
    # Safe to use result["sanitized_data"]
    clean_data = result["sanitized_data"]
else:
    # Handle validation errors
    print(f"Validation errors: {result['errors']}")
```

## FastAPI Integration

```python
from fastapi import FastAPI, Depends
from dotmac.security import (
    require_permission, 
    AuditMiddleware,
    TenantSecurityMiddleware
)

app = FastAPI()

# Add security middleware
app.add_middleware(AuditMiddleware)
app.add_middleware(TenantSecurityMiddleware)

# Protect endpoints with permissions
@app.get("/api/sensitive")
@require_permission(
    resource_type=ResourceType.API,
    action=ActionType.READ
)
async def sensitive_endpoint():
    return {"message": "Access granted"}
```

## Enterprise Features

```python
from dotmac.security.enterprise import (
    ComplianceReporter, 
    ThreatDetector,
    SSOIntegration
)

# Generate compliance reports
reporter = ComplianceReporter()
soc2_report = await reporter.generate_report(
    framework=ComplianceFramework.SOC2,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)

# Threat detection
detector = ThreatDetector()
threat_analysis = await detector.analyze_login_attempt(
    user_id="user123",
    ip_address="192.168.1.1",
    success=False
)

# SSO integration
sso = SSOIntegration(config={
    "provider": "oidc",
    "enabled": True
})
user_info = await sso.authenticate(token)
```

## Configuration

### Environment Variables

```bash
# Basic configuration
DOTMAC_SECURITY_CACHE_TTL=300
DOTMAC_SECURITY_MAX_CACHE_ENTRIES=10000
DOTMAC_SECURITY_ENABLE_AUDIT=true

# Enterprise features
DOTMAC_SECURITY_SSO_ENABLED=true
DOTMAC_SECURITY_SSO_PROVIDER=oidc
DOTMAC_SECURITY_THREAT_DETECTION=true
```

### Database Setup (Optional)

For persistent storage of permissions, roles, and audit events:

```python
from dotmac.security import setup_complete_rls
from sqlalchemy import create_engine

# Setup row-level security
engine = create_engine("postgresql://...")
session = Session(engine)

results = await setup_complete_rls(engine, session)
print(f"RLS setup: {results}")
```

## Testing

```bash
# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=dotmac.security

# Run integration tests
poetry run pytest tests/test_integration.py
```

## Architecture

The DotMac Security package follows a modular architecture:

```
dotmac.security/
├── access_control/     # RBAC/ABAC implementation
├── audit/             # Audit logging system
├── tenant_isolation/  # Multi-tenant security
├── sandbox/           # Plugin security sandbox
├── validation/        # Input validation
└── enterprise/        # Enterprise features
```

## Development

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

### Local Development

```bash
# Clone and setup
git clone <repository>
cd packages/dotmac-security
poetry install --with dev

# Run tests
poetry run pytest

# Run linting
poetry run ruff check src/
poetry run mypy src/
```

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: [https://docs.dotmac.framework](https://docs.dotmac.framework)
- Issues: [GitHub Issues](https://github.com/dotmac/framework/issues)
- Security: security@dotmac.framework