/**
 * Universal Audit & Activity System Types
 * Leverages existing ErrorLoggingService and ActivityFeed patterns
 */

import type { ErrorLogEntry } from '@dotmac/headless/src/services/ErrorLoggingService';

// Portal context for audit events
export type PortalType = 'admin' | 'customer' | 'reseller' | 'management' | 'technician';

// User action categories following existing patterns
export type ActionCategory =
  | 'authentication'     // Login, logout, password reset
  | 'customer_management' // Customer operations
  | 'billing_operations' // Payment, invoicing, billing changes
  | 'service_management' // Service modifications, troubleshooting
  | 'network_operations' // Network configuration, monitoring
  | 'configuration'      // Settings changes
  | 'compliance'         // Audit, regulatory actions
  | 'system_admin'       // System-level operations
  | 'communication'      // Notifications, messages
  | 'reporting';         // Report generation, data export

// Compliance requirements
export type ComplianceType =
  | 'gdpr'          // GDPR data protection
  | 'pci_dss'       // Payment card industry
  | 'sox'           // Sarbanes-Oxley
  | 'hipaa'         // Healthcare (if applicable)
  | 'iso27001'      // Information security
  | 'data_retention' // Data retention policies
  | 'audit_trail'   // General audit requirements
  | 'financial';    // Financial regulations

// Audit event severity
export type AuditSeverity = 'low' | 'medium' | 'high' | 'critical';

// Core audit event interface extending existing patterns
export interface AuditEvent {
  // Core identification
  id: string;
  timestamp: Date;
  correlationId?: string;
  traceId?: string;

  // User context
  userId: string;
  userEmail?: string;
  userName?: string;
  userRole?: string;
  sessionId?: string;

  // Portal context
  portalType: PortalType;
  portalVersion?: string;

  // Action details
  action: string;                    // 'user_login', 'payment_processed', 'customer_created'
  actionCategory: ActionCategory;
  actionDescription: string;         // Human-readable description

  // Resource context
  resourceType?: string;             // 'customer', 'invoice', 'service_plan'
  resourceId?: string;               // ID of affected resource
  resourceName?: string;             // Name/description of resource

  // Business context
  businessProcess?: string;          // 'customer_onboarding', 'monthly_billing'
  workflowStep?: string;            // Current step in workflow

  // Technical context
  ipAddress?: string;
  userAgent?: string;
  requestUrl?: string;
  httpMethod?: string;
  httpStatus?: number;
  duration?: number;                // Operation duration in ms

  // Compliance & Security
  complianceTypes?: ComplianceType[];
  severity: AuditSeverity;
  sensitiveData?: boolean;          // Contains PII or sensitive info
  dataClassification?: 'public' | 'internal' | 'confidential' | 'restricted';

  // Before/after state for critical changes
  beforeState?: Record<string, any>;
  afterState?: Record<string, any>;
  changedFields?: string[];

  // Additional context
  metadata?: Record<string, any>;
  tags?: string[];

  // Success/failure context
  success: boolean;
  errorCode?: string;
  errorMessage?: string;

  // Customer impact (leveraging existing ErrorLoggingService pattern)
  customerImpact?: 'none' | 'low' | 'medium' | 'high' | 'critical';

  // Compliance retention
  retentionPeriod?: number;         // Days to retain this event
  isImmutable?: boolean;            // Cannot be deleted/modified
}

// Activity item extending existing UniversalActivityFeed
export interface AuditActivityItem {
  id: string;
  type: 'user_action' | 'system_event' | 'compliance_event' | 'security_event';
  title: string;
  description: string;
  timestamp: Date;

  // User info
  user?: {
    id: string;
    name: string;
    email?: string;
    role?: string;
    avatar?: string;
  };

  // Audit context
  auditEvent?: AuditEvent;
  complianceTypes?: ComplianceType[];
  severity: AuditSeverity;
  category: ActionCategory;

  // Visual indicators
  icon?: React.ComponentType<{ className?: string }>;
  color?: string;
  priority?: 'low' | 'medium' | 'high' | 'urgent';

  // Interaction
  onClick?: () => void;
  actions?: AuditAction[];
}

export interface AuditAction {
  id: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'danger';
  requiresPermission?: string[];
}

// Audit filtering and search
export interface AuditFilters {
  dateFrom?: Date;
  dateTo?: Date;
  userId?: string;
  userRole?: string;
  portalType?: PortalType | PortalType[];
  actionCategory?: ActionCategory | ActionCategory[];
  complianceType?: ComplianceType | ComplianceType[];
  severity?: AuditSeverity | AuditSeverity[];
  success?: boolean;
  resourceType?: string;
  businessProcess?: string;
  searchQuery?: string;
  tags?: string[];
  customerImpact?: string[];
  sensitiveData?: boolean;
}

// Portal-specific audit configuration
export interface PortalAuditConfig {
  portalType: PortalType;
  enabledCategories: ActionCategory[];
  requiredCompliance: ComplianceType[];
  retentionPolicy: {
    defaultRetention: number;        // Default retention in days
    categoryRetention?: Partial<Record<ActionCategory, number>>;
    complianceRetention?: Partial<Record<ComplianceType, number>>;
  };
  sensitiveDataHandling: {
    autoRedact: boolean;
    redactionFields: string[];
    requiresApproval: boolean;
  };
  realTimeAlerts: {
    criticalActions: string[];
    securityEvents: string[];
    complianceViolations: string[];
  };
}

// Audit metrics and reporting
export interface AuditMetrics {
  totalEvents: number;
  eventsThisPeriod: number;
  eventsByCategory: Record<ActionCategory, number>;
  eventsByPortal: Record<PortalType, number>;
  eventsBySeverity: Record<AuditSeverity, number>;
  complianceEvents: Record<ComplianceType, number>;
  failureRate: number;
  averageSessionDuration: number;
  topUsers: Array<{ userId: string; userName: string; eventCount: number }>;
  suspiciousActivities: number;

  // Trends
  trends: {
    eventGrowth: number;           // Percentage change
    failureRateChange: number;
    complianceEventChange: number;
  };
}

// Compliance report structure
export interface ComplianceReport {
  id: string;
  reportType: ComplianceType;
  generatedAt: Date;
  generatedBy: string;
  period: {
    start: Date;
    end: Date;
  };

  // Report content
  summary: {
    totalEvents: number;
    complianceEvents: number;
    violations: number;
    risksIdentified: number;
  };

  // Detailed sections
  sections: Array<{
    title: string;
    content: string;
    events: AuditEvent[];
    recommendations?: string[];
  }>;

  // Attachments
  attachments?: Array<{
    name: string;
    type: string;
    url: string;
  }>;

  // Signatures and approvals
  approvals?: Array<{
    userId: string;
    userName: string;
    timestamp: Date;
    signature?: string;
  }>;
}

// Universal audit system configuration
export interface UniversalAuditConfig {
  // Core settings
  enabled: boolean;
  enableRealTime: boolean;
  batchSize: number;
  flushInterval: number;           // milliseconds

  // Storage and retention
  storage: {
    type: 'local' | 'remote' | 'hybrid';
    endpoints?: {
      events?: string;
      metrics?: string;
      compliance?: string;
    };
    encryption: boolean;
    compression: boolean;
  };

  // Portal configurations
  portals: Record<PortalType, PortalAuditConfig>;

  // Global compliance requirements
  globalCompliance: ComplianceType[];

  // Performance settings
  performance: {
    maxEventsInMemory: number;
    indexingEnabled: boolean;
    searchOptimization: boolean;
  };

  // Notifications and alerts
  notifications: {
    enableEmailAlerts: boolean;
    enableWebhooks: boolean;
    alertRecipients: string[];
    webhookUrls: string[];
  };
}

// Hook interfaces for portal-specific usage
export interface UseAuditSystemOptions {
  portalType: PortalType;
  userId?: string;
  sessionId?: string;
  enableAutoTracking?: boolean;
  trackPageViews?: boolean;
  trackUserActions?: boolean;
  customCategories?: ActionCategory[];
}

export interface AuditSystemState {
  events: AuditEvent[];
  activities: AuditActivityItem[];
  metrics: AuditMetrics | null;
  isLoading: boolean;
  error: string | null;
  filters: AuditFilters;
  config: UniversalAuditConfig;
}

export interface AuditSystemActions {
  // Event logging
  logUserAction: (action: string, details: Partial<AuditEvent>) => Promise<void>;
  logSystemEvent: (event: string, details: Partial<AuditEvent>) => Promise<void>;
  logComplianceEvent: (type: ComplianceType, details: Partial<AuditEvent>) => Promise<void>;

  // Data retrieval
  getEvents: (filters?: AuditFilters) => Promise<AuditEvent[]>;
  getActivities: (filters?: AuditFilters) => Promise<AuditActivityItem[]>;
  getMetrics: (period?: { start: Date; end: Date }) => Promise<AuditMetrics>;

  // Compliance
  generateComplianceReport: (type: ComplianceType, period: { start: Date; end: Date }) => Promise<ComplianceReport>;
  exportAuditTrail: (filters: AuditFilters, format: 'csv' | 'json' | 'pdf') => Promise<string>;

  // Real-time
  subscribeToEvents: (callback: (event: AuditEvent) => void) => () => void;

  // Management
  setFilters: (filters: Partial<AuditFilters>) => void;
  clearEvents: (olderThan?: Date) => Promise<void>;
  updateConfig: (config: Partial<UniversalAuditConfig>) => void;
}
