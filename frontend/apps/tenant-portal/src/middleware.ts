/**
 * Unified middleware for Tenant Portal
 * Uses shared security/auth/audit chain
 */
import { PORTAL_MIDDLEWARE_CONFIGS, STANDARD_MIDDLEWARE_MATCHER } from '@dotmac/middleware';

export const middleware = PORTAL_MIDDLEWARE_CONFIGS['tenant-portal'];

export const config = {
  matcher: STANDARD_MIDDLEWARE_MATCHER,
};
