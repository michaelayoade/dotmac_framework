import type { BrowserOptions } from '@sentry/nextjs';

export type PortalType =
  | 'customer'
  | 'admin'
  | 'reseller'
  | 'technician'
  | 'management-admin'
  | 'management-reseller'
  | 'tenant-portal';

export type ErrorSeverity = 'fatal' | 'error' | 'warning' | 'info' | 'debug';

export interface SentryConfig extends Partial<BrowserOptions> {
  portalType: PortalType;
  enableReplay?: boolean;
  enableProfiling?: boolean;
  customTags?: Record<string, string>;
  customContext?: Record<string, any>;
}

export interface UserFeedbackData {
  name?: string;
  email?: string;
  comments: string;
  eventId?: string;
}

export interface MonitoringMetrics {
  renderTime: number;
  interactionTime: number;
  memoryUsage: number;
  errorCount: number;
  userSatisfaction?: number;
}

export interface ErrorContext {
  userId?: string;
  tenantId?: string;
  portalType: PortalType;
  route?: string;
  userAgent?: string;
  timestamp: number;
  severity: ErrorSeverity;
  additional?: Record<string, any>;
}
