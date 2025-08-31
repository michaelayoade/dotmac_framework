/**
 * Filter Toolbar
 * Advanced filtering component with saved views and bulk operations
 */

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { clsx } from 'clsx';
import { trackAction } from '@dotmac/monitoring/observability';
import { 
  Button, 
  Input, 
  Select, 
  DatePicker, 
  Checkbox,
  Badge,
  Popover,
  Separator,
  Command,
  CommandInput,
  CommandItem,
  CommandList,
  CommandGroup
} from '@dotmac/primitives';
import { withComponentRegistration } from '@dotmac/registry';
import { 
  FilterConfig, 
  SavedViewConfig, 
  validateTemplateConfig,
  FilterConfigSchema 
} from '../types/templates';
import {
  Filter,
  X,
  Search,
  Settings,
  Save,
  Bookmark,
  RotateCcw,
  Download,
  ChevronDown,
  Plus,
  Trash2,
  Eye,
  EyeOff
} from 'lucide-react';

export interface FilterValue {
  [key: string]: any;
}

export interface FilterToolbarProps {
  filters: FilterConfig[];
  values: FilterValue;
  savedViews?: SavedViewConfig[];
  activeView?: string;
  showSearch?: boolean;
  showSavedViews?: boolean;
  showBulkActions?: boolean;
  showExport?: boolean;
  bulkActions?: Array<{
    key: string;
    label: string;
    icon?: React.ReactNode;
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
    disabled?: boolean;
  }>;
  selectedCount?: number;
  totalCount?: number;
  className?: string;
  onFilterChange: (values: FilterValue) => void;
  onViewSave?: (name: string, filters: FilterValue) => void;
  onViewLoad?: (viewId: string) => void;
  onViewDelete?: (viewId: string) => void;
  onSearch?: (query: string) => void;
  onReset?: () => void;
  onExport?: (format: 'csv' | 'excel' | 'json') => void;
  onBulkAction?: (action: string) => void;
  'data-testid'?: string;
}

function FilterToolbarImpl({
  filters = [],
  values = {},
  savedViews = [],
  activeView,
  showSearch = true,
  showSavedViews = true,
  showBulkActions = false,
  showExport = true,
  bulkActions = [],
  selectedCount = 0,
  totalCount = 0,
  className = '',
  onFilterChange,
  onViewSave,
  onViewLoad,
  onViewDelete,
  onSearch,
  onReset,
  onExport,
  onBulkAction,
  'data-testid': testId = 'filter-toolbar'
}: FilterToolbarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [saveViewName, setSaveViewName] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  // Validate filters
  const validatedFilters = useMemo(() => {
    return filters.filter(filter => {
      const validation = validateTemplateConfig(FilterConfigSchema, filter);
      return validation.isValid;
    });
  }, [filters]);

  // Get active filters count
  const activeFiltersCount = useMemo(() => {
    return Object.entries(values).filter(([key, value]) => {
      if (value === null || value === undefined || value === '') return false;
      if (Array.isArray(value) && value.length === 0) return false;
      return true;
    }).length;
  }, [values]);

  // Handle filter change
  const handleFilterChange = useCallback((key: string, value: any) => {
    const newValues = { ...values, [key]: value };
    onFilterChange(newValues);
    
    try {
      trackAction('filter_change', 'interaction', { filter: key, hasValue: !!value });
    } catch {}
  }, [values, onFilterChange]);

  // Handle search
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    onSearch?.(query);
    
    try {
      trackAction('filter_search', 'interaction', { queryLength: query.length });
    } catch {}
  }, [onSearch]);

  // Handle reset
  const handleReset = useCallback(() => {
    setSearchQuery('');
    onReset?.();
    
    try {
      trackAction('filter_reset', 'interaction');
    } catch {}
  }, [onReset]);

  // Handle save view
  const handleSaveView = useCallback(() => {
    if (!saveViewName.trim()) return;
    
    onViewSave?.(saveViewName.trim(), { ...values, searchQuery });
    setSaveViewName('');
    setShowSaveDialog(false);
    
    try {
      trackAction('saved_view_create', 'interaction', { name: saveViewName });
    } catch {}
  }, [saveViewName, values, searchQuery, onViewSave]);

  // Handle load view
  const handleLoadView = useCallback((viewId: string) => {
    onViewLoad?.(viewId);
    
    try {
      trackAction('saved_view_load', 'interaction', { viewId });
    } catch {}
  }, [onViewLoad]);

  // Handle delete view
  const handleDeleteView = useCallback((viewId: string) => {
    onViewDelete?.(viewId);
    
    try {
      trackAction('saved_view_delete', 'interaction', { viewId });
    } catch {}
  }, [onViewDelete]);

  // Handle export
  const handleExport = useCallback((format: 'csv' | 'excel' | 'json') => {
    onExport?.(format);
    
    try {
      trackAction('data_export', 'interaction', { format });
    } catch {}
  }, [onExport]);

  // Handle bulk action
  const handleBulkAction = useCallback((action: string) => {
    onBulkAction?.(action);
    
    try {
      trackAction('bulk_action', 'interaction', { action, selectedCount });
    } catch {}
  }, [onBulkAction, selectedCount]);

  // Render filter input
  const renderFilterInput = useCallback((filter: FilterConfig) => {
    const value = values[filter.key] || filter.defaultValue;
    const hasError = false; // TODO: Add validation

    switch (filter.type) {
      case 'text':
        return (
          <Input
            type="text"
            value={value || ''}
            onChange={(e) => handleFilterChange(filter.key, e.target.value)}
            placeholder={filter.placeholder || `Filter by ${filter.label}`}
            className={clsx(hasError && 'border-destructive')}
            data-testid={`${testId}-filter-${filter.key}`}
          />
        );

      case 'select':
        return (
          <Select
            value={value || ''}
            onChange={(val) => handleFilterChange(filter.key, val)}
            data-testid={`${testId}-filter-${filter.key}`}
          >
            <option value="">All {filter.label}</option>
            {filter.options?.map((option) => (
              <option 
                key={option.value} 
                value={option.value}
                disabled={option.disabled}
              >
                {option.label}
              </option>
            ))}
          </Select>
        );

      case 'multiselect':
        return (
          <Popover>
            <Popover.Trigger asChild>
              <Button
                variant="outline"
                className="justify-between"
                data-testid={`${testId}-filter-${filter.key}`}
              >
                {Array.isArray(value) && value.length > 0
                  ? `${value.length} selected`
                  : `Select ${filter.label}`}
                <ChevronDown className="h-4 w-4 opacity-50" />
              </Button>
            </Popover.Trigger>
            <Popover.Content className="w-64 p-0">
              <Command>
                <CommandInput placeholder={`Search ${filter.label}...`} />
                <CommandList>
                  <CommandGroup>
                    {filter.options?.map((option) => (
                      <CommandItem
                        key={option.value}
                        onSelect={() => {
                          const currentValues = Array.isArray(value) ? value : [];
                          const newValues = currentValues.includes(option.value)
                            ? currentValues.filter(v => v !== option.value)
                            : [...currentValues, option.value];
                          handleFilterChange(filter.key, newValues);
                        }}
                      >
                        <Checkbox
                          checked={Array.isArray(value) && value.includes(option.value)}
                          className="mr-2"
                        />
                        {option.label}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </Popover.Content>
          </Popover>
        );

      case 'date':
        return (
          <DatePicker
            value={value ? new Date(value) : null}
            onChange={(date) => handleFilterChange(filter.key, date?.toISOString())}
            placeholder={filter.placeholder || `Select ${filter.label}`}
            data-testid={`${testId}-filter-${filter.key}`}
          />
        );

      case 'dateRange':
        return (
          <div className="flex items-center space-x-2">
            <DatePicker
              value={value?.start ? new Date(value.start) : null}
              onChange={(date) => handleFilterChange(filter.key, { 
                ...value, 
                start: date?.toISOString() 
              })}
              placeholder="From"
              data-testid={`${testId}-filter-${filter.key}-start`}
            />
            <span className="text-muted-foreground">to</span>
            <DatePicker
              value={value?.end ? new Date(value.end) : null}
              onChange={(date) => handleFilterChange(filter.key, { 
                ...value, 
                end: date?.toISOString() 
              })}
              placeholder="To"
              data-testid={`${testId}-filter-${filter.key}-end`}
            />
          </div>
        );

      case 'number':
        return (
          <div className="flex items-center space-x-2">
            <Input
              type="number"
              value={value?.min || ''}
              onChange={(e) => handleFilterChange(filter.key, { 
                ...value, 
                min: e.target.value ? Number(e.target.value) : undefined 
              })}
              placeholder="Min"
              min={filter.validation?.min}
              max={filter.validation?.max}
              data-testid={`${testId}-filter-${filter.key}-min`}
            />
            <span className="text-muted-foreground">-</span>
            <Input
              type="number"
              value={value?.max || ''}
              onChange={(e) => handleFilterChange(filter.key, { 
                ...value, 
                max: e.target.value ? Number(e.target.value) : undefined 
              })}
              placeholder="Max"
              min={filter.validation?.min}
              max={filter.validation?.max}
              data-testid={`${testId}-filter-${filter.key}-max`}
            />
          </div>
        );

      case 'boolean':
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              checked={value === true}
              onChange={(checked) => handleFilterChange(filter.key, checked ? true : null)}
              data-testid={`${testId}-filter-${filter.key}`}
            />
            <span className="text-sm">{filter.label}</span>
          </div>
        );

      default:
        return null;
    }
  }, [values, handleFilterChange, testId]);

  return (
    <div className={clsx('space-y-4', className)} data-testid={testId}>
      {/* Main Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        {/* Left Section */}
        <div className="flex items-center space-x-4 flex-1 min-w-0">
          {/* Search */}
          {showSearch && (
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Search..."
                className="pl-10"
                data-testid={`${testId}-search`}
              />
            </div>
          )}

          {/* Quick Filters */}
          <div className="flex items-center space-x-2">
            {validatedFilters.slice(0, 3).map((filter) => (
              <div key={filter.key} className="min-w-0">
                <label className="text-xs text-muted-foreground mb-1 block truncate">
                  {filter.label}
                </label>
                {renderFilterInput(filter)}
              </div>
            ))}
          </div>

          {/* Advanced Filters Toggle */}
          {validatedFilters.length > 3 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center space-x-2"
              data-testid={`${testId}-advanced-toggle`}
            >
              <Filter className="h-4 w-4" />
              <span>Advanced</span>
              {activeFiltersCount > 0 && (
                <Badge variant="secondary" className="ml-1">
                  {activeFiltersCount}
                </Badge>
              )}
            </Button>
          )}
        </div>

        {/* Right Section */}
        <div className="flex items-center space-x-2">
          {/* Bulk Actions */}
          {showBulkActions && selectedCount > 0 && (
            <div className="flex items-center space-x-2">
              <span className="text-sm text-muted-foreground">
                {selectedCount} of {totalCount} selected
              </span>
              {bulkActions.map((action) => (
                <Button
                  key={action.key}
                  variant={action.variant || 'outline'}
                  size="sm"
                  disabled={action.disabled}
                  onClick={() => handleBulkAction(action.key)}
                  className="flex items-center space-x-1"
                  data-testid={`${testId}-bulk-${action.key}`}
                >
                  {action.icon && <span className="w-4 h-4">{action.icon}</span>}
                  <span>{action.label}</span>
                </Button>
              ))}
            </div>
          )}

          {/* Saved Views */}
          {showSavedViews && (
            <Popover>
              <Popover.Trigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex items-center space-x-2"
                  data-testid={`${testId}-saved-views`}
                >
                  <Bookmark className="h-4 w-4" />
                  <span>Views</span>
                  {savedViews.length > 0 && (
                    <Badge variant="secondary">{savedViews.length}</Badge>
                  )}
                </Button>
              </Popover.Trigger>
              <Popover.Content className="w-64 p-0">
                <div className="p-3 border-b">
                  <div className="flex items-center space-x-2">
                    <Input
                      value={saveViewName}
                      onChange={(e) => setSaveViewName(e.target.value)}
                      placeholder="View name..."
                      size="sm"
                    />
                    <Button
                      size="sm"
                      onClick={handleSaveView}
                      disabled={!saveViewName.trim()}
                    >
                      <Save className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="max-h-64 overflow-auto">
                  {savedViews.map((view) => (
                    <div
                      key={view.id}
                      className="flex items-center justify-between p-2 hover:bg-accent group"
                    >
                      <button
                        onClick={() => handleLoadView(view.id)}
                        className="flex-1 text-left text-sm"
                      >
                        <div className="font-medium">{view.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {view.createdAt?.toLocaleDateString()}
                        </div>
                      </button>
                      <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100">
                        {view.isDefault && (
                          <Badge variant="secondary" size="sm">Default</Badge>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteView(view.id)}
                          className="h-6 w-6 text-destructive"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                  {savedViews.length === 0 && (
                    <div className="p-4 text-center text-sm text-muted-foreground">
                      No saved views yet
                    </div>
                  )}
                </div>
              </Popover.Content>
            </Popover>
          )}

          {/* Export */}
          {showExport && (
            <Popover>
              <Popover.Trigger asChild>
                <Button
                  variant="outline"
                  size="sm"
                  className="flex items-center space-x-2"
                  data-testid={`${testId}-export`}
                >
                  <Download className="h-4 w-4" />
                  <span>Export</span>
                </Button>
              </Popover.Trigger>
              <Popover.Content className="w-48 p-2">
                <div className="space-y-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleExport('csv')}
                    className="w-full justify-start"
                  >
                    Export as CSV
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleExport('excel')}
                    className="w-full justify-start"
                  >
                    Export as Excel
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleExport('json')}
                    className="w-full justify-start"
                  >
                    Export as JSON
                  </Button>
                </div>
              </Popover.Content>
            </Popover>
          )}

          {/* Reset */}
          {(activeFiltersCount > 0 || searchQuery) && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="flex items-center space-x-2"
              data-testid={`${testId}-reset`}
            >
              <RotateCcw className="h-4 w-4" />
              <span>Reset</span>
            </Button>
          )}
        </div>
      </div>

      {/* Advanced Filters */}
      {showAdvanced && validatedFilters.length > 3 && (
        <div className="border rounded-lg p-4 bg-muted/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium">Advanced Filters</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAdvanced(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {validatedFilters.slice(3).map((filter) => (
              <div key={filter.key}>
                <label className="text-sm font-medium mb-2 block">
                  {filter.label}
                  {filter.validation?.required && (
                    <span className="text-destructive ml-1">*</span>
                  )}
                </label>
                {renderFilterInput(filter)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export const FilterToolbar = withComponentRegistration(FilterToolbarImpl, {
  name: 'FilterToolbar',
  category: 'data',
  portal: 'shared',
  version: '1.0.0',
  description: 'Advanced filtering component with saved views and bulk operations',
});

export default FilterToolbar;
