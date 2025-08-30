/**
 * Universal Audit System Hook
 * Leverages existing ErrorLoggingService patterns and provides portal-specific audit functionality
 */

'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useUniversalAuditService } from '../services/useUniversalAuditService';
import type {
  AuditEvent,
  AuditActivityItem,
  AuditFilters,
  AuditMetrics,
  ComplianceReport,
  PortalType,
  ActionCategory,
  ComplianceType,
  UseAuditSystemOptions,
  AuditSystemState,
  AuditSystemActions
} from '../types';

// Portal-specific compliance requirements
const portalComplianceRequirements: Record<PortalType, ComplianceType[]> = {
  admin: ['gdpr', 'sox', 'audit_trail', 'data_retention'],
  management: ['gdpr', 'sox', 'audit_trail', 'data_retention', 'financial'],
  reseller: ['gdpr', 'data_retention', 'financial'],
  customer: ['gdpr', 'data_retention'],
  technician: ['audit_trail', 'data_retention']
};

// Portal-specific action categories
const portalActionCategories: Record<PortalType, ActionCategory[]> = {
  admin: [
    'authentication',
    'customer_management',
    'billing_operations',
    'service_management',
    'network_operations',
    'configuration',
    'compliance',
    'system_admin',
    'communication',
    'reporting'
  ],
  management: [
    'authentication',
    'customer_management',
    'billing_operations',
    'service_management',
    'network_operations',
    'configuration',
    'compliance',
    'system_admin',
    'communication',
    'reporting'
  ],
  reseller: [
    'authentication',
    'customer_management',
    'billing_operations',
    'service_management',
    'communication',
    'reporting'
  ],
  customer: [
    'authentication',
    'billing_operations',
    'service_management',
    'communication'
  ],
  technician: [
    'authentication',
    'service_management',
    'network_operations',
    'communication'
  ]
};

export function useUniversalAudit(options: UseAuditSystemOptions) {
  const {
    portalType,
    userId,
    sessionId,
    enableAutoTracking = true,
    trackPageViews = true,
    trackUserActions = true,
    customCategories
  } = options;

  // Get universal audit service
  const auditService = useUniversalAuditService();

  // State management
  const [state, setState] = useState<AuditSystemState>({
    events: [],
    activities: [],
    metrics: null,
    isLoading: false,
    error: null,
    filters: {
      portalType,
      userId
    },
    config: auditService.getConfig()
  });

  // Portal-specific configuration
  const portalConfig = useMemo(() => ({
    compliance: portalComplianceRequirements[portalType],
    categories: customCategories || portalActionCategories[portalType]
  }), [portalType, customCategories]);

  // Error handling
  const handleError = useCallback((error: Error, context: string) => {
    console.error(`Audit system error in ${context}:`, error);
    setState(prev => ({
      ...prev,
      error: `${context}: ${error.message}`,
      isLoading: false
    }));
  }, []);

  // Log user action
  const logUserAction = useCallback(async (action: string, details: Partial<AuditEvent> = {}) => {
    try {
      const event: Partial<AuditEvent> = {
        action,
        portalType,
        userId,
        sessionId,
        actionCategory: details.actionCategory || 'system_admin',
        actionDescription: details.actionDescription || action,
        severity: details.severity || 'low',
        success: details.success !== false,
        timestamp: new Date(),
        complianceTypes: details.complianceTypes || portalConfig.compliance,
        ...details
      };

      await auditService.logEvent(event as AuditEvent);

      // Update local state
      setState(prev => ({
        ...prev,
        events: [event as AuditEvent, ...prev.events.slice(0, 99)]
      }));
    } catch (error) {
      handleError(error as Error, 'logUserAction');
    }
  }, [portalType, userId, sessionId, portalConfig.compliance, auditService, handleError]);

  // Log system event
  const logSystemEvent = useCallback(async (event: string, details: Partial<AuditEvent> = {}) => {
    await logUserAction(event, {
      ...details,
      actionCategory: 'system_admin',
      actionDescription: details.actionDescription || `System: ${event}`
    });
  }, [logUserAction]);

  // Log compliance event
  const logComplianceEvent = useCallback(async (type: ComplianceType, details: Partial<AuditEvent> = {}) => {
    await logUserAction(`compliance_${type}`, {
      ...details,
      actionCategory: 'compliance',
      complianceTypes: [type],
      severity: details.severity || 'medium',
      actionDescription: details.actionDescription || `Compliance event: ${type}`
    });
  }, [logUserAction]);

  // Get events with filters
  const getEvents = useCallback(async (filters?: AuditFilters) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const finalFilters = {
        ...state.filters,
        ...filters,
        portalType
      };

      const events = await auditService.getEvents(finalFilters);
      const activities = await auditService.getActivities(finalFilters);

      setState(prev => ({
        ...prev,
        events,
        activities,
        isLoading: false,
        filters: finalFilters
      }));

      return events;
    } catch (error) {
      handleError(error as Error, 'getEvents');
      return [];
    }
  }, [state.filters, portalType, auditService, handleError]);

  // Get activities
  const getActivities = useCallback(async (filters?: AuditFilters) => {
    try {
      const finalFilters = {
        ...state.filters,
        ...filters,
        portalType
      };

      const activities = await auditService.getActivities(finalFilters);

      setState(prev => ({
        ...prev,
        activities
      }));

      return activities;
    } catch (error) {
      handleError(error as Error, 'getActivities');
      return [];
    }
  }, [state.filters, portalType, auditService, handleError]);

  // Get metrics
  const getMetrics = useCallback(async (period?: { start: Date; end: Date }) => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      const metrics = await auditService.getMetrics(period);

      setState(prev => ({
        ...prev,
        metrics,
        isLoading: false
      }));

      return metrics;
    } catch (error) {
      handleError(error as Error, 'getMetrics');
      return null;
    }
  }, [auditService, handleError]);

  // Generate compliance report
  const generateComplianceReport = useCallback(async (type: ComplianceType, period: { start: Date; end: Date }) => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      const report = await auditService.generateComplianceReport(type, period);
      setState(prev => ({ ...prev, isLoading: false }));
      return report;
    } catch (error) {
      handleError(error as Error, 'generateComplianceReport');
      return null;
    }
  }, [auditService, handleError]);

  // Export audit trail
  const exportAuditTrail = useCallback(async (filters: AuditFilters, format: 'csv' | 'json' | 'pdf') => {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      const exportUrl = await auditService.exportAuditTrail(filters, format);
      setState(prev => ({ ...prev, isLoading: false }));

      // Trigger download
      if (typeof window !== 'undefined') {
        const link = document.createElement('a');
        link.href = exportUrl;
        link.download = `audit-trail-${Date.now()}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }

      return exportUrl;
    } catch (error) {
      handleError(error as Error, 'exportAuditTrail');
      return '';
    }
  }, [auditService, handleError]);

  // Subscribe to real-time events
  const subscribeToEvents = useCallback((callback: (event: AuditEvent) => void) => {
    return auditService.subscribeToEvents((event) => {
      // Only forward events relevant to this portal
      if (event.portalType === portalType) {
        setState(prev => ({
          ...prev,
          events: [event, ...prev.events.slice(0, 99)],
          activities: [
            {
              id: event.id,
              type: event.success ? 'user_action' : 'security_event',
              title: event.actionDescription,
              description: `${event.userName || 'System'} performed ${event.action}`,
              timestamp: event.timestamp,
              user: event.userName ? {
                id: event.userId,
                name: event.userName,
                email: event.userEmail,
                role: event.userRole
              } : undefined,
              auditEvent: event,
              complianceTypes: event.complianceTypes,
              severity: event.severity,
              category: event.actionCategory,
              priority: event.severity === 'critical' ? 'urgent' :
                       event.severity === 'high' ? 'high' :
                       event.severity === 'medium' ? 'medium' : 'low'
            },
            ...prev.activities.slice(0, 49)
          ]
        }));
        callback(event);
      }
    });
  }, [portalType, auditService]);

  // Set filters
  const setFilters = useCallback((newFilters: Partial<AuditFilters>) => {
    setState(prev => ({
      ...prev,
      filters: { ...prev.filters, ...newFilters }
    }));
  }, []);

  // Clear events
  const clearEvents = useCallback(async (olderThan?: Date) => {
    try {
      await auditService.clearEvents(olderThan);
      setState(prev => ({
        ...prev,
        events: olderThan ? prev.events.filter(e => e.timestamp > olderThan) : [],
        activities: olderThan ? prev.activities.filter(a => a.timestamp > olderThan) : []
      }));
    } catch (error) {
      handleError(error as Error, 'clearEvents');
    }
  }, [auditService, handleError]);

  // Update configuration
  const updateConfig = useCallback((newConfig: Partial<any>) => {
    auditService.updateConfig(newConfig);
    setState(prev => ({
      ...prev,
      config: auditService.getConfig()
    }));
  }, [auditService]);

  // Auto-tracking setup
  useEffect(() => {
    if (!enableAutoTracking) return;

    // Track page views
    if (trackPageViews) {
      logUserAction('page_view', {
        actionCategory: 'authentication',
        actionDescription: `Viewed ${portalType} portal page`,
        severity: 'low',
        requestUrl: typeof window !== 'undefined' ? window.location.pathname : undefined
      });
    }

    // Set up user action tracking
    if (trackUserActions && typeof window !== 'undefined') {
      const handleClick = (event: MouseEvent) => {
        const target = event.target as HTMLElement;
        if (target.tagName === 'BUTTON' || target.closest('button')) {
          const button = target.tagName === 'BUTTON' ? target : target.closest('button');
          const action = button?.getAttribute('data-audit-action') ||
                        button?.textContent?.trim() ||
                        'button_click';

          logUserAction(action, {
            actionCategory: 'configuration',
            actionDescription: `Clicked: ${action}`,
            severity: 'low'
          });
        }
      };

      document.addEventListener('click', handleClick);
      return () => document.removeEventListener('click', handleClick);
    }
  }, [enableAutoTracking, trackPageViews, trackUserActions, portalType, logUserAction]);

  // Initial data load
  useEffect(() => {
    getEvents();
    getMetrics();
  }, []);

  // Actions object
  const actions: AuditSystemActions = {
    logUserAction,
    logSystemEvent,
    logComplianceEvent,
    getEvents,
    getActivities,
    getMetrics,
    generateComplianceReport,
    exportAuditTrail,
    subscribeToEvents,
    setFilters,
    clearEvents,
    updateConfig
  };

  return {
    ...state,
    ...actions,
    portalConfig
  };
}

export default useUniversalAudit;
