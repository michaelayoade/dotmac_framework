/**
 * Production-ready Sentry client configuration
 * Handles browser-side error tracking and performance monitoring
 */

import * as Sentry from '@sentry/nextjs';
import type { SentryConfig, PortalType } from './types';
import { PORTAL_CONFIGS } from './index';

export function initializeSentry(portalType: PortalType, customConfig?: Partial<SentryConfig>) {
  const portalConfig = PORTAL_CONFIGS[portalType];

  if (!portalConfig) {
    throw new Error(`Unknown portal type: ${portalType}`);
  }

  // Validate required environment variables
  if (!process.env.NEXT_PUBLIC_SENTRY_DSN) {
    console.warn('SENTRY_DSN not configured - Sentry disabled');
    return;
  }

  const integrations: any[] = [
    new Sentry.BrowserTracing({
      routingInstrumentation: Sentry.nextRouterInstrumentation,
      // Track user interactions
      tracePropagationTargets: [
        'localhost',
        /^https:\/\/[^/]*\.dotmac\.com/,
        process.env.NEXT_PUBLIC_API_URL,
      ],
    }),
  ];

  // Add session replay for supported portals
  if (portalConfig.enableReplay) {
    integrations.push(
      new Sentry.Replay({
        maskAllText: true,
        maskAllInputs: true,
        blockAllMedia: true,
        // Reduce replay size in production
        sampleRate: process.env.NODE_ENV === 'production' ? 0.01 : 0.1,
        errorSampleRate: 1.0,
      })
    );
  }

  // Add profiling for high-traffic portals
  if (portalConfig.enableProfiling && process.env.NODE_ENV === 'production') {
    integrations.push(new Sentry.BrowserProfiling());
  }

  const config: Sentry.BrowserOptions = {
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

    // Environment configuration
    environment: process.env.NODE_ENV,
    release: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',

    // Performance monitoring
    tracesSampleRate: getTracesSampleRate(portalType),
    profilesSampleRate: portalConfig.enableProfiling ? 0.1 : 0,

    // Error filtering and processing
    beforeSend(event, hint) {
      return filterErrors(event, hint, portalType);
    },

    beforeSendTransaction(event) {
      return filterTransactions(event, portalType);
    },

    // Initial scope configuration
    initialScope: {
      tags: {
        portal: portalType,
        component: portalConfig.component,
        ...customConfig?.customTags,
      },
      contexts: {
        app: {
          name: portalConfig.name,
          version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
        },
        ...customConfig?.customContext,
      },
    },

    integrations,

    // Network and transport configuration
    transport: Sentry.makeBrowserOfflineTransport(Sentry.makeFetchTransport),
    transportOptions: {
      // Batch events for better performance
      bufferSize: 30,
      // Send events every 5 seconds or when buffer is full
      flushAttempts: 3,
    },

    // Security and privacy
    sendDefaultPii: false,
    attachStacktrace: true,

    // Custom configuration override
    ...customConfig,
  };

  Sentry.init(config);

  // Set up global error handlers
  setupGlobalErrorHandlers(portalType);

  console.log(`✅ Sentry initialized for ${portalConfig.name}`);
}

function getTracesSampleRate(portalType: PortalType): number {
  if (process.env.NODE_ENV === 'development') {
    return 1.0; // 100% sampling in development
  }

  // Production sampling rates based on traffic
  const rates: Record<PortalType, number> = {
    'customer': 0.1,           // High traffic - 10%
    'admin': 0.3,              // Medium traffic - 30%
    'reseller': 0.3,           // Medium traffic - 30%
    'technician': 0.5,         // Lower traffic - 50%
    'management-admin': 0.2,   // High importance - 20%
    'management-reseller': 0.3, // Medium traffic - 30%
    'tenant-portal': 0.4,      // Medium-low traffic - 40%
  };

  return rates[portalType] || 0.1;
}

function filterErrors(event: Sentry.Event, hint: Sentry.EventHint, portalType: PortalType) {
  // Don't send events in development unless explicitly enabled
  if (process.env.NODE_ENV === 'development' && !process.env.NEXT_PUBLIC_SENTRY_DEBUG) {
    return null;
  }

  const error = hint.originalException;

  if (error && typeof error === 'object' && 'message' in error) {
    const message = String(error.message);

    // Filter out known non-actionable errors
    const ignoredPatterns = [
      /Non-Error exception captured/,
      /ChunkLoadError/,
      /Loading chunk \d+ failed/,
      /ResizeObserver loop limit exceeded/,
      /Script error\./,
      // Browser extension errors
      /extension\//,
      /moz-extension:/,
      /chrome-extension:/,
      // Network errors that are not actionable
      /NetworkError/,
      /Failed to fetch/,
    ];

    for (const pattern of ignoredPatterns) {
      if (pattern.test(message)) {
        return null;
      }
    }
  }

  // Add portal-specific context
  event.tags = {
    ...event.tags,
    portal: portalType,
  };

  // Add user context if available
  if (typeof window !== 'undefined' && (window as any).__DOTMAC_USER__) {
    const user = (window as any).__DOTMAC_USER__;
    event.user = {
      id: user.id,
      email: user.email,
      username: user.name,
    };
    event.tags.tenant_id = user.tenant_id;
  }

  return event;
}

function filterTransactions(event: Sentry.Event, portalType: PortalType) {
  // Filter out health check and monitoring requests
  if (event.transaction?.includes('/api/health') ||
      event.transaction?.includes('/api/monitoring')) {
    return null;
  }

  // Sample down static asset requests
  if (event.transaction?.match(/\.(js|css|png|jpg|svg|ico)$/)) {
    return Math.random() < 0.01 ? event : null; // 1% sampling
  }

  return event;
}

function setupGlobalErrorHandlers(portalType: PortalType) {
  // Unhandled promise rejections
  if (typeof window !== 'undefined') {
    window.addEventListener('unhandledrejection', (event) => {
      Sentry.captureException(event.reason, {
        tags: {
          portal: portalType,
          errorType: 'unhandledRejection',
        },
      });
    });

    // Console error tracking (development only)
    if (process.env.NODE_ENV === 'development' && process.env.NEXT_PUBLIC_SENTRY_DEBUG) {
      const originalError = console.error;
      console.error = (...args: any[]) => {
        originalError.apply(console, args);
        if (args.length > 0 && args[0] instanceof Error) {
          Sentry.captureException(args[0], {
            level: 'warning',
            tags: {
              portal: portalType,
              errorType: 'consoleError',
            },
          });
        }
      };
    }
  }
}
