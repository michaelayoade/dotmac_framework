# Security Guidelines

## ⚠️ IMPORTANT SECURITY WARNINGS

### Environment Variables
**NEVER use example values in production!** All example secrets in this documentation are for illustration only.

### Required Security Configuration

Before deploying to production, you **MUST** configure these environment variables with secure values:

```bash
# Generate a strong JWT secret (32+ characters)
JWT_SECRET_KEY="$(openssl rand -hex 32)"

# Set specific CORS origins (never use "*")
CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"

# Use strong database credentials
DATABASE_URL="postgresql+asyncpg://secure_user:$(openssl rand -hex 16)@db.example.com/events"

# Redis authentication
REDIS_PASSWORD="$(openssl rand -hex 24)"

# Kafka SASL credentials
KAFKA_SASL_USERNAME="secure_user"
KAFKA_SASL_PASSWORD="$(openssl rand -hex 24)"
```

### Security Checklist

Before production deployment:

- [ ] JWT_SECRET_KEY is set to a cryptographically secure random value
- [ ] CORS_ORIGINS is configured with specific trusted domains (no wildcards)
- [ ] Database uses strong authentication and TLS/SSL
- [ ] Redis/Kafka use authentication and encryption
- [ ] Rate limiting is enabled and configured appropriately
- [ ] All example/default passwords have been changed
- [ ] TLS/HTTPS is enforced for all connections
- [ ] Security headers are enabled
- [ ] Input validation is properly configured
- [ ] Error messages don't leak sensitive information

### Vulnerability Reporting

If you discover a security vulnerability, please:

1. **DO NOT** create a public issue
2. Email security@dotmac.com with details
3. Include steps to reproduce if possible
4. Allow reasonable time for fix before public disclosure

### Security Features

This platform includes:

- JWT-based authentication with signature verification
- Multi-tenant isolation with authorization
- Input validation and sanitization
- Rate limiting protection
- Security headers (CSP, XSS protection, etc.)
- CORS protection
- SQL injection prevention
- Error information protection
- Replay attack prevention

### Security Updates

Keep dependencies updated regularly:

```bash
pip install --upgrade dotmac-core-events[all]
```

Monitor security advisories for dependencies and apply updates promptly.