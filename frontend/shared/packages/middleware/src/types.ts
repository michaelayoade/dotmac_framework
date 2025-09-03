import type { NextRequest, NextResponse } from 'next/server';

/**
 * Portal types for middleware configuration
 */
export type PortalType =
  | 'admin'
  | 'customer'
  | 'reseller'
  | 'technician'
  | 'management'
  | 'management-admin'
  | 'management-reseller'
  | 'tenant-portal';

/**
 * Security level configuration
 */
export type SecurityLevel = 'low' | 'medium' | 'high' | 'maximum';

/**
 * Middleware context passed between middlewares
 */
export interface MiddlewareContext {
  request: NextRequest;
  pathname: string;
  portal: PortalType;
  clientIP: string;
  userAgent: string;
  traceId: string;
  correlationId: string;
  timestamp: string;
  startTime: number;
  nonce?: string;
  authToken?: string;
  portalType?: string;
  csrfToken?: string;
}

/**
 * Middleware function signature
 */
export type MiddlewareFunction = (
  context: MiddlewareContext
) => Promise<NextResponse | null> | NextResponse | null;

/**
 * Portal-specific configuration
 */
export interface PortalConfig {
  portal: PortalType;
  publicRoutes: string[];
  authRequired: boolean;
  csrfProtection: boolean;
  rateLimiting: {
    general: { requests: number; windowMs: number };
    auth: { requests: number; windowMs: number };
  };
  securityLevel: SecurityLevel;
  auditLevel: 'minimal' | 'standard' | 'comprehensive';
  customHeaders?: Record<string, string>;
  permissionsPolicy?: string;
}

/**
 * Rate limiting configuration
 */
export interface RateLimitConfig {
  identifier: string;
  maxRequests: number;
  windowMs: number;
  skipSuccessfulRequests?: boolean;
  skipFailedRequests?: boolean;
}

/**
 * CSRF configuration
 */
export interface CSRFConfig {
  cookieName: string;
  headerName: string;
  excludePaths: string[];
  excludeMethods: string[];
}

/**
 * Audit event data
 */
export interface AuditEvent {
  type: string;
  context: Partial<MiddlewareContext>;
  severity: SecurityLevel;
  success: boolean;
  metadata?: Record<string, any>;
}

/**
 * Universal middleware configuration
 */
export interface UniversalMiddlewareConfig {
  portal: PortalConfig;
  enableSecurity: boolean;
  enableAuth: boolean;
  enableCSRF: boolean;
  enableRateLimit: boolean;
  enableAudit: boolean;
  development?: boolean;
  customMiddlewares?: MiddlewareFunction[];
}
