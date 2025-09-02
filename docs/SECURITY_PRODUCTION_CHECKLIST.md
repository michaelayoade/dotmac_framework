# Security Production Checklist

## 🔒 Critical Security Tasks (MANDATORY)

This checklist must be completed before any production deployment. Each item includes verification steps and represents a security-critical configuration.

### ✅ Authentication & Authorization

- [ ] **Remove Bootstrap Credentials**
  - [ ] Verify no default/example passwords in configuration
  - [ ] Execute `POST /admin/remove-bootstrap-credentials` endpoint
  - [ ] Confirm bootstrap credential removal in database
  - [ ] Document new admin credentials in secure password manager
  ```bash
  # Verification
  curl -X POST https://api.dotmac.com/admin/remove-bootstrap-credentials \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  ```

- [ ] **Multi-Factor Authentication (MFA)**
  - [ ] Enable MFA for all admin accounts
  - [ ] Configure TOTP/SMS backup methods
  - [ ] Test MFA login flows across all portals
  - [ ] Document MFA recovery procedures

- [ ] **Password Policies**
  - [ ] Minimum 12 characters with complexity requirements
  - [ ] Password expiration: 90 days for admin accounts
  - [ ] Account lockout: 5 failed attempts, 30-minute lockout
  - [ ] Session timeout: 4 hours maximum

### ✅ Secrets Management

- [ ] **OpenBao/Vault Hardening**
  - [ ] TLS enabled with valid certificates
  - [ ] All auth methods properly configured (Kubernetes, AppRole)
  - [ ] Least-privilege policies applied per service
  - [ ] Audit logging enabled to centralized system
  - [ ] Auto-unseal configured (AWS KMS, Azure Key Vault)
  ```bash
  # Verification
  bao status
  bao audit list
  bao policy list
  ```

- [ ] **Environment Variables**
  - [ ] No secrets in environment variables or logs
  - [ ] All sensitive data sourced from OpenBao
  - [ ] Kubernetes secrets mounted as files, not env vars
  - [ ] Secret rotation procedures documented

- [ ] **Database Credentials**
  - [ ] Dynamic database credentials enabled
  - [ ] Connection pooling with credential rotation
  - [ ] Database audit logging enabled
  - [ ] Encrypted connections (TLS) mandatory

### ✅ Network Security

- [ ] **TLS/SSL Configuration**
  - [ ] TLS 1.2+ minimum across all services
  - [ ] Strong cipher suites configured
  - [ ] HSTS headers enabled (max-age=31536000)
  - [ ] Certificate pinning for critical connections
  ```bash
  # Verification
  openssl s_client -connect api.dotmac.com:443 -tls1_2
  curl -I https://api.dotmac.com | grep -i strict-transport-security
  ```

- [ ] **Network Isolation**
  - [ ] Kubernetes NetworkPolicies applied
  - [ ] Database accessible only from application pods
  - [ ] Redis accessible only from application pods
  - [ ] OpenBao accessible only from authorized services
  ```bash
  # Verification
  kubectl get networkpolicies -n dotmac-prod
  kubectl describe networkpolicy dotmac-platform-network-policy -n dotmac-prod
  ```

- [ ] **Firewall Rules**
  - [ ] Only required ports exposed externally (80, 443, 22)
  - [ ] SSH access restricted to bastion host/VPN
  - [ ] Database ports (5432, 6379) not externally accessible
  - [ ] Internal service discovery only

### ✅ Application Security

- [ ] **Security Headers**
  - [ ] Content Security Policy (CSP) configured
  - [ ] X-Frame-Options: SAMEORIGIN
  - [ ] X-Content-Type-Options: nosniff
  - [ ] Referrer-Policy: strict-origin-when-cross-origin
  ```bash
  # Verification
  curl -I https://admin.dotmac.com | grep -E "(Content-Security-Policy|X-Frame-Options|X-Content-Type)"
  ```

- [ ] **Input Validation & Sanitization**
  - [ ] All user inputs validated server-side
  - [ ] SQL injection prevention (parameterized queries)
  - [ ] XSS prevention (output encoding)
  - [ ] File upload restrictions and scanning

- [ ] **API Security**
  - [ ] Rate limiting: 1000 req/min per IP, 100 req/min per user
  - [ ] JWT token expiration: 1 hour access, 24 hour refresh
  - [ ] API versioning with deprecated endpoint notifications
  - [ ] Request/response logging (excluding sensitive data)

### ✅ Data Protection

- [ ] **Encryption at Rest**
  - [ ] Database encryption enabled
  - [ ] File storage encryption enabled
  - [ ] Backup encryption with separate keys
  - [ ] Log encryption for sensitive data

- [ ] **Encryption in Transit**
  - [ ] All inter-service communication encrypted
  - [ ] Certificate validation in service mesh
  - [ ] No plaintext protocols (HTTP, FTP, Telnet)

- [ ] **Data Retention & Privacy**
  - [ ] GDPR/CCPA compliance procedures documented
  - [ ] Data retention policies configured (7 years financial, 30 days logs)
  - [ ] Data deletion capabilities tested
  - [ ] Privacy impact assessment completed

### ✅ Monitoring & Incident Response

- [ ] **Security Monitoring**
  - [ ] SIEM integration configured
  - [ ] Failed login monitoring and alerting
  - [ ] Privilege escalation detection
  - [ ] Unusual activity pattern detection
  ```bash
  # Verify security alerts are configured
  curl -s https://monitoring.dotmac.com/api/v1/rules | grep -i security
  ```

- [ ] **Audit Logging**
  - [ ] All authentication events logged
  - [ ] Administrative actions logged
  - [ ] Data access patterns logged
  - [ ] Log integrity protection (digital signatures)

- [ ] **Incident Response**
  - [ ] Security incident response plan documented
  - [ ] Emergency contacts and escalation procedures
  - [ ] Automated security playbooks configured
  - [ ] Regular security drills scheduled

### ✅ Compliance & Governance

- [ ] **Regular Security Assessments**
  - [ ] Quarterly vulnerability scans scheduled
  - [ ] Annual penetration testing planned
  - [ ] Code security reviews integrated in CI/CD
  - [ ] Dependency vulnerability scanning enabled

- [ ] **Access Management**
  - [ ] Role-based access control (RBAC) implemented
  - [ ] Principle of least privilege enforced
  - [ ] Regular access reviews scheduled (quarterly)
  - [ ] Service accounts minimally privileged

- [ ] **Business Continuity**
  - [ ] Disaster recovery plan tested
  - [ ] Backup restoration procedures verified
  - [ ] RTO/RPO targets documented and achievable
  - [ ] Communication plan for security incidents

### ✅ Container & Kubernetes Security

- [ ] **Container Security**
  - [ ] Base images from trusted sources only
  - [ ] Image vulnerability scanning in CI/CD
  - [ ] Non-root user in containers
  - [ ] Read-only root filesystem where possible
  ```bash
  # Verification
  kubectl get pods -n dotmac-prod -o jsonpath='{.items[*].spec.securityContext}'
  ```

- [ ] **Kubernetes Security**
  - [ ] Pod Security Standards enforced
  - [ ] Service mesh (Istio) configured if applicable
  - [ ] Admission controllers configured (OPA Gatekeeper)
  - [ ] Resource quotas and limits applied

## 🔍 Security Verification Commands

```bash
#!/bin/bash
# Production Security Verification Script

echo "🔍 DotMac Security Verification"
echo "=============================="

# 1. TLS Configuration
echo "📋 Checking TLS configuration..."
openssl s_client -connect api.dotmac.com:443 -servername api.dotmac.com < /dev/null 2>&1 | grep -E "(Protocol|Cipher)"

# 2. Security Headers  
echo "🔒 Checking security headers..."
curl -I -s https://admin.dotmac.com | grep -E "(Strict-Transport|Content-Security|X-Frame|X-Content-Type)"

# 3. OpenBao Status
echo "🗝️  Checking OpenBao status..."
curl -k -s https://openbao.dotmac.com:8200/v1/sys/health | jq .

# 4. Database Connectivity (from app pod)
echo "🗄️  Checking database security..."
kubectl exec -it deployment/dotmac-platform -n dotmac-prod -- \
  python -c "import ssl, asyncpg; print('DB SSL connection verified')"

# 5. Network Policies
echo "🌐 Checking network isolation..."
kubectl get networkpolicies -n dotmac-prod --no-headers | wc -l

# 6. Pod Security Context
echo "🛡️  Checking pod security context..."
kubectl get pods -n dotmac-prod -o jsonpath='{.items[*].spec.securityContext}' | grep -i "runAsNonRoot"

# 7. Certificate Expiration
echo "📅 Checking certificate expiration..."
echo | openssl s_client -servername api.dotmac.com -connect api.dotmac.com:443 2>/dev/null | openssl x509 -noout -dates

# 8. Secret Management
echo "🔐 Checking secret management..."
kubectl get secrets -n dotmac-prod --no-headers | wc -l

echo "✅ Security verification completed"
```

## 🚨 Security Incident Response

### Immediate Response (0-15 minutes)

1. **Assess and Contain**
   ```bash
   # Isolate affected services
   kubectl scale deployment dotmac-platform --replicas=0 -n dotmac-prod
   
   # Block malicious IPs at firewall level
   iptables -I INPUT -s MALICIOUS_IP -j DROP
   ```

2. **Notify Stakeholders**
   - Security team: security@dotmac.com
   - Platform team: platform-eng@dotmac.com
   - Management: incidents@dotmac.com

### Investigation (15-60 minutes)

1. **Preserve Evidence**
   ```bash
   # Collect logs
   kubectl logs deployment/dotmac-platform -n dotmac-prod --since=2h > incident-logs.txt
   
   # Database audit logs
   kubectl exec -it postgresql-0 -n dotmac-prod -- \
     psql -U postgres -c "SELECT * FROM audit_log WHERE created_at > NOW() - INTERVAL '2 hours';"
   ```

2. **Root Cause Analysis**
   - Review application logs for anomalies
   - Check OpenBao audit logs
   - Analyze network traffic patterns
   - Review recent deployments and changes

### Recovery (1-4 hours)

1. **Implement Fix**
   - Apply security patches
   - Rotate compromised credentials
   - Update firewall rules
   - Redeploy affected services

2. **Verification**
   - Run security verification script
   - Test all critical functions
   - Monitor for continued suspicious activity

### Post-Incident (24-48 hours)

1. **Documentation**
   - Complete incident report
   - Update security procedures
   - Share lessons learned
   - Plan preventive measures

2. **Improvements**
   - Enhance monitoring and alerting
   - Implement additional security controls
   - Update incident response procedures
   - Schedule security training

## 📞 Emergency Contacts

**Security Team:**
- Security Lead: security-lead@dotmac.com / +1-555-SEC-LEAD
- Platform Security: platform-security@dotmac.com
- Incident Commander: incident-commander@dotmac.com

**Vendors:**
- Cloud Provider: [Contact based on deployment]
- Security Vendor: [If applicable]
- Certificate Authority: [Let's Encrypt or commercial CA]

This checklist should be reviewed and updated quarterly, with all items re-verified before major releases.