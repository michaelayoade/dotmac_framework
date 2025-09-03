'use client';

import React, { useState, useMemo, useCallback } from 'react';
import {
  Calendar,
  Filter,
  Search,
  Download,
  Eye,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle,
  AlertCircle,
  FileText,
  CreditCard,
  DollarSign,
} from 'lucide-react';
import {
  cn,
  formatCurrency,
  formatDate,
  formatPaymentMethod,
  getPaymentStatusColor,
  getPaymentStatusIcon,
  filterBySearch,
  applyFilters,
  sortByDate,
  debounce,
} from '../utils';
import type { Invoice, Payment, BillingFilters, BillingPortalType } from '../types';

interface UniversalBillingHistoryProps {
  invoices?: Invoice[];
  payments?: Payment[];
  onViewInvoice?: (invoiceId: string) => void;
  onDownloadInvoice?: (invoiceId: string) => void;
  onRetryPayment?: (paymentId: string) => void;
  onRefundPayment?: (paymentId: string) => void;
  portalType?: BillingPortalType;
  currency?: string;
  className?: string;
  showFilters?: boolean;
  showExport?: boolean;
  showSearch?: boolean;
  itemsPerPage?: number;
}

type ViewMode = 'all' | 'invoices' | 'payments';
type SortField = 'date' | 'amount' | 'status';
type SortDirection = 'asc' | 'desc';

interface ExtendedFilters extends BillingFilters {
  viewMode: ViewMode;
  sortField: SortField;
  sortDirection: SortDirection;
}

export function UniversalBillingHistory({
  invoices = [],
  payments = [],
  onViewInvoice,
  onDownloadInvoice,
  onRetryPayment,
  onRefundPayment,
  portalType = 'customer',
  currency = 'USD',
  className,
  showFilters = true,
  showExport = true,
  showSearch = true,
  itemsPerPage = 10,
}: UniversalBillingHistoryProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [filters, setFilters] = useState<ExtendedFilters>({
    status: '',
    dateFrom: '',
    dateTo: '',
    paymentMethod: '',
    gateway: '',
    viewMode: 'all',
    sortField: 'date',
    sortDirection: 'desc',
  });

  // Debounced search
  const debouncedSetSearchQuery = useMemo(
    () =>
      debounce((query: string) => {
        setSearchQuery(query);
        setCurrentPage(1);
      }, 300),
    []
  );

  // Combined data with type discrimination
  const combinedData = useMemo(() => {
    const invoiceItems = invoices.map((invoice) => ({
      ...invoice,
      type: 'invoice' as const,
      date: invoice.issueDate,
      amount: invoice.totalAmount,
      description: `Invoice ${invoice.invoiceNumber}`,
      searchableText: `${invoice.invoiceNumber} ${invoice.customerName} ${invoice.customerEmail}`,
    }));

    const paymentItems = payments.map((payment) => ({
      ...payment,
      type: 'payment' as const,
      date: payment.createdAt,
      description: `Payment ${payment.id}`,
      searchableText: `${payment.id} ${payment.customerName} ${formatPaymentMethod(payment.method)}`,
    }));

    return [...invoiceItems, ...paymentItems];
  }, [invoices, payments]);

  // Filter and sort data
  const filteredData = useMemo(() => {
    let data = combinedData;

    // Apply view mode filter
    if (filters.viewMode !== 'all') {
      data = data.filter((item) => item.type === filters.viewMode.slice(0, -1)); // Remove 's' from 'invoices'/'payments'
    }

    // Apply search
    if (searchQuery.trim()) {
      data = filterBySearch(data, searchQuery, ['searchableText']);
    }

    // Apply other filters
    const filterObj = { ...filters };
    const { viewMode, sortField, sortDirection, ...otherFilters } = filterObj;

    data = applyFilters(data, otherFilters);

    // Apply sorting
    data = data.sort((a, b) => {
      let aValue: any = a[filters.sortField === 'date' ? 'date' : filters.sortField];
      let bValue: any = b[filters.sortField === 'date' ? 'date' : filters.sortField];

      if (filters.sortField === 'date') {
        aValue = new Date(aValue).getTime();
        bValue = new Date(bValue).getTime();
      } else if (filters.sortField === 'amount') {
        aValue = typeof aValue === 'number' ? aValue : 0;
        bValue = typeof bValue === 'number' ? bValue : 0;
      } else {
        aValue = String(aValue).toLowerCase();
        bValue = String(bValue).toLowerCase();
      }

      if (filters.sortDirection === 'asc') {
        return aValue > bValue ? 1 : -1;
      }
      return aValue < bValue ? 1 : -1;
    });

    return data;
  }, [combinedData, searchQuery, filters]);

  // Paginated data
  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredData.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredData, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);

  // Summary statistics
  const stats = useMemo(() => {
    const totalInvoices = invoices.length;
    const totalPayments = payments.length;
    const totalInvoiceAmount = invoices.reduce((sum, inv) => sum + inv.totalAmount, 0);
    const totalPaymentAmount = payments.reduce((sum, pay) => sum + pay.amount, 0);
    const pendingInvoices = invoices.filter((inv) =>
      ['sent', 'overdue'].includes(inv.status)
    ).length;
    const failedPayments = payments.filter((pay) => pay.status === 'failed').length;

    return {
      totalInvoices,
      totalPayments,
      totalInvoiceAmount,
      totalPaymentAmount,
      pendingInvoices,
      failedPayments,
      netBalance: totalInvoiceAmount - totalPaymentAmount,
    };
  }, [invoices, payments]);

  const handleFilterChange = useCallback((key: keyof ExtendedFilters, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setCurrentPage(1);
  }, []);

  const handleExport = useCallback(() => {
    const csv = [
      ['Type', 'Date', 'Description', 'Amount', 'Status'].join(','),
      ...filteredData.map((item) =>
        [item.type, formatDate(item.date), `"${item.description}"`, item.amount, item.status].join(
          ','
        )
      ),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `billing-history-${formatDate(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [filteredData]);

  const getItemIcon = (item: any) => {
    if (item.type === 'invoice') {
      return <FileText className='w-4 h-4 text-blue-600' />;
    }
    return <CreditCard className='w-4 h-4 text-green-600' />;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
      case 'completed':
        return <CheckCircle className='w-4 h-4 text-green-600' />;
      case 'pending':
      case 'processing':
        return <Clock className='w-4 h-4 text-yellow-600' />;
      case 'overdue':
      case 'failed':
        return <AlertCircle className='w-4 h-4 text-red-600' />;
      default:
        return <Clock className='w-4 h-4 text-gray-600' />;
    }
  };

  const renderSummaryCards = () => (
    <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6'>
      <div className='bg-white rounded-lg border border-gray-200 p-4'>
        <div className='flex items-center justify-between'>
          <div>
            <p className='text-sm font-medium text-gray-600'>Total Invoices</p>
            <p className='text-2xl font-bold text-gray-900'>{stats.totalInvoices}</p>
            <p className='text-sm text-gray-500'>
              {formatCurrency(stats.totalInvoiceAmount, currency)}
            </p>
          </div>
          <FileText className='w-8 h-8 text-blue-600' />
        </div>
      </div>

      <div className='bg-white rounded-lg border border-gray-200 p-4'>
        <div className='flex items-center justify-between'>
          <div>
            <p className='text-sm font-medium text-gray-600'>Total Payments</p>
            <p className='text-2xl font-bold text-gray-900'>{stats.totalPayments}</p>
            <p className='text-sm text-gray-500'>
              {formatCurrency(stats.totalPaymentAmount, currency)}
            </p>
          </div>
          <CreditCard className='w-8 h-8 text-green-600' />
        </div>
      </div>

      <div className='bg-white rounded-lg border border-gray-200 p-4'>
        <div className='flex items-center justify-between'>
          <div>
            <p className='text-sm font-medium text-gray-600'>Pending Invoices</p>
            <p className='text-2xl font-bold text-orange-600'>{stats.pendingInvoices}</p>
            <p className='text-sm text-gray-500'>Awaiting payment</p>
          </div>
          <Clock className='w-8 h-8 text-orange-600' />
        </div>
      </div>

      <div className='bg-white rounded-lg border border-gray-200 p-4'>
        <div className='flex items-center justify-between'>
          <div>
            <p className='text-sm font-medium text-gray-600'>Net Balance</p>
            <p
              className={cn(
                'text-2xl font-bold',
                stats.netBalance >= 0 ? 'text-green-600' : 'text-red-600'
              )}
            >
              {formatCurrency(Math.abs(stats.netBalance), currency)}
            </p>
            <div className='flex items-center text-sm'>
              {stats.netBalance >= 0 ? (
                <TrendingUp className='w-3 h-3 text-green-600 mr-1' />
              ) : (
                <TrendingDown className='w-3 h-3 text-red-600 mr-1' />
              )}
              <span className={stats.netBalance >= 0 ? 'text-green-600' : 'text-red-600'}>
                {stats.netBalance >= 0 ? 'Credit' : 'Debit'}
              </span>
            </div>
          </div>
          <DollarSign
            className={cn('w-8 h-8', stats.netBalance >= 0 ? 'text-green-600' : 'text-red-600')}
          />
        </div>
      </div>
    </div>
  );

  const renderFilters = () =>
    showFilterPanel && (
      <div className='bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6'>
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>View</label>
            <select
              value={filters.viewMode}
              onChange={(e) => handleFilterChange('viewMode', e.target.value)}
              className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            >
              <option value='all'>All Transactions</option>
              <option value='invoices'>Invoices Only</option>
              <option value='payments'>Payments Only</option>
            </select>
          </div>

          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>Status</label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            >
              <option value=''>All Statuses</option>
              <option value='paid'>Paid</option>
              <option value='pending'>Pending</option>
              <option value='overdue'>Overdue</option>
              <option value='failed'>Failed</option>
              <option value='cancelled'>Cancelled</option>
            </select>
          </div>

          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>From Date</label>
            <input
              type='date'
              value={filters.dateFrom}
              onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
              className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            />
          </div>

          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>To Date</label>
            <input
              type='date'
              value={filters.dateTo}
              onChange={(e) => handleFilterChange('dateTo', e.target.value)}
              className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            />
          </div>
        </div>

        <div className='flex justify-between items-center mt-4 pt-4 border-t border-gray-200'>
          <div className='text-sm text-gray-600'>
            Showing {filteredData.length} of {combinedData.length} transactions
          </div>
          <button
            onClick={() => {
              setFilters({
                status: '',
                dateFrom: '',
                dateTo: '',
                paymentMethod: '',
                gateway: '',
                viewMode: 'all',
                sortField: 'date',
                sortDirection: 'desc',
              });
              setSearchQuery('');
              setCurrentPage(1);
            }}
            className='text-sm text-blue-600 hover:text-blue-800'
          >
            Clear Filters
          </button>
        </div>
      </div>
    );

  const renderPagination = () =>
    totalPages > 1 && (
      <div className='flex items-center justify-between mt-6'>
        <div className='text-sm text-gray-700'>
          Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
          {Math.min(currentPage * itemsPerPage, filteredData.length)} of {filteredData.length}{' '}
          results
        </div>
        <div className='flex items-center space-x-2'>
          <button
            onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
            className='px-3 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed'
          >
            Previous
          </button>

          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            const pageNum = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
            return (
              <button
                key={pageNum}
                onClick={() => setCurrentPage(pageNum)}
                className={cn(
                  'px-3 py-2 border rounded-md text-sm',
                  currentPage === pageNum
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'border-gray-300 hover:bg-gray-50'
                )}
              >
                {pageNum}
              </button>
            );
          })}

          <button
            onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
            className='px-3 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed'
          >
            Next
          </button>
        </div>
      </div>
    );

  return (
    <div className={cn('space-y-6', className)}>
      <div className='flex items-center justify-between'>
        <h2 className='text-xl font-semibold text-gray-900'>Billing History</h2>
        <div className='flex items-center space-x-2'>
          {showExport && (
            <button
              onClick={handleExport}
              className='flex items-center px-3 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 text-sm'
            >
              <Download className='w-4 h-4 mr-2' />
              Export
            </button>
          )}
          {showFilters && (
            <button
              onClick={() => setShowFilterPanel(!showFilterPanel)}
              className={cn(
                'flex items-center px-3 py-2 border rounded-md text-sm',
                showFilterPanel
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              )}
            >
              <Filter className='w-4 h-4 mr-2' />
              Filters
            </button>
          )}
        </div>
      </div>

      {renderSummaryCards()}

      {showSearch && (
        <div className='relative'>
          <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5' />
          <input
            type='text'
            placeholder='Search invoices, payments, customers...'
            onChange={(e) => debouncedSetSearchQuery(e.target.value)}
            className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
          />
        </div>
      )}

      {renderFilters()}

      <div className='bg-white border border-gray-200 rounded-lg overflow-hidden'>
        {paginatedData.length === 0 ? (
          <div className='text-center py-12'>
            <div className='text-gray-400 text-4xl mb-4'>📄</div>
            <h3 className='text-lg font-medium text-gray-900 mb-2'>No transactions found</h3>
            <p className='text-gray-500'>
              {searchQuery || Object.values(filters).some((v) => v)
                ? 'Try adjusting your search or filters'
                : 'No billing history available'}
            </p>
          </div>
        ) : (
          <div className='overflow-x-auto'>
            <table className='min-w-full divide-y divide-gray-200'>
              <thead className='bg-gray-50'>
                <tr>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Type
                  </th>
                  <th
                    className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100'
                    onClick={() => {
                      const newDirection =
                        filters.sortField === 'date' && filters.sortDirection === 'desc'
                          ? 'asc'
                          : 'desc';
                      handleFilterChange('sortField', 'date');
                      handleFilterChange('sortDirection', newDirection);
                    }}
                  >
                    Date
                    {filters.sortField === 'date' &&
                      (filters.sortDirection === 'desc' ? (
                        <TrendingDown className='w-3 h-3 inline ml-1' />
                      ) : (
                        <TrendingUp className='w-3 h-3 inline ml-1' />
                      ))}
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Description
                  </th>
                  <th
                    className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100'
                    onClick={() => {
                      const newDirection =
                        filters.sortField === 'amount' && filters.sortDirection === 'desc'
                          ? 'asc'
                          : 'desc';
                      handleFilterChange('sortField', 'amount');
                      handleFilterChange('sortDirection', newDirection);
                    }}
                  >
                    Amount
                    {filters.sortField === 'amount' &&
                      (filters.sortDirection === 'desc' ? (
                        <TrendingDown className='w-3 h-3 inline ml-1' />
                      ) : (
                        <TrendingUp className='w-3 h-3 inline ml-1' />
                      ))}
                  </th>
                  <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Status
                  </th>
                  <th className='px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider'>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className='bg-white divide-y divide-gray-200'>
                {paginatedData.map((item) => (
                  <tr key={`${item.type}-${item.id}`} className='hover:bg-gray-50'>
                    <td className='px-6 py-4 whitespace-nowrap'>
                      <div className='flex items-center'>
                        {getItemIcon(item)}
                        <span className='ml-2 text-sm font-medium text-gray-900 capitalize'>
                          {item.type}
                        </span>
                      </div>
                    </td>
                    <td className='px-6 py-4 whitespace-nowrap text-sm text-gray-900'>
                      {formatDate(item.date)}
                    </td>
                    <td className='px-6 py-4'>
                      <div>
                        <div className='text-sm font-medium text-gray-900'>{item.description}</div>
                        {portalType === 'admin' && (
                          <div className='text-sm text-gray-500'>
                            {item.type === 'invoice' ? item.customerName : item.customerName}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className='px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900'>
                      {formatCurrency(item.amount, currency)}
                    </td>
                    <td className='px-6 py-4 whitespace-nowrap'>
                      <div className='flex items-center'>
                        {getStatusIcon(item.status)}
                        <span
                          className={cn(
                            'ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                            getPaymentStatusColor(item.status)
                          )}
                        >
                          {item.status}
                        </span>
                      </div>
                    </td>
                    <td className='px-6 py-4 whitespace-nowrap text-right text-sm font-medium'>
                      <div className='flex items-center justify-end space-x-2'>
                        {item.type === 'invoice' && (
                          <>
                            {onViewInvoice && (
                              <button
                                onClick={() => onViewInvoice(item.id)}
                                className='text-blue-600 hover:text-blue-800'
                                title='View Invoice'
                              >
                                <Eye className='w-4 h-4' />
                              </button>
                            )}
                            {onDownloadInvoice && (
                              <button
                                onClick={() => onDownloadInvoice(item.id)}
                                className='text-green-600 hover:text-green-800'
                                title='Download Invoice'
                              >
                                <Download className='w-4 h-4' />
                              </button>
                            )}
                          </>
                        )}
                        {item.type === 'payment' && (
                          <>
                            {item.status === 'failed' && onRetryPayment && (
                              <button
                                onClick={() => onRetryPayment(item.id)}
                                className='text-blue-600 hover:text-blue-800'
                                title='Retry Payment'
                              >
                                <RefreshCw className='w-4 h-4' />
                              </button>
                            )}
                            {item.status === 'completed' &&
                              onRefundPayment &&
                              portalType === 'admin' && (
                                <button
                                  onClick={() => onRefundPayment(item.id)}
                                  className='text-red-600 hover:text-red-800'
                                  title='Refund Payment'
                                >
                                  <RefreshCw className='w-4 h-4' />
                                </button>
                              )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {renderPagination()}
    </div>
  );
}
