/**
 * Production-ready Sentry configuration package
 * Provides unified error tracking across all DotMac portals
 */

export { initializeSentry } from './client-config';
export { initializeSentryServer } from './server-config';
export { initializeSentryEdge } from './edge-config';
export { SentryErrorBoundary } from './error-boundary';
export { withSentryMonitoring } from './monitoring-wrapper';
export { captureUserFeedback, captureException, captureMessage } from './utils';
export type { SentryConfig, PortalType, ErrorSeverity, UserFeedbackData } from './types';

// Portal-specific configurations
export const PORTAL_CONFIGS = {
  customer: {
    component: 'customer-portal',
    name: 'DotMac Customer Portal',
    enableReplay: true,
    enableProfiling: true,
  },
  admin: {
    component: 'admin-portal',
    name: 'DotMac Admin Portal',
    enableReplay: true,
    enableProfiling: false,
  },
  reseller: {
    component: 'reseller-portal',
    name: 'DotMac Reseller Portal',
    enableReplay: true,
    enableProfiling: false,
  },
  technician: {
    component: 'technician-portal',
    name: 'DotMac Technician Portal',
    enableReplay: false,
    enableProfiling: false,
  },
  'management-admin': {
    component: 'management-admin-portal',
    name: 'DotMac Management Admin Portal',
    enableReplay: true,
    enableProfiling: true,
  },
  'management-reseller': {
    component: 'management-reseller-portal',
    name: 'DotMac Management Reseller Portal',
    enableReplay: true,
    enableProfiling: false,
  },
  'tenant-portal': {
    component: 'tenant-portal',
    name: 'DotMac Tenant Portal',
    enableReplay: true,
    enableProfiling: false,
  },
} as const;
