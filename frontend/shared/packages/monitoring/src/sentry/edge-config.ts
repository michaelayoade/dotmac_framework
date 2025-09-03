/**
 * Production-ready Sentry edge configuration
 * Handles edge runtime error tracking and performance monitoring
 */

import * as Sentry from '@sentry/nextjs';
import type { SentryConfig, PortalType } from './types';
import { PORTAL_CONFIGS } from './index';

export function initializeSentryEdge(portalType: PortalType, customConfig?: Partial<SentryConfig>) {
  const portalConfig = PORTAL_CONFIGS[portalType];

  if (!portalConfig) {
    throw new Error(`Unknown portal type: ${portalType}`);
  }

  // Validate required environment variables
  if (!process.env.SENTRY_DSN) {
    console.warn('SENTRY_DSN not configured - Edge Sentry disabled');
    return;
  }

  const config: Sentry.EdgeOptions = {
    dsn: process.env.SENTRY_DSN,

    // Environment configuration
    environment: process.env.NODE_ENV,
    release: process.env.APP_VERSION || '1.0.0',

    // Performance monitoring (reduced for edge)
    tracesSampleRate: getEdgeTracesSampleRate(portalType),

    // Error filtering and processing
    beforeSend(event, hint) {
      return filterEdgeErrors(event, hint, portalType);
    },

    beforeSendTransaction(event) {
      return filterEdgeTransactions(event, portalType);
    },

    // Initial scope configuration
    initialScope: {
      tags: {
        portal: portalType,
        component: portalConfig.component + '-edge',
        runtime: 'edge',
        ...customConfig?.customTags,
      },
      contexts: {
        app: {
          name: portalConfig.name,
          version: process.env.APP_VERSION || '1.0.0',
        },
        runtime: {
          name: 'Vercel Edge Runtime',
          version: 'latest',
        },
        ...customConfig?.customContext,
      },
    },

    // Edge-specific optimizations
    maxBreadcrumbs: 20, // Reduced for memory efficiency
    attachStacktrace: true,
    sendDefaultPii: false,

    // Custom configuration override
    ...customConfig,
  };

  Sentry.init(config);

  console.log(`✅ Edge Sentry initialized for ${portalConfig.name}`);
}

function getEdgeTracesSampleRate(portalType: PortalType): number {
  if (process.env.NODE_ENV === 'development') {
    return 1.0; // 100% sampling in development
  }

  // Edge sampling rates (lower due to performance constraints)
  const rates: Record<PortalType, number> = {
    customer: 0.02, // High traffic - 2%
    admin: 0.1, // Medium traffic - 10%
    reseller: 0.1, // Medium traffic - 10%
    technician: 0.2, // Lower traffic - 20%
    'management-admin': 0.05, // High importance - 5%
    'management-reseller': 0.1, // Medium traffic - 10%
    'tenant-portal': 0.2, // Medium-low traffic - 20%
  };

  return rates[portalType] || 0.05;
}

function filterEdgeErrors(event: Sentry.Event, hint: Sentry.EventHint, portalType: PortalType) {
  // Don't send events in development unless explicitly enabled
  if (process.env.NODE_ENV === 'development' && !process.env.SENTRY_DEBUG) {
    return null;
  }

  const error = hint.originalException;

  if (error && typeof error === 'object' && 'message' in error) {
    const message = String(error.message);

    // Filter out edge-specific non-actionable errors
    const ignoredPatterns = [
      /Network connection lost/,
      /Request timeout/,
      /AbortError/,
      /The user aborted a request/,
      // Edge runtime limitations
      /Dynamic require/,
      /Module not found/,
      // Middleware errors that are expected
      /Middleware.*blocked/,
      /Rate limit/,
    ];

    for (const pattern of ignoredPatterns) {
      if (pattern.test(message)) {
        return null;
      }
    }
  }

  // Add edge-specific context
  event.tags = {
    ...event.tags,
    portal: portalType,
    runtime: 'edge',
  };

  // Add request context if available (sanitized for edge)
  if (hint.request) {
    event.request = {
      url: hint.request.url,
      method: hint.request.method,
      headers: sanitizeEdgeHeaders(hint.request.headers),
    };
  }

  return event;
}

function filterEdgeTransactions(event: Sentry.Event, portalType: PortalType) {
  // Filter out middleware and system requests
  if (
    event.transaction?.includes('middleware') ||
    event.transaction?.includes('/_next/') ||
    event.transaction?.includes('/api/health')
  ) {
    return null;
  }

  // Sample down static requests heavily
  if (event.transaction?.match(/\.(js|css|png|jpg|svg|ico|woff|woff2)$/)) {
    return Math.random() < 0.001 ? event : null; // 0.1% sampling
  }

  return event;
}

function sanitizeEdgeHeaders(headers: any): Record<string, string> {
  if (!headers) return {};

  const sanitized: Record<string, string> = {};
  const allowedHeaders = [
    'user-agent',
    'accept',
    'content-type',
    'x-forwarded-for',
    'cf-ray', // Cloudflare
    'x-vercel-id', // Vercel
  ];

  for (const [key, value] of Object.entries(headers)) {
    if (allowedHeaders.includes(key.toLowerCase()) && typeof value === 'string') {
      // Truncate long headers for edge efficiency
      sanitized[key] = value.length > 200 ? value.substring(0, 200) + '...' : value;
    }
  }

  return sanitized;
}

// Edge-specific utilities for manual error capture
export function captureEdgeException(
  error: any,
  portalType: PortalType,
  context?: Record<string, any>
) {
  Sentry.captureException(error, {
    tags: {
      portal: portalType,
      runtime: 'edge',
      ...context?.tags,
    },
    extra: context?.extra,
    level: context?.level || 'error',
  });
}

export function captureEdgeMessage(
  message: string,
  portalType: PortalType,
  level: 'info' | 'warning' | 'error' = 'info',
  context?: Record<string, any>
) {
  Sentry.captureMessage(message, {
    level,
    tags: {
      portal: portalType,
      runtime: 'edge',
      ...context?.tags,
    },
    extra: context?.extra,
  });
}
