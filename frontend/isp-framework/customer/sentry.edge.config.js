// This file configures the initialization of Sentry for edge runtime (middleware)
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.SENTRY_DSN,

  // Reduced sampling for edge runtime
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.05 : 1.0,

  // Environment and release info
  environment: process.env.NODE_ENV,
  release: process.env.APP_VERSION,

  // Edge runtime specific configuration
  beforeSend(event, hint) {
    // Don't send events in development
    if (process.env.NODE_ENV === 'development') {
      return null;
    }

    return event;
  },

  // Minimal context for edge runtime
  initialScope: {
    tags: {
      component: 'customer-portal-edge',
    },
  },
});
