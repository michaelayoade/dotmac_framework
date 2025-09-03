/**
 * Production-ready Sentry server configuration
 * Handles server-side error tracking and performance monitoring
 */

import * as Sentry from '@sentry/nextjs';
import type { SentryConfig, PortalType } from './types';
import { PORTAL_CONFIGS } from './index';

export function initializeSentryServer(
  portalType: PortalType,
  customConfig?: Partial<SentryConfig>
) {
  const portalConfig = PORTAL_CONFIGS[portalType];

  if (!portalConfig) {
    throw new Error(`Unknown portal type: ${portalType}`);
  }

  // Validate required environment variables
  if (!process.env.SENTRY_DSN) {
    console.warn('SENTRY_DSN not configured - Server Sentry disabled');
    return;
  }

  const integrations: any[] = [
    new Sentry.Integrations.Http({
      tracing: true,
      breadcrumbs: true,
      // Track HTTP requests
      tracePropagationTargets: [
        'localhost',
        /^https:\/\/[^/]*\.dotmac\.com/,
        process.env.API_BASE_URL,
      ],
    }),
    new Sentry.Integrations.OnUnhandledRejection({
      mode: 'warn',
    }),
  ];

  // Add profiling for performance-critical portals
  if (portalConfig.enableProfiling && process.env.NODE_ENV === 'production') {
    integrations.push(new Sentry.ProfilingIntegration());
  }

  const config: Sentry.NodeOptions = {
    dsn: process.env.SENTRY_DSN,

    // Environment configuration
    environment: process.env.NODE_ENV,
    release: process.env.APP_VERSION || '1.0.0',
    serverName: process.env.HOSTNAME || 'unknown',

    // Performance monitoring
    tracesSampleRate: getServerTracesSampleRate(portalType),
    profilesSampleRate: portalConfig.enableProfiling ? 0.1 : 0,

    // Error filtering and processing
    beforeSend(event, hint) {
      return filterServerErrors(event, hint, portalType);
    },

    beforeSendTransaction(event) {
      return filterServerTransactions(event, portalType);
    },

    // Initial scope configuration
    initialScope: {
      tags: {
        portal: portalType,
        component: portalConfig.component + '-server',
        runtime: 'nodejs',
        ...customConfig?.customTags,
      },
      contexts: {
        app: {
          name: portalConfig.name,
          version: process.env.APP_VERSION || '1.0.0',
        },
        server: {
          name: process.env.HOSTNAME,
          runtime: `Node.js ${process.version}`,
        },
        ...customConfig?.customContext,
      },
    },

    integrations,

    // Security and privacy
    sendDefaultPii: false,
    attachStacktrace: true,

    // Server-specific options
    maxBreadcrumbs: 50,
    debug: process.env.NODE_ENV === 'development' && !!process.env.SENTRY_DEBUG,

    // Custom configuration override
    ...customConfig,
  };

  Sentry.init(config);

  // Set up server error handlers
  setupServerErrorHandlers(portalType);

  console.log(`✅ Server Sentry initialized for ${portalConfig.name}`);
}

function getServerTracesSampleRate(portalType: PortalType): number {
  if (process.env.NODE_ENV === 'development') {
    return 1.0; // 100% sampling in development
  }

  // Production sampling rates based on server load
  const rates: Record<PortalType, number> = {
    customer: 0.05, // High traffic - 5%
    admin: 0.2, // Medium traffic - 20%
    reseller: 0.2, // Medium traffic - 20%
    technician: 0.3, // Lower traffic - 30%
    'management-admin': 0.1, // High importance - 10%
    'management-reseller': 0.2, // Medium traffic - 20%
    'tenant-portal': 0.3, // Medium-low traffic - 30%
  };

  return rates[portalType] || 0.1;
}

function filterServerErrors(event: Sentry.Event, hint: Sentry.EventHint, portalType: PortalType) {
  // Don't send events in development unless explicitly enabled
  if (process.env.NODE_ENV === 'development' && !process.env.SENTRY_DEBUG) {
    return null;
  }

  const error = hint.originalException;

  if (error && typeof error === 'object' && 'message' in error) {
    const message = String(error.message);

    // Filter out known framework errors
    const ignoredPatterns = [
      /ENOENT.*\.next/,
      /Module not found.*node_modules/,
      /Cannot resolve module/,
      // Health check failures
      /Health check/,
      // Expected validation errors
      /ValidationError/,
      /Bad Request/,
      // Database connection timeouts (handled by retry logic)
      /connect ECONNREFUSED/,
      /Connection terminated/,
    ];

    for (const pattern of ignoredPatterns) {
      if (pattern.test(message)) {
        return null;
      }
    }
  }

  // Add server-specific context
  event.tags = {
    ...event.tags,
    portal: portalType,
    server: process.env.HOSTNAME || 'unknown',
  };

  // Add request context if available
  if (hint.request) {
    event.request = {
      url: hint.request.url,
      method: hint.request.method,
      headers: sanitizeHeaders(hint.request.headers),
    };
  }

  return event;
}

function filterServerTransactions(event: Sentry.Event, portalType: PortalType) {
  // Filter out health check and monitoring requests
  if (
    event.transaction?.includes('/api/health') ||
    event.transaction?.includes('/api/monitoring') ||
    event.transaction?.includes('/_next/')
  ) {
    return null;
  }

  // Sample down static asset requests
  if (event.transaction?.match(/\.(js|css|png|jpg|svg|ico|woff|woff2)$/)) {
    return Math.random() < 0.01 ? event : null; // 1% sampling
  }

  return event;
}

function sanitizeHeaders(headers: any): Record<string, string> {
  if (!headers) return {};

  const sanitized: Record<string, string> = {};
  const allowedHeaders = ['user-agent', 'accept', 'accept-language', 'content-type', 'referer'];

  for (const [key, value] of Object.entries(headers)) {
    if (allowedHeaders.includes(key.toLowerCase()) && typeof value === 'string') {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

function setupServerErrorHandlers(portalType: PortalType) {
  // Unhandled promise rejections
  process.on('unhandledRejection', (reason) => {
    Sentry.captureException(reason, {
      tags: {
        portal: portalType,
        errorType: 'unhandledRejection',
        process: 'server',
      },
    });
  });

  // Uncaught exceptions
  process.on('uncaughtException', (error) => {
    Sentry.captureException(error, {
      tags: {
        portal: portalType,
        errorType: 'uncaughtException',
        process: 'server',
      },
    });

    // Don't exit the process in development
    if (process.env.NODE_ENV === 'production') {
      process.exit(1);
    }
  });

  // Graceful shutdown handling
  const shutdownSignals = ['SIGTERM', 'SIGINT'];
  shutdownSignals.forEach((signal) => {
    process.on(signal, async () => {
      console.log(`Received ${signal}, shutting down gracefully...`);

      // Flush Sentry events before shutdown
      await Sentry.flush(2000);

      process.exit(0);
    });
  });
}
