# API Audit: Frontend to Backend Endpoint Mapping

## Executive Summary

This document maps frontend API calls to their corresponding backend endpoints, identifying alignment issues and action items for the immediate authentication fix and component integration tasks.

## 🚨 Critical Issues Identified

### 1. Authentication Endpoint Mismatch
**Frontend:** `/auth/login` (AuthApiClient.ts:133)  
**Backend:** `/auth/login` (identity/router.py:105) ✅ **ALIGNED**

**Frontend:** `/auth/refresh` (AuthApiClient.ts:140)  
**Backend:** `/auth/refresh` (identity/router.py:219) ✅ **ALIGNED**

**Frontend:** `/auth/me` (AuthApiClient.ts:156)  
**Backend:** `/me` (identity/router.py:261) ❌ **MISALIGNED**

### 2. Base URL Configuration Issues
- Frontend clients expect `/api/v1` prefix
- Backend routers register at `/api/v1/{module}` 
- Need to verify base URL configuration in frontend

## Module-by-Module Mapping

### Authentication & Identity
| Frontend Endpoint | Backend Endpoint | Status | Notes |
|------------------|------------------|--------|-------|
| `POST /auth/login` | `POST /auth/login` | ✅ Aligned | |
| `POST /auth/refresh` | `POST /auth/refresh` | ✅ Aligned | |
| `POST /auth/logout` | `POST /auth/logout` | ✅ Aligned | |
| `GET /auth/me` | `GET /me` | ❌ Mismatch | Backend missing `/auth` prefix |
| `PATCH /auth/profile` | `PUT /me` | ❌ Method Mismatch | PATCH vs PUT |
| `POST /auth/password/reset` | Not Found | ❌ Missing | Backend needs implementation |
| `POST /auth/mfa/setup` | Not Found | ❌ Missing | Backend needs implementation |

### Billing Module  
| Frontend Endpoint | Backend Endpoint | Status | Notes |
|------------------|------------------|--------|-------|
| `GET /invoices` | `GET /invoices` | ✅ Aligned | At `/api/v1/billing/invoices` |
| `POST /invoices` | `POST /invoices` | ✅ Aligned | |
| `GET /invoices/{id}` | `GET /invoices/{invoice_id}` | ✅ Aligned | |
| `GET /invoices/by-number/{number}` | `GET /invoices/by-number/{invoice_number}` | ✅ Aligned | |
| `POST /payments` | Backend TBD | ⚠️ Pending | Need to verify payment endpoints |
| `GET /customers/{id}/invoices` | Backend TBD | ⚠️ Pending | Customer-specific endpoints |

### Services Module
| Frontend Endpoint | Backend Endpoint | Status | Notes |
|------------------|------------------|--------|-------|
| `GET /services` | Registered at `/api/v1/services` | ⚠️ Pending | Need router analysis |
| `POST /services` | Registered at `/api/v1/services` | ⚠️ Pending | Need router analysis |

## Backend Router Registration Analysis

Based on `src/dotmac_isp/api/routers.py`, the following modules are registered:

```python
# Core modules with confirmed routers
"/api/v1/identity"           # ✅ identity.router
"/api/v1/billing"            # ✅ billing.router (billing_router)
"/api/v1/services"           # ✅ services.router (services_router) 
"/api/v1/support"            # ✅ support.router (support_router)
"/api/v1/networking"         # ✅ network_integration.router
"/api/v1/network-monitoring" # ✅ network_monitoring.router
"/api/v1/analytics"          # ✅ analytics.router (analytics_router)
"/api/v1/inventory"          # ✅ inventory.router
"/api/v1/compliance"         # ✅ compliance.router
"/api/v1/field-ops"          # ✅ field_ops.router
```

## Frontend API Client Structure

### Base Configuration Issues
1. **BaseApiClient** - Need to verify base URL setup
2. **Authentication Headers** - Token management alignment
3. **Error Handling** - Response format consistency

### Missing Frontend Clients
Based on backend routers, these frontend clients may be needed:
- ProjectsApiClient (projects router exists)
- OmnichannelApiClient (omnichannel router exists)
- PortalManagementApiClient (portal_management router exists)

## Immediate Action Items

### 1. Authentication Fix (High Priority)
- ✅ Backend `/auth/login` endpoint working
- ❌ Fix `/auth/me` endpoint path mismatch
- ❌ Implement missing password reset endpoints
- ❌ Add MFA endpoints to backend

### 2. Base URL Configuration
- Verify frontend `BaseApiClient` uses correct base URLs
- Check environment configuration for API endpoints
- Ensure `/api/v1` prefix consistency

### 3. Method Alignment
- Fix PATCH vs PUT inconsistencies (auth profile update)
- Standardize response formats across all endpoints

### 4. Missing Endpoints
Priority order for implementation:
1. Password reset flow
2. MFA setup/verification
3. Session management
4. API key management

## Testing Strategy

### Immediate Tests Needed
1. **Authentication Flow Test**
   - Login → Token → Protected endpoint
   - Refresh token flow
   - Logout and token invalidation

2. **API Client Integration Tests**
   - Each client against its backend module
   - Error handling and response parsing
   - Base URL and header configuration

3. **Cross-Module Communication**
   - Customer → Billing integration
   - Identity → All modules (auth headers)

## Next Steps

1. **Fix authentication endpoint misalignment** (`/auth/me` vs `/me`)
2. **Implement missing password reset endpoints**
3. **Add comprehensive API integration tests**
4. **Verify all frontend clients have working backend counterparts**

---

*Generated during API Audit task - Week of immediate actions*
*Priority: Fix authentication flow, then verify all client-to-backend mappings*