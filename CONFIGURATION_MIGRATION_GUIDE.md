# Configuration Migration Guide

## Overview

This guide provides step-by-step instructions for migrating from the legacy configuration system to the enhanced unified configuration management system across both the DotMac ISP Framework and Management Platform.

## Migration Timeline

**Estimated Migration Time**: 2-4 hours per platform instance
**Recommended Window**: Maintenance window with backup systems ready

## Pre-Migration Checklist

### ✅ Prerequisites

1. **Backup Current Configuration**
   ```bash
   # Create full configuration backup
   curl -X POST http://localhost:8000/api/v1/config/backup \
     -H "Authorization: Bearer <admin-token>" \
     -d '{"backup_name": "pre-migration-backup", "include_secrets": true}'
   ```

2. **Verify OpenBao/Vault Access**
   ```bash
   # Test OpenBao connectivity
   export OPENBAO_ADDR="https://vault.dotmac.internal:8200"
   export OPENBAO_TOKEN="your-token-here"
   openbao status
   ```

3. **Check Current Configuration Health**
   ```bash
   # Verify current configuration is healthy
   curl -X GET http://localhost:8000/health
   ```

4. **Document Current Environment Variables**
   ```bash
   # Export current environment variables
   printenv | grep -E "(DATABASE|REDIS|STRIPE|TWILIO|SMTP)" > current_env_vars.txt
   ```

## Migration Steps

### Phase 1: Install Enhanced Configuration Components

#### 1.1 Update Dependencies

**For ISP Framework:**
```bash
cd /home/dotmac_framework/dotmac_isp_framework
pip install openbao-client cryptography python-jose pydantic-settings
```

**For Management Platform:**
```bash
cd /home/dotmac_framework/dotmac_management_platform
pip install openbao-client cryptography python-jose
```

#### 1.2 Deploy Enhanced Configuration Files

The enhanced configuration system includes these new components:
- `src/dotmac_isp/core/enhanced_settings.py` (replaces `settings.py`)
- `src/dotmac_isp/core/secrets_manager.py`
- `src/dotmac_isp/core/config_encryption.py`
- `src/dotmac_isp/core/config_audit.py`
- `src/dotmac_isp/core/config_backup.py`
- `src/dotmac_isp/core/config_hotreload.py`
- `src/dotmac_isp/core/secure_config_validator.py`
- `src/dotmac_isp/core/config_disaster_recovery.py`

### Phase 2: OpenBao/Vault Setup

#### 2.1 Initialize OpenBao Vault

```bash
# Initialize OpenBao server
openbao operator init -key-shares=5 -key-threshold=3

# Save unseal keys and root token securely
echo "OPENBAO_UNSEAL_KEY_1=key1" >> .openbao_keys
echo "OPENBAO_UNSEAL_KEY_2=key2" >> .openbao_keys  
echo "OPENBAO_UNSEAL_KEY_3=key3" >> .openbao_keys
echo "OPENBAO_ROOT_TOKEN=root_token" >> .openbao_keys
chmod 600 .openbao_keys
```

#### 2.2 Configure OpenBao Policies

```bash
# Create tenant-specific policies
openbao policy write tenant-123-secrets - <<EOF
path "dotmac/tenants/tenant-123/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF

# Create service-specific policies  
openbao policy write isp-framework-secrets - <<EOF
path "dotmac/services/isp-framework/*" {
  capabilities = ["read", "list"]
}
EOF
```

#### 2.3 Enable Secret Engines

```bash
# Enable KV secrets engine for tenant secrets
openbao secrets enable -path=dotmac kv-v2

# Create tenant namespace structure
openbao kv put dotmac/tenants/tenant-123/database \
  host="tenant-123-db.internal" \
  username="dotmac_tenant_123" \
  password="generated-secure-password"
```

### Phase 3: Migrate Existing Secrets

#### 3.1 Extract Current Secrets

```bash
# Create migration script
cat > migrate_secrets.py <<EOF
import os
import json
from dotmac_isp.core.secrets_manager import SecretsManager

# Initialize secrets manager
secrets_manager = SecretsManager()

# Current environment secrets to migrate
secrets_to_migrate = {
    "database/url": os.getenv("DATABASE_URL"),
    "database/async_url": os.getenv("ASYNC_DATABASE_URL"),
    "redis/url": os.getenv("REDIS_URL"),
    "stripe/secret_key": os.getenv("STRIPE_SECRET_KEY"),
    "twilio/account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
    "smtp/server": os.getenv("SMTP_SERVER")
}

# Migrate each secret
async def migrate_secrets():
    for path, value in secrets_to_migrate.items():
        if value:
            await secrets_manager.store_secret(
                secret_path=path,
                secret_value=value,
                description=f"Migrated from environment variable",
                rotation_interval_days=30
            )
            print(f"Migrated secret: {path}")

# Run migration
import asyncio
asyncio.run(migrate_secrets())
EOF

# Execute migration
python migrate_secrets.py
```

#### 3.2 Configure Environment Variables

Update your environment configuration:

```bash
# Add OpenBao configuration
cat >> .env <<EOF
# Enhanced Configuration Settings
OPENBAO_URL=https://vault.dotmac.internal:8200
OPENBAO_TOKEN=hvs.your-token-here
OPENBAO_NAMESPACE=dotmac/tenants/tenant-123
CONFIG_ENCRYPTION_KEY=$(openssl rand -base64 32)
ENABLE_CONFIG_HOT_RELOAD=true
CONFIG_AUDIT_WEBHOOK_URL=https://audit.dotmac.internal/webhook

# Legacy settings (will be deprecated after migration)
DATABASE_URL=postgresql://user:pass@localhost:5432/dotmac_isp  # DEPRECATED
REDIS_URL=redis://localhost:6379/0  # DEPRECATED
EOF
```

### Phase 4: Update Application Configuration

#### 4.1 Update Import Statements

**Before (old settings.py):**
```python
from dotmac_isp.core.settings import settings
```

**After (enhanced_settings.py):**
```python
from dotmac_isp.core.enhanced_settings import settings
```

#### 4.2 Update Configuration Usage

**Before:**
```python
# Direct environment variable access
database_url = os.getenv("DATABASE_URL")
stripe_key = os.getenv("STRIPE_SECRET_KEY")
```

**After:**
```python
# Secure secrets manager access
database_url = await settings.secrets_manager.get_secret("database/url")
stripe_key = await settings.secrets_manager.get_secret("stripe/secret_key")
```

### Phase 5: Enable Advanced Features

#### 5.1 Configure Audit Logging

```python
# Add audit logging to critical operations
from dotmac_isp.core.config_audit import ConfigurationAudit

audit = ConfigurationAudit()
await audit.log_configuration_change(
    component="database",
    old_values={"host": "old-host"},
    new_values={"host": "new-host"},
    user_id="admin-123",
    change_reason="Database migration"
)
```

#### 5.2 Setup Hot-Reload Capability

```python
# Enable hot-reload for specific components
from dotmac_isp.core.config_hotreload import ConfigurationHotReload

hot_reload = ConfigurationHotReload()
await hot_reload.trigger_reload(
    component="redis",
    validate_only=True,  # Test reload first
    rollback_on_failure=True
)
```

#### 5.3 Configure Automatic Backups

```bash
# Setup backup cron job
crontab -e

# Add line: Create configuration backup daily at 2 AM
0 2 * * * curl -X POST http://localhost:8000/api/v1/config/backup \
  -H "Authorization: Bearer $(cat /etc/dotmac/admin-token)" \
  -d '{"backup_name": "daily-auto-backup"}'
```

### Phase 6: Management Platform Cross-Platform Integration

#### 6.1 Configure Multi-Tenant Secrets Management

```python
# Initialize multi-tenant secrets manager
from dotmac_management.shared.security.secrets_manager import MultiTenantSecretsManager

mt_secrets = MultiTenantSecretsManager()

# Create tenant secret namespace
await mt_secrets.create_tenant_secret_namespace("tenant-123")

# Provision tenant-specific secrets
await mt_secrets.provision_tenant_secrets(
    tenant_id="tenant-123",
    secrets={
        "database": {"password": "tenant-secure-pwd"},
        "plugins": {"advanced_analytics": "license-key-123"}
    }
)
```

#### 6.2 Setup Cross-Platform Audit Orchestration

```python
# Configure audit orchestrator
from dotmac_management.shared.audit_orchestrator import CrossPlatformAuditOrchestrator

audit_orchestrator = CrossPlatformAuditOrchestrator()

# Log cross-platform events
await audit_orchestrator.log_cross_platform_event(
    source="management_platform",
    target="tenant_isp_framework",
    tenant_id="tenant-123",
    event="configuration_sync",
    event_data={"component": "billing", "action": "webhook_update"}
)
```

## Validation and Testing

### 6.1 Verify Migration Success

```bash
# Test secret retrieval
curl -X GET http://localhost:8000/api/v1/config/secrets/database/url \
  -H "Authorization: Bearer <admin-token>"

# Test configuration health
curl -X GET http://localhost:8000/api/v1/config/health \
  -H "Authorization: Bearer <admin-token>"

# Test hot-reload capability
curl -X POST http://localhost:8000/api/v1/config/hot-reload \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"component": "redis", "validate_only": true}'
```

### 6.2 Run Compliance Validation

```bash
# Validate compliance with all frameworks
curl -X POST http://localhost:8000/api/v1/config/compliance/validate \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"frameworks": ["SOC2", "GDPR", "PCI_DSS", "ISO27001"]}'
```

### 6.3 Test Disaster Recovery

```bash
# Test disaster detection
curl -X POST http://localhost:8000/api/v1/config/disaster-recovery/detect \
  -H "Authorization: Bearer <admin-token>"

# Test backup restoration (use test backup)
curl -X POST http://localhost:8000/api/v1/config/backup/test-backup-id/restore \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"components": ["redis"], "confirm_restore": true}'
```

## Post-Migration Steps

### 7.1 Remove Legacy Configuration

```bash
# After successful validation, remove legacy environment variables
cat > cleanup_legacy.sh <<EOF
#!/bin/bash
# Remove legacy environment variables from .env file
sed -i '/# DEPRECATED/d' .env

# Remove old settings.py (renamed as backup)
mv src/dotmac_isp/core/settings.py src/dotmac_isp/core/settings.py.legacy

# Create symbolic link to enhanced settings
ln -sf enhanced_settings.py src/dotmac_isp/core/settings.py
EOF

chmod +x cleanup_legacy.sh
./cleanup_legacy.sh
```

### 7.2 Configure Monitoring and Alerting

```bash
# Setup configuration monitoring webhook
curl -X POST http://localhost:8000/api/v1/config/webhooks \
  -H "Authorization: Bearer <admin-token>" \
  -d '{
    "url": "https://monitoring.dotmac.internal/config-alerts",
    "events": [
      "configuration.updated",
      "secret.rotated",
      "compliance.violation",
      "disaster.detected"
    ]
  }'
```

### 7.3 Setup Secret Rotation Schedule

```bash
# Configure automatic secret rotation
curl -X POST http://localhost:8000/api/v1/config/secrets/stripe/secret_key/rotate \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"schedule": "monthly", "auto_rotation": true}'
```

## Rollback Plan

In case migration fails, follow these rollback steps:

### 8.1 Emergency Rollback

```bash
# Restore from pre-migration backup
curl -X POST http://localhost:8000/api/v1/config/backup/pre-migration-backup/restore \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"confirm_restore": true, "components": ["all"]}'

# Revert to legacy settings
mv src/dotmac_isp/core/settings.py.legacy src/dotmac_isp/core/settings.py

# Restart service with legacy configuration
systemctl restart dotmac-isp-framework
```

### 8.2 Verify Rollback

```bash
# Confirm service is healthy with legacy config
curl -X GET http://localhost:8000/health

# Verify database connectivity
curl -X GET http://localhost:8000/api/v1/identity/users \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json"
```

## Troubleshooting

### Common Issues

#### Issue: OpenBao Connection Failed
```bash
# Check OpenBao status
openbao status

# Verify network connectivity
curl -k https://vault.dotmac.internal:8200/v1/sys/health

# Check firewall rules
sudo netstat -tlnp | grep 8200
```

#### Issue: Secret Retrieval Failed
```bash
# Test OpenBao token permissions
openbao token lookup

# List available secrets
openbao kv list dotmac/tenants/tenant-123/

# Test direct secret access
openbao kv get dotmac/tenants/tenant-123/database
```

#### Issue: Configuration Validation Failed
```bash
# Check configuration syntax
python -c "from dotmac_isp.core.enhanced_settings import settings; print('Config valid')"

# Validate specific components
curl -X POST http://localhost:8000/api/v1/config/validate \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"component": "database"}'
```

## Support and Documentation

- **Configuration API Reference**: `/CONFIGURATION_API.md`
- **Cross-Platform API Reference**: `/CROSS_PLATFORM_CONFIG_API.md`  
- **Architecture Documentation**: `/ARCHITECTURE.md`
- **Security Implementation**: `/SECURITY_IMPLEMENTATION_SUMMARY.md`

## Migration Checklist

- [ ] ✅ Created pre-migration backup
- [ ] ✅ Installed enhanced configuration components  
- [ ] ✅ Configured OpenBao/Vault server
- [ ] ✅ Migrated existing secrets to vault
- [ ] ✅ Updated application imports and configuration usage
- [ ] ✅ Enabled audit logging
- [ ] ✅ Configured hot-reload capability
- [ ] ✅ Setup automatic backups
- [ ] ✅ Configured cross-platform orchestration (Management Platform)
- [ ] ✅ Validated migration success
- [ ] ✅ Ran compliance validation
- [ ] ✅ Tested disaster recovery
- [ ] ✅ Removed legacy configuration
- [ ] ✅ Setup monitoring and alerting
- [ ] ✅ Configured secret rotation schedules

**Migration Complete!** 🎉

Your DotMac platform now benefits from enterprise-grade configuration management with enhanced security, audit trails, hot-reloading, and disaster recovery capabilities.