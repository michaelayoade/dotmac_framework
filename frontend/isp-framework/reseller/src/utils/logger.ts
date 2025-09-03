/**
 * Production-safe logging utility
 * Logs are only output in development mode
 */

export interface LogContext {
  userId?: string;
  partnerId?: string;
  component?: string;
  action?: string;
  [key: string]: any;
}

class Logger {
  private isDevelopment: boolean;

  constructor() {
    this.isDevelopment = process.env.NODE_ENV === 'development';
  }

  private formatMessage(level: string, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    const contextStr = context ? ` | Context: ${JSON.stringify(context)}` : '';
    return `[${timestamp}] ${level.toUpperCase()}: ${message}${contextStr}`;
  }

  private shouldLog(level: 'error' | 'warn' | 'info' | 'debug'): boolean {
    // Always log errors, even in production (they go to monitoring)
    if (level === 'error') return true;
    // Other levels only in development
    return this.isDevelopment;
  }

  error(message: string, error?: Error | unknown, context?: LogContext): void {
    if (this.shouldLog('error')) {
      const errorDetails = error instanceof Error ? error.message : String(error);
      const fullContext = { ...context, error: errorDetails };
      console.error(this.formatMessage('error', message, fullContext));

      // In production, you would send this to your error monitoring service
      // Example: Sentry.captureException(error, { extra: context });
    }
  }

  warn(message: string, context?: LogContext): void {
    if (this.shouldLog('warn')) {
      console.warn(this.formatMessage('warn', message, context));
    }
  }

  info(message: string, context?: LogContext): void {
    if (this.shouldLog('info')) {
      console.info(this.formatMessage('info', message, context));
    }
  }

  debug(message: string, context?: LogContext): void {
    if (this.shouldLog('debug')) {
      console.debug(this.formatMessage('debug', message, context));
    }
  }
}

// Export singleton instance
export const logger = new Logger();

// Helper function for authentication events
export const logAuthEvent = (event: string, userId?: string, success: boolean = true) => {
  logger.info(`Auth event: ${event}`, {
    userId,
    success,
    component: 'auth',
    timestamp: Date.now(),
  });
};

// Helper function for security events
export const logSecurityEvent = (event: string, details: LogContext) => {
  logger.warn(`Security event: ${event}`, {
    ...details,
    component: 'security',
    timestamp: Date.now(),
  });
};
