import React, { ReactNode, useState } from 'react';
import { ChevronUpIcon, ChevronDownIcon } from '@heroicons/react/24/outline';
import { LoadingSpinner } from './LoadingSpinner';
import { TableLoading } from './LoadingStates';

export interface Column<T = any> {
  key: keyof T | string;
  label: string;
  sortable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  render?: (value: any, item: T, index: number) => ReactNode;
}

export interface SortConfig {
  key: string;
  direction: 'asc' | 'desc';
}

interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
  loading?: boolean;
  empty?: ReactNode;
  sortConfig?: SortConfig;
  onSort?: (key: string) => void;
  selectable?: boolean;
  selectedRows?: string[];
  onSelectionChange?: (selectedIds: string[]) => void;
  getRowId?: (item: T) => string;
  onRowClick?: (item: T, index: number) => void;
  className?: string;
  compact?: boolean;
}

export function Table<T>({
  data,
  columns,
  loading = false,
  empty,
  sortConfig,
  onSort,
  selectable = false,
  selectedRows = [],
  onSelectionChange,
  getRowId,
  onRowClick,
  className = '',
  compact = false,
}: TableProps<T>) {
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);

  const handleSort = (key: string) => {
    if (onSort && columns.find(col => col.key === key)?.sortable) {
      onSort(key);
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange || !getRowId) return;
    
    if (checked) {
      const allIds = data.map(item => getRowId(item));
      onSelectionChange(allIds);
    } else {
      onSelectionChange([]);
    }
  };

  const handleRowSelect = (rowId: string, checked: boolean) => {
    if (!onSelectionChange) return;

    if (checked) {
      onSelectionChange([...selectedRows, rowId]);
    } else {
      onSelectionChange(selectedRows.filter(id => id !== rowId));
    }
  };

  const isAllSelected = selectable && selectedRows.length > 0 && selectedRows.length === data.length;
  const isPartiallySelected = selectable && selectedRows.length > 0 && selectedRows.length < data.length;

  if (loading) {
    return <TableLoading columns={columns.length + (selectable ? 1 : 0)} />;
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12">
        {empty || (
          <div>
            <h3 className="text-sm font-medium text-gray-900">No data available</h3>
            <p className="mt-1 text-sm text-gray-500">
              There are no items to display at this time.
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg ${className}`}>
      <table className="min-w-full divide-y divide-gray-300">
        {/* Header */}
        <thead className="bg-gray-50">
          <tr>
            {selectable && (
              <th className="relative w-12 px-6 sm:w-16 sm:px-8">
                <input
                  type="checkbox"
                  checked={isAllSelected}
                  ref={(input) => {
                    if (input) input.indeterminate = isPartiallySelected;
                  }}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="absolute left-4 top-1/2 -mt-2 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 sm:left-6"
                  aria-label="Select all rows"
                />
              </th>
            )}
            
            {columns.map((column) => (
              <th
                key={String(column.key)}
                className={`
                  px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider
                  ${column.sortable ? 'cursor-pointer hover:bg-gray-100' : ''}
                  ${column.align === 'center' ? 'text-center' : ''}
                  ${column.align === 'right' ? 'text-right' : ''}
                  ${compact ? 'px-3 py-2' : ''}
                `}
                style={{ width: column.width }}
                onClick={() => column.sortable && handleSort(String(column.key))}
              >
                <div className="flex items-center space-x-1">
                  <span>{column.label}</span>
                  {column.sortable && (
                    <span className="flex flex-col">
                      <ChevronUpIcon 
                        className={`
                          h-3 w-3 
                          ${sortConfig?.key === column.key && sortConfig.direction === 'asc' 
                            ? 'text-gray-900' 
                            : 'text-gray-400'
                          }
                        `} 
                      />
                      <ChevronDownIcon 
                        className={`
                          h-3 w-3 -mt-1
                          ${sortConfig?.key === column.key && sortConfig.direction === 'desc' 
                            ? 'text-gray-900' 
                            : 'text-gray-400'
                          }
                        `} 
                      />
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>

        {/* Body */}
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((item, index) => {
            const rowId = getRowId ? getRowId(item) : String(index);
            const isSelected = selectedRows.includes(rowId);
            
            return (
              <tr
                key={rowId}
                className={`
                  ${isSelected ? 'bg-gray-50' : 'hover:bg-gray-50'}
                  ${onRowClick ? 'cursor-pointer' : ''}
                  ${hoveredRow === index ? 'bg-gray-100' : ''}
                `}
                onClick={() => onRowClick?.(item, index)}
                onMouseEnter={() => setHoveredRow(index)}
                onMouseLeave={() => setHoveredRow(null)}
              >
                {selectable && (
                  <td className="relative w-12 px-6 sm:w-16 sm:px-8">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={(e) => handleRowSelect(rowId, e.target.checked)}
                      onClick={(e) => e.stopPropagation()}
                      className="absolute left-4 top-1/2 -mt-2 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 sm:left-6"
                      aria-label={`Select row ${index + 1}`}
                    />
                  </td>
                )}
                
                {columns.map((column) => (
                  <td
                    key={String(column.key)}
                    className={`
                      px-6 py-4 whitespace-nowrap text-sm text-gray-900
                      ${column.align === 'center' ? 'text-center' : ''}
                      ${column.align === 'right' ? 'text-right' : ''}
                      ${compact ? 'px-3 py-2' : ''}
                    `}
                  >
                    {column.render 
                      ? column.render(item[column.key as keyof T], item, index)
                      : String(item[column.key as keyof T] || '')
                    }
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Table Actions Component
interface TableActionsProps {
  children: ReactNode;
  selectedCount?: number;
  totalCount?: number;
  className?: string;
}

export function TableActions({ 
  children, 
  selectedCount, 
  totalCount, 
  className = '' 
}: TableActionsProps) {
  return (
    <div className={`flex items-center justify-between bg-white px-4 py-3 sm:px-6 ${className}`}>
      <div className="flex items-center">
        {typeof selectedCount === 'number' && typeof totalCount === 'number' && (
          <p className="text-sm text-gray-700">
            {selectedCount > 0 ? (
              <>
                <span className="font-medium">{selectedCount}</span> of{' '}
                <span className="font-medium">{totalCount}</span> selected
              </>
            ) : (
              <>
                Showing <span className="font-medium">{totalCount}</span> results
              </>
            )}
          </p>
        )}
      </div>
      
      <div className="flex items-center space-x-3">
        {children}
      </div>
    </div>
  );
}

// Pagination Component
interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  itemsPerPage: number;
  totalItems: number;
  className?: string;
  compact?: boolean;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  itemsPerPage,
  totalItems,
  className = '',
  compact = false,
}: PaginationProps) {
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  const getVisiblePages = () => {
    const delta = 2;
    const range = [];
    const rangeWithDots = [];

    for (let i = Math.max(2, currentPage - delta); 
         i <= Math.min(totalPages - 1, currentPage + delta); 
         i++) {
      range.push(i);
    }

    if (currentPage - delta > 2) {
      rangeWithDots.push(1, '...');
    } else {
      rangeWithDots.push(1);
    }

    rangeWithDots.push(...range);

    if (currentPage + delta < totalPages - 1) {
      rangeWithDots.push('...', totalPages);
    } else {
      rangeWithDots.push(totalPages);
    }

    return rangeWithDots;
  };

  if (totalPages <= 1) return null;

  return (
    <div className={`flex items-center justify-between bg-white px-4 py-3 sm:px-6 ${className}`}>
      {!compact && (
        <div>
          <p className="text-sm text-gray-700">
            Showing <span className="font-medium">{startItem}</span> to{' '}
            <span className="font-medium">{endItem}</span> of{' '}
            <span className="font-medium">{totalItems}</span> results
          </p>
        </div>
      )}
      
      <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
        >
          <span className="sr-only">Previous</span>
          <ChevronUpIcon className="h-5 w-5 rotate-90" aria-hidden="true" />
        </button>
        
        {getVisiblePages().map((page, index) => (
          <React.Fragment key={index}>
            {page === '...' ? (
              <span className="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-inset ring-gray-300">
                ...
              </span>
            ) : (
              <button
                onClick={() => onPageChange(Number(page))}
                className={`
                  relative inline-flex items-center px-4 py-2 text-sm font-semibold ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0
                  ${currentPage === page 
                    ? 'z-10 bg-primary-600 text-white focus:ring-primary-600' 
                    : 'text-gray-900'
                  }
                `}
              >
                {page}
              </button>
            )}
          </React.Fragment>
        ))}
        
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
        >
          <span className="sr-only">Next</span>
          <ChevronDownIcon className="h-5 w-5 -rotate-90" aria-hidden="true" />
        </button>
      </nav>
    </div>
  );
}