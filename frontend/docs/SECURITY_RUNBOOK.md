# 🔐 Security Operations Runbook

## Overview
This runbook provides detailed procedures for security operations, incident response, and ongoing security maintenance for the DotMac Customer Portal.

## 🚨 Security Incident Response

### Incident Classification
```yaml
Critical (P0):
  - Active data breach
  - System compromise
  - Customer data exposure
  - Response: Immediate (< 15 minutes)

High (P1):
  - Suspicious authentication activity
  - Potential vulnerability exploitation
  - Security control bypass
  - Response: < 1 hour

Medium (P2):
  - Failed security scans
  - Policy violations
  - Suspicious user behavior
  - Response: < 4 hours

Low (P3):
  - Security configuration drift
  - Non-critical alerts
  - Compliance issues
  - Response: Next business day
```

### Emergency Response Procedures

#### Data Breach Response
```bash
# STEP 1: Immediate Containment (0-15 minutes)
echo "🚨 SECURITY BREACH DETECTED - INITIATING CONTAINMENT"

# Stop all external traffic
kubectl patch ingress customer-portal -p '{"spec":{"rules":[]}}'

# Invalidate all active sessions
kubectl exec -it redis-0 -- redis-cli FLUSHALL

# Enable maintenance mode
kubectl set env deployment/customer-portal MAINTENANCE_MODE=true

# Alert security team
curl -X POST https://hooks.slack.com/services/YOUR/SECURITY/WEBHOOK \
  -H 'Content-type: application/json' \
  --data '{"text":"🚨 SECURITY BREACH: Customer Portal containment initiated"}'
```

#### System Compromise Response
```bash
# STEP 2: Evidence Preservation (15-30 minutes)
echo "📁 PRESERVING EVIDENCE"

# Create forensic snapshots
kubectl exec -it customer-portal-0 -- \
  tar -czf /tmp/system-snapshot-$(date +%Y%m%d-%H%M%S).tgz \
  /var/log /etc /home

# Collect network traffic
kubectl exec -it customer-portal-0 -- tcpdump -w /tmp/network-capture.pcap

# Export audit logs
kubectl logs -l app=customer-portal --since=24h > incident-logs-$(date +%Y%m%d).txt

# Database forensics
kubectl exec -it postgres-0 -- pg_dump --verbose customerportal > db-snapshot.sql
```

#### Investigation Procedures
```bash
# STEP 3: Investigation (30 minutes - 4 hours)
echo "🔍 STARTING INVESTIGATION"

# Check authentication logs
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  timestamp, 
  user_id, 
  ip_address, 
  action, 
  result 
FROM audit_logs 
WHERE timestamp >= NOW() - INTERVAL '24 hours' 
AND (action LIKE '%login%' OR action LIKE '%auth%')
ORDER BY timestamp DESC;
"

# Analyze failed authentication attempts
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  ip_address, 
  COUNT(*) as failed_attempts,
  MIN(timestamp) as first_attempt,
  MAX(timestamp) as last_attempt
FROM audit_logs 
WHERE action = 'auth.failed_login' 
AND timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY ip_address 
HAVING COUNT(*) > 10
ORDER BY failed_attempts DESC;
"

# Check for privilege escalations
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT * FROM audit_logs 
WHERE action LIKE '%privilege%' 
OR action LIKE '%admin%' 
OR action LIKE '%role%'
ORDER BY timestamp DESC 
LIMIT 50;
"
```

### Communication Templates

#### Internal Security Alert
```yaml
Subject: "SECURITY INCIDENT: [Severity] - [Brief Description]"

Body: |
  INCIDENT DETAILS:
  - Severity: [P0/P1/P2/P3]
  - Detection Time: [Timestamp]
  - Affected Systems: [List]
  - Current Status: [Contained/Under Investigation/Resolved]
  
  IMMEDIATE ACTIONS TAKEN:
  - [Action 1]
  - [Action 2]
  - [Action 3]
  
  NEXT STEPS:
  - [Step 1 with timeline]
  - [Step 2 with timeline]
  
  INCIDENT COMMANDER: [Name/Contact]
  WAR ROOM: [Slack channel/Bridge number]
```

#### Customer Communication
```yaml
Subject: "Security Update - Your DotMac Account"

Body: |
  Dear [Customer Name],
  
  We are writing to inform you of a security incident that may have affected your account.
  
  WHAT HAPPENED:
  [Brief, non-technical description]
  
  INFORMATION INVOLVED:
  [Specific data types affected]
  
  WHAT WE'RE DOING:
  - Immediate containment measures implemented
  - Law enforcement and regulators notified (if applicable)
  - Enhanced monitoring activated
  - Full forensic investigation underway
  
  WHAT YOU SHOULD DO:
  1. Change your password immediately
  2. Monitor your account for unusual activity
  3. Enable two-factor authentication
  4. Contact us with any concerns
  
  We sincerely apologize for this incident and are taking all necessary steps to prevent future occurrences.
  
  Support: support@dotmac.com | 1-800-DOTMAC-1
```

## 🔍 Security Monitoring Procedures

### Real-time Monitoring Checks
```bash
#!/bin/bash
# security-monitoring.sh - Continuous security monitoring

echo "🛡️  Starting security monitoring checks..."

# Check for brute force attacks
echo "Checking for brute force attacks..."
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  ip_address,
  COUNT(*) as attempts,
  MAX(timestamp) as latest_attempt
FROM audit_logs 
WHERE action = 'auth.failed_login' 
AND timestamp >= NOW() - INTERVAL '15 minutes'
GROUP BY ip_address 
HAVING COUNT(*) >= 5;
"

# Monitor privilege escalations
echo "Checking for privilege escalations..."
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT * FROM audit_logs 
WHERE (action LIKE '%role%' OR action LIKE '%permission%' OR action LIKE '%admin%')
AND timestamp >= NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
"

# Check for data access anomalies
echo "Checking for unusual data access..."
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  user_id,
  action,
  resource,
  COUNT(*) as frequency
FROM audit_logs 
WHERE action LIKE 'data.%'
AND timestamp >= NOW() - INTERVAL '1 hour'
GROUP BY user_id, action, resource
HAVING COUNT(*) > 100
ORDER BY frequency DESC;
"

# Monitor security header bypasses
echo "Checking security headers..."
kubectl logs -l app=customer-portal --since=15m | grep -E "(CSP|CSRF|X-Frame|bypass)"

echo "✅ Security monitoring check completed"
```

### Weekly Security Reviews
```bash
#!/bin/bash
# weekly-security-review.sh - Comprehensive weekly security audit

echo "📊 Weekly Security Review Starting..."

# Generate authentication statistics
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  DATE(timestamp) as date,
  COUNT(*) FILTER (WHERE action = 'auth.login') as successful_logins,
  COUNT(*) FILTER (WHERE action = 'auth.failed_login') as failed_logins,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(DISTINCT ip_address) as unique_ips
FROM audit_logs 
WHERE timestamp >= NOW() - INTERVAL '7 days'
AND action LIKE 'auth.%'
GROUP BY DATE(timestamp)
ORDER BY date;
"

# Security incidents summary
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  action,
  severity,
  COUNT(*) as incidents,
  COUNT(DISTINCT user_id) as affected_users
FROM audit_logs 
WHERE action LIKE 'security.%'
AND timestamp >= NOW() - INTERVAL '7 days'
GROUP BY action, severity
ORDER BY incidents DESC;
"

# Top suspicious IPs
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  ip_address,
  COUNT(*) as total_requests,
  COUNT(*) FILTER (WHERE action LIKE '%failed%') as failed_requests,
  ROUND(
    (COUNT(*) FILTER (WHERE action LIKE '%failed%') * 100.0 / COUNT(*)), 2
  ) as failure_rate
FROM audit_logs 
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY ip_address
HAVING COUNT(*) FILTER (WHERE action LIKE '%failed%') > 50
ORDER BY failure_rate DESC, failed_requests DESC;
"

echo "📈 Weekly security review completed"
```

## 🔒 Access Control Management

### User Access Audit
```bash
#!/bin/bash
# access-audit.sh - User access rights verification

echo "👥 Starting user access audit..."

# List all active user sessions
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  u.id,
  u.email,
  u.role,
  u.last_login,
  u.status,
  COUNT(s.id) as active_sessions
FROM users u 
LEFT JOIN sessions s ON u.id = s.user_id AND s.expires_at > NOW()
WHERE u.status = 'active'
GROUP BY u.id, u.email, u.role, u.last_login, u.status
ORDER BY u.last_login DESC;
"

# Check for dormant accounts (no login in 90 days)
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  id,
  email,
  role,
  last_login,
  created_at,
  EXTRACT(days FROM NOW() - last_login) as days_inactive
FROM users 
WHERE last_login < NOW() - INTERVAL '90 days'
OR last_login IS NULL
ORDER BY last_login ASC;
"

# Privileged access review
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  email,
  role,
  last_login,
  created_at,
  CASE 
    WHEN last_login IS NULL THEN 'Never logged in'
    WHEN last_login < NOW() - INTERVAL '30 days' THEN 'Inactive'
    ELSE 'Active'
  END as status
FROM users 
WHERE role IN ('admin', 'super_admin', 'support_admin')
ORDER BY role, last_login DESC;
"
```

### Permission Cleanup
```bash
#!/bin/bash
# permission-cleanup.sh - Remove unnecessary permissions

echo "🧹 Starting permission cleanup..."

# Disable dormant accounts
kubectl exec -it postgres-0 -- psql customerportal -c "
UPDATE users 
SET status = 'disabled', disabled_at = NOW()
WHERE last_login < NOW() - INTERVAL '180 days'
AND status = 'active'
AND role NOT IN ('admin', 'super_admin');"

# Expire old sessions
kubectl exec -it postgres-0 -- psql customerportal -c "
DELETE FROM sessions 
WHERE expires_at < NOW() - INTERVAL '7 days';"

# Clean up old audit logs (keep 7 years for compliance)
kubectl exec -it postgres-0 -- psql customerportal -c "
DELETE FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '7 years';"

echo "✅ Permission cleanup completed"
```

## 🛡️ Vulnerability Management

### Security Scanning Procedures
```bash
#!/bin/bash
# security-scan.sh - Comprehensive security scanning

echo "🔍 Starting security scans..."

# Container vulnerability scan
echo "Scanning container images..."
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image customer-portal:latest \
  --format json > container-vulnerabilities.json

# Dependency vulnerability scan
echo "Scanning dependencies..."
cd /app && npm audit --json > dependency-vulnerabilities.json

# OWASP ZAP security scan (if available)
echo "Running OWASP ZAP scan..."
docker run -v $(pwd):/zap/wrk/:rw \
  -t owasp/zap2docker-stable zap-baseline.py \
  -t https://portal.dotmac.com \
  -J zap-report.json

# Generate security report
echo "Generating security report..."
cat << EOF > security-scan-report.md
# Security Scan Report - $(date)

## Container Vulnerabilities
$(cat container-vulnerabilities.json | jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH" or .Severity=="CRITICAL") | "- \(.PkgName): \(.VulnerabilityID) (\(.Severity))"' | head -10)

## Dependency Vulnerabilities  
$(cat dependency-vulnerabilities.json | jq -r '.vulnerabilities | to_entries[]? | select(.value.severity=="high" or .value.severity=="critical") | "- \(.key): \(.value.title) (\(.value.severity))"' | head -10)

## Recommendations
- Update vulnerable dependencies immediately
- Review container base images
- Schedule regular security scans
- Monitor for new vulnerabilities

Generated: $(date)
EOF

echo "📋 Security scan completed - check security-scan-report.md"
```

### Patch Management
```bash
#!/bin/bash
# patch-management.sh - System patching procedures

echo "🔧 Starting patch management..."

# Check for OS updates
kubectl exec -it customer-portal-0 -- apt list --upgradable

# Update container base images
docker pull node:18-alpine
docker pull postgres:15-alpine
docker pull redis:7-alpine

# Check application dependencies
cd /app && npm outdated

# Generate patch report
cat << EOF > patch-report.md
# Patch Management Report - $(date)

## System Updates Available
$(kubectl exec -it customer-portal-0 -- apt list --upgradable 2>/dev/null | grep -v "WARNING" | tail -n +2)

## Container Updates
- node:18-alpine: Latest version pulled
- postgres:15-alpine: Latest version pulled  
- redis:7-alpine: Latest version pulled

## NPM Updates
$(cd /app && npm outdated 2>/dev/null)

## Next Steps
1. Schedule maintenance window for OS updates
2. Test application with updated dependencies
3. Deploy updated container images
4. Monitor for issues post-deployment

Generated: $(date)
EOF

echo "✅ Patch management report generated"
```

## 🔐 Encryption & Key Management

### Certificate Management
```bash
#!/bin/bash
# certificate-management.sh - SSL/TLS certificate operations

echo "🔐 Certificate Management Operations..."

# Check certificate expiry
echo "Checking certificate expiry..."
kubectl get secrets -o json | jq -r '
.items[] | 
select(.type == "kubernetes.io/tls") | 
{
  name: .metadata.name,
  namespace: .metadata.namespace,
  cert: .data."tls.crt"
} | 
.cert | @base64d' | \
openssl x509 -noout -dates -subject

# Generate new certificates (if needed)
echo "Certificate renewal procedures..."
cat << 'EOF' > renew-certificates.sh
#!/bin/bash
# Certificate renewal procedure

# Generate new private key
openssl genrsa -out new-tls.key 2048

# Generate certificate signing request
openssl req -new -key new-tls.key -out new-tls.csr \
  -subj "/C=US/ST=State/L=City/O=DotMac/CN=portal.dotmac.com"

# Create new certificate secret
kubectl create secret tls new-tls-cert \
  --cert=new-tls.crt --key=new-tls.key

# Update ingress to use new certificate
kubectl patch ingress customer-portal \
  -p '{"spec":{"tls":[{"secretName":"new-tls-cert","hosts":["portal.dotmac.com"]}]}}'
EOF

chmod +x renew-certificates.sh
echo "Certificate renewal script created: renew-certificates.sh"
```

### Key Rotation Procedures
```bash
#!/bin/bash
# key-rotation.sh - Cryptographic key rotation

echo "🔄 Starting key rotation procedures..."

# Rotate JWT signing keys
echo "Rotating JWT keys..."
kubectl create secret generic jwt-new-key \
  --from-literal=key="$(openssl rand -base64 32)"

# Rotate database encryption keys
echo "Rotating database keys..."
kubectl exec -it postgres-0 -- psql customerportal -c "
-- Create new encryption key
INSERT INTO encryption_keys (key_id, key_data, created_at, status) 
VALUES (
  'key_' || extract(epoch from now())::text, 
  encode(gen_random_bytes(32), 'base64'),
  NOW(),
  'active'
);"

# Rotate session secrets
echo "Rotating session secrets..."
kubectl patch secret session-secret \
  -p '{"data":{"key":"'$(echo -n $(openssl rand -base64 32) | base64 -w 0)'"}}'

# Update CSRF tokens
echo "Invalidating CSRF tokens..."
kubectl exec -it redis-0 -- redis-cli EVAL "
return redis.call('del', unpack(redis.call('keys', 'csrf:*')))
" 0

echo "🔑 Key rotation completed"
```

## 📊 Security Metrics & Reporting

### Daily Security Metrics
```bash
#!/bin/bash
# daily-metrics.sh - Generate daily security metrics

echo "📈 Generating daily security metrics..."

# Create metrics report
cat << EOF > daily-security-metrics.json
{
  "date": "$(date -I)",
  "metrics": {
    "authentication": {
      "total_logins": $(kubectl exec -it postgres-0 -- psql customerportal -t -c "SELECT COUNT(*) FROM audit_logs WHERE action = 'auth.login' AND DATE(timestamp) = CURRENT_DATE;" | xargs),
      "failed_logins": $(kubectl exec -it postgres-0 -- psql customerportal -t -c "SELECT COUNT(*) FROM audit_logs WHERE action = 'auth.failed_login' AND DATE(timestamp) = CURRENT_DATE;" | xargs),
      "unique_users": $(kubectl exec -it postgres-0 -- psql customerportal -t -c "SELECT COUNT(DISTINCT user_id) FROM audit_logs WHERE action = 'auth.login' AND DATE(timestamp) = CURRENT_DATE;" | xargs)
    },
    "security_events": {
      "total_events": $(kubectl exec -it postgres-0 -- psql customerportal -t -c "SELECT COUNT(*) FROM audit_logs WHERE action LIKE 'security.%' AND DATE(timestamp) = CURRENT_DATE;" | xargs),
      "high_severity": $(kubectl exec -it postgres-0 -- psql customerportal -t -c "SELECT COUNT(*) FROM audit_logs WHERE action LIKE 'security.%' AND severity IN ('high', 'critical') AND DATE(timestamp) = CURRENT_DATE;" | xargs)
    },
    "data_access": {
      "total_operations": $(kubectl exec -it postgres-0 -- psql customerportal -t -c "SELECT COUNT(*) FROM audit_logs WHERE action LIKE 'data.%' AND DATE(timestamp) = CURRENT_DATE;" | xargs),
      "sensitive_access": $(kubectl exec -it postgres-0 -- psql customerportal -t -c "SELECT COUNT(*) FROM audit_logs WHERE action LIKE 'data.%' AND resource IN ('customer_data', 'payment_info') AND DATE(timestamp) = CURRENT_DATE;" | xargs)
    }
  }
}
EOF

echo "📊 Daily metrics saved to daily-security-metrics.json"
```

### Monthly Security Report
```bash
#!/bin/bash
# monthly-report.sh - Comprehensive monthly security report

echo "📋 Generating monthly security report..."

MONTH=$(date +%Y-%m)

cat << EOF > monthly-security-report-${MONTH}.md
# Monthly Security Report - ${MONTH}

## Executive Summary
This report covers security activities and metrics for ${MONTH}.

## Authentication Statistics
$(kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  DATE_TRUNC('week', timestamp) as week,
  COUNT(*) FILTER (WHERE action = 'auth.login') as successful_logins,
  COUNT(*) FILTER (WHERE action = 'auth.failed_login') as failed_logins,
  COUNT(DISTINCT user_id) as unique_users
FROM audit_logs 
WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE)
AND timestamp < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
AND action LIKE 'auth.%'
GROUP BY DATE_TRUNC('week', timestamp)
ORDER BY week;
" -H)

## Security Incidents
$(kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  action,
  severity,
  COUNT(*) as incidents,
  MIN(timestamp) as first_occurrence,
  MAX(timestamp) as last_occurrence
FROM audit_logs 
WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE)
AND timestamp < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
AND action LIKE 'security.%'
GROUP BY action, severity
ORDER BY incidents DESC;
" -H)

## Top Risk IPs
$(kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  ip_address,
  COUNT(*) as total_requests,
  COUNT(*) FILTER (WHERE action LIKE '%failed%' OR action LIKE 'security.%') as suspicious_requests,
  ROUND((COUNT(*) FILTER (WHERE action LIKE '%failed%' OR action LIKE 'security.%') * 100.0 / COUNT(*)), 2) as risk_score
FROM audit_logs 
WHERE timestamp >= DATE_TRUNC('month', CURRENT_DATE)
AND timestamp < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
GROUP BY ip_address
HAVING COUNT(*) FILTER (WHERE action LIKE '%failed%' OR action LIKE 'security.%') > 10
ORDER BY risk_score DESC, suspicious_requests DESC
LIMIT 20;
" -H)

## Recommendations
- Continue monitoring high-risk IP addresses
- Review failed authentication patterns
- Update security policies based on incident trends
- Schedule quarterly security training
- Plan next vulnerability assessment

Generated: $(date)
EOF

echo "✅ Monthly report saved to monthly-security-report-${MONTH}.md"
```

## 🎯 Compliance & Audit

### SOC 2 Compliance Check
```bash
#!/bin/bash
# soc2-compliance.sh - SOC 2 compliance verification

echo "📋 SOC 2 Compliance Check..."

# Verify audit log retention
echo "Checking audit log retention..."
kubectl exec -it postgres-0 -- psql customerportal -c "
SELECT 
  MIN(timestamp) as oldest_log,
  MAX(timestamp) as newest_log,
  COUNT(*) as total_logs,
  EXTRACT(days FROM NOW() - MIN(timestamp)) as retention_days
FROM audit_logs;
"

# Check encryption at rest
echo "Verifying encryption at rest..."
kubectl get persistentvolumes -o yaml | grep -i encryption

# Verify access controls
echo "Checking access control implementation..."
grep -r "rbac\|authorization\|permission" k8s/ | head -10

echo "✅ SOC 2 compliance check completed"
```

---

**Document Version**: 1.0  
**Last Updated**: $(date)  
**Owner**: Security Team  
**Review Frequency**: Monthly  
**Distribution**: Security Team, Operations Team, Engineering Leadership