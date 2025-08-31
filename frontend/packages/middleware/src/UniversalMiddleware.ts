/**
 * Universal Middleware
 * Orchestrates all middleware functions in the correct order
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import type { 
  MiddlewareFunction, 
  UniversalMiddlewareConfig, 
  PortalType,
  PortalConfig 
} from './types';
import { createContext, PORTAL_DEFAULTS } from './utils';
import { createSecurityMiddleware } from './middlewares/SecurityMiddleware';
import { createAuthMiddleware } from './middlewares/AuthMiddleware';
import { createCSRFMiddleware, createCSRFTokenMiddleware } from './middlewares/CSRFMiddleware';
import { createRateLimitMiddleware } from './middlewares/RateLimitMiddleware';
import { createAuditMiddleware, createAuditCompletionMiddleware, createPerformanceMonitoringMiddleware } from './middlewares/AuditMiddleware';

/**
 * Create portal configuration with defaults
 */
function createPortalConfig(portal: PortalType, overrides: Partial<PortalConfig> = {}): PortalConfig {
  const defaults = PORTAL_DEFAULTS[portal];
  
  return {
    portal,
    publicRoutes: defaults.publicRoutes,
    authRequired: defaults.authRequired,
    csrfProtection: true,
    rateLimiting: defaults.rateLimiting,
    securityLevel: defaults.securityLevel,
    auditLevel: 'standard',
    ...overrides
  };
}

/**
 * Universal Middleware Factory
 * Creates a middleware function that orchestrates all security, auth, and audit middlewares
 */
export function createUniversalMiddleware(config: UniversalMiddlewareConfig) {
  const portalConfig = createPortalConfig(config.portal.portal, config.portal);
  const development = config.development || process.env.NODE_ENV === 'development';

  // Build middleware chain in correct order
  const middlewares: MiddlewareFunction[] = [];

  // 1. Audit initialization (first)
  if (config.enableAudit) {
    middlewares.push(createAuditMiddleware(portalConfig.auditLevel));
  }

  // 2. Rate limiting (early, before expensive operations)
  if (config.enableRateLimit) {
    middlewares.push(
      createRateLimitMiddleware(
        portalConfig.rateLimiting.general,
        portalConfig.rateLimiting.auth
      )
    );
  }

  // 3. CSRF token generation (before CSRF validation)
  if (config.enableCSRF) {
    middlewares.push(createCSRFTokenMiddleware());
  }

  // 4. CSRF validation (after token generation)
  if (config.enableCSRF) {
    middlewares.push(createCSRFMiddleware(portalConfig.publicRoutes));
  }

  // 5. Authentication (after CSRF to prevent CSRF attacks on auth)
  if (config.enableAuth) {
    middlewares.push(
      createAuthMiddleware(
        portalConfig.portal,
        portalConfig.publicRoutes,
        portalConfig.authRequired
      )
    );
  }

  // 6. Custom middlewares (user-defined logic)
  if (config.customMiddlewares) {
    middlewares.push(...config.customMiddlewares);
  }

  // 7. Performance monitoring
  if (config.enableAudit) {
    middlewares.push(createPerformanceMonitoringMiddleware());
  }

  // 8. Security headers (last, to ensure they're always applied)
  if (config.enableSecurity) {
    middlewares.push(
      createSecurityMiddleware(
        portalConfig.securityLevel,
        development,
        portalConfig.customHeaders
      )
    );
  }

  // 9. Audit completion (very last)
  if (config.enableAudit) {
    middlewares.push(createAuditCompletionMiddleware());
  }

  // Return the main middleware function
  return async function universalMiddleware(request: NextRequest): Promise<NextResponse> {
    // Create middleware context
    const context = createContext(request, portalConfig.portal);

    // Execute middlewares in order
    for (const middleware of middlewares) {
      try {
        const result = await middleware(context);
        
        // If middleware returns a response, return it immediately
        if (result instanceof NextResponse) {
          return result;
        }
      } catch (error) {
        console.error('Middleware error:', error);
        
        // Log the error if audit is enabled
        if (config.enableAudit && (context as any).auditHandler) {
          await (context as any).auditHandler.security(
            'middleware_error',
            {
              pathname: context.pathname,
              error: error instanceof Error ? error.message : 'Unknown error',
              traceId: context.traceId
            },
            'high',
            false
          );
        }
        
        // Return error response
        return NextResponse.json(
          { error: 'Internal server error' },
          { status: 500 }
        );
      }
    }

    // If no middleware returned a response, continue normally
    return NextResponse.next();
  };
}

/**
 * Predefined middleware configurations for each portal
 */
export const PORTAL_MIDDLEWARE_CONFIGS = {
  admin: createUniversalMiddleware({
    portal: createPortalConfig('admin'),
    enableSecurity: true,
    enableAuth: true,
    enableCSRF: true,
    enableRateLimit: true,
    enableAudit: true
  }),

  'management-admin': createUniversalMiddleware({
    portal: createPortalConfig('management-admin', {
      securityLevel: 'maximum',
      auditLevel: 'comprehensive'
    }),
    enableSecurity: true,
    enableAuth: true,
    enableCSRF: true,
    enableRateLimit: true,
    enableAudit: true
  }),

  'management-reseller': createUniversalMiddleware({
    portal: createPortalConfig('management-reseller', {
      securityLevel: 'high',
      auditLevel: 'standard'
    }),
    enableSecurity: true,
    enableAuth: true,
    enableCSRF: true,
    enableRateLimit: true,
    enableAudit: true
  }),

  customer: createUniversalMiddleware({
    portal: createPortalConfig('customer'),
    enableSecurity: true,
    enableAuth: true,
    enableCSRF: true,
    enableRateLimit: true,
    enableAudit: true
  }),

  reseller: createUniversalMiddleware({
    portal: createPortalConfig('reseller'),
    enableSecurity: true,
    enableAuth: true,
    enableCSRF: true,
    enableRateLimit: true,
    enableAudit: true
  }),

  technician: createUniversalMiddleware({
    portal: createPortalConfig('technician', {
      securityLevel: 'medium', // Relaxed for mobile
      auditLevel: 'minimal' // Reduced logging for mobile performance
    }),
    enableSecurity: true,
    enableAuth: true,
    enableCSRF: true,
    enableRateLimit: true,
    enableAudit: true
  }),

  management: createUniversalMiddleware({
    portal: createPortalConfig('management', {
      securityLevel: 'maximum',
      auditLevel: 'comprehensive'
    }),
    enableSecurity: true,
    enableAuth: true,
    enableCSRF: true,
    enableRateLimit: true,
    enableAudit: true
  }),

  'tenant-portal': createUniversalMiddleware({
    portal: createPortalConfig('tenant-portal', {
      securityLevel: 'high',
      auditLevel: 'standard'
    }),
    enableSecurity: true,
    enableAuth: true,
    enableCSRF: true,
    enableRateLimit: true,
    enableAudit: true
  })
};

/**
 * Standard Next.js middleware matcher configuration
 */
export const STANDARD_MIDDLEWARE_MATCHER = [
  /*
   * Match all request paths except for the ones starting with:
   * - api (handled by API routes)
   * - _next/static (static files)
   * - _next/image (image optimization files)
   * - favicon.ico (favicon file)
   * - public folder
   */
  '/((?!api|_next/static|_next/image|favicon.ico|public).*)',
];
