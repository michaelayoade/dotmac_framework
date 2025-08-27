/**
 * DataTable Component
 * Enterprise-grade data table with sorting, filtering, pagination, and accessibility
 */

'use client';

import React, { useState, useMemo, useCallback, ReactNode } from 'react';
import { ChevronUp, ChevronDown, Search, Filter, Download, MoreHorizontal, RefreshCw } from 'lucide-react';
import { cn } from '../../design-system/utils';

// Types
export type SortDirection = 'asc' | 'desc' | null;

export interface TableColumn<T = any> {
  key: keyof T | string;
  header: string | ReactNode;
  accessor: (item: T) => ReactNode;
  sortable?: boolean;
  filterable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

export interface TableData {
  id: string | number;
  [key: string]: any;
}

export interface DataTableProps<T extends TableData = TableData> {
  data: T[];
  columns: TableColumn<T>[];
  loading?: boolean;
  error?: string | null;
  title?: string;
  description?: string;
  searchable?: boolean;
  filterable?: boolean;
  sortable?: boolean;
  exportable?: boolean;
  refreshable?: boolean;
  selectable?: boolean;
  pageSize?: number;
  className?: string;
  emptyState?: ReactNode;
  loadingRows?: number;
  onRowClick?: (item: T) => void;
  onSelectionChange?: (selectedIds: (string | number)[]) => void;
  onRefresh?: () => void;
  onExport?: () => void;
}

interface FilterState {
  [key: string]: string;
}

export function DataTable<T extends TableData>({
  data,
  columns,
  loading = false,
  error = null,
  title,
  description,
  searchable = true,
  filterable = false,
  sortable = true,
  exportable = false,
  refreshable = false,
  selectable = false,
  pageSize = 10,
  className = '',
  emptyState,
  loadingRows = 5,
  onRowClick,
  onSelectionChange,
  onRefresh,
  onExport,
}: DataTableProps<T>) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortConfig, setSortConfig] = useState<{
    key: string;
    direction: SortDirection;
  }>({ key: '', direction: null });
  const [filters, setFilters] = useState<FilterState>({});
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedItems, setSelectedItems] = useState<Set<string | number>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  // Memoized filtered and sorted data
  const processedData = useMemo(() => {
    let result = [...data];

    // Apply search
    if (searchQuery && searchable) {
      const query = searchQuery.toLowerCase();
      result = result.filter(item =>
        columns.some(col => {
          const value = col.accessor(item);
          return String(value).toLowerCase().includes(query);
        })
      );
    }

    // Apply filters
    if (filterable) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) {
          const column = columns.find(col => col.key === key);
          if (column) {
            result = result.filter(item => {
              const itemValue = String(column.accessor(item)).toLowerCase();
              return itemValue.includes(value.toLowerCase());
            });
          }
        }
      });
    }

    // Apply sorting
    if (sortConfig.key && sortConfig.direction && sortable) {
      result.sort((a, b) => {
        const column = columns.find(col => col.key === sortConfig.key);
        if (!column) return 0;

        const aValue = column.accessor(a);
        const bValue = column.accessor(b);

        if (aValue < bValue) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }

    return result;
  }, [data, searchQuery, sortConfig, filters, columns, searchable, filterable, sortable]);

  // Pagination
  const totalPages = Math.ceil(processedData.length / pageSize);
  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return processedData.slice(startIndex, startIndex + pageSize);
  }, [processedData, currentPage, pageSize]);

  const handleSort = useCallback((columnKey: string) => {
    if (!sortable) return;
    
    const column = columns.find(col => col.key === columnKey);
    if (!column?.sortable) return;

    setSortConfig(prev => {
      if (prev.key === columnKey) {
        const direction = prev.direction === 'asc' ? 'desc' : prev.direction === 'desc' ? null : 'asc';
        return { key: direction ? columnKey : '', direction };
      }
      return { key: columnKey, direction: 'asc' };
    });
  }, [columns, sortable]);

  const handleSelectItem = useCallback((id: string | number) => {
    if (!selectable) return;

    setSelectedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      onSelectionChange?.(Array.from(newSet));
      return newSet;
    });
  }, [selectable, onSelectionChange]);

  const handleSelectAll = useCallback(() => {
    if (!selectable) return;

    const allIds = paginatedData.map(item => item.id);
    const allSelected = allIds.every(id => selectedItems.has(id));
    
    if (allSelected) {
      const newSet = new Set(selectedItems);
      allIds.forEach(id => newSet.delete(id));
      setSelectedItems(newSet);
      onSelectionChange?.(Array.from(newSet));
    } else {
      const newSet = new Set([...selectedItems, ...allIds]);
      setSelectedItems(newSet);
      onSelectionChange?.(Array.from(newSet));
    }
  }, [selectable, paginatedData, selectedItems, onSelectionChange]);

  const renderSortIcon = (columnKey: string) => {
    if (!sortable || sortConfig.key !== columnKey) {
      return <ChevronUp className="w-4 h-4 opacity-0" />;
    }
    
    if (sortConfig.direction === 'asc') {
      return <ChevronUp className="w-4 h-4 text-blue-600" />;
    }
    if (sortConfig.direction === 'desc') {
      return <ChevronDown className="w-4 h-4 text-blue-600" />;
    }
    return <ChevronUp className="w-4 h-4 opacity-0" />;
  };

  const renderLoadingSkeleton = () => (
    <>
      {Array.from({ length: loadingRows }).map((_, index) => (
        <tr key={index}>
          {selectable && (
            <td className="px-6 py-4">
              <div className="w-4 h-4 bg-gray-200 rounded animate-pulse" />
            </td>
          )}
          {columns.map((col, colIndex) => (
            <td key={colIndex} className="px-6 py-4">
              <div className="h-4 bg-gray-200 rounded animate-pulse" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );

  const renderEmptyState = () => (
    <tr>
      <td colSpan={columns.length + (selectable ? 1 : 0)} className="px-6 py-12 text-center">
        {emptyState || (
          <div className="text-gray-500">
            <div className="text-lg font-medium mb-2">No data available</div>
            <div className="text-sm">There are no items to display at the moment.</div>
          </div>
        )}
      </td>
    </tr>
  );

  const renderErrorState = () => (
    <tr>
      <td colSpan={columns.length + (selectable ? 1 : 0)} className="px-6 py-12 text-center">
        <div className="text-red-600">
          <div className="text-lg font-medium mb-2">Error loading data</div>
          <div className="text-sm">{error}</div>
        </div>
      </td>
    </tr>
  );

  return (
    <div className={cn('bg-white rounded-lg border', className)}>
      {/* Header */}
      {(title || searchable || filterable || exportable || refreshable) && (
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  {title}
                </h3>
              )}
              {description && (
                <p className="text-sm text-gray-600">{description}</p>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              {searchable && (
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input
                    type="text"
                    placeholder="Search..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              )}
              
              {filterable && (
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className={cn(
                    'p-2 border border-gray-300 rounded-lg hover:bg-gray-50',
                    showFilters && 'bg-blue-50 border-blue-300'
                  )}
                >
                  <Filter className="w-4 h-4" />
                </button>
              )}
              
              {refreshable && onRefresh && (
                <button
                  onClick={onRefresh}
                  disabled={loading}
                  className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                >
                  <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
                </button>
              )}
              
              {exportable && onExport && (
                <button
                  onClick={onExport}
                  className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  <Download className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
          
          {/* Filters */}
          {filterable && showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {columns.filter(col => col.filterable).map(col => (
                  <div key={String(col.key)}>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {typeof col.header === 'string' ? col.header : 'Filter'}
                    </label>
                    <input
                      type="text"
                      placeholder={`Filter by ${typeof col.header === 'string' ? col.header.toLowerCase() : 'value'}`}
                      value={filters[String(col.key)] || ''}
                      onChange={(e) => setFilters(prev => ({
                        ...prev,
                        [String(col.key)]: e.target.value
                      }))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {selectable && (
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={paginatedData.length > 0 && paginatedData.every(item => selectedItems.has(item.id))}
                    onChange={handleSelectAll}
                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                </th>
              )}
              {columns.map((column) => (
                <th
                  key={String(column.key)}
                  className={cn(
                    'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider',
                    column.sortable && sortable && 'cursor-pointer hover:bg-gray-100',
                    column.align === 'center' && 'text-center',
                    column.align === 'right' && 'text-right',
                    column.className
                  )}
                  style={{ width: column.width }}
                  onClick={() => handleSort(String(column.key))}
                >
                  <div className="flex items-center justify-between">
                    <span>{column.header}</span>
                    {column.sortable && sortable && renderSortIcon(String(column.key))}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? renderLoadingSkeleton() :
             error ? renderErrorState() :
             processedData.length === 0 ? renderEmptyState() :
             paginatedData.map((item) => (
              <tr
                key={item.id}
                className={cn(
                  'hover:bg-gray-50',
                  onRowClick && 'cursor-pointer',
                  selectedItems.has(item.id) && 'bg-blue-50'
                )}
                onClick={() => onRowClick?.(item)}
              >
                {selectable && (
                  <td className="px-6 py-4">
                    <input
                      type="checkbox"
                      checked={selectedItems.has(item.id)}
                      onChange={(e) => {
                        e.stopPropagation();
                        handleSelectItem(item.id);
                      }}
                      className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                  </td>
                )}
                {columns.map((column) => (
                  <td
                    key={String(column.key)}
                    className={cn(
                      'px-6 py-4 whitespace-nowrap text-sm text-gray-900',
                      column.align === 'center' && 'text-center',
                      column.align === 'right' && 'text-right',
                      column.className
                    )}
                  >
                    {column.accessor(item)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-6 py-3 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
            
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Showing{' '}
                  <span className="font-medium">
                    {Math.min((currentPage - 1) * pageSize + 1, processedData.length)}
                  </span>{' '}
                  to{' '}
                  <span className="font-medium">
                    {Math.min(currentPage * pageSize, processedData.length)}
                  </span>{' '}
                  of{' '}
                  <span className="font-medium">{processedData.length}</span>{' '}
                  results
                </p>
              </div>
              
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                    disabled={currentPage === 1}
                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <span className="sr-only">Previous</span>
                    <ChevronDown className="h-5 w-5 rotate-90" />
                  </button>
                  
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(page => 
                      page === 1 || 
                      page === totalPages || 
                      (page >= currentPage - 2 && page <= currentPage + 2)
                    )
                    .map((page, index, array) => (
                      <React.Fragment key={page}>
                        {index > 0 && array[index - 1] !== page - 1 && (
                          <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700">
                            ...
                          </span>
                        )}
                        <button
                          onClick={() => setCurrentPage(page)}
                          className={cn(
                            'relative inline-flex items-center px-4 py-2 border text-sm font-medium',
                            currentPage === page
                              ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                              : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                          )}
                        >
                          {page}
                        </button>
                      </React.Fragment>
                    ))}
                  
                  <button
                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                    disabled={currentPage === totalPages}
                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <span className="sr-only">Next</span>
                    <ChevronDown className="h-5 w-5 -rotate-90" />
                  </button>
                </nav>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}