/**
 * Universal Audit Service
 * Leverages existing ErrorLoggingService patterns for consistency
 * Provides centralized audit logging, activity tracking, and compliance
 */

import type {
  AuditEvent,
  AuditActivityItem,
  AuditMetrics,
  AuditFilters,
  ComplianceReport,
  UniversalAuditConfig,
  PortalType,
  ActionCategory,
  ComplianceType,
  AuditSeverity,
} from '../types';

// Integration with existing services
import { errorLogger } from '@dotmac/headless/src/services/ErrorLoggingService';

class UniversalAuditService {
  private config: UniversalAuditConfig;
  private eventBuffer: AuditEvent[] = [];
  private activityBuffer: AuditActivityItem[] = [];
  private metricsCache: AuditMetrics | null = null;
  private subscribers: Set<(event: AuditEvent) => void> = new Set();
  private flushTimer?: NodeJS.Timeout;

  constructor(config: Partial<UniversalAuditConfig> = {}) {
    this.config = {
      enabled: true,
      enableRealTime: true,
      batchSize: 50,
      flushInterval: 30000, // 30 seconds

      storage: {
        type: 'hybrid',
        encryption: true,
        compression: false,
        endpoints: {
          events: '/api/audit/events',
          metrics: '/api/audit/metrics',
          compliance: '/api/audit/compliance',
        },
      },

      portals: {
        admin: {
          portalType: 'admin',
          enabledCategories: [
            'authentication',
            'customer_management',
            'billing_operations',
            'system_admin',
            'configuration',
          ],
          requiredCompliance: ['audit_trail', 'data_retention', 'sox'],
          retentionPolicy: { defaultRetention: 2555 }, // 7 years for admin
          sensitiveDataHandling: {
            autoRedact: true,
            redactionFields: ['password', 'ssn', 'credit_card'],
            requiresApproval: true,
          },
          realTimeAlerts: {
            criticalActions: ['user_delete', 'data_export'],
            securityEvents: ['failed_login_attempts'],
            complianceViolations: ['gdpr_violation'],
          },
        },
        customer: {
          portalType: 'customer',
          enabledCategories: ['authentication', 'billing_operations', 'service_management'],
          requiredCompliance: ['gdpr', 'pci_dss', 'data_retention'],
          retentionPolicy: { defaultRetention: 730 }, // 2 years
          sensitiveDataHandling: {
            autoRedact: true,
            redactionFields: ['credit_card', 'bank_account'],
            requiresApproval: false,
          },
          realTimeAlerts: {
            criticalActions: ['payment_failure'],
            securityEvents: ['suspicious_login'],
            complianceViolations: ['gdpr_violation'],
          },
        },
        reseller: {
          portalType: 'reseller',
          enabledCategories: [
            'authentication',
            'customer_management',
            'billing_operations',
            'reporting',
          ],
          requiredCompliance: ['audit_trail', 'financial', 'data_retention'],
          retentionPolicy: { defaultRetention: 1825 }, // 5 years
          sensitiveDataHandling: {
            autoRedact: true,
            redactionFields: ['commission_rates', 'financial_data'],
            requiresApproval: true,
          },
          realTimeAlerts: {
            criticalActions: ['commission_change'],
            securityEvents: ['data_breach'],
            complianceViolations: ['financial_irregularity'],
          },
        },
        management: {
          portalType: 'management',
          enabledCategories: [
            'authentication',
            'customer_management',
            'billing_operations',
            'network_operations',
            'reporting',
          ],
          requiredCompliance: ['audit_trail', 'sox', 'iso27001', 'financial'],
          retentionPolicy: { defaultRetention: 2555 }, // 7 years
          sensitiveDataHandling: {
            autoRedact: true,
            redactionFields: ['financial_data', 'strategic_data'],
            requiresApproval: true,
          },
          realTimeAlerts: {
            criticalActions: ['financial_report'],
            securityEvents: ['privilege_escalation'],
            complianceViolations: ['sox_violation'],
          },
        },
        technician: {
          portalType: 'technician',
          enabledCategories: ['authentication', 'service_management', 'network_operations'],
          requiredCompliance: ['audit_trail', 'data_retention'],
          retentionPolicy: { defaultRetention: 365 }, // 1 year
          sensitiveDataHandling: {
            autoRedact: false,
            redactionFields: [],
            requiresApproval: false,
          },
          realTimeAlerts: {
            criticalActions: ['network_change'],
            securityEvents: ['unauthorized_access'],
            complianceViolations: [],
          },
        },
      },

      globalCompliance: ['audit_trail', 'data_retention'],

      performance: {
        maxEventsInMemory: 10000,
        indexingEnabled: true,
        searchOptimization: true,
      },

      notifications: {
        enableEmailAlerts: true,
        enableWebhooks: true,
        alertRecipients: [],
        webhookUrls: [],
      },

      ...config,
    };

    this.setupFlushTimer();
  }

  /**
   * Log user action with comprehensive context
   */
  async logUserAction(
    action: string,
    details: Partial<AuditEvent> & {
      portalType: PortalType;
      userId: string;
      actionCategory: ActionCategory;
    }
  ): Promise<void> {
    if (!this.config.enabled) return;

    const event: AuditEvent = {
      id: this.generateId(),
      timestamp: new Date(),
      correlationId: this.generateCorrelationId(),

      // User context (required)
      userId: details.userId,
      userEmail: details.userEmail,
      userName: details.userName,
      userRole: details.userRole,
      sessionId: details.sessionId || this.getCurrentSessionId(),

      // Portal context
      portalType: details.portalType,
      portalVersion: process.env.NEXT_PUBLIC_APP_VERSION,

      // Action details
      action,
      actionCategory: details.actionCategory,
      actionDescription:
        details.actionDescription || this.generateActionDescription(action, details.actionCategory),

      // Technical context
      ipAddress: await this.getClientIP(),
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
      requestUrl: typeof window !== 'undefined' ? window.location.href : undefined,
      duration: details.duration,

      // Compliance context
      complianceTypes: this.determineComplianceTypes(details.portalType, details.actionCategory),
      severity: details.severity || this.determineSeverity(action, details.actionCategory),
      sensitiveData: details.sensitiveData || this.containsSensitiveData(details),
      dataClassification: details.dataClassification || 'internal',

      // Success tracking
      success: details.success !== false, // Default to true unless explicitly false
      errorCode: details.errorCode,
      errorMessage: details.errorMessage,
      customerImpact: details.customerImpact || 'none',

      // State tracking for critical changes
      beforeState: details.beforeState,
      afterState: details.afterState,
      changedFields: details.changedFields,

      // Additional context
      resourceType: details.resourceType,
      resourceId: details.resourceId,
      resourceName: details.resourceName,
      businessProcess: details.businessProcess,
      workflowStep: details.workflowStep,
      metadata: details.metadata,
      tags: details.tags,

      // Retention
      retentionPeriod: this.getRetentionPeriod(details.portalType, details.actionCategory),
      isImmutable: this.isImmutableEvent(action, details.actionCategory),
    };

    // Add to buffer
    this.eventBuffer.push(event);

    // Create activity item for UI display
    const activity = this.createActivityItem(event);
    this.activityBuffer.push(activity);

    // Real-time notifications
    if (this.config.enableRealTime) {
      this.notifySubscribers(event);
    }

    // Handle critical events immediately
    if (event.severity === 'critical' || this.isCriticalAction(action)) {
      await this.flushEvents();
      await this.sendRealTimeAlert(event);
    }

    // Integrate with existing error logging for failures
    if (!event.success && event.errorCode) {
      this.integrateWithErrorLogging(event);
    }
  }

  /**
   * Log system event (automated operations)
   */
  async logSystemEvent(
    event: string,
    details: Partial<AuditEvent> & {
      portalType: PortalType;
      actionCategory: ActionCategory;
    }
  ): Promise<void> {
    return this.logUserAction(event, {
      ...details,
      userId: 'system',
      userName: 'System',
      userRole: 'system',
      actionDescription: details.actionDescription || `System ${event}`,
    });
  }

  /**
   * Log compliance-specific event
   */
  async logComplianceEvent(
    type: ComplianceType,
    details: Partial<AuditEvent> & {
      portalType: PortalType;
      userId: string;
    }
  ): Promise<void> {
    const action = `compliance_${type}`;
    return this.logUserAction(action, {
      ...details,
      actionCategory: 'compliance',
      complianceTypes: [type, ...this.config.globalCompliance],
      severity: 'high',
      isImmutable: true,
      dataClassification: 'restricted',
    });
  }

  /**
   * Get events with filtering
   */
  async getEvents(filters: AuditFilters = {}): Promise<AuditEvent[]> {
    let events = [...this.eventBuffer];

    // Apply filters
    if (filters.dateFrom) {
      events = events.filter((e) => e.timestamp >= filters.dateFrom!);
    }

    if (filters.dateTo) {
      events = events.filter((e) => e.timestamp <= filters.dateTo!);
    }

    if (filters.userId) {
      events = events.filter((e) => e.userId === filters.userId);
    }

    if (filters.portalType) {
      const portals = Array.isArray(filters.portalType) ? filters.portalType : [filters.portalType];
      events = events.filter((e) => portals.includes(e.portalType));
    }

    if (filters.actionCategory) {
      const categories = Array.isArray(filters.actionCategory)
        ? filters.actionCategory
        : [filters.actionCategory];
      events = events.filter((e) => categories.includes(e.actionCategory));
    }

    if (filters.severity) {
      const severities = Array.isArray(filters.severity) ? filters.severity : [filters.severity];
      events = events.filter((e) => severities.includes(e.severity));
    }

    if (filters.success !== undefined) {
      events = events.filter((e) => e.success === filters.success);
    }

    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      events = events.filter(
        (e) =>
          e.action.toLowerCase().includes(query) ||
          e.actionDescription.toLowerCase().includes(query) ||
          e.userName?.toLowerCase().includes(query) ||
          e.resourceType?.toLowerCase().includes(query)
      );
    }

    return events.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }

  /**
   * Get activity items for UI display
   */
  async getActivities(filters: AuditFilters = {}): Promise<AuditActivityItem[]> {
    const events = await this.getEvents(filters);
    return events.map((event) => this.createActivityItem(event));
  }

  /**
   * Get audit metrics
   */
  async getMetrics(period?: { start: Date; end: Date }): Promise<AuditMetrics> {
    const events = period
      ? await this.getEvents({ dateFrom: period.start, dateTo: period.end })
      : this.eventBuffer;

    const now = new Date();
    const periodStart = period?.start || new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const eventsThisPeriod = events.filter((e) => e.timestamp >= periodStart);

    // Calculate metrics
    const eventsByCategory = this.groupBy(events, 'actionCategory') as Record<
      ActionCategory,
      number
    >;
    const eventsByPortal = this.groupBy(events, 'portalType') as Record<PortalType, number>;
    const eventsBySeverity = this.groupBy(events, 'severity') as Record<AuditSeverity, number>;

    const complianceEvents: Record<ComplianceType, number> = {};
    events.forEach((event) => {
      event.complianceTypes?.forEach((type) => {
        complianceEvents[type] = (complianceEvents[type] || 0) + 1;
      });
    });

    const failedEvents = events.filter((e) => !e.success);
    const userEventCounts = this.groupBy(events, 'userId');
    const topUsers = Object.entries(userEventCounts)
      .map(([userId, count]) => {
        const event = events.find((e) => e.userId === userId);
        return {
          userId,
          userName: event?.userName || 'Unknown',
          eventCount: count,
        };
      })
      .sort((a, b) => b.eventCount - a.eventCount)
      .slice(0, 10);

    return {
      totalEvents: events.length,
      eventsThisPeriod: eventsThisPeriod.length,
      eventsByCategory,
      eventsByPortal,
      eventsBySeverity,
      complianceEvents,
      failureRate: events.length > 0 ? (failedEvents.length / events.length) * 100 : 0,
      averageSessionDuration: this.calculateAverageSessionDuration(events),
      topUsers,
      suspiciousActivities: this.detectSuspiciousActivities(events),

      trends: {
        eventGrowth: this.calculateGrowthRate(events, period),
        failureRateChange: this.calculateFailureRateChange(events, period),
        complianceEventChange: this.calculateComplianceEventChange(events, period),
      },
    };
  }

  /**
   * Generate compliance report
   */
  async generateComplianceReport(
    type: ComplianceType,
    period: { start: Date; end: Date }
  ): Promise<ComplianceReport> {
    const events = await this.getEvents({
      dateFrom: period.start,
      dateTo: period.end,
      complianceType: type,
    });

    const complianceEvents = events.filter((e) => e.complianceTypes?.includes(type));
    const violations = complianceEvents.filter((e) => e.tags?.includes('violation'));

    return {
      id: this.generateId(),
      reportType: type,
      generatedAt: new Date(),
      generatedBy: 'System', // Could be enhanced with current user
      period,

      summary: {
        totalEvents: events.length,
        complianceEvents: complianceEvents.length,
        violations: violations.length,
        risksIdentified: this.identifyComplianceRisks(complianceEvents, type),
      },

      sections: [
        {
          title: 'Executive Summary',
          content: this.generateExecutiveSummary(type, complianceEvents, violations),
          events: violations.slice(0, 10), // Top violations
        },
        {
          title: 'Detailed Event Analysis',
          content: this.generateDetailedAnalysis(complianceEvents),
          events: complianceEvents,
          recommendations: this.generateRecommendations(type, violations),
        },
      ],
    };
  }

  /**
   * Subscribe to real-time events
   */
  subscribeToEvents(callback: (event: AuditEvent) => void): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  // Private helper methods
  private createActivityItem(event: AuditEvent): AuditActivityItem {
    return {
      id: event.id,
      type: event.userId === 'system' ? 'system_event' : 'user_action',
      title: event.action.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
      description: event.actionDescription,
      timestamp: event.timestamp,

      user:
        event.userId !== 'system'
          ? {
              id: event.userId,
              name: event.userName || 'Unknown User',
              email: event.userEmail,
              role: event.userRole,
            }
          : undefined,

      auditEvent: event,
      complianceTypes: event.complianceTypes,
      severity: event.severity,
      category: event.actionCategory,

      priority: this.severityToPriority(event.severity),
      color: this.getCategoryColor(event.actionCategory),
    };
  }

  private notifySubscribers(event: AuditEvent): void {
    this.subscribers.forEach((callback) => {
      try {
        callback(event);
      } catch (error) {
        console.warn('Error in audit event subscriber:', error);
      }
    });
  }

  private async flushEvents(): Promise<void> {
    if (this.eventBuffer.length === 0) return;

    const eventsToFlush = [...this.eventBuffer];
    this.eventBuffer = [];

    try {
      if (this.config.storage.endpoints?.events) {
        await this.sendEventsToEndpoint(eventsToFlush);
      }
    } catch (error) {
      // Put events back in buffer on failure
      this.eventBuffer.unshift(...eventsToFlush);
      console.error('Failed to flush audit events:', error);
    }
  }

  private setupFlushTimer(): void {
    this.flushTimer = setInterval(() => {
      if (this.eventBuffer.length >= this.config.batchSize) {
        this.flushEvents();
      }
    }, this.config.flushInterval);
  }

  // Utility methods leveraging existing patterns
  private generateId(): string {
    return `audit_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateCorrelationId(): string {
    return `corr_${Date.now()}_${Math.random().toString(16).substr(2, 8)}`;
  }

  private getCurrentSessionId(): string {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      let sessionId = window.sessionStorage.getItem('audit_session_id');
      if (!sessionId) {
        sessionId = this.generateId();
        window.sessionStorage.setItem('audit_session_id', sessionId);
      }
      return sessionId;
    }
    return 'unknown_session';
  }

  private async getClientIP(): Promise<string> {
    // Implementation depends on your infrastructure
    return 'unknown';
  }

  private determineComplianceTypes(
    portalType: PortalType,
    category: ActionCategory
  ): ComplianceType[] {
    const portalConfig = this.config.portals[portalType];
    const complianceTypes = [...portalConfig.requiredCompliance];

    // Add category-specific compliance
    if (category === 'billing_operations') {
      complianceTypes.push('pci_dss', 'financial');
    }

    if (category === 'customer_management') {
      complianceTypes.push('gdpr');
    }

    return [...new Set([...complianceTypes, ...this.config.globalCompliance])];
  }

  private determineSeverity(action: string, category: ActionCategory): AuditSeverity {
    const criticalActions = ['user_delete', 'data_export', 'privilege_escalation', 'payment_fraud'];
    const highActions = ['password_change', 'permission_change', 'financial_transaction'];

    if (criticalActions.some((a) => action.includes(a))) return 'critical';
    if (highActions.some((a) => action.includes(a))) return 'high';
    if (category === 'authentication' || category === 'compliance') return 'medium';

    return 'low';
  }

  private containsSensitiveData(details: Partial<AuditEvent>): boolean {
    const sensitiveFields = ['password', 'ssn', 'credit_card', 'bank_account'];
    const dataStr = JSON.stringify(details).toLowerCase();
    return sensitiveFields.some((field) => dataStr.includes(field));
  }

  private getRetentionPeriod(portalType: PortalType, category: ActionCategory): number {
    const portalConfig = this.config.portals[portalType];
    return (
      portalConfig.retentionPolicy.categoryRetention?.[category] ||
      portalConfig.retentionPolicy.defaultRetention
    );
  }

  private isImmutableEvent(action: string, category: ActionCategory): boolean {
    return (
      category === 'compliance' ||
      action.includes('financial') ||
      action.includes('legal') ||
      action.includes('audit')
    );
  }

  private isCriticalAction(action: string): boolean {
    const criticalActions = ['user_delete', 'data_export', 'system_shutdown', 'security_breach'];
    return criticalActions.some((a) => action.includes(a));
  }

  private integrateWithErrorLogging(event: AuditEvent): void {
    // Integrate with existing ErrorLoggingService
    if (event.errorCode && event.errorMessage) {
      console.warn('Audit event with error:', {
        auditId: event.id,
        errorCode: event.errorCode,
        errorMessage: event.errorMessage,
        context: event.metadata,
      });
    }
  }

  private async sendRealTimeAlert(event: AuditEvent): Promise<void> {
    const portalConfig = this.config.portals[event.portalType];

    if (portalConfig.realTimeAlerts.criticalActions.some((a) => event.action.includes(a))) {
      // Send critical action alert
      console.warn('🚨 Critical audit event:', event);
    }
  }

  private async sendEventsToEndpoint(events: AuditEvent[]): Promise<void> {
    if (!this.config.storage.endpoints?.events) return;

    const response = await fetch(this.config.storage.endpoints.events, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events }),
    });

    if (!response.ok) {
      throw new Error(`Failed to send audit events: ${response.status}`);
    }
  }

  // Helper methods for metrics and reporting
  private groupBy<T>(array: T[], key: keyof T): Record<string, number> {
    return array.reduce(
      (groups, item) => {
        const groupKey = String(item[key]);
        groups[groupKey] = (groups[groupKey] || 0) + 1;
        return groups;
      },
      {} as Record<string, number>
    );
  }

  private calculateAverageSessionDuration(events: AuditEvent[]): number {
    // Implementation for session duration calculation
    return 0; // Placeholder
  }

  private detectSuspiciousActivities(events: AuditEvent[]): number {
    // Implementation for suspicious activity detection
    return events.filter((e) => e.tags?.includes('suspicious')).length;
  }

  private calculateGrowthRate(events: AuditEvent[], period?: { start: Date; end: Date }): number {
    // Implementation for growth rate calculation
    return 0; // Placeholder
  }

  private calculateFailureRateChange(
    events: AuditEvent[],
    period?: { start: Date; end: Date }
  ): number {
    // Implementation for failure rate change calculation
    return 0; // Placeholder
  }

  private calculateComplianceEventChange(
    events: AuditEvent[],
    period?: { start: Date; end: Date }
  ): number {
    // Implementation for compliance event change calculation
    return 0; // Placeholder
  }

  private identifyComplianceRisks(events: AuditEvent[], type: ComplianceType): number {
    // Implementation for compliance risk identification
    return events.filter((e) => e.severity === 'high' || e.severity === 'critical').length;
  }

  private generateExecutiveSummary(
    type: ComplianceType,
    events: AuditEvent[],
    violations: AuditEvent[]
  ): string {
    return `Compliance report for ${type} covering ${events.length} events with ${violations.length} violations identified.`;
  }

  private generateDetailedAnalysis(events: AuditEvent[]): string {
    return `Detailed analysis of ${events.length} compliance-related events.`;
  }

  private generateRecommendations(type: ComplianceType, violations: AuditEvent[]): string[] {
    return violations.length > 0
      ? [`Address ${violations.length} compliance violations immediately`]
      : ['No immediate actions required'];
  }

  private generateActionDescription(action: string, category: ActionCategory): string {
    return `${category.replace(/_/g, ' ')} - ${action.replace(/_/g, ' ')}`;
  }

  private severityToPriority(severity: AuditSeverity): 'low' | 'medium' | 'high' | 'urgent' {
    const mapping: Record<AuditSeverity, 'low' | 'medium' | 'high' | 'urgent'> = {
      low: 'low',
      medium: 'medium',
      high: 'high',
      critical: 'urgent',
    };
    return mapping[severity];
  }

  private getCategoryColor(category: ActionCategory): string {
    const colors: Record<ActionCategory, string> = {
      authentication: 'blue',
      customer_management: 'green',
      billing_operations: 'purple',
      service_management: 'orange',
      network_operations: 'red',
      configuration: 'gray',
      compliance: 'yellow',
      system_admin: 'indigo',
      communication: 'pink',
      reporting: 'cyan',
    };
    return colors[category] || 'gray';
  }
}

// Singleton instance
export const auditService = new UniversalAuditService();

// Named and default exports
export { UniversalAuditService };
export default UniversalAuditService;
