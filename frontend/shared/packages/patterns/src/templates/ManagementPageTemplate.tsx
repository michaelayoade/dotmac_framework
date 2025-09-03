/**
 * ManagementPageTemplate
 *
 * Template for operational management pages with metrics, filters, data tables,
 * and actions. Optimized for admin, reseller, and management portals.
 */

import React, { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import { trackPageView, trackAction } from '@dotmac/monitoring/observability';
import { clsx } from 'clsx';
import {
  Search,
  Filter,
  RefreshCw,
  Download,
  Plus,
  Settings2,
  ChevronDown,
  X,
  Save,
  Eye,
} from 'lucide-react';
import { Button, Input, Select, Badge, Skeleton } from '@dotmac/primitives';
import { LayoutRoot, LayoutHeader, LayoutMain, LayoutContainer } from '../composition/Layout';
import { withComponentRegistration } from '@dotmac/registry';
import { useRenderProfiler } from '@dotmac/primitives';
import {
  ManagementPageConfig,
  TemplateState,
  TemplateContextValue,
  ActionConfig,
  FilterConfig,
  SavedViewConfig,
  MetricConfig,
  validateTemplateConfig,
  TemplateConfigSchemas,
} from '../types/templates';

// Management Page Context
const ManagementPageContext = createContext<TemplateContextValue | null>(null);

export function useManagementPage() {
  const context = useContext(ManagementPageContext);
  if (!context) {
    throw new Error('useManagementPage must be used within ManagementPageTemplate');
  }
  return context;
}

// Metric Card Component
interface MetricCardProps {
  metric: MetricConfig;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

function MetricCardImpl({ metric, size = 'md', className }: MetricCardProps) {
  const formatValue = (value: string | number, format: string, precision: number) => {
    const num = typeof value === 'string' ? parseFloat(value) : value;

    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          minimumFractionDigits: precision,
          maximumFractionDigits: precision,
        }).format(num);
      case 'percentage':
        return `${(num * 100).toFixed(precision)}%`;
      case 'bytes':
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        if (num === 0) return '0 B';
        const i = Math.floor(Math.log(num) / Math.log(1024));
        return `${(num / Math.pow(1024, i)).toFixed(precision)} ${sizes[i]}`;
      case 'duration':
        const hours = Math.floor(num / 3600);
        const minutes = Math.floor((num % 3600) / 60);
        const seconds = Math.floor(num % 60);
        return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      default:
        return num.toLocaleString('en-US', {
          minimumFractionDigits: precision,
          maximumFractionDigits: precision,
        });
    }
  };

  const sizeClasses = {
    sm: 'p-3',
    md: 'p-4',
    lg: 'p-6',
  };

  const valueSizes = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-3xl',
  };

  return (
    <div
      className={clsx(
        'rounded-lg border bg-card text-card-foreground shadow-sm',
        sizeClasses[size],
        className
      )}
      style={{ borderColor: metric.color }}
    >
      <div className='flex items-center justify-between'>
        <div className='space-y-2 flex-1'>
          <p className='text-sm font-medium leading-none text-muted-foreground'>{metric.title}</p>
          <p className={clsx('font-bold tracking-tight', valueSizes[size])}>
            {formatValue(metric.value, metric.format, metric.precision)}
          </p>
        </div>

        {metric.icon && (
          <div className='rounded-full bg-primary/10 p-2'>
            <div className='h-4 w-4' dangerouslySetInnerHTML={{ __html: metric.icon }} />
          </div>
        )}
      </div>

      {metric.change && (
        <div className='mt-2 flex items-center text-xs'>
          <div
            className={clsx(
              'flex items-center space-x-1',
              metric.change.type === 'increase' && 'text-green-600',
              metric.change.type === 'decrease' && 'text-red-600',
              metric.change.type === 'neutral' && 'text-muted-foreground'
            )}
          >
            <span>
              {metric.change.value > 0 ? '+' : ''}
              {metric.change.value}%
            </span>
            {metric.change.period && (
              <span className='text-muted-foreground'>vs {metric.change.period}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const MetricCard = withComponentRegistration(MetricCardImpl, {
  name: 'MetricCard',
  category: 'template',
  portal: 'shared',
  version: '1.0.0',
});

// Filter Toolbar Component
interface FilterToolbarProps {
  filters: FilterConfig[];
  values: Record<string, any>;
  savedViews: SavedViewConfig[];
  onFilterChange: (key: string, value: any) => void;
  onClearFilters: () => void;
  onSaveView: (name: string) => void;
  onLoadView: (view: SavedViewConfig) => void;
  className?: string;
}

function FilterToolbarImpl({
  filters,
  values,
  savedViews,
  onFilterChange,
  onClearFilters,
  onSaveView,
  onLoadView,
  className,
}: FilterToolbarProps) {
  const [showFilters, setShowFilters] = useState(false);
  const [saveViewName, setSaveViewName] = useState('');
  const [showSaveView, setShowSaveView] = useState(false);

  const activeFiltersCount = useMemo(() => {
    return Object.keys(values).filter((key) => values[key] !== undefined && values[key] !== '')
      .length;
  }, [values]);

  const renderFilter = (filter: FilterConfig) => {
    const value = values[filter.key];

    switch (filter.type) {
      case 'text':
        return (
          <Input
            key={filter.key}
            placeholder={filter.placeholder || `Filter by ${filter.label.toLowerCase()}`}
            value={value || ''}
            onChange={(e) => onFilterChange(filter.key, e.target.value)}
            className='w-48'
          />
        );

      case 'select':
        return (
          <Select
            key={filter.key}
            value={value || ''}
            onValueChange={(val) => onFilterChange(filter.key, val)}
          >
            <option value=''>{filter.placeholder || `Select ${filter.label.toLowerCase()}`}</option>
            {filter.options?.map((option) => (
              <option key={option.value} value={option.value} disabled={option.disabled}>
                {option.label}
              </option>
            ))}
          </Select>
        );

      case 'boolean':
        return (
          <Select
            key={filter.key}
            value={value === undefined ? '' : value.toString()}
            onValueChange={(val) =>
              onFilterChange(filter.key, val === '' ? undefined : val === 'true')
            }
          >
            <option value=''>{filter.placeholder || `All ${filter.label.toLowerCase()}`}</option>
            <option value='true'>Yes</option>
            <option value='false'>No</option>
          </Select>
        );

      default:
        return (
          <Input
            key={filter.key}
            type={filter.type}
            placeholder={filter.placeholder || filter.label}
            value={value || ''}
            onChange={(e) => onFilterChange(filter.key, e.target.value)}
            className='w-48'
          />
        );
    }
  };

  return (
    <div className={clsx('space-y-4', className)}>
      {/* Filter Toggle Bar */}
      <div className='flex items-center justify-between'>
        <div className='flex items-center space-x-2'>
          <Button
            variant='outline'
            size='sm'
            onClick={() => setShowFilters(!showFilters)}
            data-testid='filter-toggle'
          >
            <Filter className='h-4 w-4 mr-2' />
            Filters
            {activeFiltersCount > 0 && (
              <Badge variant='secondary' className='ml-2'>
                {activeFiltersCount}
              </Badge>
            )}
            <ChevronDown
              className={clsx('h-4 w-4 ml-2 transition-transform', showFilters && 'rotate-180')}
            />
          </Button>

          {activeFiltersCount > 0 && (
            <Button variant='ghost' size='sm' onClick={onClearFilters} data-testid='clear-filters'>
              <X className='h-4 w-4 mr-2' />
              Clear
            </Button>
          )}
        </div>

        <div className='flex items-center space-x-2'>
          {/* Saved Views */}
          {savedViews.length > 0 && (
            <Select
              value=''
              onValueChange={(viewId) => {
                const view = savedViews.find((v) => v.id === viewId);
                if (view) onLoadView(view);
              }}
            >
              <option value=''>Load view...</option>
              {savedViews.map((view) => (
                <option key={view.id} value={view.id}>
                  {view.name} {view.isDefault && '(Default)'}
                </option>
              ))}
            </Select>
          )}

          <Button
            variant='ghost'
            size='sm'
            onClick={() => setShowSaveView(!showSaveView)}
            data-testid='save-view-toggle'
          >
            <Save className='h-4 w-4' />
          </Button>
        </div>
      </div>

      {/* Filter Controls */}
      {showFilters && (
        <div className='flex flex-wrap gap-4 p-4 bg-muted/30 rounded-lg border'>
          {filters.map(renderFilter)}
        </div>
      )}

      {/* Save View */}
      {showSaveView && (
        <div className='flex items-center space-x-2 p-3 bg-card rounded-lg border'>
          <Input
            placeholder='View name...'
            value={saveViewName}
            onChange={(e) => setSaveViewName(e.target.value)}
            className='flex-1'
          />
          <Button
            size='sm'
            onClick={() => {
              if (saveViewName.trim()) {
                onSaveView(saveViewName.trim());
                setSaveViewName('');
                setShowSaveView(false);
              }
            }}
            disabled={!saveViewName.trim()}
          >
            Save
          </Button>
          <Button
            variant='ghost'
            size='sm'
            onClick={() => {
              setShowSaveView(false);
              setSaveViewName('');
            }}
          >
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}

const FilterToolbar = withComponentRegistration(FilterToolbarImpl, {
  name: 'FilterToolbar',
  category: 'template',
  portal: 'shared',
  version: '1.0.0',
});

// Action Bar Component
interface ActionBarProps {
  actions: ActionConfig[];
  selectedCount: number;
  showExport?: boolean;
  showRefresh?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  onExport?: (format: 'csv' | 'excel' | 'json') => void;
  className?: string;
}

function ActionBarImpl({
  actions,
  selectedCount,
  showExport = true,
  showRefresh = true,
  refreshing = false,
  onRefresh,
  onExport,
  className,
}: ActionBarProps) {
  const [showExportMenu, setShowExportMenu] = useState(false);

  return (
    <div className={clsx('flex items-center justify-between', className)}>
      <div className='flex items-center space-x-2'>
        {/* Primary Actions */}
        {actions
          .filter((action) => action.variant === 'primary')
          .map((action) => (
            <Button
              key={action.key}
              variant={action.variant}
              disabled={action.disabled || action.loading}
              onClick={action.onClick}
              data-testid={`action-${action.key}`}
            >
              {action.loading && (
                <div className='animate-spin h-4 w-4 mr-2 border-2 border-current border-t-transparent rounded-full' />
              )}
              {action.icon && !action.loading && (
                <div className='h-4 w-4 mr-2' dangerouslySetInnerHTML={{ __html: action.icon }} />
              )}
              {action.label}
            </Button>
          ))}
      </div>

      <div className='flex items-center space-x-2'>
        {/* Selection Info */}
        {selectedCount > 0 && (
          <span className='text-sm text-muted-foreground'>{selectedCount} selected</span>
        )}

        {/* Secondary Actions */}
        {actions
          .filter((action) => action.variant !== 'primary')
          .map((action) => (
            <Button
              key={action.key}
              variant={action.variant}
              size='sm'
              disabled={action.disabled || action.loading}
              onClick={action.onClick}
              data-testid={`action-${action.key}`}
            >
              {action.loading && (
                <div className='animate-spin h-4 w-4 mr-2 border-2 border-current border-t-transparent rounded-full' />
              )}
              {action.icon && !action.loading && (
                <div className='h-4 w-4 mr-2' dangerouslySetInnerHTML={{ __html: action.icon }} />
              )}
              {action.label}
            </Button>
          ))}

        {/* Export Menu */}
        {showExport && onExport && (
          <div className='relative'>
            <Button
              variant='outline'
              size='sm'
              onClick={() => setShowExportMenu(!showExportMenu)}
              data-testid='export-menu'
            >
              <Download className='h-4 w-4 mr-2' />
              Export
            </Button>

            {showExportMenu && (
              <div className='absolute right-0 top-full mt-1 bg-card border rounded-lg shadow-lg z-10'>
                <div className='py-1'>
                  <button
                    className='w-full text-left px-3 py-2 hover:bg-muted'
                    onClick={() => {
                      onExport('csv');
                      setShowExportMenu(false);
                    }}
                  >
                    Export as CSV
                  </button>
                  <button
                    className='w-full text-left px-3 py-2 hover:bg-muted'
                    onClick={() => {
                      onExport('excel');
                      setShowExportMenu(false);
                    }}
                  >
                    Export as Excel
                  </button>
                  <button
                    className='w-full text-left px-3 py-2 hover:bg-muted'
                    onClick={() => {
                      onExport('json');
                      setShowExportMenu(false);
                    }}
                  >
                    Export as JSON
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Refresh Button */}
        {showRefresh && onRefresh && (
          <Button
            variant='ghost'
            size='sm'
            onClick={onRefresh}
            disabled={refreshing}
            data-testid='refresh-button'
          >
            <RefreshCw className={clsx('h-4 w-4', refreshing && 'animate-spin')} />
          </Button>
        )}
      </div>
    </div>
  );
}

const ActionBar = withComponentRegistration(ActionBarImpl, {
  name: 'ActionBar',
  category: 'template',
  portal: 'shared',
  version: '1.0.0',
});

// Main Management Page Template
export interface ManagementPageTemplateProps {
  config: ManagementPageConfig;
  children: React.ReactNode;
  className?: string;
  onDataLoad?: (filters: Record<string, any>, sorting: any, pagination: any) => Promise<any>;
  onAction?: (actionKey: string, data?: any) => Promise<void>;
  onExport?: (format: 'csv' | 'excel' | 'json', data: any) => Promise<void>;
  initialData?: Record<string, any>;
}

function ManagementPageTemplateImpl({
  config,
  children,
  className,
  onDataLoad,
  onAction,
  onExport,
  initialData = {},
}: ManagementPageTemplateProps) {
  useRenderProfiler('ManagementPageTemplate', { config });

  // Validate configuration
  const validation = useMemo(() => {
    return validateTemplateConfig(TemplateConfigSchemas.management, config);
  }, [config]);

  if (!validation.isValid) {
    console.error('ManagementPageTemplate: Invalid configuration', validation.errors);
    return (
      <div className='p-6 text-center'>
        <p className='text-destructive'>Template configuration error</p>
        <details className='mt-2 text-left text-sm'>
          <summary>Configuration Issues</summary>
          <ul className='mt-2 space-y-1'>
            {validation.errors?.map((error, index) => (
              <li key={index} className='text-muted-foreground'>
                • {error}
              </li>
            ))}
          </ul>
        </details>
      </div>
    );
  }

  // Template state
  const [state, setState] = useState<TemplateState>({
    loading: false,
    error: null,
    data: initialData,
    filters: {},
    sorting: null,
    pagination: { page: 1, pageSize: 20, total: 0 },
    selectedItems: [],
    bulkAction: null,
    refreshing: false,
    lastRefresh: null,
  });

  // Actions
  const actions = useMemo(
    () => ({
      setLoading: (loading: boolean) => {
        setState((prev) => ({ ...prev, loading }));
      },
      setError: (error: string | null) => {
        setState((prev) => ({ ...prev, error }));
      },
      setData: (data: Record<string, any>) => {
        setState((prev) => ({ ...prev, data }));
      },
      updateFilters: (filters: Record<string, any>) => {
        setState((prev) => ({ ...prev, filters, pagination: { ...prev.pagination, page: 1 } }));
      },
      updateSorting: (field: string, direction: 'asc' | 'desc') => {
        setState((prev) => ({ ...prev, sorting: { field, direction } }));
      },
      updatePagination: (page: number, pageSize?: number) => {
        setState((prev) => ({
          ...prev,
          pagination: {
            ...prev.pagination,
            page,
            ...(pageSize && { pageSize }),
          },
        }));
      },
      setSelectedItems: (items: string[]) => {
        setState((prev) => ({ ...prev, selectedItems: items }));
      },
      setBulkAction: (action: string | null) => {
        setState((prev) => ({ ...prev, bulkAction: action }));
      },
      refresh: async () => {
        if (!onDataLoad) return;

        setState((prev) => ({ ...prev, refreshing: true, error: null }));
        try {
          const result = await onDataLoad(state.filters, state.sorting, state.pagination);
          setState((prev) => ({
            ...prev,
            data: result,
            refreshing: false,
            lastRefresh: new Date(),
          }));
        } catch (error) {
          setState((prev) => ({
            ...prev,
            error: error instanceof Error ? error.message : 'Failed to load data',
            refreshing: false,
          }));
        }
      },
      exportData: async (format: 'csv' | 'excel' | 'json') => {
        if (!onExport) return;

        try {
          await onExport(format, state.data);
        } catch (error) {
          setState((prev) => ({
            ...prev,
            error: error instanceof Error ? error.message : 'Failed to export data',
          }));
        }
      },
    }),
    [onDataLoad, onExport, state.filters, state.sorting, state.pagination, state.data]
  );

  // Context value
  const contextValue: TemplateContextValue = useMemo(
    () => ({
      config,
      state,
      actions,
      permissions: {
        canView: true,
        canEdit: true,
        canDelete: true,
        canExport: config.showExport,
        canBulkEdit: config.enableBulkActions,
      },
    }),
    [config, state, actions]
  );

  // Auto-refresh effect
  useEffect(() => {
    if (!config.autoRefresh || !config.refreshInterval || !onDataLoad) return;

    const interval = setInterval(() => {
      actions.refresh();
    }, config.refreshInterval);

    return () => clearInterval(interval);
  }, [config.autoRefresh, config.refreshInterval, actions, onDataLoad]);

  // Initial data load
  useEffect(() => {
    if (onDataLoad && Object.keys(state.data).length === 0) {
      actions.refresh();
    }
  }, [onDataLoad, state.data, actions]);

  // Page view tracking
  useEffect(() => {
    try {
      trackPageView(`management-${config?.title || 'page'}`, {
        portal: config?.portal,
        entity: (config as any)?.entity,
        filters: state.filters,
      });
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <ManagementPageContext.Provider value={contextValue}>
      <LayoutRoot className={className}>
        {config.showHeader && (
          <LayoutHeader>
            <div className='flex items-center justify-between w-full'>
              <div>
                <h1 className='text-2xl font-semibold tracking-tight'>{config.title}</h1>
                {config.description && (
                  <p className='text-sm text-muted-foreground mt-1'>{config.description}</p>
                )}
              </div>
            </div>
          </LayoutHeader>
        )}

        <LayoutMain padding={config.padding}>
          <LayoutContainer maxWidth={config.maxWidth} centered>
            <div className='space-y-6'>
              {/* Error Display */}
              {state.error && (
                <div className='rounded-md bg-destructive/15 border border-destructive/20 p-4'>
                  <div className='text-sm text-destructive'>{state.error}</div>
                </div>
              )}

              {/* Metrics Grid */}
              {config.showMetrics && config.metrics.length > 0 && (
                <div className='grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4'>
                  {state.loading
                    ? Array.from({ length: 4 }).map((_, i) => (
                        <Skeleton key={i} className='h-24 w-full' />
                      ))
                    : config.metrics.map((metric) => (
                        <MetricCard key={metric.key} metric={metric} size={metric.size} />
                      ))}
                </div>
              )}

              {/* Filters */}
              {config.showFilters && config.filters.length > 0 && (
                <FilterToolbar
                  filters={config.filters}
                  values={state.filters}
                  savedViews={config.savedViews}
                  onFilterChange={(values) => {
                    try {
                      trackAction('filter', 'management-filters', { values });
                    } catch {}
                    actions.updateFilters(values);
                  }}
                  onClearFilters={() => actions.updateFilters({})}
                  onSaveView={(name) => {
                    // Implementation would save the view
                    // TODO: Implement saved view persistence
                  }}
                  onLoadView={(view) => {
                    actions.updateFilters(view.filters);
                  }}
                />
              )}

              {/* Actions */}
              {config.showActions && config.actions.length > 0 && (
                <ActionBar
                  actions={config.actions}
                  selectedCount={state.selectedItems.length}
                  showExport={config.showExport}
                  showRefresh={!!onDataLoad}
                  refreshing={state.refreshing}
                  onRefresh={actions.refresh}
                  onExport={actions.exportData}
                />
              )}

              {/* Main Content */}
              <div className='space-y-4'>{children}</div>
            </div>
          </LayoutContainer>
        </LayoutMain>
      </LayoutRoot>
    </ManagementPageContext.Provider>
  );
}

export const ManagementPageTemplate = withComponentRegistration(ManagementPageTemplateImpl, {
  name: 'ManagementPageTemplate',
  category: 'template',
  portal: 'shared',
  version: '1.0.0',
  description: 'Comprehensive template for operational management pages',
});

export default ManagementPageTemplate;
