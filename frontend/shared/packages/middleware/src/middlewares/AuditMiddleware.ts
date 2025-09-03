/**
 * Audit Middleware
 * Handles request logging and security event auditing
 */

import type { MiddlewareFunction, MiddlewareContext, AuditEvent, SecurityLevel } from '../types';

/**
 * Audit event handler interface
 */
interface AuditHandler {
  system: (
    type: string,
    context: any,
    success: boolean,
    severity: SecurityLevel,
    metadata?: any
  ) => Promise<void>;
  security: (
    type: string,
    context: any,
    severity: SecurityLevel,
    success: boolean,
    metadata?: any
  ) => Promise<void>;
}

/**
 * Default audit handler (logs to console in development)
 */
const defaultAuditHandler: AuditHandler = {
  async system(type, context, success, severity, metadata) {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[AUDIT:SYSTEM] ${type}`, { context, success, severity, metadata });
    }

    // In production, send to your audit service
    if (process.env.NODE_ENV === 'production') {
      try {
        await fetch('/api/audit/system', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type,
            context,
            success,
            severity,
            metadata,
            timestamp: new Date().toISOString(),
          }),
        });
      } catch (error) {
        // Fail silently to avoid breaking the app
        console.error('Failed to send audit log:', error);
      }
    }
  },

  async security(type, context, severity, success, metadata) {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[AUDIT:SECURITY] ${type}`, { context, severity, success, metadata });
    }

    // In production, send to your security audit service
    if (process.env.NODE_ENV === 'production') {
      try {
        await fetch('/api/audit/security', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type,
            context,
            severity,
            success,
            metadata,
            timestamp: new Date().toISOString(),
          }),
        });
      } catch (error) {
        // Fail silently to avoid breaking the app
        console.error('Failed to send security audit log:', error);
      }
    }
  },
};

/**
 * Audit middleware factory
 */
export function createAuditMiddleware(
  auditLevel: 'minimal' | 'standard' | 'comprehensive' = 'standard',
  customHandler?: AuditHandler
): MiddlewareFunction {
  const auditHandler = customHandler || defaultAuditHandler;

  return async (context: MiddlewareContext) => {
    const { request, pathname, clientIP, userAgent, traceId, startTime } = context;
    const { method } = request;

    // Log request start (for comprehensive auditing)
    if (auditLevel === 'comprehensive') {
      await auditHandler.system(
        'request_received',
        {
          method,
          pathname,
          clientIP,
          userAgent: userAgent.substring(0, 200), // Truncate long user agents
          traceId,
          timestamp: context.timestamp,
        },
        true,
        'low'
      );
    }

    // Store audit context for later use
    (context as any).auditHandler = auditHandler;
    (context as any).auditLevel = auditLevel;

    return null; // Continue to next middleware
  };
}

/**
 * Audit completion middleware (should be last in chain)
 */
export function createAuditCompletionMiddleware(): MiddlewareFunction {
  return async (context: MiddlewareContext) => {
    const auditHandler = (context as any).auditHandler as AuditHandler;
    const auditLevel = (context as any).auditLevel as string;

    if (!auditHandler || auditLevel === 'minimal') {
      return null;
    }

    const { request, pathname, startTime, traceId } = context;
    const { method } = request;
    const duration = Date.now() - startTime;

    // Log request completion
    await auditHandler.system(
      'request_completed',
      {
        method,
        pathname,
        duration,
        traceId,
        // Note: response status not available in middleware
        timestamp: new Date().toISOString(),
      },
      true,
      'low'
    );

    return null;
  };
}

/**
 * Helper function to log security events from other middlewares
 */
export async function logSecurityEvent(
  context: MiddlewareContext,
  type: string,
  severity: SecurityLevel,
  success: boolean,
  metadata?: any
) {
  const auditHandler = (context as any).auditHandler as AuditHandler;

  if (!auditHandler) {
    return; // No audit handler available
  }

  await auditHandler.security(
    type,
    {
      pathname: context.pathname,
      clientIP: context.clientIP,
      traceId: context.traceId,
      timestamp: new Date().toISOString(),
    },
    severity,
    success,
    metadata
  );
}

/**
 * Performance monitoring middleware
 */
export function createPerformanceMonitoringMiddleware(
  slowRequestThreshold: number = 1000 // 1 second
): MiddlewareFunction {
  return async (context: MiddlewareContext) => {
    const { request, pathname, startTime, traceId } = context;
    const duration = Date.now() - startTime;

    // Log slow requests
    if (duration > slowRequestThreshold) {
      const auditHandler = (context as any).auditHandler as AuditHandler;

      if (auditHandler) {
        await auditHandler.system(
          'slow_request',
          {
            pathname,
            method: request.method,
            duration,
            traceId,
            threshold: slowRequestThreshold,
          },
          false, // Consider slow requests as non-successful
          'medium'
        );
      }
    }

    return null;
  };
}
