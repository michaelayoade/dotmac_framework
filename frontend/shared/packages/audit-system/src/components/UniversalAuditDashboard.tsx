/**
 * Universal Audit Dashboard
 * Leverages existing UniversalActivityFeed and creates comprehensive audit interface
 * Portal-agnostic with specific optimizations for each portal type
 */

'use client';

import React, { useState, useMemo } from 'react';
import {
  Shield,
  Activity,
  AlertTriangle,
  FileText,
  Settings,
  Download,
  Filter,
  Search,
  Users,
  Clock,
  TrendingUp,
  Calendar,
  ChevronDown,
} from 'lucide-react';

import { UniversalActivityFeed } from '@dotmac/primitives/src/dashboard/UniversalActivityFeed';
import type {
  AuditEvent,
  AuditActivityItem,
  AuditFilters,
  AuditMetrics,
  PortalType,
  ActionCategory,
  ComplianceType,
  AuditSeverity,
} from '../types';

import { useUniversalAudit } from '../hooks/useUniversalAudit';

interface UniversalAuditDashboardProps {
  portalType: PortalType;
  userId?: string;
  className?: string;

  // Display options
  enableRealTime?: boolean;
  showCompliancePanel?: boolean;
  showMetricsOverview?: boolean;
  compactMode?: boolean;

  // Feature flags per portal
  features?: {
    eventFiltering?: boolean;
    complianceReports?: boolean;
    eventExport?: boolean;
    realTimeAlerts?: boolean;
    auditTrail?: boolean;
    userTracking?: boolean;
    systemEvents?: boolean;
  };

  // Customization
  customCategories?: ActionCategory[];
  customFilters?: Partial<AuditFilters>;
  onEventClick?: (event: AuditEvent) => void;
}

type TabType = 'activity' | 'events' | 'compliance' | 'metrics' | 'reports';

const portalFeatures: Record<PortalType, UniversalAuditDashboardProps['features']> = {
  admin: {
    eventFiltering: true,
    complianceReports: true,
    eventExport: true,
    realTimeAlerts: true,
    auditTrail: true,
    userTracking: true,
    systemEvents: true,
  },
  management: {
    eventFiltering: true,
    complianceReports: true,
    eventExport: true,
    realTimeAlerts: true,
    auditTrail: true,
    userTracking: true,
    systemEvents: true,
  },
  reseller: {
    eventFiltering: true,
    complianceReports: false,
    eventExport: true,
    realTimeAlerts: true,
    auditTrail: true,
    userTracking: false,
    systemEvents: false,
  },
  customer: {
    eventFiltering: false,
    complianceReports: false,
    eventExport: false,
    realTimeAlerts: false,
    auditTrail: true,
    userTracking: false,
    systemEvents: false,
  },
  technician: {
    eventFiltering: true,
    complianceReports: false,
    eventExport: false,
    realTimeAlerts: true,
    auditTrail: true,
    userTracking: false,
    systemEvents: true,
  },
};

export function UniversalAuditDashboard({
  portalType,
  userId,
  className = '',
  enableRealTime = true,
  showCompliancePanel = true,
  showMetricsOverview = true,
  compactMode = false,
  features,
  customCategories,
  customFilters,
  onEventClick,
}: UniversalAuditDashboardProps) {
  const [activeTab, setActiveTab] = useState<TabType>('activity');
  const [showFilters, setShowFilters] = useState(false);
  const [dateRange, setDateRange] = useState<{ start: Date; end: Date }>({
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
    end: new Date(),
  });

  // Get portal-specific features
  const portalConfig = useMemo(() => {
    return { ...portalFeatures[portalType], ...features };
  }, [portalType, features]);

  // Use universal audit hook with portal-specific configuration
  const {
    events,
    activities,
    metrics,
    isLoading,
    error,
    filters,
    logUserAction,
    getEvents,
    getMetrics,
    generateComplianceReport,
    exportAuditTrail,
    setFilters,
    subscribeToEvents,
  } = useUniversalAudit({
    portalType,
    userId,
    enableAutoTracking: enableRealTime,
    trackPageViews: true,
    trackUserActions: true,
    customCategories,
  });

  // Portal-specific tab configuration
  const availableTabs = useMemo(() => {
    const tabs = [{ id: 'activity', label: 'Activity Feed', icon: Activity }];

    if (portalConfig.auditTrail) {
      tabs.push({ id: 'events', label: 'Audit Events', icon: FileText });
    }

    if (portalConfig.complianceReports) {
      tabs.push({ id: 'compliance', label: 'Compliance', icon: Shield });
    }

    if (showMetricsOverview) {
      tabs.push({ id: 'metrics', label: 'Metrics', icon: TrendingUp });
    }

    if (portalConfig.eventExport) {
      tabs.push({ id: 'reports', label: 'Reports', icon: Download });
    }

    return tabs;
  }, [portalConfig, showMetricsOverview]);

  // Convert audit events to activity items for the feed
  const activityItems = useMemo(() => {
    return activities.map((activity) => ({
      ...activity,
      type: activity.type as
        | 'user_action'
        | 'system_event'
        | 'error'
        | 'success'
        | 'info'
        | 'warning',
      onClick: () => onEventClick?.(activity.auditEvent!),
    }));
  }, [activities, onEventClick]);

  // Metrics summary cards
  const renderMetricsOverview = () => {
    if (!metrics || !showMetricsOverview) return null;

    const cards = [
      {
        title: 'Total Events',
        value: metrics.totalEvents.toLocaleString(),
        change: `+${metrics.eventsThisPeriod}`,
        trend: metrics.trends.eventGrowth >= 0 ? 'up' : 'down',
        color: 'blue',
      },
      {
        title: 'Success Rate',
        value: `${(100 - metrics.failureRate).toFixed(1)}%`,
        change: `${metrics.trends.failureRateChange >= 0 ? '+' : ''}${metrics.trends.failureRateChange.toFixed(1)}%`,
        trend: metrics.trends.failureRateChange <= 0 ? 'up' : 'down',
        color: 'green',
      },
      {
        title: 'Compliance Events',
        value: Object.values(metrics.complianceEvents)
          .reduce((a, b) => a + b, 0)
          .toString(),
        change: `${metrics.trends.complianceEventChange >= 0 ? '+' : ''}${metrics.trends.complianceEventChange}`,
        trend: metrics.trends.complianceEventChange >= 0 ? 'up' : 'down',
        color: 'purple',
      },
      {
        title: 'Suspicious Activities',
        value: metrics.suspiciousActivities.toString(),
        change: '0',
        trend: 'stable',
        color: metrics.suspiciousActivities > 0 ? 'red' : 'gray',
      },
    ];

    return (
      <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6'>
        {cards.map((card, index) => (
          <div key={index} className={`bg-white rounded-lg p-4 border border-${card.color}-100`}>
            <div className='flex items-center justify-between'>
              <div>
                <p className='text-sm font-medium text-gray-600'>{card.title}</p>
                <p className='text-2xl font-bold text-gray-900'>{card.value}</p>
              </div>
              <div
                className={`text-sm ${card.trend === 'up' ? 'text-green-600' : card.trend === 'down' ? 'text-red-600' : 'text-gray-500'}`}
              >
                {card.change}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  // Activity tab content
  const renderActivityTab = () => (
    <UniversalActivityFeed
      activities={activityItems}
      title={`${portalType.charAt(0).toUpperCase() + portalType.slice(1)} Activity`}
      isLive={enableRealTime}
      showTimestamps={true}
      showAvatars={portalConfig.userTracking}
      showCategories={true}
      allowFiltering={portalConfig.eventFiltering}
      categories={customCategories || Object.values(metrics?.eventsByCategory || {})}
      maxItems={compactMode ? 10 : undefined}
      variant={compactMode ? 'compact' : 'default'}
      onRefresh={() => getEvents()}
      className='bg-white rounded-lg shadow-sm'
    />
  );

  // Audit events tab content
  const renderEventsTab = () => (
    <div className='bg-white rounded-lg shadow-sm'>
      <div className='p-4 border-b border-gray-200'>
        <div className='flex items-center justify-between'>
          <h3 className='font-semibold text-gray-900'>Audit Events</h3>
          <div className='flex items-center space-x-2'>
            {portalConfig.eventFiltering && (
              <button
                onClick={() => setShowFilters(!showFilters)}
                className='flex items-center space-x-1 px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50'
              >
                <Filter className='w-4 h-4' />
                <span>Filters</span>
                <ChevronDown
                  className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`}
                />
              </button>
            )}
            {portalConfig.eventExport && (
              <button
                onClick={() => exportAuditTrail(filters, 'csv')}
                className='flex items-center space-x-1 px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700'
              >
                <Download className='w-4 h-4' />
                <span>Export</span>
              </button>
            )}
          </div>
        </div>

        {showFilters && portalConfig.eventFiltering && (
          <div className='mt-4 p-4 bg-gray-50 rounded-lg'>
            <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Date Range</label>
                <input
                  type='date'
                  value={dateRange.start.toISOString().split('T')[0]}
                  onChange={(e) =>
                    setDateRange({
                      ...dateRange,
                      start: new Date(e.target.value),
                    })
                  }
                  className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm'
                />
              </div>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Category</label>
                <select
                  value={filters.actionCategory || ''}
                  onChange={(e) =>
                    setFilters({
                      ...filters,
                      actionCategory: (e.target.value as ActionCategory) || undefined,
                    })
                  }
                  className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm'
                >
                  <option value=''>All Categories</option>
                  <option value='authentication'>Authentication</option>
                  <option value='customer_management'>Customer Management</option>
                  <option value='billing_operations'>Billing Operations</option>
                  <option value='service_management'>Service Management</option>
                  <option value='network_operations'>Network Operations</option>
                  <option value='configuration'>Configuration</option>
                  <option value='compliance'>Compliance</option>
                </select>
              </div>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Severity</label>
                <select
                  value={filters.severity || ''}
                  onChange={(e) =>
                    setFilters({
                      ...filters,
                      severity: (e.target.value as AuditSeverity) || undefined,
                    })
                  }
                  className='w-full px-3 py-2 border border-gray-300 rounded-md text-sm'
                >
                  <option value=''>All Severities</option>
                  <option value='low'>Low</option>
                  <option value='medium'>Medium</option>
                  <option value='high'>High</option>
                  <option value='critical'>Critical</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className='max-h-96 overflow-y-auto'>
        {isLoading ? (
          <div className='p-8 text-center'>
            <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto'></div>
            <p className='mt-2 text-sm text-gray-500'>Loading audit events...</p>
          </div>
        ) : events.length === 0 ? (
          <div className='p-8 text-center text-gray-500'>
            <FileText className='w-8 h-8 mx-auto mb-2 text-gray-400' />
            <p>No audit events found</p>
          </div>
        ) : (
          <div className='divide-y divide-gray-100'>
            {events.slice(0, compactMode ? 20 : 100).map((event) => (
              <div
                key={event.id}
                className='p-4 hover:bg-gray-50 cursor-pointer'
                onClick={() => onEventClick?.(event)}
              >
                <div className='flex items-start space-x-3'>
                  <div
                    className={`p-1 rounded-full ${
                      event.severity === 'critical'
                        ? 'bg-red-100'
                        : event.severity === 'high'
                          ? 'bg-yellow-100'
                          : event.severity === 'medium'
                            ? 'bg-blue-100'
                            : 'bg-gray-100'
                    }`}
                  >
                    <div
                      className={`w-2 h-2 rounded-full ${
                        event.severity === 'critical'
                          ? 'bg-red-600'
                          : event.severity === 'high'
                            ? 'bg-yellow-600'
                            : event.severity === 'medium'
                              ? 'bg-blue-600'
                              : 'bg-gray-600'
                      }`}
                    />
                  </div>

                  <div className='flex-1 min-w-0'>
                    <div className='flex items-center justify-between'>
                      <p className='text-sm font-medium text-gray-900'>{event.actionDescription}</p>
                      <span className='text-xs text-gray-500'>
                        {event.timestamp.toLocaleTimeString()}
                      </span>
                    </div>

                    <div className='mt-1 flex items-center space-x-4 text-xs text-gray-500'>
                      <span>{event.userName || 'System'}</span>
                      <span>{event.actionCategory.replace(/_/g, ' ')}</span>
                      {event.resourceType && <span>{event.resourceType}</span>}
                      {!event.success && <span className='text-red-600 font-medium'>Failed</span>}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  // Compliance tab content
  const renderComplianceTab = () => (
    <div className='space-y-6'>
      <div className='bg-white rounded-lg shadow-sm p-6'>
        <h3 className='font-semibold text-gray-900 mb-4'>Compliance Overview</h3>

        {metrics && (
          <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'>
            {Object.entries(metrics.complianceEvents).map(([type, count]) => (
              <div key={type} className='border border-gray-200 rounded-lg p-4'>
                <div className='flex items-center justify-between'>
                  <div>
                    <p className='text-sm font-medium text-gray-600'>
                      {type.toUpperCase().replace(/_/g, ' ')}
                    </p>
                    <p className='text-2xl font-bold text-gray-900'>{count}</p>
                  </div>
                  <Shield className='w-6 h-6 text-blue-600' />
                </div>
              </div>
            ))}
          </div>
        )}

        <div className='mt-6'>
          <button
            onClick={() => generateComplianceReport('audit_trail', dateRange)}
            className='inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700'
          >
            <FileText className='w-4 h-4 mr-2' />
            Generate Compliance Report
          </button>
        </div>
      </div>
    </div>
  );

  // Main render
  return (
    <div className={`space-y-6 ${className}`}>
      {renderMetricsOverview()}

      {/* Tab Navigation */}
      <div className='border-b border-gray-200'>
        <nav className='-mb-px flex space-x-8'>
          {availableTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap flex items-center space-x-2 ${
                  isActive
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className='w-4 h-4' />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'activity' && renderActivityTab()}
        {activeTab === 'events' && renderEventsTab()}
        {activeTab === 'compliance' && renderComplianceTab()}
        {activeTab === 'metrics' && metrics && (
          <div className='bg-white rounded-lg shadow-sm p-6'>
            <h3 className='font-semibold text-gray-900 mb-4'>Detailed Metrics</h3>
            <pre className='text-sm text-gray-600 bg-gray-50 p-4 rounded-md overflow-auto'>
              {JSON.stringify(metrics, null, 2)}
            </pre>
          </div>
        )}
        {activeTab === 'reports' && (
          <div className='bg-white rounded-lg shadow-sm p-6'>
            <h3 className='font-semibold text-gray-900 mb-4'>Export & Reports</h3>
            <div className='space-y-4'>
              <button
                onClick={() => exportAuditTrail(filters, 'csv')}
                className='inline-flex items-center px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700'
              >
                <Download className='w-4 h-4 mr-2' />
                Export as CSV
              </button>
              <button
                onClick={() => exportAuditTrail(filters, 'json')}
                className='inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 ml-2'
              >
                <Download className='w-4 h-4 mr-2' />
                Export as JSON
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className='bg-red-50 border border-red-200 rounded-md p-4'>
          <div className='flex'>
            <AlertTriangle className='w-5 h-5 text-red-400' />
            <div className='ml-3'>
              <h3 className='text-sm font-medium text-red-800'>Error</h3>
              <p className='text-sm text-red-700 mt-1'>{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UniversalAuditDashboard;
