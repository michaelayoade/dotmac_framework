/**
 * Audit and Compliance Monitoring
 * Export audit logging functionality
 */

export {
  AuditLogger,
  CUSTOMER_PORTAL_AUDIT_CONFIG,
  type AuditEvent,
  type AuditContext,
  type AuditLoggerConfig,
} from './AuditLogger';

// Singleton instance for application-wide use
let auditLoggerInstance: AuditLogger | null = null;

/**
 * Get or create audit logger singleton
 */
export function getAuditLogger(config?: import('./AuditLogger').AuditLoggerConfig): AuditLogger {
  if (!auditLoggerInstance) {
    const { AuditLogger: AuditLoggerClass, CUSTOMER_PORTAL_AUDIT_CONFIG } = require('./AuditLogger');
    auditLoggerInstance = new AuditLoggerClass(config || CUSTOMER_PORTAL_AUDIT_CONFIG);
  }
  return auditLoggerInstance;
}

/**
 * Audit helper functions for common operations
 */
export const audit = {
  /**
   * Log user login attempt
   */
  async login(userId: string, success: boolean, context: Partial<import('./AuditLogger').AuditContext> = {}) {
    const logger = getAuditLogger();
    await logger.logAuthentication(
      success ? 'login' : 'failed_login',
      { userId, ...context }
    );
  },

  /**
   * Log user logout
   */
  async logout(userId: string, context: Partial<import('./AuditLogger').AuditContext> = {}) {
    const logger = getAuditLogger();
    await logger.logAuthentication('logout', { userId, ...context });
  },

  /**
   * Log data access
   */
  async dataAccess(
    action: 'read' | 'create' | 'update' | 'delete' | 'export',
    resource: string,
    resourceId: string,
    context: import('./AuditLogger').AuditContext,
    success: boolean = true
  ) {
    const logger = getAuditLogger();
    await logger.logDataAccess(
      action,
      resource,
      resourceId,
      context,
      success ? 'success' : 'failure'
    );
  },

  /**
   * Log security event
   */
  async security(
    event: string,
    context: import('./AuditLogger').AuditContext,
    severity: 'low' | 'medium' | 'high' | 'critical' = 'medium',
    success: boolean = false
  ) {
    const logger = getAuditLogger();
    await logger.logSecurity(
      event,
      context,
      success ? 'success' : 'denied',
      severity
    );
  },

  /**
   * Log business transaction
   */
  async business(
    action: string,
    resource: string,
    resourceId: string,
    context: import('./AuditLogger').AuditContext,
    metadata: Record<string, unknown> = {}
  ) {
    const logger = getAuditLogger();
    await logger.logBusiness(action, resource, resourceId, context, metadata);
  },

  /**
   * Log system event
   */
  async system(
    event: string,
    resource: string,
    success: boolean = true,
    severity: 'low' | 'medium' | 'high' | 'critical' = 'low',
    metadata: Record<string, unknown> = {}
  ) {
    const logger = getAuditLogger();
    await logger.logSystem(event, resource, success ? 'success' : 'failure', severity, metadata);
  },
};

/**
 * Audit context helpers
 */
export const auditContext = {
  /**
   * Create audit context from Next.js request
   */
  fromRequest(request: Request): import('./AuditLogger').AuditContext {
    const headers = request.headers;
    
    return {
      ipAddress: this.getClientIP(request),
      userAgent: headers.get('user-agent') || undefined,
      traceId: headers.get('x-trace-id') || undefined,
      correlationId: headers.get('x-correlation-id') || undefined,
    };
  },

  /**
   * Create audit context from browser
   */
  fromBrowser(userId?: string, sessionId?: string): import('./AuditLogger').AuditContext {
    return {
      userId,
      sessionId,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
      traceId: this.generateTraceId(),
      correlationId: this.generateCorrelationId(),
    };
  },

  /**
   * Extract client IP from request
   */
  getClientIP(request: Request): string {
    const headers = request.headers;
    
    // Check common proxy headers
    const forwardedFor = headers.get('x-forwarded-for');
    if (forwardedFor) {
      return forwardedFor.split(',')[0].trim();
    }
    
    const realIP = headers.get('x-real-ip');
    if (realIP) {
      return realIP;
    }
    
    const remoteAddr = headers.get('x-remote-addr');
    if (remoteAddr) {
      return remoteAddr;
    }
    
    return 'unknown';
  },

  /**
   * Generate trace ID for request tracking
   */
  generateTraceId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 10);
    return `trace_${timestamp}_${random}`;
  },

  /**
   * Generate correlation ID for related events
   */
  generateCorrelationId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 10);
    return `corr_${timestamp}_${random}`;
  },
};