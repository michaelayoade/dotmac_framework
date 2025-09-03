# JWT Configuration for Nginx

## Setup Instructions

1. **Generate JWT Key:**
   ```bash
   # Create directory
   mkdir -p /etc/nginx/jwt
   
   # Generate a secure key for JWT validation
   openssl rand -base64 32 > /etc/nginx/jwt/jwt.key
   chmod 600 /etc/nginx/jwt/jwt.key
   chown nginx:nginx /etc/nginx/jwt/jwt.key
   ```

2. **Configure JWT Module:**
   The nginx configuration references the JWT key file at `/etc/nginx/jwt/jwt.key`.
   Ensure this matches your application's JWT signing key.

## Security Features Implemented

### Tenant Mapping
- Extracts tenant ID from host header using regex patterns
- Sets trusted `X-Tenant-ID` header (ignores client-sent headers)
- Maps tenants to rate limiting zones

### JWT Authentication
- **Required**: `/api/v1/auth/*` endpoints require valid JWT
- **Optional**: Other API endpoints have optional JWT validation
- JWT user claims are passed to backend via `X-JWT-User` header

### WebSocket Security
- Connection limits per tenant
- Rate limiting for WebSocket upgrades
- Optional JWT validation for WebSocket connections
- Proper timeout configurations

### mTLS Support
- Optional mutual TLS authentication
- Client certificate validation
- Enhanced security for API-to-API communication

## Rate Limiting Zones

- `tenant`: 100r/s per tenant
- `ws_rate`: 50r/s WebSocket connections per tenant
- `ws_conn`: Connection limits (50 for admin, 100 for ISP)

## Tenant Patterns

Host patterns that map to tenant IDs:
- `tenant.isp.dotmac.local` → `tenant`
- `tenant.yourdomain.com` → `tenant`
- `portal.dotmac.local` → `portal`
- `admin.dotmac.local` → `admin`
- `monitoring.dotmac.local` → `monitoring`