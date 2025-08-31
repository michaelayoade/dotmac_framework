/**
 * Production Error Handling and Monitoring
 * Enhanced error tracking for production deployments
 */

export interface ErrorMetrics {
  timestamp: Date;
  error: Error;
  context: ErrorContext;
  severity: 'low' | 'medium' | 'high' | 'critical';
  portal: string;
  userId?: string;
  sessionId: string;
}

export interface ErrorContext {
  component?: string;
  action?: string;
  route?: string;
  userAgent?: string;
  viewport?: string;
  props?: Record<string, any>;
}

export class ProductionErrorHandler {
  private static instance: ProductionErrorHandler;
  private errorQueue: ErrorMetrics[] = [];
  private reportingEndpoint: string;
  
  constructor(config: { reportingEndpoint: string }) {
    this.reportingEndpoint = config.reportingEndpoint;
  }

  static getInstance(config?: { reportingEndpoint: string }): ProductionErrorHandler {
    if (!ProductionErrorHandler.instance) {
      if (!config) {
        throw new Error('ProductionErrorHandler requires configuration on first initialization');
      }
      ProductionErrorHandler.instance = new ProductionErrorHandler(config);
    }
    return ProductionErrorHandler.instance;
  }

  /**
   * Capture and report error with context
   */
  captureError(error: Error, context: ErrorContext = {}, severity: ErrorMetrics['severity'] = 'medium'): void {
    const errorMetric: ErrorMetrics = {
      timestamp: new Date(),
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      } as Error,
      context: {
        ...context,
        userAgent: typeof window !== 'undefined' ? window.navigator.userAgent : 'server',
        viewport: typeof window !== 'undefined' ? 
          `${window.innerWidth}x${window.innerHeight}` : 'server',
      },
      severity,
      portal: context.component?.includes('admin') ? 'admin' : 
              context.component?.includes('customer') ? 'customer' :
              context.component?.includes('reseller') ? 'reseller' :
              context.component?.includes('technician') ? 'technician' : 'unknown',
      sessionId: this.getSessionId(),
      userId: this.getUserId(),
    };

    // Add to queue for batch reporting
    this.errorQueue.push(errorMetric);

    // Critical errors are reported immediately
    if (severity === 'critical') {
      this.reportError(errorMetric);
    }

    // Console logging in development
    if (process.env.NODE_ENV === 'development') {
      console.error('Production Error Handler:', errorMetric);
    }
  }

  /**
   * Report error to monitoring service
   */
  private async reportError(errorMetric: ErrorMetrics): Promise<void> {
    try {
      await fetch(this.reportingEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          error: errorMetric,
          platform: 'dotmac-isp-frontend',
          version: process.env.NEXT_PUBLIC_VERSION || '1.0.0',
        }),
      });
    } catch (reportingError) {
      console.error('Failed to report error to monitoring service:', reportingError);
    }
  }

  /**
   * Batch report queued errors
   */
  async flushErrors(): Promise<void> {
    if (this.errorQueue.length === 0) return;

    const errors = [...this.errorQueue];
    this.errorQueue = [];

    try {
      await fetch(this.reportingEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          errors,
          platform: 'dotmac-isp-frontend',
          version: process.env.NEXT_PUBLIC_VERSION || '1.0.0',
          batch: true,
        }),
      });
    } catch (reportingError) {
      console.error('Failed to flush errors to monitoring service:', reportingError);
      // Re-queue errors for next attempt
      this.errorQueue.unshift(...errors);
    }
  }

  private getSessionId(): string {
    if (typeof window === 'undefined') return 'server-session';
    
    let sessionId = sessionStorage.getItem('dotmac-session-id');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('dotmac-session-id', sessionId);
    }
    return sessionId;
  }

  private getUserId(): string | undefined {
    if (typeof window === 'undefined') return undefined;
    
    const userData = localStorage.getItem('dotmac-user');
    if (userData) {
      try {
        const user = JSON.parse(userData);
        return user.id;
      } catch {
        return undefined;
      }
    }
    return undefined;
  }
}

/**
 * Production-ready error boundary hook
 */
export function useProductionErrorHandler() {
  const errorHandler = ProductionErrorHandler.getInstance({
    reportingEndpoint: process.env.NEXT_PUBLIC_ERROR_REPORTING_ENDPOINT || '/api/errors'
  });

  return {
    captureError: errorHandler.captureError.bind(errorHandler),
    flushErrors: errorHandler.flushErrors.bind(errorHandler),
  };
}

/**
 * Global error handler setup
 */
export function setupGlobalErrorHandling(): void {
  if (typeof window === 'undefined') return;

  const errorHandler = ProductionErrorHandler.getInstance({
    reportingEndpoint: process.env.NEXT_PUBLIC_ERROR_REPORTING_ENDPOINT || '/api/errors'
  });

  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    errorHandler.captureError(
      new Error(`Unhandled Promise Rejection: ${event.reason}`),
      { component: 'global', action: 'unhandledrejection' },
      'high'
    );
  });

  // Handle global errors
  window.addEventListener('error', (event) => {
    errorHandler.captureError(
      event.error || new Error(event.message),
      { 
        component: 'global', 
        action: 'error',
        route: window.location.pathname 
      },
      'high'
    );
  });

  // Flush errors periodically
  setInterval(() => {
    errorHandler.flushErrors();
  }, 30000); // Every 30 seconds

  // Flush errors before page unload
  window.addEventListener('beforeunload', () => {
    errorHandler.flushErrors();
  });
}