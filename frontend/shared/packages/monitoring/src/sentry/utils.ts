/**
 * Production-ready Sentry utility functions
 * Provides consistent error capture and user feedback across all portals
 */

import * as Sentry from '@sentry/nextjs';
import type { PortalType, ErrorSeverity, UserFeedbackData, ErrorContext } from './types';

/**
 * Capture an exception with portal-specific context
 */
export function captureException(
  error: any,
  portalType: PortalType,
  context?: Partial<ErrorContext>
) {
  const eventId = Sentry.captureException(error, {
    level: context?.severity || 'error',
    tags: {
      portal: portalType,
      userId: context?.userId,
      tenantId: context?.tenantId,
      route: context?.route,
      timestamp: context?.timestamp || Date.now(),
      ...context?.additional?.tags,
    },
    user: context?.userId
      ? {
          id: context.userId,
          ip_address: '{{auto}}', // Let Sentry handle IP
        }
      : undefined,
    extra: {
      userAgent: context?.userAgent,
      timestamp: new Date().toISOString(),
      portal: portalType,
      ...context?.additional?.extra,
    },
  });

  return eventId;
}

/**
 * Capture a message with portal-specific context
 */
export function captureMessage(
  message: string,
  portalType: PortalType,
  level: ErrorSeverity = 'info',
  context?: Partial<ErrorContext>
) {
  const eventId = Sentry.captureMessage(message, {
    level,
    tags: {
      portal: portalType,
      userId: context?.userId,
      tenantId: context?.tenantId,
      route: context?.route,
      messageType: 'manual',
      ...context?.additional?.tags,
    },
    user: context?.userId
      ? {
          id: context.userId,
        }
      : undefined,
    extra: {
      timestamp: new Date().toISOString(),
      portal: portalType,
      ...context?.additional?.extra,
    },
  });

  return eventId;
}

/**
 * Capture user feedback for an error
 */
export function captureUserFeedback(eventId: string, feedback: UserFeedbackData) {
  Sentry.captureUserFeedback({
    event_id: eventId,
    name: feedback.name || 'Anonymous',
    email: feedback.email || 'unknown@example.com',
    comments: feedback.comments,
  });
}

/**
 * Set user context for current session
 */
export function setUserContext(
  userId: string,
  userInfo?: {
    email?: string;
    username?: string;
    tenantId?: string;
    subscription?: string;
  }
) {
  Sentry.setUser({
    id: userId,
    email: userInfo?.email,
    username: userInfo?.username,
    segment: userInfo?.subscription,
  });

  // Set additional context
  if (userInfo?.tenantId) {
    Sentry.setTag('tenant_id', userInfo.tenantId);
  }
}

/**
 * Clear user context (e.g., on logout)
 */
export function clearUserContext() {
  Sentry.setUser(null);
}

/**
 * Add breadcrumb for tracking user actions
 */
export function addBreadcrumb(
  message: string,
  category: string,
  level: 'info' | 'warning' | 'error' | 'debug' = 'info',
  data?: Record<string, any>
) {
  Sentry.addBreadcrumb({
    message,
    category,
    level,
    timestamp: Date.now() / 1000,
    data,
  });
}

/**
 * Track performance metrics
 */
export function trackPerformance(
  name: string,
  portalType: PortalType,
  metrics: {
    duration?: number;
    startTime?: number;
    endTime?: number;
    tags?: Record<string, string>;
    data?: Record<string, any>;
  }
) {
  const transaction = Sentry.startTransaction({
    name,
    op: 'performance.track',
    tags: {
      portal: portalType,
      ...metrics.tags,
    },
    data: metrics.data,
    startTimestamp: metrics.startTime ? metrics.startTime / 1000 : undefined,
  });

  if (metrics.duration) {
    transaction.setMeasurement('duration', metrics.duration, 'millisecond');
  }

  if (metrics.endTime) {
    transaction.finish(metrics.endTime / 1000);
  } else {
    transaction.finish();
  }
}

/**
 * Monitor async function execution with automatic error capture
 */
export function withSentryMonitoring<T extends any[], R>(
  fn: (...args: T) => Promise<R>,
  portalType: PortalType,
  operationName: string
) {
  return async (...args: T): Promise<R> => {
    const transaction = Sentry.startTransaction({
      name: operationName,
      op: 'function.monitored',
      tags: {
        portal: portalType,
      },
    });

    Sentry.getCurrentHub().configureScope((scope) => {
      scope.setSpan(transaction);
    });

    try {
      const result = await fn(...args);
      transaction.setStatus('ok');
      return result;
    } catch (error) {
      transaction.setStatus('internal_error');
      captureException(error, portalType, {
        additional: {
          tags: {
            operation: operationName,
          },
          extra: {
            arguments: args,
          },
        },
      });
      throw error;
    } finally {
      transaction.finish();
    }
  };
}

/**
 * Create a performance span for measuring operations
 */
export function measureOperation<T>(
  operationName: string,
  operation: () => T,
  portalType: PortalType
): T {
  const span = Sentry.getCurrentHub()
    .getScope()
    ?.getSpan()
    ?.startChild({
      op: 'measure',
      description: operationName,
      tags: {
        portal: portalType,
      },
    });

  try {
    const result = operation();
    span?.setStatus('ok');
    return result;
  } catch (error) {
    span?.setStatus('internal_error');
    throw error;
  } finally {
    span?.finish();
  }
}

/**
 * Flush all pending Sentry events (useful for serverless functions)
 */
export async function flushEvents(timeout: number = 2000): Promise<boolean> {
  return await Sentry.flush(timeout);
}

/**
 * Configure scope with portal-specific context
 */
export function configurePortalScope(
  portalType: PortalType,
  context: {
    userId?: string;
    tenantId?: string;
    route?: string;
    feature?: string;
    tags?: Record<string, string>;
  }
) {
  Sentry.configureScope((scope) => {
    scope.setTag('portal', portalType);

    if (context.userId) {
      scope.setUser({ id: context.userId });
      scope.setTag('user_id', context.userId);
    }

    if (context.tenantId) {
      scope.setTag('tenant_id', context.tenantId);
    }

    if (context.route) {
      scope.setTag('route', context.route);
    }

    if (context.feature) {
      scope.setTag('feature', context.feature);
    }

    if (context.tags) {
      Object.entries(context.tags).forEach(([key, value]) => {
        scope.setTag(key, value);
      });
    }
  });
}

/**
 * Debug utilities (development only)
 */
export const debug = {
  /**
   * Log debug information in development
   */
  log: (message: string, data?: any) => {
    if (process.env.NODE_ENV === 'development' && process.env.NEXT_PUBLIC_SENTRY_DEBUG) {
      console.log(`[Sentry Debug] ${message}`, data);
    }
  },

  /**
   * Test Sentry integration
   */
  testError: (portalType: PortalType) => {
    if (process.env.NODE_ENV === 'development') {
      captureException(new Error('Test error from development environment'), portalType, {
        severity: 'info',
        additional: {
          tags: {
            test: 'true',
            source: 'debug.testError',
          },
        },
      });
    }
  },

  /**
   * Test performance tracking
   */
  testPerformance: (portalType: PortalType) => {
    if (process.env.NODE_ENV === 'development') {
      trackPerformance('test-performance', portalType, {
        duration: Math.random() * 1000,
        tags: {
          test: 'true',
          source: 'debug.testPerformance',
        },
      });
    }
  },
};
