/**
 * Dashboard Template
 * Universal dashboard template for all portal types
 */

import React, { useState, useEffect, useMemo } from 'react';
import { trackPageView, trackAction } from '@dotmac/monitoring/observability';
import { 
  Card, 
  Button, 
  Badge, 
  Skeleton,
  Select,
  RefreshCw
} from '@dotmac/primitives';
import { UniversalMetricsGrid, MetricData } from '@dotmac/primitives';
import { InteractiveChart } from '@dotmac/primitives';
import { VirtualizedTable } from '@dotmac/primitives/performance';
import { PermissionGuard } from '@dotmac/rbac';
import { useQuery } from '@tanstack/react-query';
import { Calendar, Download, Filter, TrendingUp, Users, MapPin } from 'lucide-react';

export interface ChartConfig {
  id: string;
  title: string;
  type: 'line' | 'bar' | 'pie' | 'area' | 'donut';
  dataKey: string;
  height?: number;
  color?: string;
  showLegend?: boolean;
  interactive?: boolean;
}

export interface TableSection {
  id: string;
  title: string;
  columns: Array<{
    key: string;
    label: string;
    render?: (value: any) => React.ReactNode;
  }>;
  apiEndpoint: string;
  maxItems?: number;
  showViewAll?: boolean;
}

export interface DashboardSection {
  id: string;
  title: string;
  type: 'metrics' | 'chart' | 'table' | 'custom';
  size: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  order: number;
  config?: ChartConfig | TableSection | any;
  component?: React.ComponentType<any>;
  permission?: string;
}

export interface DashboardConfig {
  title: string;
  subtitle?: string;
  portal: 'admin' | 'customer' | 'reseller' | 'technician' | 'management';
  metrics: MetricData[];
  sections: DashboardSection[];
  refreshInterval?: number;
  timeRanges?: Array<{ label: string; value: string }>;
  filters?: Array<{
    key: string;
    label: string;
    type: 'select' | 'daterange';
    options?: Array<{ label: string; value: string }>;
  }>;
  apiEndpoint: string;
  permissions?: {
    view: string;
    export?: string;
    manage?: string;
  };
}

interface DashboardTemplateProps {
  config: DashboardConfig;
  className?: string;
}

export function DashboardTemplate({ config, className = '' }: DashboardTemplateProps) {
  const [timeRange, setTimeRange] = useState('7d');
  const [filters, setFilters] = useState<Record<string, any>>({});
  const [lastRefresh, setLastRefresh] = useState(Date.now());

  // Auto-refresh effect
  useEffect(() => {
    if (!config.refreshInterval) return;
    
    const interval = setInterval(() => {
      setLastRefresh(Date.now());
    }, config.refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [config.refreshInterval]);

  // Data fetching
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [`dashboard-${config.portal}`, timeRange, filters, lastRefresh],
    queryFn: async () => {
      const params = new URLSearchParams({
        timeRange,
        ...filters,
        timestamp: lastRefresh.toString()
      });
      
      const response = await fetch(`${config.apiEndpoint}?${params}`);
      if (!response.ok) throw new Error('Failed to fetch dashboard data');
      return response.json();
    }
  });

  // Emit observability events
  useEffect(() => {
    if (window.performance && window.performance.mark) {
      window.performance.mark('dashboard-render-start');
    }
    
    // Emit page view event
    const event = new CustomEvent('ui.page.view', {
      detail: {
        page: `dashboard-${config.portal}`,
        timestamp: new Date().toISOString(),
        filters,
        timeRange
      }
    });
    window.dispatchEvent(event);
    try { trackPageView(`dashboard-${config.portal}`, { filters, timeRange }); } catch {}

    return () => {
      if (window.performance && window.performance.mark) {
        window.performance.mark('dashboard-render-end');
        window.performance.measure(
          'dashboard-render',
          'dashboard-render-start',
          'dashboard-render-end'
        );
      }
    };
  }, [config.portal, filters, timeRange]);

  // Sort sections by order
  const sortedSections = useMemo(() => {
    return [...config.sections].sort((a, b) => a.order - b.order);
  }, [config.sections]);

  const handleRefresh = async () => {
    // Emit action event
    const event = new CustomEvent('ui.action.refresh', {
      detail: {
        component: 'dashboard',
        timestamp: new Date().toISOString()
      }
    });
    window.dispatchEvent(event);
    try { trackAction('refresh', 'dashboard'); } catch {}

    setLastRefresh(Date.now());
    await refetch();
  };

  const handleExport = async () => {
    // Emit action event
    const event = new CustomEvent('ui.action.export', {
      detail: {
        component: 'dashboard',
        format: 'json',
        timestamp: new Date().toISOString()
      }
    });
    window.dispatchEvent(event);
    try { trackAction('export', 'dashboard', { format: 'json' }); } catch {}

    const exportData = {
      dashboard: config.title,
      timeRange,
      filters,
      data: data?.metrics,
      exportedAt: new Date().toISOString()
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `dashboard-${config.portal}-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
  };

  const renderSection = (section: DashboardSection) => {
    const sizeClasses = {
      sm: 'col-span-1',
      md: 'col-span-2',
      lg: 'col-span-3',
      xl: 'col-span-4',
      full: 'col-span-full'
    };

    const content = () => {
      switch (section.type) {
        case 'metrics':
          return (
            <UniversalMetricsGrid
              metrics={data?.metrics || config.metrics}
              portal={config.portal}
              columns={section.size === 'full' ? 4 : section.size === 'lg' ? 3 : 2}
              size="sm"
              isLoading={isLoading}
            />
          );

        case 'chart':
          const chartConfig = section.config as ChartConfig;
          return (
            <InteractiveChart
              type={chartConfig.type}
              data={data?.charts?.[chartConfig.id] || []}
              title={chartConfig.title}
              dataKey={chartConfig.dataKey}
              height={chartConfig.height || 300}
              color={chartConfig.color}
              showLegend={chartConfig.showLegend}
              interactive={chartConfig.interactive}
              isLoading={isLoading}
            />
          );

        case 'table':
          const tableConfig = section.config as TableSection;
          return (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium">{tableConfig.title}</h3>
                {tableConfig.showViewAll && (
                  <Button variant="outline" size="sm">
                    View All
                  </Button>
                )}
              </div>
              <VirtualizedTable
                data={data?.tables?.[tableConfig.id] || []}
                columns={tableConfig.columns}
                maxHeight={400}
                isLoading={isLoading}
              />
            </div>
          );

        case 'custom':
          const CustomComponent = section.component;
          return CustomComponent ? (
            <CustomComponent {...section.config} data={data} isLoading={isLoading} />
          ) : null;

        default:
          return null;
      }
    };

    if (section.permission) {
      return (
        <PermissionGuard key={section.id} permission={section.permission}>
          <div className={sizeClasses[section.size]}>{content()}</div>
        </PermissionGuard>
      );
    }

    return (
      <div key={section.id} className={sizeClasses[section.size]}>
        {content()}
      </div>
    );
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 text-xl mb-4">Error loading dashboard</div>
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <PermissionGuard permission={config.permissions?.view || `dashboard:${config.portal}:view`}>
      <div className={`space-y-6 ${className}`} data-testid={`dashboard-${config.portal}`}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900" data-testid="dashboard-title">
              {config.title}
            </h1>
            {config.subtitle && (
              <p className="mt-1 text-lg text-gray-500" data-testid="dashboard-subtitle">
                {config.subtitle}
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Time Range Selector */}
            {config.timeRanges && (
              <Select
                value={timeRange}
                onChange={(value) => setTimeRange(value)}
                data-testid="time-range-select"
              >
                {config.timeRanges.map((range) => (
                  <option key={range.value} value={range.value}>
                    {range.label}
                  </option>
                ))}
              </Select>
            )}

            {/* Filters */}
            {config.filters?.map((filter) => (
              <Select
                key={filter.key}
                placeholder={filter.label}
                value={filters[filter.key] || ''}
                onChange={(value) => setFilters(prev => ({ ...prev, [filter.key]: value }))}
                data-testid={`filter-${filter.key}`}
              >
                <option value="">All {filter.label}</option>
                {filter.options?.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            ))}

            {/* Export Button */}
            <PermissionGuard permission={config.permissions?.export} fallback={null}>
              <Button onClick={handleExport} variant="outline" data-testid="export-button">
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </PermissionGuard>

            {/* Refresh Button */}
            <Button onClick={handleRefresh} variant="outline" data-testid="refresh-button">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-4 gap-6">
          {isLoading ? (
            <>
              <Card className="col-span-full p-6">
                <Skeleton className="h-32 w-full" />
              </Card>
              <Card className="col-span-2 p-6">
                <Skeleton className="h-64 w-full" />
              </Card>
              <Card className="col-span-2 p-6">
                <Skeleton className="h-64 w-full" />
              </Card>
            </>
          ) : (
            sortedSections.map((section) => (
              <Card key={section.id} className="p-6">
                {renderSection(section)}
              </Card>
            ))
          )}
        </div>

        {/* Last Updated */}
        <div className="text-sm text-gray-500 text-center" data-testid="last-updated">
          Last updated: {new Date(lastRefresh).toLocaleTimeString()}
        </div>
      </div>
    </PermissionGuard>
  );
}

export default DashboardTemplate;
