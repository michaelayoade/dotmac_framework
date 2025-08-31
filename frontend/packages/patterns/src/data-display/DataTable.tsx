/**
 * Advanced Data Table Component
 * 
 * High-performance data table with virtualization, sorting, filtering,
 * pagination, and security features built-in
 */

import React, { useMemo, useState, useCallback, useEffect } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  ColumnDef,
  flexRender,
  SortingState,
  ColumnFiltersState,
  PaginationState,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { clsx } from 'clsx';
import { ArrowUpDown, ArrowUp, ArrowDown, Search, Filter, MoreHorizontal } from 'lucide-react';
import { Button } from '@dotmac/primitives';
import { Input } from '@dotmac/primitives';
import { withComponentRegistration } from '@dotmac/registry';
import { useInputValidation } from '@dotmac/security';

// Data table types
export interface DataTableProps<TData = any> {
  data: TData[];
  columns: ColumnDef<TData>[];
  
  // Virtualization
  enableVirtualization?: boolean;
  estimateRowHeight?: () => number;
  overscan?: number;
  
  // Features
  enableSorting?: boolean;
  enableFiltering?: boolean;
  enableGlobalFilter?: boolean;
  enablePagination?: boolean;
  enableRowSelection?: boolean;
  
  // Pagination
  pageSize?: number;
  pageSizeOptions?: number[];
  
  // Styling
  className?: string;
  headerClassName?: string;
  rowClassName?: string | ((row: any) => string);
  cellClassName?: string | ((cell: any) => string);
  
  // Events
  onRowSelect?: (selectedRows: TData[]) => void;
  onRowClick?: (row: TData, index: number) => void;
  onSort?: (sorting: SortingState) => void;
  onFilter?: (filters: ColumnFiltersState) => void;
  
  // Loading state
  isLoading?: boolean;
  loadingComponent?: React.ReactNode;
  
  // Empty state
  emptyComponent?: React.ReactNode;
  
  // Security
  sanitizeData?: boolean;
  allowHtml?: boolean;
  
  // Accessibility
  ariaLabel?: string;
  caption?: string;
}

function DataTableImpl<TData = any>({
  data,
  columns,
  enableVirtualization = false,
  estimateRowHeight = () => 50,
  overscan = 5,
  enableSorting = true,
  enableFiltering = true,
  enableGlobalFilter = true,
  enablePagination = true,
  enableRowSelection = false,
  pageSize = 10,
  pageSizeOptions = [10, 20, 50, 100],
  className,
  headerClassName,
  rowClassName,
  cellClassName,
  onRowSelect,
  onRowClick,
  onSort,
  onFilter,
  isLoading = false,
  loadingComponent,
  emptyComponent,
  sanitizeData = true,
  allowHtml = false,
  ariaLabel,
  caption,
}: DataTableProps<TData>) {
  // State management
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize,
  });
  const [rowSelection, setRowSelection] = useState({});

  // Security validation for global filter
  const { validateInput } = useInputValidation();

  // Memoized columns with security considerations
  const secureColumns = useMemo(() => {
    if (!sanitizeData && allowHtml) return columns;
    
    return columns.map(column => ({
      ...column,
      cell: column.cell ? (info: any) => {
        const originalCell = typeof column.cell === 'function' 
          ? column.cell(info)
          : column.cell;
        
        // Sanitize cell content if needed
        if (sanitizeData && typeof originalCell === 'string') {
          const result = validateInput(originalCell);
          return result.sanitizedValue;
        }
        
        return originalCell;
      } : column.cell,
    }));
  }, [columns, sanitizeData, allowHtml, validateInput]);

  // Table instance
  const table = useReactTable({
    data,
    columns: secureColumns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
      pagination,
      rowSelection,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    onPaginationChange: setPagination,
    onRowSelectionChange: setRowSelection,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
    getFilteredRowModel: enableFiltering ? getFilteredRowModel() : undefined,
    getPaginationRowModel: enablePagination ? getPaginationRowModel() : undefined,
    enableRowSelection,
    enableSorting,
    enableFiltering,
    enableGlobalFiltering: enableGlobalFilter,
  });

  // Virtualization setup
  const parentRef = React.useRef<HTMLDivElement>(null);
  const rows = table.getRowModel().rows;

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: estimateRowHeight,
    overscan,
    enabled: enableVirtualization,
  });

  // Event handlers
  const handleGlobalFilterChange = useCallback((value: string) => {
    if (sanitizeData) {
      const result = validateInput(value);
      setGlobalFilter(result.sanitizedValue);
    } else {
      setGlobalFilter(value);
    }
  }, [sanitizeData, validateInput]);

  const handleRowClick = useCallback((row: any, index: number) => {
    onRowClick?.(row.original, index);
  }, [onRowClick]);

  // Update external handlers
  useEffect(() => {
    onSort?.(sorting);
  }, [sorting, onSort]);

  useEffect(() => {
    onFilter?.(columnFilters);
  }, [columnFilters, onFilter]);

  useEffect(() => {
    if (onRowSelect) {
      const selectedRows = table.getSelectedRowModel().rows.map(row => row.original);
      onRowSelect(selectedRows);
    }
  }, [rowSelection, onRowSelect, table]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        {loadingComponent || (
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        )}
      </div>
    );
  }

  // Empty state
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 text-muted-foreground">
        {emptyComponent || 'No data available'}
      </div>
    );
  }

  return (
    <div className={clsx('w-full', className)}>
      {/* Global Filter */}
      {enableGlobalFilter && (
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center space-x-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search all columns..."
              value={globalFilter}
              onChange={(e) => handleGlobalFilterChange(e.target.value)}
              className="max-w-sm"
            />
          </div>
        </div>
      )}

      {/* Table Container */}
      <div className="rounded-md border">
        <div
          ref={parentRef}
          className={clsx(
            'overflow-auto',
            enableVirtualization && 'max-h-96'
          )}
        >
          <table 
            className="w-full caption-bottom text-sm"
            aria-label={ariaLabel}
          >
            {caption && <caption className="mt-4 text-sm text-muted-foreground">{caption}</caption>}
            
            {/* Header */}
            <thead className={clsx('[&_tr]:border-b', headerClassName)}>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0"
                    >
                      {header.isPlaceholder ? null : (
                        <div className="flex items-center space-x-2">
                          <div
                            className={clsx(
                              enableSorting && header.column.getCanSort() && 'cursor-pointer select-none',
                              'flex items-center space-x-1'
                            )}
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            
                            {enableSorting && header.column.getCanSort() && (
                              <span className="ml-2">
                                {header.column.getIsSorted() === 'desc' ? (
                                  <ArrowDown className="h-4 w-4" />
                                ) : header.column.getIsSorted() === 'asc' ? (
                                  <ArrowUp className="h-4 w-4" />
                                ) : (
                                  <ArrowUpDown className="h-4 w-4 opacity-50" />
                                )}
                              </span>
                            )}
                          </div>
                          
                          {enableFiltering && header.column.getCanFilter() && (
                            <Filter className="h-3 w-3 opacity-50" />
                          )}
                        </div>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>

            {/* Body */}
            <tbody className="[&_tr:last-child]:border-0">
              {enableVirtualization ? (
                // Virtualized rows
                <tr>
                  <td colSpan={columns.length} className="p-0">
                    <div
                      style={{
                        height: `${virtualizer.getTotalSize()}px`,
                        width: '100%',
                        position: 'relative',
                      }}
                    >
                      {virtualizer.getVirtualItems().map((virtualRow) => {
                        const row = rows[virtualRow.index];
                        return (
                          <div
                            key={row.id}
                            style={{
                              position: 'absolute',
                              top: 0,
                              left: 0,
                              width: '100%',
                              height: `${virtualRow.size}px`,
                              transform: `translateY(${virtualRow.start}px)`,
                            }}
                          >
                            <div
                              className={clsx(
                                'border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted',
                                typeof rowClassName === 'function' 
                                  ? rowClassName(row) 
                                  : rowClassName,
                                onRowClick && 'cursor-pointer'
                              )}
                              onClick={() => handleRowClick(row, virtualRow.index)}
                            >
                              {row.getVisibleCells().map((cell) => (
                                <div
                                  key={cell.id}
                                  className={clsx(
                                    'p-4 align-middle [&:has([role=checkbox])]:pr-0',
                                    typeof cellClassName === 'function' 
                                      ? cellClassName(cell) 
                                      : cellClassName
                                  )}
                                  style={{ display: 'table-cell' }}
                                >
                                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </td>
                </tr>
              ) : (
                // Regular rows
                rows.map((row, index) => (
                  <tr
                    key={row.id}
                    data-state={row.getIsSelected() && 'selected'}
                    className={clsx(
                      'border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted',
                      typeof rowClassName === 'function' 
                        ? rowClassName(row) 
                        : rowClassName,
                      onRowClick && 'cursor-pointer'
                    )}
                    onClick={() => handleRowClick(row, index)}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td
                        key={cell.id}
                        className={clsx(
                          'p-4 align-middle [&:has([role=checkbox])]:pr-0',
                          typeof cellClassName === 'function' 
                            ? cellClassName(cell) 
                            : cellClassName
                        )}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {enablePagination && (
          <div className="flex items-center justify-between space-x-2 p-4">
            <div className="flex items-center space-x-2">
              <p className="text-sm font-medium">Rows per page</p>
              <select
                value={table.getState().pagination.pageSize}
                onChange={(e) => {
                  table.setPageSize(Number(e.target.value));
                }}
                className="h-8 w-16 rounded border border-input bg-background px-2 text-sm"
              >
                {pageSizeOptions.map((pageSize) => (
                  <option key={pageSize} value={pageSize}>
                    {pageSize}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center space-x-6 lg:space-x-8">
              <div className="flex w-24 items-center justify-center text-sm font-medium">
                Page {table.getState().pagination.pageIndex + 1} of{' '}
                {table.getPageCount()}
              </div>
              
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  className="h-8 w-8 p-0"
                  onClick={() => table.setPageIndex(0)}
                  disabled={!table.getCanPreviousPage()}
                >
                  <span className="sr-only">Go to first page</span>
                  {'<<'}
                </Button>
                <Button
                  variant="outline"
                  className="h-8 w-8 p-0"
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                >
                  <span className="sr-only">Go to previous page</span>
                  {'<'}
                </Button>
                <Button
                  variant="outline"
                  className="h-8 w-8 p-0"
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                >
                  <span className="sr-only">Go to next page</span>
                  {'>'}
                </Button>
                <Button
                  variant="outline"
                  className="h-8 w-8 p-0"
                  onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                  disabled={!table.getCanNextPage()}
                >
                  <span className="sr-only">Go to last page</span>
                  {'>>'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Selection Summary */}
        {enableRowSelection && Object.keys(rowSelection).length > 0 && (
          <div className="border-t bg-muted/50 p-2">
            <div className="text-sm text-muted-foreground">
              {table.getSelectedRowModel().rows.length} of{' '}
              {table.getRowModel().rows.length} row(s) selected
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export const DataTable = withComponentRegistration(DataTableImpl as any, {
  name: 'DataTable',
  category: 'data-display',
  portal: 'shared',
  version: '1.0.0',
  description: 'Advanced data table with virtualization and security features',
  props: {
    data: { type: 'Array', required: true, description: 'Table data array' },
    columns: { type: 'Array', required: true, description: 'Column definitions' },
    enableVirtualization: { type: 'boolean', defaultValue: false, description: 'Enable row virtualization for large datasets' },
    enableSorting: { type: 'boolean', defaultValue: true, description: 'Enable column sorting' },
    enableFiltering: { type: 'boolean', defaultValue: true, description: 'Enable column filtering' },
  },
  accessibility: {
    ariaSupport: true,
    keyboardSupport: true,
    screenReaderSupport: true,
    wcagLevel: 'AA',
  },
  security: {
    xssProtection: true,
    inputSanitization: true,
    outputEncoding: true,
  },
  performance: {
    lazyLoading: true,
    memoization: true,
    renderingCost: 'medium',
  },
});
