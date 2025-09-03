/**
 * Network Alerts List
 * Comprehensive network alerting and notification management interface
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Card, Button, Badge } from '@dotmac/primitives';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  X,
  Eye,
  EyeOff,
  Filter,
  Search,
  Bell,
  BellOff,
  Archive,
  Trash2,
  RefreshCw,
  Calendar,
  MapPin,
  Activity,
  Wifi,
  Server,
  AlertCircle,
} from 'lucide-react';

export type AlertSeverity = 'critical' | 'warning' | 'info';
export type AlertStatus = 'active' | 'acknowledged' | 'resolved' | 'suppressed';
export type AlertCategory =
  | 'connectivity'
  | 'performance'
  | 'security'
  | 'configuration'
  | 'hardware';

export interface NetworkAlert {
  id: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  status: AlertStatus;
  category: AlertCategory;
  source: {
    type: 'device' | 'service' | 'system';
    name: string;
    id: string;
    location?: string;
  };
  timestamp: number;
  acknowledgedBy?: string;
  acknowledgedAt?: number;
  resolvedAt?: number;
  metadata: Record<string, any>;
  count?: number; // For grouped/repeated alerts
  relatedAlerts?: string[]; // IDs of related alerts
}

export interface AlertFilter {
  severities: AlertSeverity[];
  statuses: AlertStatus[];
  categories: AlertCategory[];
  sources: string[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  searchQuery?: string;
}

export interface NetworkAlertsListProps {
  alerts: NetworkAlert[];
  onAcknowledge: (alertIds: string[], userId: string) => void;
  onResolve: (alertIds: string[]) => void;
  onSuppress: (alertIds: string[], duration?: number) => void;
  onDelete: (alertIds: string[]) => void;
  onRefresh: () => void;
  currentUserId: string;
  isLoading?: boolean;
  className?: string;
}

export const NetworkAlertsList: React.FC<NetworkAlertsListProps> = ({
  alerts = [],
  onAcknowledge,
  onResolve,
  onSuppress,
  onDelete,
  onRefresh,
  currentUserId,
  isLoading = false,
  className,
}) => {
  const [selectedAlerts, setSelectedAlerts] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<AlertFilter>({
    severities: ['critical', 'warning', 'info'],
    statuses: ['active', 'acknowledged'],
    categories: ['connectivity', 'performance', 'security', 'configuration', 'hardware'],
    sources: [],
  });
  const [showFilters, setShowFilters] = useState(false);
  const [sortBy, setSortBy] = useState<'timestamp' | 'severity' | 'source'>('timestamp');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Filter and sort alerts
  const filteredAlerts = useMemo(() => {
    let filtered = alerts.filter((alert) => {
      // Severity filter
      if (!filter.severities.includes(alert.severity)) return false;

      // Status filter
      if (!filter.statuses.includes(alert.status)) return false;

      // Category filter
      if (!filter.categories.includes(alert.category)) return false;

      // Source filter
      if (filter.sources.length > 0 && !filter.sources.includes(alert.source.name)) return false;

      // Search query filter
      if (filter.searchQuery) {
        const query = filter.searchQuery.toLowerCase();
        return (
          alert.title.toLowerCase().includes(query) ||
          alert.description.toLowerCase().includes(query) ||
          alert.source.name.toLowerCase().includes(query)
        );
      }

      // Date range filter
      if (filter.dateRange) {
        const alertDate = new Date(alert.timestamp);
        if (alertDate < filter.dateRange.start || alertDate > filter.dateRange.end) return false;
      }

      return true;
    });

    // Sort alerts
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (sortBy) {
        case 'timestamp':
          comparison = a.timestamp - b.timestamp;
          break;
        case 'severity':
          const severityOrder = { critical: 0, warning: 1, info: 2 };
          comparison = severityOrder[a.severity] - severityOrder[b.severity];
          break;
        case 'source':
          comparison = a.source.name.localeCompare(b.source.name);
          break;
      }

      return sortOrder === 'desc' ? -comparison : comparison;
    });

    return filtered;
  }, [alerts, filter, sortBy, sortOrder]);

  // Alert statistics
  const alertStats = useMemo(() => {
    const stats = {
      total: alerts.length,
      critical: alerts.filter((a) => a.severity === 'critical').length,
      warning: alerts.filter((a) => a.severity === 'warning').length,
      info: alerts.filter((a) => a.severity === 'info').length,
      active: alerts.filter((a) => a.status === 'active').length,
      acknowledged: alerts.filter((a) => a.status === 'acknowledged').length,
      resolved: alerts.filter((a) => a.status === 'resolved').length,
    };

    return stats;
  }, [alerts]);

  // Bulk actions
  const handleSelectAll = useCallback(() => {
    if (selectedAlerts.size === filteredAlerts.length) {
      setSelectedAlerts(new Set());
    } else {
      setSelectedAlerts(new Set(filteredAlerts.map((a) => a.id)));
    }
  }, [filteredAlerts, selectedAlerts.size]);

  const handleSelectAlert = useCallback(
    (alertId: string) => {
      const newSelected = new Set(selectedAlerts);
      if (newSelected.has(alertId)) {
        newSelected.delete(alertId);
      } else {
        newSelected.add(alertId);
      }
      setSelectedAlerts(newSelected);
    },
    [selectedAlerts]
  );

  const handleBulkAction = useCallback(
    (action: 'acknowledge' | 'resolve' | 'suppress' | 'delete') => {
      const alertIds = Array.from(selectedAlerts);
      if (alertIds.length === 0) return;

      switch (action) {
        case 'acknowledge':
          onAcknowledge(alertIds, currentUserId);
          break;
        case 'resolve':
          onResolve(alertIds);
          break;
        case 'suppress':
          onSuppress(alertIds, 3600); // 1 hour default
          break;
        case 'delete':
          onDelete(alertIds);
          break;
      }

      setSelectedAlerts(new Set());
    },
    [selectedAlerts, onAcknowledge, onResolve, onSuppress, onDelete, currentUserId]
  );

  // Helper functions
  const getSeverityIcon = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className='w-4 h-4 text-red-500' />;
      case 'warning':
        return <AlertTriangle className='w-4 h-4 text-yellow-500' />;
      case 'info':
        return <AlertCircle className='w-4 h-4 text-blue-500' />;
    }
  };

  const getSeverityColor = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'info':
        return 'bg-blue-100 text-blue-800';
    }
  };

  const getStatusColor = (status: AlertStatus) => {
    switch (status) {
      case 'active':
        return 'bg-red-100 text-red-800';
      case 'acknowledged':
        return 'bg-yellow-100 text-yellow-800';
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'suppressed':
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'device':
        return <Server className='w-4 h-4' />;
      case 'service':
        return <Activity className='w-4 h-4' />;
      case 'system':
        return <Wifi className='w-4 h-4' />;
      default:
        return <AlertCircle className='w-4 h-4' />;
    }
  };

  return (
    <div className={`space-y-6 ${className || ''}`}>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div className='flex items-center space-x-2'>
          <Bell className='w-6 h-6 text-orange-500' />
          <h2 className='text-2xl font-bold text-gray-900'>Network Alerts</h2>
        </div>

        <div className='flex items-center space-x-2'>
          <Button variant='outline' size='sm' onClick={() => setShowFilters(!showFilters)}>
            <Filter className='w-4 h-4 mr-2' />
            Filters
          </Button>

          <Button variant='outline' size='sm' onClick={onRefresh} disabled={isLoading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Statistics */}
      <div className='grid grid-cols-2 md:grid-cols-7 gap-4'>
        <Card className='p-3'>
          <div className='text-center'>
            <div className='text-2xl font-bold text-gray-900'>{alertStats.total}</div>
            <div className='text-xs text-gray-500'>Total</div>
          </div>
        </Card>

        <Card className='p-3'>
          <div className='text-center'>
            <div className='text-2xl font-bold text-red-600'>{alertStats.critical}</div>
            <div className='text-xs text-gray-500'>Critical</div>
          </div>
        </Card>

        <Card className='p-3'>
          <div className='text-center'>
            <div className='text-2xl font-bold text-yellow-600'>{alertStats.warning}</div>
            <div className='text-xs text-gray-500'>Warning</div>
          </div>
        </Card>

        <Card className='p-3'>
          <div className='text-center'>
            <div className='text-2xl font-bold text-blue-600'>{alertStats.info}</div>
            <div className='text-xs text-gray-500'>Info</div>
          </div>
        </Card>

        <Card className='p-3'>
          <div className='text-center'>
            <div className='text-2xl font-bold text-red-600'>{alertStats.active}</div>
            <div className='text-xs text-gray-500'>Active</div>
          </div>
        </Card>

        <Card className='p-3'>
          <div className='text-center'>
            <div className='text-2xl font-bold text-yellow-600'>{alertStats.acknowledged}</div>
            <div className='text-xs text-gray-500'>Acknowledged</div>
          </div>
        </Card>

        <Card className='p-3'>
          <div className='text-center'>
            <div className='text-2xl font-bold text-green-600'>{alertStats.resolved}</div>
            <div className='text-xs text-gray-500'>Resolved</div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      {showFilters && (
        <Card className='p-4'>
          <div className='space-y-4'>
            <div className='flex items-center space-x-4'>
              <div className='flex-1'>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Search</label>
                <div className='relative'>
                  <Search className='w-4 h-4 absolute left-3 top-2.5 text-gray-400' />
                  <input
                    type='text'
                    value={filter.searchQuery || ''}
                    onChange={(e) => setFilter({ ...filter, searchQuery: e.target.value })}
                    placeholder='Search alerts...'
                    className='pl-10 pr-3 py-2 border border-gray-300 rounded w-full text-sm'
                  />
                </div>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-1'>Sort By</label>
                <select
                  value={`${sortBy}-${sortOrder}`}
                  onChange={(e) => {
                    const [by, order] = e.target.value.split('-');
                    setSortBy(by as any);
                    setSortOrder(order as any);
                  }}
                  className='px-3 py-2 border border-gray-300 rounded text-sm'
                >
                  <option value='timestamp-desc'>Newest First</option>
                  <option value='timestamp-asc'>Oldest First</option>
                  <option value='severity-asc'>Severity (High to Low)</option>
                  <option value='severity-desc'>Severity (Low to High)</option>
                  <option value='source-asc'>Source (A to Z)</option>
                  <option value='source-desc'>Source (Z to A)</option>
                </select>
              </div>
            </div>

            <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>Severity</label>
                <div className='space-y-1'>
                  {(['critical', 'warning', 'info'] as AlertSeverity[]).map((severity) => (
                    <label key={severity} className='flex items-center'>
                      <input
                        type='checkbox'
                        checked={filter.severities.includes(severity)}
                        onChange={(e) => {
                          const severities = e.target.checked
                            ? [...filter.severities, severity]
                            : filter.severities.filter((s) => s !== severity);
                          setFilter({ ...filter, severities });
                        }}
                        className='mr-2'
                      />
                      <span className='capitalize text-sm'>{severity}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>Status</label>
                <div className='space-y-1'>
                  {(['active', 'acknowledged', 'resolved', 'suppressed'] as AlertStatus[]).map(
                    (status) => (
                      <label key={status} className='flex items-center'>
                        <input
                          type='checkbox'
                          checked={filter.statuses.includes(status)}
                          onChange={(e) => {
                            const statuses = e.target.checked
                              ? [...filter.statuses, status]
                              : filter.statuses.filter((s) => s !== status);
                            setFilter({ ...filter, statuses });
                          }}
                          className='mr-2'
                        />
                        <span className='capitalize text-sm'>{status}</span>
                      </label>
                    )
                  )}
                </div>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>Category</label>
                <div className='space-y-1'>
                  {(
                    [
                      'connectivity',
                      'performance',
                      'security',
                      'configuration',
                      'hardware',
                    ] as AlertCategory[]
                  ).map((category) => (
                    <label key={category} className='flex items-center'>
                      <input
                        type='checkbox'
                        checked={filter.categories.includes(category)}
                        onChange={(e) => {
                          const categories = e.target.checked
                            ? [...filter.categories, category]
                            : filter.categories.filter((c) => c !== category);
                          setFilter({ ...filter, categories });
                        }}
                        className='mr-2'
                      />
                      <span className='capitalize text-sm'>{category}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Bulk Actions */}
      {selectedAlerts.size > 0 && (
        <Card className='p-4 bg-blue-50 border-blue-200'>
          <div className='flex items-center justify-between'>
            <span className='text-sm font-medium text-blue-900'>
              {selectedAlerts.size} alert{selectedAlerts.size !== 1 ? 's' : ''} selected
            </span>

            <div className='flex items-center space-x-2'>
              <Button size='sm' variant='outline' onClick={() => handleBulkAction('acknowledge')}>
                <Eye className='w-4 h-4 mr-1' />
                Acknowledge
              </Button>

              <Button size='sm' variant='outline' onClick={() => handleBulkAction('resolve')}>
                <CheckCircle className='w-4 h-4 mr-1' />
                Resolve
              </Button>

              <Button size='sm' variant='outline' onClick={() => handleBulkAction('suppress')}>
                <EyeOff className='w-4 h-4 mr-1' />
                Suppress
              </Button>

              <Button size='sm' variant='destructive' onClick={() => handleBulkAction('delete')}>
                <Trash2 className='w-4 h-4 mr-1' />
                Delete
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Alert List */}
      <Card className='p-0'>
        {filteredAlerts.length === 0 ? (
          <div className='p-8 text-center'>
            <Bell className='w-12 h-12 text-gray-300 mx-auto mb-4' />
            <p className='text-gray-500'>No alerts match your current filters.</p>
          </div>
        ) : (
          <>
            {/* List Header */}
            <div className='p-4 border-b border-gray-200'>
              <div className='flex items-center'>
                <input
                  type='checkbox'
                  checked={
                    selectedAlerts.size === filteredAlerts.length && filteredAlerts.length > 0
                  }
                  onChange={handleSelectAll}
                  className='mr-4'
                />
                <span className='text-sm font-medium text-gray-700'>
                  Showing {filteredAlerts.length} of {alerts.length} alerts
                </span>
              </div>
            </div>

            {/* Alert Items */}
            <div className='divide-y divide-gray-200'>
              {filteredAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`p-4 hover:bg-gray-50 ${
                    selectedAlerts.has(alert.id) ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className='flex items-start space-x-4'>
                    <input
                      type='checkbox'
                      checked={selectedAlerts.has(alert.id)}
                      onChange={() => handleSelectAlert(alert.id)}
                      className='mt-1'
                    />

                    <div className='flex-1 min-w-0'>
                      <div className='flex items-start justify-between'>
                        <div className='flex-1 min-w-0'>
                          <div className='flex items-center space-x-2 mb-1'>
                            {getSeverityIcon(alert.severity)}
                            <h3 className='text-sm font-medium text-gray-900 truncate'>
                              {alert.title}
                            </h3>
                            {alert.count && alert.count > 1 && (
                              <Badge variant='outline' className='text-xs'>
                                {alert.count}x
                              </Badge>
                            )}
                          </div>

                          <p className='text-sm text-gray-600 mb-2 line-clamp-2'>
                            {alert.description}
                          </p>

                          <div className='flex items-center space-x-4 text-xs text-gray-500'>
                            <div className='flex items-center space-x-1'>
                              {getSourceIcon(alert.source.type)}
                              <span>{alert.source.name}</span>
                            </div>

                            {alert.source.location && (
                              <div className='flex items-center space-x-1'>
                                <MapPin className='w-3 h-3' />
                                <span>{alert.source.location}</span>
                              </div>
                            )}

                            <div className='flex items-center space-x-1'>
                              <Calendar className='w-3 h-3' />
                              <span>{new Date(alert.timestamp).toLocaleString()}</span>
                            </div>
                          </div>

                          {alert.acknowledgedBy && (
                            <div className='text-xs text-gray-500 mt-1'>
                              Acknowledged by {alert.acknowledgedBy} at{' '}
                              {new Date(alert.acknowledgedAt!).toLocaleString()}
                            </div>
                          )}
                        </div>

                        <div className='flex items-center space-x-2 ml-4'>
                          <Badge className={getSeverityColor(alert.severity)}>
                            {alert.severity}
                          </Badge>
                          <Badge className={getStatusColor(alert.status)}>{alert.status}</Badge>
                          <Badge variant='outline' className='capitalize'>
                            {alert.category}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </Card>
    </div>
  );
};
