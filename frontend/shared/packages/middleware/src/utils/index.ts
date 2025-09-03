/**
 * Shared middleware utilities
 */

import type { MiddlewareContext, PortalType } from '../types';

/**
 * Generate unique trace ID
 */
export function generateTraceId(): string {
  return `trace-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Generate unique correlation ID
 */
export function generateCorrelationId(): string {
  return `corr-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Extract client IP from request
 */
export function getClientIP(request: Request): string {
  return (
    (request as any).ip ||
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-real-ip') ||
    request.headers.get('cf-connecting-ip') ||
    'unknown'
  );
}

/**
 * Create middleware context from request
 */
export function createContext(request: any, portal: PortalType): MiddlewareContext {
  const { pathname } = new URL(request.url);

  return {
    request,
    pathname,
    portal,
    clientIP: getClientIP(request),
    userAgent: request.headers.get('user-agent') || 'unknown',
    traceId: generateTraceId(),
    correlationId: generateCorrelationId(),
    timestamp: new Date().toISOString(),
    startTime: Date.now(),
    authToken:
      request.cookies.get('auth-token')?.value || request.cookies.get('secure-auth-token')?.value,
    portalType: request.cookies.get('portal-type')?.value,
    csrfToken: request.cookies.get('csrf-token')?.value,
  };
}

/**
 * Check if route is public
 */
export function isPublicRoute(pathname: string, publicRoutes: string[]): boolean {
  return publicRoutes.some(
    (route) =>
      pathname === route || pathname.startsWith('/api/auth') || pathname.startsWith('/api/health')
  );
}

/**
 * Check if route is API route
 */
export function isApiRoute(pathname: string): boolean {
  return pathname.startsWith('/api/');
}

/**
 * Check if route is authentication endpoint
 */
export function isAuthEndpoint(pathname: string): boolean {
  return pathname.startsWith('/api/auth') || pathname === '/login';
}

/**
 * Portal-specific default configurations
 */
export const PORTAL_DEFAULTS = {
  admin: {
    publicRoutes: ['/', '/login', '/forgot-password', '/reset-password'],
    authRequired: true,
    securityLevel: 'high' as const,
    rateLimiting: {
      general: { requests: 100, windowMs: 60 * 1000 },
      auth: { requests: 3, windowMs: 15 * 60 * 1000 },
    },
  },
  customer: {
    publicRoutes: ['/', '/login', '/register', '/forgot-password', '/reset-password'],
    authRequired: true,
    securityLevel: 'medium' as const,
    rateLimiting: {
      general: { requests: 100, windowMs: 60 * 1000 },
      auth: { requests: 5, windowMs: 15 * 60 * 1000 },
    },
  },
  reseller: {
    publicRoutes: ['/', '/login', '/forgot-password', '/reset-password'],
    authRequired: true,
    securityLevel: 'high' as const,
    rateLimiting: {
      general: { requests: 150, windowMs: 60 * 1000 },
      auth: { requests: 5, windowMs: 15 * 60 * 1000 },
    },
  },
  technician: {
    publicRoutes: ['/', '/login', '/offline'],
    authRequired: true,
    securityLevel: 'medium' as const,
    rateLimiting: {
      general: { requests: 200, windowMs: 60 * 1000 }, // Higher for mobile sync
      auth: { requests: 5, windowMs: 15 * 60 * 1000 },
    },
  },
  management: {
    publicRoutes: ['/', '/login'],
    authRequired: true,
    securityLevel: 'maximum' as const,
    rateLimiting: {
      general: { requests: 80, windowMs: 60 * 1000 },
      auth: { requests: 2, windowMs: 15 * 60 * 1000 },
    },
  },
  'management-admin': {
    publicRoutes: ['/', '/login'],
    authRequired: true,
    securityLevel: 'maximum' as const,
    rateLimiting: {
      general: { requests: 80, windowMs: 60 * 1000 },
      auth: { requests: 2, windowMs: 15 * 60 * 1000 },
    },
  },
  'management-reseller': {
    publicRoutes: ['/', '/login'],
    authRequired: true,
    securityLevel: 'high' as const,
    rateLimiting: {
      general: { requests: 120, windowMs: 60 * 1000 },
      auth: { requests: 3, windowMs: 15 * 60 * 1000 },
    },
  },
  'tenant-portal': {
    publicRoutes: ['/', '/login', '/api/health', '/api/csp-report'],
    authRequired: true,
    securityLevel: 'high' as const,
    rateLimiting: {
      general: { requests: 100, windowMs: 60 * 1000 },
      auth: { requests: 4, windowMs: 15 * 60 * 1000 },
    },
  },
} as const;
