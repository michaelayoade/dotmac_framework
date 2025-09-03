# Security Policy

## 🛡️ Security Overview

The DotMac Framework implements comprehensive security measures across all components to protect ISP operations and customer data.

## 🚨 Reporting Security Vulnerabilities

### How to Report

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead, please:

1. **Email**: Send details to `security@dotmac.com` (replace with actual email)
2. **Subject Line**: `[SECURITY] Vulnerability Report - DotMac Framework`
3. **Include**:
   - Detailed description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Suggested fix (if applicable)

### Response Timeline

- **Acknowledgment**: Within 24 hours
- **Initial Assessment**: Within 72 hours
- **Fix Timeline**: Critical issues within 7 days, others within 30 days
- **Public Disclosure**: After fix is deployed and tested

## 🔒 Security Measures Implemented

### 1. **Authentication & Authorization**

#### ✅ **Implemented**:
- JWT-based authentication with secure key management
- Role-Based Access Control (RBAC) across all portals
- Multi-factor authentication support
- Session management with secure token rotation
- API key authentication for service-to-service communication

#### ⚠️ **Security Requirements**:
- JWT secrets MUST be 64+ characters
- Tokens expire within 30 minutes (configurable)
- All authentication failures are logged and monitored

### 2. **Data Protection**

#### ✅ **Implemented**:
- Field-level encryption for sensitive data
- Row-Level Security (RLS) for multi-tenant isolation
- TLS encryption for all communications
- Secure password hashing (bcrypt with salt)
- PII masking in logs and debug output

#### ⚠️ **Security Requirements**:
- Encryption keys stored in OpenBao/Vault only
- Database connections use TLS
- No plaintext passwords in any configuration

### 3. **Input Validation & Sanitization**

#### ✅ **Implemented**:
- SQL injection prevention via parameterized queries
- XSS protection with input sanitization
- CSRF protection on all forms
- Request size limits and rate limiting
- Input validation using Pydantic models

#### 🚫 **Unsafe Functions Removed**:
- `eval()` usage replaced with safe expression evaluation
- `exec()` usage replaced with secure `importlib`
- All user input is validated and sanitized

### 4. **Infrastructure Security**

#### ✅ **Implemented**:
- Container security with non-root users
- Resource limits to prevent DoS attacks
- Network isolation between services
- Health checks and monitoring
- Automated security scanning in CI/CD

#### ⚠️ **Security Requirements**:
- All containers run as non-root
- Secrets managed via Kubernetes/Docker secrets
- Regular security updates and patching

### 5. **Monitoring & Logging**

#### ✅ **Implemented**:
- Security event logging and alerting
- Failed authentication monitoring
- Unusual access pattern detection
- Audit trails for all administrative actions
- Prometheus metrics for security events

#### 📊 **Security Metrics Monitored**:
- Login success/failure rates
- API error rates (5xx responses)
- Unusual access patterns
- Resource usage anomalies

## 🔧 Security Configuration

### Environment Variables

All sensitive configuration MUST use environment variables:

```bash
# ✅ CORRECT - Use environment variables
SECRET_KEY=${SECRET_KEY}
JWT_SECRET=${JWT_SECRET}
DATABASE_URL=${DATABASE_URL}

# ❌ INCORRECT - Never hardcode secrets
SECRET_KEY=hardcoded-secret-value
```

### Database Security

```bash
# ✅ REQUIRED for production
APPLY_RLS_AFTER_MIGRATION=true
STRICT_PROD_BASELINE=true
DATABASE_URL=postgresql://...  # Never use SQLite in production
```

### OpenBao/Vault Integration

```bash
# ✅ REQUIRED for production
OPENBAO_URL=https://vault.yourdomain.com
OPENBAO_TOKEN=${VAULT_TOKEN}  # Retrieved from secure source
```

## 🚦 Security Testing

### Automated Scans

Our CI/CD pipeline includes:

- **Bandit**: Static analysis for Python security issues
- **Safety**: Dependency vulnerability scanning  
- **Semgrep**: Advanced static analysis
- **TruffleHog**: Secret detection
- **Custom checks**: Hardcoded credential detection

### Manual Testing

Regular security assessments include:

- Penetration testing
- Code reviews focusing on security
- Infrastructure security audits
- Social engineering assessments

## 🛠️ Security Updates

### Dependency Management

- Dependencies pinned to specific versions
- Regular vulnerability scanning
- Automated security updates for non-breaking changes
- Monthly security review cycles

### Patch Management

- Critical security patches: Within 24 hours
- High priority patches: Within 1 week
- Regular updates: Monthly maintenance window

## 📋 Security Checklist for Deployments

### Pre-Production

- [ ] All secrets use environment variables
- [ ] No hardcoded credentials in any file
- [ ] TLS certificates properly configured
- [ ] Database RLS enabled and tested
- [ ] Authentication and authorization tested
- [ ] Security scanning results reviewed

### Production Deployment

- [ ] OpenBao/Vault properly configured
- [ ] Monitoring and alerting active
- [ ] Backup and recovery procedures tested
- [ ] Incident response plan ready
- [ ] Security team notified of deployment

### Post-Production

- [ ] Security monitoring dashboards reviewed
- [ ] Log aggregation functioning
- [ ] Alert thresholds properly configured
- [ ] Access controls validated
- [ ] Security metrics baseline established

## 🚨 Incident Response

### Security Incident Categories

1. **Critical**: Data breach, system compromise
2. **High**: Authentication bypass, privilege escalation  
3. **Medium**: DoS attacks, information disclosure
4. **Low**: Configuration issues, minor vulnerabilities

### Response Procedures

1. **Immediate**: Contain and isolate affected systems
2. **Assessment**: Determine scope and impact
3. **Communication**: Notify stakeholders and authorities
4. **Remediation**: Fix vulnerability and restore service
5. **Review**: Post-incident analysis and improvements

## 📞 Security Contacts

- **Security Team**: `security@dotmac.com`
- **Emergency**: `emergency@dotmac.com`
- **Compliance**: `compliance@dotmac.com`

## 📚 Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [ISP Security Best Practices](https://www.example.com/isp-security)

---

**Last Updated**: 2024-09-03  
**Next Review**: 2024-12-03

For questions about this security policy, contact `security@dotmac.com`.