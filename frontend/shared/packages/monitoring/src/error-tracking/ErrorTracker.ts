/**
 * Production Error Tracking and Monitoring System
 * Integrates with Sentry, DataDog, or custom error reporting
 */

interface ErrorContext {
  userId?: string;
  sessionId?: string;
  portalType?: 'customer' | 'admin' | 'reseller' | 'technician';
  userAgent?: string;
  url?: string;
  timestamp?: number;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  fingerprint?: string[];
  tags?: Record<string, string>;
  extra?: Record<string, any>;
}

interface NetworkError extends Error {
  status?: number;
  statusText?: string;
  url?: string;
  method?: string;
}

interface JSError extends Error {
  componentStack?: string;
  errorBoundary?: boolean;
  filename?: string;
  lineno?: number;
  colno?: number;
}

export interface ErrorReport {
  id: string;
  error: Error;
  context: ErrorContext;
  breadcrumbs: Breadcrumb[];
  timestamp: number;
  environment: string;
  release?: string;
}

interface Breadcrumb {
  timestamp: number;
  category: string;
  message: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  data?: Record<string, any>;
}

class ProductionErrorTracker {
  private breadcrumbs: Breadcrumb[] = [];
  private maxBreadcrumbs = 100;
  private isEnabled = true;
  private environment: string;
  private release?: string;
  private beforeSend?: (report: ErrorReport) => ErrorReport | null;
  private onError?: (report: ErrorReport) => void;

  constructor(config: {
    environment: string;
    release?: string;
    maxBreadcrumbs?: number;
    beforeSend?: (report: ErrorReport) => ErrorReport | null;
    onError?: (report: ErrorReport) => void;
  }) {
    this.environment = config.environment;
    this.release = config.release;
    this.maxBreadcrumbs = config.maxBreadcrumbs ?? 100;
    this.beforeSend = config.beforeSend;
    this.onError = config.onError;

    this.setupErrorHandlers();
  }

  /**
   * Manually capture an error with context
   */
  captureError(error: Error, context: Partial<ErrorContext> = {}): void {
    if (!this.isEnabled) return;

    const report = this.createErrorReport(error, context);
    this.processError(report);
  }

  /**
   * Capture an exception with automatic context detection
   */
  captureException(error: Error, extra?: Record<string, any>): void {
    const context: Partial<ErrorContext> = {
      severity: this.determineSeverity(error),
      extra,
      ...this.getAutomaticContext(),
    };

    this.captureError(error, context);
  }

  /**
   * Capture a network error with request details
   */
  captureNetworkError(
    error: NetworkError,
    requestContext?: {
      method?: string;
      url?: string;
      status?: number;
      response?: any;
    }
  ): void {
    const context: Partial<ErrorContext> = {
      severity: error.status && error.status >= 500 ? 'high' : 'medium',
      tags: {
        errorType: 'network',
        status: error.status?.toString() || 'unknown',
        method: requestContext?.method || error.method || 'unknown',
      },
      extra: {
        url: requestContext?.url || error.url,
        status: requestContext?.status || error.status,
        statusText: error.statusText,
        response: requestContext?.response,
      },
      ...this.getAutomaticContext(),
    };

    this.captureError(error, context);
  }

  /**
   * Capture a React error boundary error
   */
  captureComponentError(
    error: JSError,
    errorInfo: {
      componentStack?: string;
      errorBoundary?: boolean;
    }
  ): void {
    const context: Partial<ErrorContext> = {
      severity: 'high',
      tags: {
        errorType: 'component',
        errorBoundary: errorInfo.errorBoundary ? 'true' : 'false',
      },
      extra: {
        componentStack: errorInfo.componentStack,
        filename: error.filename,
        lineno: error.lineno,
        colno: error.colno,
      },
      ...this.getAutomaticContext(),
    };

    this.captureError(error, context);
  }

  /**
   * Add a breadcrumb for debugging context
   */
  addBreadcrumb(breadcrumb: Omit<Breadcrumb, 'timestamp'>): void {
    if (!this.isEnabled) return;

    const fullBreadcrumb: Breadcrumb = {
      ...breadcrumb,
      timestamp: Date.now(),
    };

    this.breadcrumbs.push(fullBreadcrumb);

    if (this.breadcrumbs.length > this.maxBreadcrumbs) {
      this.breadcrumbs = this.breadcrumbs.slice(-this.maxBreadcrumbs);
    }
  }

  /**
   * Set user context for error reports
   */
  setUser(user: {
    id?: string;
    email?: string;
    accountNumber?: string;
    portalType?: string;
  }): void {
    this.addBreadcrumb({
      category: 'auth',
      message: 'User context updated',
      level: 'info',
      data: { userId: user.id, portalType: user.portalType },
    });
  }

  /**
   * Set additional context tags
   */
  setTags(tags: Record<string, string>): void {
    this.addBreadcrumb({
      category: 'context',
      message: 'Tags updated',
      level: 'debug',
      data: tags,
    });
  }

  /**
   * Enable/disable error tracking
   */
  setEnabled(enabled: boolean): void {
    this.isEnabled = enabled;
    this.addBreadcrumb({
      category: 'system',
      message: `Error tracking ${enabled ? 'enabled' : 'disabled'}`,
      level: 'info',
    });
  }

  /**
   * Clear all breadcrumbs
   */
  clearBreadcrumbs(): void {
    this.breadcrumbs = [];
  }

  /**
   * Setup global error handlers
   */
  private setupErrorHandlers(): void {
    // Unhandled JavaScript errors
    window.addEventListener('error', (event) => {
      const error = event.error || new Error(event.message);
      error.filename = event.filename;
      error.lineno = event.lineno;
      error.colno = event.colno;

      this.captureError(error, {
        severity: 'high',
        tags: { errorType: 'unhandled' },
        extra: {
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
      });
    });

    // Unhandled Promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason));

      this.captureError(error, {
        severity: 'high',
        tags: { errorType: 'unhandled-promise' },
        extra: { reason: event.reason },
      });
    });

    // Network errors
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      try {
        const response = await originalFetch(...args);

        if (!response.ok) {
          const error = new Error(
            `HTTP ${response.status}: ${response.statusText}`
          ) as NetworkError;
          error.status = response.status;
          error.statusText = response.statusText;
          error.url = typeof args[0] === 'string' ? args[0] : args[0].url;
          error.method = args[1]?.method || 'GET';

          this.captureNetworkError(error);
        }

        return response;
      } catch (error) {
        if (error instanceof Error) {
          const networkError = error as NetworkError;
          networkError.url = typeof args[0] === 'string' ? args[0] : args[0].url;
          networkError.method = args[1]?.method || 'GET';
          this.captureNetworkError(networkError);
        }
        throw error;
      }
    };
  }

  /**
   * Create a complete error report
   */
  private createErrorReport(error: Error, context: Partial<ErrorContext>): ErrorReport {
    return {
      id: this.generateErrorId(),
      error,
      context: {
        timestamp: Date.now(),
        fingerprint: this.generateFingerprint(error, context),
        ...this.getAutomaticContext(),
        ...context,
      },
      breadcrumbs: [...this.breadcrumbs],
      timestamp: Date.now(),
      environment: this.environment,
      release: this.release,
    };
  }

  /**
   * Process and send error report
   */
  private processError(report: ErrorReport): void {
    // Apply beforeSend filter
    const processedReport = this.beforeSend ? this.beforeSend(report) : report;
    if (!processedReport) return;

    // Log to console in development
    if (this.environment === 'development') {
      console.group(`🚨 Error Report: ${report.id}`);
      console.error('Error:', report.error);
      console.log('Context:', report.context);
      console.log('Breadcrumbs:', report.breadcrumbs);
      console.groupEnd();
    }

    // Send to error tracking service
    this.sendToErrorService(processedReport);

    // Call custom error handler
    this.onError?.(processedReport);

    // Add breadcrumb about error capture
    this.addBreadcrumb({
      category: 'error',
      message: `Error captured: ${error.message}`,
      level: 'error',
      data: {
        errorId: report.id,
        severity: report.context.severity,
      },
    });
  }

  /**
   * Send error to external monitoring service
   */
  private async sendToErrorService(report: ErrorReport): Promise<void> {
    try {
      // This would integrate with services like Sentry, DataDog, etc.
      // For now, we'll use a custom endpoint
      const response = await fetch('/api/monitoring/errors', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: report.id,
          message: report.error.message,
          stack: report.error.stack,
          context: report.context,
          breadcrumbs: report.breadcrumbs,
          timestamp: report.timestamp,
          environment: report.environment,
          release: report.release,
        }),
      });

      if (!response.ok) {
        console.warn('Failed to send error report to monitoring service');
      }
    } catch (error) {
      console.warn('Error sending error report:', error);
    }
  }

  /**
   * Generate unique error ID
   */
  private generateErrorId(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
  }

  /**
   * Generate error fingerprint for grouping
   */
  private generateFingerprint(error: Error, context: Partial<ErrorContext>): string[] {
    const fingerprint = [];

    // Include error message
    if (error.message) {
      fingerprint.push(error.message);
    }

    // Include error type
    fingerprint.push(error.name || 'Error');

    // Include URL for location-specific errors
    if (context.url) {
      fingerprint.push(new URL(context.url).pathname);
    }

    // Include user context for user-specific errors
    if (context.portalType) {
      fingerprint.push(context.portalType);
    }

    return fingerprint;
  }

  /**
   * Get automatic context information
   */
  private getAutomaticContext(): Partial<ErrorContext> {
    return {
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: Date.now(),
    };
  }

  /**
   * Determine error severity based on error type and context
   */
  private determineSeverity(error: Error): ErrorContext['severity'] {
    // Network errors
    if (error.message.includes('fetch') || error.message.includes('network')) {
      return 'medium';
    }

    // Authentication errors
    if (error.message.includes('auth') || error.message.includes('unauthorized')) {
      return 'high';
    }

    // Critical system errors
    if (error.message.includes('database') || error.message.includes('server')) {
      return 'critical';
    }

    // Default to medium severity
    return 'medium';
  }
}

// Global error tracker instance
let globalErrorTracker: ProductionErrorTracker | null = null;

/**
 * Initialize the global error tracker
 */
export function initErrorTracking(config: {
  environment: string;
  release?: string;
  dsn?: string; // For Sentry integration
  maxBreadcrumbs?: number;
  beforeSend?: (report: ErrorReport) => ErrorReport | null;
  onError?: (report: ErrorReport) => void;
}): ProductionErrorTracker {
  globalErrorTracker = new ProductionErrorTracker(config);
  return globalErrorTracker;
}

/**
 * Get the global error tracker instance
 */
export function getErrorTracker(): ProductionErrorTracker | null {
  return globalErrorTracker;
}

/**
 * Convenience functions for error reporting
 */
export const ErrorTracker = {
  captureError: (error: Error, context?: Partial<ErrorContext>) => {
    globalErrorTracker?.captureError(error, context);
  },

  captureException: (error: Error, extra?: Record<string, any>) => {
    globalErrorTracker?.captureException(error, extra);
  },

  captureNetworkError: (error: NetworkError, context?: any) => {
    globalErrorTracker?.captureNetworkError(error, context);
  },

  captureComponentError: (error: JSError, errorInfo: any) => {
    globalErrorTracker?.captureComponentError(error, errorInfo);
  },

  addBreadcrumb: (breadcrumb: Omit<Breadcrumb, 'timestamp'>) => {
    globalErrorTracker?.addBreadcrumb(breadcrumb);
  },

  setUser: (user: any) => {
    globalErrorTracker?.setUser(user);
  },

  setTags: (tags: Record<string, string>) => {
    globalErrorTracker?.setTags(tags);
  },
};

export type { ErrorContext, ErrorReport, Breadcrumb, NetworkError, JSError };
