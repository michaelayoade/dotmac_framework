# DotMac Container Configuration Service

A comprehensive configuration management service for multi-tenant ISP container deployments, designed to handle per-container configuration injection, environment-specific settings, and secure secret management.

## 🚀 Features

### Configuration Management

- **Template-based Configuration Generation** per ISP tenant
- **Environment Variable Management** (dev, staging, production)
- **Secret Injection** with encryption (API keys, database passwords)
- **Feature Flag Management** per ISP (premium bundles, feature toggles)
- **Configuration Validation** and comprehensive error handling

### Multi-Tenant Support

- **Per-Tenant Isolation** with secure configuration boundaries
- **Subscription Plan Integration** for feature-based configuration
- **Dynamic Configuration Updates** without service restarts
- **Tenant-Specific Templates** and customization options

### Security & Compliance

- **Encrypted Secret Storage** with rotation support
- **Access Control** with tenant-scoped permissions
- **Audit Logging** for configuration changes
- **Validation Framework** with security checks
- **Secure Template Processing** with sandboxing

## 🏗️ Architecture

```
dotmac_shared/container_config/
├── README.md                   # This documentation
├── pyproject.toml             # Package configuration
├── __init__.py                # Package exports
├── core/                      # Core configuration components
│   ├── config_generator.py    # Main configuration generator
│   ├── template_engine.py     # Jinja2-based template processing
│   ├── secret_manager.py      # Secret handling with encryption
│   ├── feature_flags.py       # Premium feature management
│   └── validators.py          # Configuration validation
├── templates/                 # Configuration templates
│   ├── isp_config.yaml.j2     # ISP framework config template
│   ├── database_config.j2     # Database connection template
│   ├── feature_config.j2      # Premium features template
│   └── environments/          # Environment-specific templates
├── schemas/                   # Pydantic schemas
│   ├── config_schemas.py      # Configuration data models
│   ├── tenant_schemas.py      # Tenant-specific schemas
│   └── feature_schemas.py     # Feature flag schemas
├── adapters/                  # Platform integration
│   ├── isp_adapter.py         # ISP Framework integration
│   └── management_adapter.py  # Management Platform integration
└── tests/                     # Test suite
    ├── test_config_generation.py
    ├── test_template_engine.py
    ├── test_secret_manager.py
    └── test_feature_flags.py
```

## 🚀 Quick Start

### Installation

```bash
cd /home/dotmac_framework/src/dotmac_shared/container_config
pip install -e .
```

### Basic Usage

```python
from dotmac_shared.container_config import (
    ConfigurationGenerator,
    TemplateEngine,
    SecretManager,
    FeatureFlagManager
)
from dotmac_shared.container_config.schemas import ISPConfiguration, SubscriptionPlan

# Initialize components
config_generator = ConfigurationGenerator()
template_engine = TemplateEngine()
secret_manager = SecretManager()
feature_manager = FeatureFlagManager()

# Generate ISP configuration
isp_config = await config_generator.generate_isp_config(
    isp_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    plan=SubscriptionPlan.PREMIUM,
    environment="production"
)

# Apply secrets and features
config_with_secrets = await secret_manager.inject_secrets(isp_config)
final_config = await feature_manager.apply_feature_flags(config_with_secrets)

# Validate configuration
validation_result = await config_generator.validate_configuration(final_config)
```

### Template-Based Configuration

```python
# Create custom template
template_content = """
database:
  host: {{ database.host }}
  port: {{ database.port }}
  name: {{ tenant.database_name }}
  {% if plan.tier == "premium" %}
  connection_pool_size: 20
  {% else %}
  connection_pool_size: 5
  {% endif %}

features:
  {% for feature in enabled_features %}
  {{ feature.name }}: {{ feature.enabled }}
  {% endfor %}
"""

# Generate configuration
config = await template_engine.render_template(
    template_content,
    context={
        "tenant": tenant_data,
        "plan": subscription_plan,
        "database": db_config,
        "enabled_features": feature_list
    }
)
```

### Secret Management

```python
# Store encrypted secrets
await secret_manager.store_secret(
    tenant_id="tenant-123",
    key="database_password",
    value="super_secret_password",
    rotation_interval_days=90
)

# Inject secrets into configuration
config_with_secrets = await secret_manager.inject_secrets(
    config,
    tenant_id="tenant-123"
)

# Automatic secret rotation
await secret_manager.rotate_expired_secrets()
```

### Feature Flag Management

```python
# Configure premium features
feature_config = {
    "advanced_analytics": {
        "plans": ["premium", "enterprise"],
        "default_enabled": False
    },
    "custom_branding": {
        "plans": ["enterprise"],
        "default_enabled": False
    },
    "api_access": {
        "plans": ["premium", "enterprise"],
        "rate_limit": {"premium": 1000, "enterprise": 10000}
    }
}

# Apply feature flags to configuration
final_config = await feature_manager.apply_feature_flags(
    config,
    tenant_id="tenant-123",
    subscription_plan="premium"
)
```

## 🔧 Configuration

### Environment Variables

```bash
# Secret Management
SECRET_ENCRYPTION_KEY="your-256-bit-encryption-key"
SECRET_ROTATION_INTERVAL_DAYS=90
SECRET_STORAGE_BACKEND="database"  # database, vault, file

# Template Engine
TEMPLATE_CACHE_ENABLED=true
TEMPLATE_CACHE_TTL=3600
TEMPLATE_SANDBOX_ENABLED=true

# Feature Flags
FEATURE_FLAG_CACHE_TTL=300
FEATURE_FLAG_REFRESH_INTERVAL=60

# Validation
CONFIG_VALIDATION_STRICT=true
CONFIG_SCHEMA_VERSION="v1"
```

### Database Schema

The service requires database tables for storing configurations, secrets, and feature flags:

```sql
-- Tenant configurations
CREATE TABLE tenant_configurations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    environment VARCHAR(50) NOT NULL,
    config_data JSONB NOT NULL,
    template_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, environment)
);

-- Encrypted secrets
CREATE TABLE tenant_secrets (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    secret_key VARCHAR(255) NOT NULL,
    encrypted_value TEXT NOT NULL,
    rotation_interval_days INTEGER DEFAULT 90,
    last_rotated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, secret_key)
);

-- Feature flags
CREATE TABLE tenant_features (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    feature_name VARCHAR(255) NOT NULL,
    enabled BOOLEAN DEFAULT false,
    config_data JSONB,
    subscription_plan VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(tenant_id, feature_name)
);
```

## 📊 Core Functions

### Configuration Generation

```python
async def generate_isp_config(
    isp_id: UUID,
    plan: SubscriptionPlan,
    environment: str
) -> ISPConfiguration:
    """
    Generate complete ISP configuration for a specific tenant.

    Args:
        isp_id: Unique tenant identifier
        plan: Subscription plan (basic, premium, enterprise)
        environment: Target environment (dev, staging, production)

    Returns:
        Complete ISP configuration with all components
    """
```

### Secret Injection

```python
async def inject_secrets(
    config: ISPConfiguration
) -> ISPConfiguration:
    """
    Inject encrypted secrets into configuration.

    Args:
        config: Base configuration without secrets

    Returns:
        Configuration with secrets injected
    """
```

### Configuration Validation

```python
async def validate_configuration(
    config: ISPConfiguration
) -> ValidationResult:
    """
    Comprehensive configuration validation.

    Args:
        config: Configuration to validate

    Returns:
        Validation result with errors/warnings
    """
```

### Feature Flag Application

```python
async def apply_feature_flags(
    config: ISPConfiguration
) -> ISPConfiguration:
    """
    Apply feature flags based on subscription plan.

    Args:
        config: Base configuration

    Returns:
        Configuration with feature flags applied
    """
```

## 🛡️ Security Features

### Encryption at Rest

- **AES-256 encryption** for all secrets
- **Key rotation** with configurable intervals
- **Secure key derivation** using PBKDF2
- **Audit trail** for all secret operations

### Access Control

- **Tenant isolation** with strict boundaries
- **Role-based permissions** for configuration access
- **API key authentication** for service access
- **Rate limiting** to prevent abuse

### Validation & Sandboxing

- **Template sandboxing** to prevent code injection
- **Input validation** on all configuration data
- **Schema validation** with version control
- **Security scanning** for dangerous patterns

## 🧪 Testing

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=dotmac_shared.container_config --cov-report=html

# Run specific test categories
pytest tests/ -m "unit"
pytest tests/ -m "integration"
pytest tests/ -m "security"

# Performance tests
pytest tests/ -m "performance"
```

### Test Examples

```python
@pytest.mark.asyncio
async def test_generate_isp_config():
    """Test ISP configuration generation."""
    config_generator = ConfigurationGenerator()

    config = await config_generator.generate_isp_config(
        isp_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        plan=SubscriptionPlan.PREMIUM,
        environment="production"
    )

    assert config.tenant_id is not None
    assert config.database_config is not None
    assert config.feature_flags is not None
    assert len(config.services) > 0

@pytest.mark.asyncio
async def test_secret_injection():
    """Test secret injection into configuration."""
    secret_manager = SecretManager()

    # Store test secret
    await secret_manager.store_secret(
        tenant_id="test-tenant",
        key="db_password",
        value="test_password"
    )

    # Create config with placeholder
    config = ISPConfiguration(
        tenant_id="test-tenant",
        database_config={
            "password": "${SECRET:db_password}"
        }
    )

    # Inject secrets
    result = await secret_manager.inject_secrets(config)

    assert result.database_config["password"] == "test_password"
```

## 🔗 Integration Examples

### ISP Framework Integration

```python
from dotmac_shared.container_config.adapters import ISPConfigAdapter

# Initialize adapter
config_adapter = ISPConfigAdapter(config_generator)

# Use in ISP Framework startup
async def configure_isp_container():
    config = await config_adapter.get_tenant_config(
        tenant_id=current_tenant_id,
        environment=current_environment
    )

    # Apply configuration to services
    await setup_database(config.database_config)
    await setup_features(config.feature_flags)
    await setup_integrations(config.external_services)
```

### Management Platform Integration

```python
from dotmac_shared.container_config.adapters import ManagementConfigAdapter

# Initialize adapter
config_adapter = ManagementConfigAdapter(config_generator)

# Create tenant configuration
@router.post("/tenants/{tenant_id}/config")
async def create_tenant_config(
    tenant_id: UUID,
    plan: SubscriptionPlan,
    environment: str
):
    config = await config_adapter.create_tenant_config(
        tenant_id=tenant_id,
        plan=plan,
        environment=environment
    )

    return {"config_id": config.id, "status": "created"}
```

## 📈 Performance Considerations

- **Template Caching**: Compiled templates cached for reuse
- **Configuration Caching**: Generated configs cached per tenant/environment
- **Lazy Loading**: Secrets loaded only when needed
- **Batch Operations**: Support for bulk configuration updates
- **Connection Pooling**: Database connections efficiently managed

## 📞 Support

For issues and questions:

- GitHub Issues: [container-config/issues](https://github.com/dotmac-framework/container-config/issues)
- Documentation: [docs.dotmac-framework.com/container-config](https://docs.dotmac-framework.com/container-config)
- Email: <support@dotmac-framework.com>

## 📜 License

MIT License - see LICENSE file for details.

---

**Built for secure, scalable ISP container configuration management** 🚀
