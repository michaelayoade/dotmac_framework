/**
 * Higher-order components and utilities for Sentry monitoring integration
 */

import React from 'react';
import * as Sentry from '@sentry/nextjs';
import { SentryErrorBoundary } from './error-boundary';
import type { PortalType } from './types';

/**
 * HOC to add Sentry monitoring to any component
 */
export function withSentryMonitoring<P extends Record<string, any>>(
  WrappedComponent: React.ComponentType<P>,
  portalType: PortalType,
  options: {
    componentName?: string;
    enableErrorBoundary?: boolean;
    enablePerformanceMonitoring?: boolean;
    tags?: Record<string, string>;
  } = {}
) {
  const {
    componentName = WrappedComponent.displayName || WrappedComponent.name || 'Component',
    enableErrorBoundary = true,
    enablePerformanceMonitoring = true,
    tags = {},
  } = options;

  const MonitoredComponent = React.forwardRef<any, P>((props, ref) => {
    // Performance monitoring
    const [renderCount, setRenderCount] = React.useState(0);

    React.useEffect(() => {
      setRenderCount(prev => prev + 1);
    });

    React.useEffect(() => {
      if (enablePerformanceMonitoring) {
        const markName = `${componentName}-mount-${renderCount}`;
        performance.mark(markName);

        // Add breadcrumb for component mounting
        Sentry.addBreadcrumb({
          message: `Component ${componentName} mounted`,
          category: 'ui.lifecycle',
          level: 'info',
          data: {
            portal: portalType,
            renderCount,
            ...tags,
          },
        });

        return () => {
          try {
            const endMarkName = `${componentName}-unmount-${renderCount}`;
            performance.mark(endMarkName);
            performance.measure(
              `${componentName}-lifecycle-${renderCount}`,
              markName,
              endMarkName
            );
          } catch (error) {
            // Performance API might not be available
          }
        };
      }
    }, [renderCount]);

    // Render component with performance tracking
    if (enablePerformanceMonitoring) {
      const spanName = `${componentName}-render-${renderCount}`;

      return Sentry.withProfiler(
        React.createElement(WrappedComponent, { ...props, ref }),
        {
          name: spanName,
          tags: {
            portal: portalType,
            component: componentName,
            renderCount: renderCount.toString(),
            ...tags,
          },
        }
      );
    }

    return React.createElement(WrappedComponent, { ...props, ref });
  });

  MonitoredComponent.displayName = `withSentryMonitoring(${componentName})`;

  // Wrap with error boundary if enabled
  if (enableErrorBoundary) {
    return React.forwardRef<any, P>((props, ref) => (
      <SentryErrorBoundary
        portalType={portalType}
        tags={{
          component: componentName,
          ...tags,
        }}
        beforeCapture={(error) => {
          Sentry.addBreadcrumb({
            message: `Error in component ${componentName}`,
            category: 'ui.error',
            level: 'error',
            data: {
              portal: portalType,
              component: componentName,
              error: error.message,
            },
          });
        }}
      >
        <MonitoredComponent {...props} ref={ref} />
      </SentryErrorBoundary>
    ));
  }

  return MonitoredComponent;
}

/**
 * Hook to add Sentry context to functional components
 */
export function useSentryMonitoring(
  componentName: string,
  portalType: PortalType,
  dependencies: any[] = []
) {
  React.useEffect(() => {
    Sentry.configureScope((scope) => {
      scope.setTag('component', componentName);
      scope.setTag('portal', portalType);
      scope.setContext('component', {
        name: componentName,
        portal: portalType,
        timestamp: new Date().toISOString(),
      });
    });

    // Add breadcrumb for component lifecycle
    Sentry.addBreadcrumb({
      message: `Component ${componentName} rendered`,
      category: 'ui.lifecycle',
      level: 'info',
      data: {
        portal: portalType,
        dependencies: dependencies.length,
      },
    });
  }, dependencies);

  return {
    captureException: (error: any, context?: Record<string, any>) => {
      Sentry.captureException(error, {
        tags: {
          component: componentName,
          portal: portalType,
          ...context?.tags,
        },
        extra: {
          timestamp: new Date().toISOString(),
          ...context?.extra,
        },
      });
    },

    captureMessage: (message: string, level: 'info' | 'warning' | 'error' = 'info') => {
      Sentry.captureMessage(message, {
        level,
        tags: {
          component: componentName,
          portal: portalType,
        },
      });
    },

    addBreadcrumb: (message: string, data?: Record<string, any>) => {
      Sentry.addBreadcrumb({
        message,
        category: 'ui.action',
        level: 'info',
        data: {
          component: componentName,
          portal: portalType,
          ...data,
        },
      });
    },
  };
}

/**
 * Context provider for Sentry monitoring configuration
 */
interface SentryMonitoringContextValue {
  portalType: PortalType;
  enablePerformanceMonitoring: boolean;
  enableErrorBoundaries: boolean;
  globalTags: Record<string, string>;
}

const SentryMonitoringContext = React.createContext<SentryMonitoringContextValue | null>(null);

export function SentryMonitoringProvider({
  children,
  portalType,
  enablePerformanceMonitoring = true,
  enableErrorBoundaries = true,
  globalTags = {},
}: {
  children: React.ReactNode;
  portalType: PortalType;
  enablePerformanceMonitoring?: boolean;
  enableErrorBoundaries?: boolean;
  globalTags?: Record<string, string>;
}) {
  const value = React.useMemo(() => ({
    portalType,
    enablePerformanceMonitoring,
    enableErrorBoundaries,
    globalTags,
  }), [portalType, enablePerformanceMonitoring, enableErrorBoundaries, globalTags]);

  React.useEffect(() => {
    // Set global tags when provider mounts
    Sentry.configureScope((scope) => {
      scope.setTag('portal', portalType);
      Object.entries(globalTags).forEach(([key, value]) => {
        scope.setTag(key, value);
      });
    });
  }, [portalType, globalTags]);

  return (
    <SentryMonitoringContext.Provider value={value}>
      {children}
    </SentryMonitoringContext.Provider>
  );
}

export function useSentryMonitoringContext() {
  const context = React.useContext(SentryMonitoringContext);
  if (!context) {
    throw new Error('useSentryMonitoringContext must be used within SentryMonitoringProvider');
  }
  return context;
}

/**
 * Decorator for async functions to add Sentry monitoring
 */
export function withSentryTransaction<T extends any[], R>(
  fn: (...args: T) => Promise<R>,
  transactionName: string,
  portalType: PortalType
) {
  return async (...args: T): Promise<R> => {
    const transaction = Sentry.startTransaction({
      name: transactionName,
      op: 'function',
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
      Sentry.captureException(error, {
        tags: {
          transaction: transactionName,
          portal: portalType,
        },
      });
      throw error;
    } finally {
      transaction.finish();
    }
  };
}

/**
 * React component to manually trigger Sentry events (development only)
 */
export function SentryDebugPanel({ portalType }: { portalType: PortalType }) {
  if (process.env.NODE_ENV !== 'development' || !process.env.NEXT_PUBLIC_SENTRY_DEBUG) {
    return null;
  }

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 10,
        right: 10,
        background: 'rgba(0,0,0,0.8)',
        color: 'white',
        padding: '10px',
        borderRadius: '5px',
        fontSize: '12px',
        zIndex: 9999,
      }}
    >
      <div>Sentry Debug Panel ({portalType})</div>
      <button
        onClick={() => {
          Sentry.captureException(new Error('Test error from debug panel'), {
            tags: { source: 'debug-panel', portal: portalType },
          });
        }}
        style={{ margin: '2px', padding: '2px 8px', fontSize: '10px' }}
      >
        Test Error
      </button>
      <button
        onClick={() => {
          Sentry.captureMessage('Test message from debug panel', {
            level: 'info',
            tags: { source: 'debug-panel', portal: portalType },
          });
        }}
        style={{ margin: '2px', padding: '2px 8px', fontSize: '10px' }}
      >
        Test Message
      </button>
    </div>
  );
}
