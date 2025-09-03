# Nginx Modules for DotMac Platform

## Required Modules

### JWT Authentication Module
The configuration requires the `ngx_http_auth_jwt_module` for JWT validation.

**Installation Options:**

1. **Commercial Nginx Plus:**
   ```bash
   # JWT module is included with Nginx Plus
   load_module modules/ngx_http_auth_jwt_module.so;
   ```

2. **Open Source Alternatives:**
   
   **Option A: auth_jwt module from GitHub**
   ```bash
   # Install from: https://github.com/kjdev/nginx-auth-jwt
   git clone https://github.com/kjdev/nginx-auth-jwt.git
   cd nginx-auth-jwt
   # Compile as dynamic module
   ```
   
   **Option B: lua-resty-jwt with OpenResty**
   ```bash
   # Use OpenResty with lua-resty-jwt
   # Requires lua scripting in location blocks
   ```

3. **Alternative: Backend JWT Validation**
   If JWT module is not available, validate JWTs in the backend application.
   The nginx config will pass headers but skip JWT validation.

## Module Loading

Current configuration attempts to load:
- `modules/ngx_http_auth_jwt_module.so`

If module is not available, comment out the `load_module` line in `nginx.conf` and handle JWT validation in the application backend.

## Fallback Configuration

For environments without JWT module support, authentication will be handled at the application level with the following headers still being set:
- `X-Tenant-ID`: Extracted from host
- `X-Real-IP`: Client IP
- `X-Forwarded-For`: Proxy chain
- `X-Forwarded-Proto`: Original protocol