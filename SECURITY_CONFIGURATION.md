# Security Configuration Guide

## Overview

This document outlines the security hardening measures implemented in the DotMac Platform.

## Security Improvements Implemented

### 1. Dynamic Import Security

**Issue**: Unsafe dynamic imports could allow code injection
**Solution**: Implemented module allowlists and secure import functions

**Files Modified:**
- `/isp-framework/src/dotmac_isp/core/secrets/dependencies.py`
- `/isp-framework/src/dotmac_isp/api/routers.py`

**Security Controls:**
```python
# Allowlist for trusted modules only
ALLOWED_MODULE_PREFIXES = (
    'dotmac_isp',
    'structlog', 
    'pydantic',
    'cryptography',
    'jwt',
    'sqlalchemy',
    'redis',
    'celery',
    'fastapi',
    'uvicorn',
    'opentelemetry',
    'hvac',
    'prometheus_client',
    'psutil'
)

# Validation before import
if not module_name.startswith(ALLOWED_MODULE_PREFIXES):
    logging.warning(f"Security: Blocked import of untrusted module: {module_name}")
    return None
```

### 2. Environment File Consolidation

**Issue**: Multiple environment files could create conflicts
**Solution**: Removed duplicate/unnecessary environment files

**Removed Files:**
- `.env.development.template`
- `.env.production.template` 
- `.env.unified`
- `.env.staging`

**Retained Structure:**
```
├── .env                    # Local development
├── .env.example            # Template file
├── .env.development        # Development environment
├── .env.production         # Production environment
└── .env.signoz            # Monitoring configuration
```

### 3. Explicit Imports

**Issue**: Star imports could expose unintended modules
**Solution**: Replaced critical star imports with explicit imports

**Files Modified:**
- `/management-platform/migrations/env.py` - Critical Alembic migration file

**Before:**
```python
from app.models import *
```

**After:**
```python
from app.models.billing import (
    BillingAccount, Invoice, InvoiceItem, Payment, PaymentMethod,
    Subscription, SubscriptionItem, UsageRecord, BillingEvent
)
from app.models.deployment import (
    Deployment, DeploymentLog, Infrastructure, Resource
)
# ... explicit imports for all models
```

## Security Features Already in Place

### 1. Import Validation
- Module allowlists prevent arbitrary code execution
- Logging of blocked import attempts
- Graceful fallback for missing dependencies

### 2. Configuration Security
- Environment files properly gitignored
- Separate configurations for different environments
- No sensitive data in templates

### 3. Router Security
- Only trusted modules can register routes
- Namespace validation for all dynamic router loading
- Import path validation before module loading

## Production Security Checklist

### Environment Setup
- [ ] Use `.env.production` with production values
- [ ] Ensure all `.env*` files have proper permissions (600)
- [ ] Verify no sensitive data in `.env.example`

### Module Security
- [ ] Review allowlist in `dependencies.py` for your deployment
- [ ] Monitor logs for blocked import attempts
- [ ] Validate all dynamic imports use secure functions

### Monitoring
- [ ] Enable security logging in production
- [ ] Set up alerts for blocked import attempts
- [ ] Monitor environment file access

## Additional Recommendations

### 1. Runtime Security
```python
# Add to production startup
import logging
logging.getLogger('dotmac_isp.core.secrets.dependencies').setLevel(logging.WARNING)
```

### 2. File Permissions
```bash
# Secure environment files
chmod 600 .env*
chown app:app .env*
```

### 3. Monitoring
```python
# Add security metrics
from prometheus_client import Counter
blocked_imports = Counter('blocked_imports_total', 'Number of blocked import attempts')
```

## Testing Security Controls

### 1. Test Import Blocking
```python
# This should be blocked and logged
from dotmac_isp.core.secrets.dependencies import import_optional
result = import_optional('os')  # Should return None and log warning
assert result is None
```

### 2. Test Router Security
```python
# This should be blocked in router registration
malicious_router = ('malicious_module', 'router', '/api/evil')
# Should log warning and continue without registering
```

## Security Maintenance

1. **Regular Reviews**: Review allowlists monthly
2. **Log Monitoring**: Check security logs weekly
3. **Dependency Updates**: Update security dependencies promptly
4. **Configuration Audits**: Audit environment files quarterly

## Contact

For security concerns, review the implementation in:
- Security module: `/isp-framework/src/dotmac_isp/core/secrets/`
- Router security: `/isp-framework/src/dotmac_isp/api/routers.py`
- Environment management: Root and service-level `.env` files