/**
 * Admin Portal Middleware
 * Uses the unified middleware system for consistency and security
 */

import { PORTAL_MIDDLEWARE_CONFIGS, STANDARD_MIDDLEWARE_MATCHER } from '@dotmac/middleware';

// Use the pre-configured admin middleware
export const middleware = PORTAL_MIDDLEWARE_CONFIGS.admin;

export const config = {
  matcher: STANDARD_MIDDLEWARE_MATCHER,
};
