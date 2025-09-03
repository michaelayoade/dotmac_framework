// This file configures the initialization of Sentry for server-side rendering
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.SENTRY_DSN,

  // Performance monitoring for server-side
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  // Environment and release info
  environment: process.env.NODE_ENV,
  release: process.env.APP_VERSION,

  // Server-specific configuration
  beforeSend(event, hint) {
    // Don't send events in development unless explicitly enabled
    if (process.env.NODE_ENV === 'development' && !process.env.SENTRY_DEBUG) {
      return null;
    }

    // Filter out known framework errors
    const error = hint.originalException;
    if (error && error.message) {
      // Ignore common Next.js warnings that aren't actual errors
      if (error.message.includes('ENOENT') && error.message.includes('.next')) {
        return null;
      }
    }

    return event;
  },

  // User context and additional data
  initialScope: {
    tags: {
      component: 'customer-portal-server',
    },
    contexts: {
      app: {
        name: 'DotMac Customer Portal',
        version: process.env.APP_VERSION,
      },
      server: {
        runtime: 'nodejs',
      },
    },
  },

  // Configure server-side integrations
  integrations: [
    new Sentry.Integrations.Http({
      tracing: true,
      breadcrumbs: true,
    }),
  ],
});
