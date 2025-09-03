// This file configures the initialization of Sentry on the browser side
import * as Sentry from '@sentry/nextjs';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Performance monitoring
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  // Session replay for debugging
  replaysSessionSampleRate: process.env.NODE_ENV === 'production' ? 0.01 : 0.1,
  replaysOnErrorSampleRate: 1.0,

  // Environment and release info
  environment: process.env.NODE_ENV,
  release: process.env.NEXT_PUBLIC_APP_VERSION,

  // Configure which URLs to capture
  beforeSend(event, hint) {
    // Don't send events in development unless explicitly enabled
    if (process.env.NODE_ENV === 'development' && !process.env.NEXT_PUBLIC_SENTRY_DEBUG) {
      return null;
    }

    // Filter out known third-party errors
    const error = hint.originalException;
    if (error && error.message) {
      // Ignore common browser extension errors
      if (
        error.message.includes('Non-Error exception captured') ||
        error.message.includes('ChunkLoadError') ||
        error.message.includes('Loading chunk')
      ) {
        return null;
      }
    }

    return event;
  },

  // User context and additional data
  initialScope: {
    tags: {
      component: 'customer-portal',
    },
    contexts: {
      app: {
        name: 'DotMac Customer Portal',
        version: process.env.NEXT_PUBLIC_APP_VERSION,
      },
    },
  },

  // Configure integrations
  integrations: [
    new Sentry.BrowserTracing({
      // Capture interactions and navigation
      routingInstrumentation: Sentry.nextRouterInstrumentation,
    }),
    new Sentry.Replay({
      // Mask all text and input content for privacy
      maskAllText: true,
      maskAllInputs: true,
      blockAllMedia: true,
    }),
  ],
});
