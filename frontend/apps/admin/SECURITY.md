# Security Guidelines for Admin Portal

## Overview

The DotMac Admin Portal handles sensitive ISP management data and requires robust security measures. This document outlines security best practices, threat mitigation strategies, and implementation guidelines.

## Security Architecture

### Authentication & Authorization

#### Multi-Factor Authentication (MFA)
- **Requirement**: All admin accounts must use MFA
- **Implementation**: TOTP-based (Google Authenticator, Authy)
- **Backup**: SMS fallback for emergency access
- **Session**: Re-authentication required for sensitive operations

#### Role-Based Access Control (RBAC)
```typescript
// Permission hierarchy
const PERMISSIONS = {
  READ: 'read',
  WRITE: 'write', 
  ADMIN: 'admin',
  SUPER_ADMIN: 'super_admin'
} as const

// Role definitions
const ROLES = {
  VIEWER: ['read'],
  OPERATOR: ['read', 'write'],
  ADMIN: ['read', 'write', 'admin'],
  SUPER_ADMIN: ['read', 'write', 'admin', 'super_admin']
}
```

#### Session Management
- **Timeout**: 30 minutes of inactivity
- **Refresh**: Automatic token refresh before expiration
- **Invalidation**: Immediate session termination on logout
- **Concurrent Sessions**: Limited to 3 active sessions per user

### Input Validation & Sanitization

#### XSS Prevention
```typescript
import { sanitizeInput, sanitizeHTML } from '@/lib/security'

// Sanitize all user inputs
const safeInput = sanitizeInput(userInput)

// For HTML content, use whitelist approach
const safeHTML = sanitizeHTML(htmlContent, {
  allowedTags: ['p', 'br', 'strong', 'em'],
  allowedAttributes: {}
})
```

#### SQL Injection Prevention
- Use parameterized queries exclusively
- Validate all database inputs
- Implement query allowlists for dynamic queries

#### File Upload Security
```typescript
// Validate file types and sizes
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'application/pdf']
const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

function validateFile(file: File): boolean {
  return ALLOWED_TYPES.includes(file.type) && 
         file.size <= MAX_FILE_SIZE
}
```

### Content Security Policy (CSP)

```typescript
// Next.js security headers
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: `
      default-src 'self';
      script-src 'self' 'unsafe-eval' 'unsafe-inline';
      style-src 'self' 'unsafe-inline';
      img-src 'self' data: https:;
      font-src 'self';
      connect-src 'self' https://api.dotmac.com;
      frame-ancestors 'none';
    `.replace(/\s{2,}/g, ' ').trim()
  }
]
```

### CSRF Protection

#### Implementation
```typescript
import { generateCSRFToken, validateCSRFToken } from '@/lib/security'

// Generate token on login
const csrfToken = generateCSRFToken()

// Validate on state-changing operations
const isValid = await validateCSRFToken(token)
if (!isValid) {
  throw new Error('CSRF token validation failed')
}
```

#### Headers
- Include CSRF token in all POST/PUT/DELETE requests
- Validate Origin and Referer headers
- Use SameSite cookies

### Rate Limiting

#### Implementation
```typescript
import { rateLimitCheck } from '@/lib/security'

// Rate limit sensitive endpoints
const limit = rateLimitCheck('login', 5, 300000) // 5 attempts per 5 minutes

if (!limit.allowed) {
  throw new Error(`Rate limit exceeded. Try again in ${limit.resetTime - Date.now()}ms`)
}
```

#### Limits by Endpoint
- **Login**: 5 attempts per 5 minutes per IP
- **Password Reset**: 3 attempts per hour per email
- **API Calls**: 1000 requests per hour per user
- **File Uploads**: 10 files per minute per user

### Data Protection

#### Encryption at Rest
- All sensitive data encrypted using AES-256
- Separate encryption keys for different data types
- Key rotation every 90 days

#### Encryption in Transit
- TLS 1.3 minimum for all connections
- Certificate pinning for API endpoints
- HSTS headers with long max-age

#### Sensitive Data Handling
```typescript
// Never log sensitive information
const logSafeData = (userData: User) => ({
  id: userData.id,
  email: userData.email.replace(/(.{3}).*(@.*)/, '$1***$2'),
  role: userData.role,
  // Never include: password, tokens, PII
})

logger.info('User action', logSafeData(user))
```

### Audit Logging

#### Required Events
```typescript
// Authentication events
logger.authEvent('login', success, userId, { ip, userAgent })
logger.authEvent('logout', true, userId)
logger.authEvent('password-change', success, userId)

// Security events
logger.securityEvent('permission-denied', 'high', { 
  userId, 
  attemptedAction, 
  requiredPermission 
})

// Data access events
logger.userAction('data-export', 'billing', { 
  recordCount, 
  exportType,
  userId 
})
```

#### Log Retention
- Security logs: 7 years
- Access logs: 2 years  
- Error logs: 1 year
- Performance logs: 90 days

### Security Headers

#### Required Headers
```typescript
const securityHeaders = {
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
}
```

### Vulnerability Management

#### Dependency Scanning
- Automated daily scans of npm dependencies
- Critical vulnerabilities: Patch within 24 hours
- High vulnerabilities: Patch within 7 days
- Medium/Low vulnerabilities: Patch within 30 days

#### Code Security Reviews
- All code changes reviewed for security issues
- Automated SAST scanning on pull requests
- Manual review for authentication/authorization changes

### Incident Response

#### Security Event Classification
1. **Critical**: Data breach, system compromise, privilege escalation
2. **High**: Authentication bypass, unauthorized access attempts
3. **Medium**: Failed login attempts, permission denials
4. **Low**: General security warnings, policy violations

#### Response Procedures
1. **Detection**: Automated alerts and monitoring
2. **Analysis**: Immediate investigation of security events
3. **Containment**: Isolate affected systems/accounts
4. **Recovery**: Restore normal operations securely
5. **Documentation**: Record incident details and lessons learned

### Compliance Requirements

#### Data Privacy (GDPR/CCPA)
- User consent for data processing
- Right to data export/deletion
- Data minimization principles
- Privacy by design implementation

#### SOC 2 Type II
- Access controls and monitoring
- System availability and performance
- Data integrity and confidentiality
- Privacy protection measures

### Security Testing

#### Automated Testing
```typescript
// Security test examples
describe('Security', () => {
  it('should prevent XSS attacks', () => {
    const maliciousInput = '<script>alert("xss")</script>'
    const sanitized = sanitizeInput(maliciousInput)
    expect(sanitized).not.toContain('<script>')
  })

  it('should enforce rate limiting', () => {
    // Simulate rapid requests
    for (let i = 0; i < 10; i++) {
      const result = rateLimitCheck('test', 5, 60000)
      if (i >= 5) {
        expect(result.allowed).toBe(false)
      }
    }
  })
})
```

#### Manual Testing
- Quarterly penetration testing
- Annual security audit
- Regular vulnerability assessments

### Security Monitoring

#### Real-time Monitoring
- Failed authentication attempts
- Privilege escalation attempts  
- Unusual data access patterns
- System performance anomalies

#### Alerting Thresholds
- **Immediate**: >5 failed logins from same IP
- **High Priority**: Unauthorized admin access
- **Medium Priority**: Unusual user behavior patterns
- **Low Priority**: Policy violations

### Development Security

#### Secure Coding Practices
1. Never hardcode secrets or credentials
2. Validate all inputs at application boundaries
3. Use prepared statements for database queries
4. Implement proper error handling without information leakage
5. Follow principle of least privilege

#### Environment Security
```typescript
// Environment variable validation
const requiredEnvVars = [
  'JWT_SECRET_KEY',
  'DATABASE_URL',
  'ENCRYPTION_KEY',
  'API_BASE_URL'
]

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    throw new Error(`Required environment variable ${envVar} is missing`)
  }
}
```

### Deployment Security

#### Production Checklist
- [ ] All environment variables configured
- [ ] HTTPS enabled with valid certificates
- [ ] Security headers configured
- [ ] Rate limiting enabled
- [ ] Logging and monitoring active
- [ ] Database encrypted
- [ ] Backup encryption verified
- [ ] Access controls tested

#### Infrastructure Security
- Container security scanning
- Network segmentation
- Firewall configuration
- Regular security patches

### Emergency Procedures

#### Security Breach Response
1. **Immediate Actions**:
   - Disconnect affected systems
   - Preserve evidence
   - Notify security team
   - Document timeline

2. **Communication**:
   - Internal stakeholders
   - Affected users (if applicable)
   - Regulatory bodies (if required)
   - Law enforcement (if criminal)

3. **Recovery**:
   - Patch vulnerabilities
   - Reset compromised credentials
   - Verify system integrity
   - Restore normal operations

### Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [SOC 2 Compliance Guide](https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/aicpasoc2report)
- [GDPR Compliance](https://gdpr.eu/)

---

**Last Updated**: {{ current_date }}
**Next Review**: {{ next_review_date }}
**Document Owner**: Security Team