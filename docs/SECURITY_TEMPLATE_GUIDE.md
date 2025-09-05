# Security Template Guide for DotMac Framework

## 🛡️ Overview

This guide explains how to work with secret templates in the DotMac Framework while maintaining security scanning compatibility.

## ✅ Approved Template Patterns

### Secret Injection Templates

Use `${SECRET:descriptive_name}` for all secret placeholders:

```python
# ✅ CORRECT - Will be ignored by security scanners
database_config = {
    "host": "postgres.example.com",
    "password": "${SECRET:database_password}",  # nosec: template
    "username": "${SECRET:database_username}"   # nosec: template
}

api_config = {
    "stripe_key": "${SECRET:stripe_secret_key}",    # nosec: template
    "sendgrid_key": "${SECRET:sendgrid_api_key}",   # nosec: template
    "twilio_key": "${SECRET:twilio_api_key}"        # nosec: template
}
```

## 📝 Inline Documentation

### Required Comments

Add these comments to help security scanners and developers:

```python
# Template patterns - replaced at deployment time
password = "${SECRET:redis_password}"      # nosec: template
api_key = "${SECRET:payment_gateway_key}"  # nosec: template

# Validation logic for secret templates
if config.jwt_secret.startswith("${SECRET:"):  # nosec: validation
    result.add_info("SECRET_PLACEHOLDER", "Using template")
```

### Comment Patterns Recognized

Security scanners look for these patterns:
- `# nosec: template` - Indicates legitimate secret template
- `# Template - replaced at deployment` - Deployment documentation
- `# Will be replaced by secret manager` - Secret management note
- `# Safe: secret injection placeholder` - Safety confirmation

## 🔧 Configuration File Templates

### Environment Configuration

```python
# config/environment.py
class DatabaseConfig:
    def __init__(self):
        # Database credentials injected at runtime
        self.host = os.getenv("DB_HOST", "localhost")
        self.password = "${SECRET:postgres_password}"  # nosec: template
        self.username = "${SECRET:postgres_username}"  # nosec: template
        
class ExternalServiceConfig:
    def __init__(self):
        # Third-party service credentials  
        self.stripe_key = "${SECRET:stripe_secret_key}"    # nosec: template
        self.sendgrid_key = "${SECRET:sendgrid_api_key}"   # nosec: template
```

### Kubernetes ConfigMaps

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  database_url: "postgres://user:${SECRET:db_password}@postgres:5432/app"
  redis_url: "redis://:${SECRET:redis_password}@redis:6379/0"
  
  # External service configurations
  stripe_webhook_secret: "${SECRET:stripe_webhook_secret}"
  sendgrid_api_key: "${SECRET:sendgrid_api_key}"
```

## ❌ Patterns to Avoid

### Never Do This

```python
# ❌ WRONG - Will trigger security alerts
password = "my_real_password_123"
api_key = "sk_live_abc123def456ghi789"
secret = "hardcoded_secret_value"

# ❌ WRONG - Partial templates
password = "prefix_${SECRET:db_pass}_suffix"

# ❌ WRONG - No descriptive names  
password = "${SECRET:pass1}"
api_key = "${SECRET:key}"
```

## 🔍 Security Scanning Integration

### How Scanners Handle Templates

Our security tools are configured to:

1. **Recognize Templates**: `${SECRET:*}` patterns are allowlisted
2. **Context Awareness**: Different rules for config vs validation files
3. **Comment Detection**: `# nosec: template` comments are respected
4. **Path-Based Rules**: Config generators have relaxed scanning

### Supported Security Tools

| Tool | Configuration File | Purpose |
|------|-------------------|---------|
| GitLeaks | `.security/gitleaks.toml` | Git history scanning |
| TruffleHog | `.security/trufflehog-exclude.txt` | Pattern exclusions |
| Semgrep | `.github/workflows/security-scanning.yml` | Static analysis |
| Custom Scanner | `.security/template-aware-scan.py` | Template-aware detection |

## 🏗️ Development Workflow

### Adding New Secret Templates

1. **Use Standard Format**
   ```python
   new_service_key = "${SECRET:service_name_api_key}"  # nosec: template
   ```

2. **Add Documentation**
   ```python
   # PayPal integration credentials - injected by deployment system
   paypal_client_id = "${SECRET:paypal_client_id}"      # nosec: template
   paypal_secret = "${SECRET:paypal_client_secret}"     # nosec: template
   ```

3. **Test Security Scanning**
   ```bash
   # Run local security scan
   python3 .security/template-aware-scan.py
   
   # Should show: "✅ All ${SECRET:*} templates properly ignored"
   ```

4. **Document in Deployment**
   - Add to secret management documentation
   - Include in deployment checklist
   - Update environment variable lists

### Pull Request Checklist

When adding secret templates:

- [ ] Uses `${SECRET:descriptive_name}` format
- [ ] Includes `# nosec: template` comment
- [ ] Has descriptive documentation
- [ ] Passes security scanning locally
- [ ] Added to deployment documentation

## 🚨 Troubleshooting

### Security Scan Failures

If security scanning fails:

1. **Check Pattern Format**
   - Ensure `${SECRET:name}` format is exact
   - No spaces inside the braces
   - Descriptive names used

2. **Add Appropriate Comments**
   ```python
   # Add this comment for scanners
   password = "${SECRET:db_password}"  # nosec: template
   ```

3. **Verify File Patterns**
   - Config files should use templates
   - Validation files have special rules
   - Test files are usually ignored

### Common Issues

**Issue**: Scanner still reports template as violation  
**Solution**: Check comment format and ensure no typos in template

**Issue**: Template not being replaced in deployment  
**Solution**: Verify secret name matches in secret management system

**Issue**: Multiple security tools giving different results  
**Solution**: Check each tool's configuration file in `.security/`

## 📋 Template Registry

### Database Secrets
- `${SECRET:postgres_password}` - PostgreSQL password
- `${SECRET:postgres_username}` - PostgreSQL username  
- `${SECRET:redis_password}` - Redis authentication
- `${SECRET:mongodb_connection_string}` - MongoDB URI

### External Service APIs
- `${SECRET:stripe_secret_key}` - Stripe payments
- `${SECRET:stripe_webhook_secret}` - Stripe webhook validation
- `${SECRET:sendgrid_api_key}` - SendGrid email service
- `${SECRET:twilio_api_key}` - Twilio SMS service
- `${SECRET:aws_access_key_id}` - AWS API access
- `${SECRET:aws_secret_access_key}` - AWS API secret

### Application Secrets
- `${SECRET:jwt_secret_key}` - JWT token signing
- `${SECRET:encryption_key}` - Data encryption
- `${SECRET:session_secret}` - Session management
- `${SECRET:webhook_signing_secret}` - Webhook validation

## 🔄 Maintenance

### Regular Tasks

- **Monthly**: Review template usage in codebase
- **Quarterly**: Update security tool configurations  
- **Per Release**: Verify all templates resolve in production
- **As Needed**: Add new templates to registry

### Template Lifecycle

1. **Development**: Add template with documentation
2. **Testing**: Verify scanner ignores template
3. **Deployment**: Configure secret in management system
4. **Production**: Monitor template resolution
5. **Maintenance**: Update or rotate secrets as needed

This approach ensures **strong security** while enabling **efficient development** with proper secret management.