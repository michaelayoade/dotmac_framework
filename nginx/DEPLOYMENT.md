# API Gateway Deployment Instructions

## Summary of Changes

The API Gateway has been fixed with the following improvements:

### 1. Tenant Mapping
- **Host-based tenant extraction** using regex patterns
- **Trusted X-Tenant-ID header** set by Nginx (ignores client-sent headers)
- **Per-tenant rate limiting** zones

### 2. Edge Authentication
- **JWT validation** for `/api/v1/auth/*` endpoints (when module is available)
- **Optional JWT validation** for other API endpoints
- **mTLS support** for enhanced API-to-API security

### 3. WebSocket Connection Capabilities
- **Connection limits** per tenant (50 for admin, 100 for ISP)
- **Rate limiting** for WebSocket upgrades (50r/s per tenant)
- **Proper timeouts** and upgrade handling
- **Optional JWT validation** for WebSocket connections

## Deployment Steps

### 1. Install JWT Module (Production Only)

**For Nginx Plus:**
```bash
# JWT module is included
load_module modules/ngx_http_auth_jwt_module.so;
```

**For Open Source Nginx:**
```bash
# Install auth_jwt module
git clone https://github.com/kjdev/nginx-auth-jwt.git
# Or use OpenResty with lua-resty-jwt
```

### 2. Generate JWT Keys

```bash
# Create JWT directory
mkdir -p /etc/nginx/jwt

# Generate secure key
openssl rand -base64 32 > /etc/nginx/jwt/jwt.key
chmod 600 /etc/nginx/jwt/jwt.key
chown nginx:nginx /etc/nginx/jwt/jwt.key
```

### 3. Enable JWT Module

Uncomment these lines in `nginx.conf`:
```nginx
load_module modules/ngx_http_auth_jwt_module.so;
auth_jwt_key_file /etc/nginx/jwt/jwt.key;
```

And in `dotmac-platform.conf`, uncomment JWT directives:
```nginx
auth_jwt "DotMac Auth API";
auth_jwt_claim_set $jwt_user sub;
proxy_set_header X-JWT-User $jwt_user;
```

### 4. Configure SSL/TLS Certificates

Ensure these certificate files exist:
- `/etc/nginx/ssl/admin.dotmac.local.crt`
- `/etc/nginx/ssl/admin.dotmac.local.key`
- `/etc/nginx/ssl/dotmac.local.crt`
- `/etc/nginx/ssl/dotmac.local.key`
- `/etc/nginx/ssl/ca.crt` (for mTLS)

### 5. Test Configuration

```bash
nginx -t
systemctl reload nginx
```

## Features

### Tenant Patterns
- `tenant.isp.dotmac.local` → tenant ID: `tenant`
- `tenant.yourdomain.com` → tenant ID: `tenant`
- `portal.dotmac.local` → tenant ID: `portal`
- `admin.dotmac.local` → tenant ID: `admin`

### Rate Limits
- **API endpoints**: 30r/s general, 100r/s per tenant
- **Auth endpoints**: 5r/m with strict limits
- **WebSocket**: 50r/s per tenant
- **Connections**: Per-tenant WebSocket limits

### Security Headers
- Trusted `X-Tenant-ID` (server-extracted)
- `X-JWT-User` (when JWT module is enabled)
- Standard security headers (HSTS, CSP, etc.)
- Optional mTLS client certificate validation

## Monitoring

Logs now include tenant information:
```
tenant="tenant_id" rt=request_time
```

Monitor these metrics:
- Rate limit violations (429 responses)
- WebSocket connection counts
- JWT validation failures
- Tenant-specific traffic patterns