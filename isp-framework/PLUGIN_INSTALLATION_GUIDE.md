# Plugin Installation Guide

This guide explains how to install and manage third-party integration plugins in the DotMac ISP Framework.

## Overview

The DotMac ISP Framework uses a **plugin-based architecture** for third-party integrations like Twilio, Stripe, network automation tools, and more. This approach provides:

- **Clean separation** between core framework and vendor-specific code
- **Optional dependencies** - only install what you need
- **Multi-tenant support** with isolated plugin configurations
- **Secure credential management** via vault/secrets
- **Hot-reloadable plugins** for development
- **Health monitoring** and usage metrics

## Installation Methods

### Method 1: Command Line (Recommended)

```bash
# Install a specific plugin
make install-plugin PLUGIN=twilio

# Install multiple common plugins
make install-common-plugins

# List available and installed plugins
make list-plugins

# Remove a plugin
make remove-plugin PLUGIN=twilio
```

### Method 2: Admin Web Interface

1. Navigate to **Admin Dashboard** → **Plugins**
2. Browse available plugins by category
3. Click **Install** on desired plugins
4. Configure plugin credentials
5. Activate plugins for your tenant(s)

### Method 3: Direct Script Usage

```bash
# Install plugin directly
python scripts/install_plugin.py twilio

# List all plugins with status
python scripts/list_plugins.py

# Remove plugin
python scripts/remove_plugin.py twilio
```

## Available Plugins

### Communication
- **twilio** - SMS communication via Twilio API
- **sendgrid** - Email delivery via SendGrid API  
- **slack** - Slack notifications and integrations

### Billing & Payments
- **stripe** - Payment processing via Stripe API

### Network Automation
- **network-automation** - SNMP, SSH, and Ansible automation
  - Includes: pysnmp, paramiko, ansible-runner

### CRM Integration
- **hubspot** - CRM integration with HubSpot
- **mailchimp** - Email marketing via Mailchimp

## Plugin Configuration

### 1. Environment Variables (Simple)

```bash
# Twilio
export TWILIO_ACCOUNT_SID="ACXXXX..."
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_PHONE_NUMBER="+1234567890"

# Stripe  
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
```

### 2. Configuration Files (Advanced)

After installation, plugins create example configuration files:

```bash
config/plugins/twilio.json.example
config/plugins/stripe.json.example
```

Copy and customize:

```bash
cp config/plugins/twilio.json.example config/plugins/twilio.json
```

Example configuration:

```json
{
  "plugin_id": "twilio",
  "name": "Twilio SMS Plugin",
  "category": "communication",
  "enabled": true,
  "config_data": {
    "account_sid": "${vault:twilio/account_sid}",
    "auth_token": "${vault:twilio/auth_token}",
    "phone_number": "${vault:twilio/phone_number}"
  },
  "security": {
    "sandbox_enabled": true,
    "resource_limits": {
      "memory_mb": 256,
      "cpu_percent": 10
    }
  }
}
```

### 3. Vault/Secrets Management (Production)

Store sensitive credentials in OpenBao/Vault:

```bash
# Store Twilio credentials
vault kv put secret/twilio \
  account_sid="ACXXXX..." \
  auth_token="your_token" \
  phone_number="+1234567890"
```

Reference in config using `${vault:path/key}` syntax.

## Plugin Management via API

### List Plugins

```bash
curl -X GET "http://localhost:8000/api/admin/plugins" \
  -H "Authorization: Bearer $TOKEN"
```

### Install Plugin

```bash
curl -X POST "http://localhost:8000/api/admin/plugins/install" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "plugin_id": "twilio",
    "config_data": {
      "account_sid": "ACXXXX...",
      "auth_token": "your_token",
      "phone_number": "+1234567890"
    }
  }'
```

### Plugin Status

```bash
curl -X GET "http://localhost:8000/api/admin/plugins/twilio/status" \
  -H "Authorization: Bearer $TOKEN"
```

### Activate Plugin

```bash
curl -X POST "http://localhost:8000/api/admin/plugins/twilio/activate" \
  -H "Authorization: Bearer $TOKEN"
```

## Plugin Development

### Creating Custom Plugins

1. **Inherit from Base Plugin Class**:

```python
from dotmac_isp.plugins.core.base import BasePlugin, PluginInfo, PluginCategory

class MyCustomPlugin(BasePlugin):
    @property
    def plugin_info(self) -> PluginInfo:
        return PluginInfo(
            id="my-plugin",
            name="My Custom Plugin",
            version="1.0.0",
            description="Custom integration plugin",
            author="Your Company",
            category=PluginCategory.CUSTOM
        )
    
    async def initialize(self) -> None:
        # Setup resources
        pass
    
    async def activate(self) -> None:
        # Start plugin operations
        pass
    
    async def deactivate(self) -> None:
        # Stop plugin operations
        pass
    
    async def cleanup(self) -> None:
        # Clean up resources
        pass
```

2. **Add to Plugin Definitions**:

Update `scripts/install_plugin.py`:

```python
PLUGIN_DEFINITIONS["my-plugin"] = {
    "name": "My Custom Plugin",
    "dependencies": ["my-dependency>=1.0.0"],
    "category": "custom",
    "description": "My custom integration",
    "config_example": {
        "api_key": "your_api_key",
        "endpoint": "https://api.example.com"
    }
}
```

## Multi-Tenant Usage

### Tenant-Specific Installation

```python
from dotmac_isp.plugins.core.manager import plugin_manager

# Install for specific tenant
await plugin_manager.install_plugin(
    plugin_source="twilio_plugin",
    config=PluginConfig(
        tenant_id=tenant_id,
        config_data={"account_sid": "tenant_specific_sid"}
    ),
    tenant_id=tenant_id
)
```

### Tenant Context

```python
# Set tenant context before plugin operations
context = PluginContext(tenant_id=tenant_id, user_id=user_id)
plugin_instance.set_context(context)
```

## Monitoring & Health Checks

### Plugin Health Status

```bash
# Via CLI
make list-plugins

# Via API
curl -X GET "http://localhost:8000/api/admin/plugins/twilio/status"
```

### Plugin Metrics

```python
# Get plugin metrics
metrics = await plugin_manager.get_plugin_metrics("twilio")
print(f"API calls: {metrics.get('api_calls', 0)}")
print(f"Uptime: {metrics.get('uptime_seconds', 0)}s")
```

### Health Monitoring

Plugins automatically report:
- Installation status
- Dependency availability  
- Runtime health
- Error rates
- Performance metrics

## Troubleshooting

### Common Issues

**Plugin not found:**
```bash
# Check available plugins
make list-plugins

# Check plugin definitions
python scripts/list_plugins.py
```

**Dependency conflicts:**
```bash
# Check for conflicts before removal
python scripts/remove_plugin.py plugin_name
```

**Import errors after installation:**
```bash
# Restart the application
make run-dev

# Check plugin status
curl -X GET "http://localhost:8000/api/admin/plugins/plugin_name/status"
```

**Configuration issues:**
```bash
# Validate configuration
python scripts/install_plugin.py plugin_name

# Check logs
docker logs dotmac-isp-app
```

## Security Considerations

- **Credential Storage**: Use vault/secrets management for production
- **Plugin Sandboxing**: Enable sandbox mode in plugin configurations
- **Resource Limits**: Set memory and CPU limits per plugin
- **Access Control**: Restrict plugin management to admin users
- **Audit Logging**: All plugin operations are logged for compliance

## Migration from Direct Dependencies

If you previously had direct dependencies in `pyproject.toml`:

1. **Remove direct dependencies** (already done)
2. **Install plugins individually**:
   ```bash
   make install-plugin PLUGIN=twilio
   make install-plugin PLUGIN=stripe  
   make install-plugin PLUGIN=network-automation
   ```
3. **Update application code** to use plugin manager instead of direct imports
4. **Configure plugins** with your existing credentials
5. **Test functionality** to ensure everything works

## Support

- **Documentation**: See `/docs/plugins/` for detailed plugin documentation
- **API Reference**: Available at `/docs` when running the server
- **Issues**: Report plugin issues via the admin interface or logs
- **Custom Development**: Contact support for custom plugin development