'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import {
  ChevronDownIcon,
  ChevronUpIcon,
  SearchIcon,
  FilterIcon,
  DownloadIcon,
  EyeIcon,
  PauseIcon,
  TrashIcon,
  EditIcon,
  MoreHorizontalIcon,
  UserIcon,
  MapPinIcon,
  CreditCardIcon,
} from 'lucide-react';
import { deleteCustomerAction, suspendCustomerAction } from '../../app/actions/customers';

interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  status: 'active' | 'suspended' | 'inactive' | 'pending';
  plan: string;
  planType: 'residential' | 'business' | 'enterprise';
  monthlyRevenue: number;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
  };
  lastLogin: string | null;
  dataUsage: {
    current: number;
    limit: number;
    unit: 'GB' | 'TB';
  };
  paymentStatus: 'current' | 'overdue' | 'pending';
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

type SortField =
  | 'name'
  | 'email'
  | 'status'
  | 'plan'
  | 'monthlyRevenue'
  | 'createdAt'
  | 'lastLogin';
type SortOrder = 'asc' | 'desc';

interface FilterOptions {
  status: string[];
  planType: string[];
  paymentStatus: string[];
  tags: string[];
  dateRange: {
    start: string;
    end: string;
  };
  revenueRange: {
    min: number;
    max: number;
  };
}

interface CustomersTableProps {
  customers: Customer[];
  totalCount: number;
  currentPage: number;
  pageSize?: number;
  loading?: boolean;
  onCustomersUpdate?: () => void;
}

export function CustomersTable({
  customers,
  totalCount,
  currentPage,
  pageSize = 20,
  loading = false,
  onCustomersUpdate,
}: CustomersTableProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [selectedCustomers, setSelectedCustomers] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<SortField>('createdAt');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<FilterOptions>({
    status: [],
    planType: [],
    paymentStatus: [],
    tags: [],
    dateRange: { start: '', end: '' },
    revenueRange: { min: 0, max: 10000 },
  });

  // Filtering and search logic
  const filteredAndSearchedCustomers = useMemo(() => {
    let filtered = customers;

    // Apply search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (customer) =>
          customer.name.toLowerCase().includes(query) ||
          customer.email.toLowerCase().includes(query) ||
          customer.phone.includes(query) ||
          customer.id.toLowerCase().includes(query) ||
          customer.address.city.toLowerCase().includes(query)
      );
    }

    // Apply filters
    if (filters.status.length > 0) {
      filtered = filtered.filter((customer) => filters.status.includes(customer.status));
    }
    if (filters.planType.length > 0) {
      filtered = filtered.filter((customer) => filters.planType.includes(customer.planType));
    }
    if (filters.paymentStatus.length > 0) {
      filtered = filtered.filter((customer) =>
        filters.paymentStatus.includes(customer.paymentStatus)
      );
    }
    if (filters.tags.length > 0) {
      filtered = filtered.filter((customer) =>
        filters.tags.some((tag) => customer.tags.includes(tag))
      );
    }
    if (filters.dateRange.start && filters.dateRange.end) {
      filtered = filtered.filter((customer) => {
        const createdDate = new Date(customer.createdAt);
        return (
          createdDate >= new Date(filters.dateRange.start) &&
          createdDate <= new Date(filters.dateRange.end)
        );
      });
    }
    if (filters.revenueRange.min > 0 || filters.revenueRange.max < 10000) {
      filtered = filtered.filter(
        (customer) =>
          customer.monthlyRevenue >= filters.revenueRange.min &&
          customer.monthlyRevenue <= filters.revenueRange.max
      );
    }

    return filtered;
  }, [customers, searchQuery, filters]);

  // Sorting logic
  const sortedCustomers = useMemo(() => {
    return [...filteredAndSearchedCustomers].sort((a, b) => {
      let aValue: any = a[sortField];
      let bValue: any = b[sortField];

      // Handle nested values and special cases
      if (sortField === 'monthlyRevenue') {
        aValue = a.monthlyRevenue;
        bValue = b.monthlyRevenue;
      } else if (sortField === 'createdAt' || sortField === 'lastLogin') {
        aValue = new Date(aValue || 0);
        bValue = new Date(bValue || 0);
      } else if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredAndSearchedCustomers, sortField, sortOrder]);

  // URL management
  const updateURL = useCallback(
    (params: Record<string, string | null>) => {
      const newParams = new URLSearchParams(searchParams);

      Object.entries(params).forEach(([key, value]) => {
        if (value === null || value === '') {
          newParams.delete(key);
        } else {
          newParams.set(key, value);
        }
      });

      router.push(`${pathname}?${newParams.toString()}`);
    },
    [pathname, router, searchParams]
  );

  // Handlers
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    updateURL({ search: query, page: '1' });
  };

  const handleSelectAll = () => {
    if (selectedCustomers.size === sortedCustomers.length) {
      setSelectedCustomers(new Set());
    } else {
      setSelectedCustomers(new Set(sortedCustomers.map((c) => c.id)));
    }
  };

  const handleSelectCustomer = (id: string) => {
    const newSelected = new Set(selectedCustomers);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedCustomers(newSelected);
  };

  const handleBulkAction = async (action: 'suspend' | 'activate' | 'delete') => {
    if (selectedCustomers.size === 0) return;

    const confirmMessage = `Are you sure you want to ${action} ${selectedCustomers.size} customers?`;
    if (!confirm(confirmMessage)) return;

    // Implement bulk actions
    console.log(`Bulk ${action} for customers:`, Array.from(selectedCustomers));
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this customer?')) return;

    setActionLoading(id);
    const result = await deleteCustomerAction(id);
    setActionLoading(null);

    if (result.success) {
      onCustomersUpdate?.();
      router.refresh();
    } else {
      alert(result.error || 'Failed to delete customer');
    }
  };

  const handleSuspend = async (id: string) => {
    if (!confirm('Are you sure you want to suspend this customer?')) return;

    setActionLoading(id);
    const result = await suspendCustomerAction(id);
    setActionLoading(null);

    if (result.success) {
      onCustomersUpdate?.();
      router.refresh();
    } else {
      alert(result.error || 'Failed to suspend customer');
    }
  };

  const exportToCSV = () => {
    const headers = [
      'ID',
      'Name',
      'Email',
      'Phone',
      'Status',
      'Plan',
      'Monthly Revenue',
      'Created At',
    ];
    const csvData = [
      headers,
      ...sortedCustomers.map((customer) => [
        customer.id,
        customer.name,
        customer.email,
        customer.phone,
        customer.status,
        customer.plan,
        customer.monthlyRevenue.toString(),
        customer.createdAt,
      ]),
    ];

    const csvContent = csvData.map((row) => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `customers-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const totalPages = Math.ceil(totalCount / pageSize);
  const startIndex = (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, totalCount);

  const SortableHeader = ({
    field,
    children,
    className = '',
  }: {
    field: SortField;
    children: React.ReactNode;
    className?: string;
  }) => (
    <th
      className={`px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none ${className}`}
      onClick={() => handleSort(field)}
    >
      <div className='flex items-center space-x-1'>
        <span>{children}</span>
        {sortField === field &&
          (sortOrder === 'asc' ? (
            <ChevronUpIcon className='h-4 w-4' />
          ) : (
            <ChevronDownIcon className='h-4 w-4' />
          ))}
      </div>
    </th>
  );

  const StatusBadge = ({ status }: { status: Customer['status'] }) => {
    const config = {
      active: { bg: 'bg-green-100', text: 'text-green-800', label: 'Active' },
      suspended: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Suspended' },
      inactive: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Inactive' },
      pending: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Pending' },
    };
    const { bg, text, label } = config[status];
    return (
      <span
        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${bg} ${text}`}
      >
        {label}
      </span>
    );
  };

  const PaymentStatusBadge = ({ status }: { status: Customer['paymentStatus'] }) => {
    const config = {
      current: { bg: 'bg-green-100', text: 'text-green-800', icon: '✓' },
      overdue: { bg: 'bg-red-100', text: 'text-red-800', icon: '⚠' },
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: '⏳' },
    };
    const { bg, text, icon } = config[status];
    return (
      <span
        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${bg} ${text}`}
      >
        {icon} {status}
      </span>
    );
  };

  return (
    <div className='space-y-6'>
      {/* Search and Filter Bar */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
        <div className='flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between'>
          <div className='flex-1 max-w-lg'>
            <div className='relative'>
              <SearchIcon className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5' />
              <input
                type='text'
                placeholder='Search customers by name, email, phone, or ID...'
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
              />
            </div>
          </div>

          <div className='flex gap-2'>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded-lg border font-medium transition-colors ${
                showFilters
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <FilterIcon className='h-4 w-4 mr-2 inline' />
              Filters
            </button>
            <button
              onClick={exportToCSV}
              className='px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors'
            >
              <DownloadIcon className='h-4 w-4 mr-2 inline' />
              Export
            </button>
          </div>
        </div>

        {/* Advanced Filters Panel */}
        {showFilters && (
          <div className='mt-6 pt-6 border-t border-gray-200'>
            <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4'>
              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>Status</label>
                <select
                  multiple
                  className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions, (option) => option.value);
                    setFilters((prev) => ({ ...prev, status: values }));
                  }}
                >
                  <option value='active'>Active</option>
                  <option value='suspended'>Suspended</option>
                  <option value='inactive'>Inactive</option>
                  <option value='pending'>Pending</option>
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>Plan Type</label>
                <select
                  multiple
                  className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions, (option) => option.value);
                    setFilters((prev) => ({ ...prev, planType: values }));
                  }}
                >
                  <option value='residential'>Residential</option>
                  <option value='business'>Business</option>
                  <option value='enterprise'>Enterprise</option>
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>
                  Payment Status
                </label>
                <select
                  multiple
                  className='w-full border border-gray-300 rounded-lg px-3 py-2 text-sm'
                  onChange={(e) => {
                    const values = Array.from(e.target.selectedOptions, (option) => option.value);
                    setFilters((prev) => ({ ...prev, paymentStatus: values }));
                  }}
                >
                  <option value='current'>Current</option>
                  <option value='overdue'>Overdue</option>
                  <option value='pending'>Pending</option>
                </select>
              </div>

              <div>
                <label className='block text-sm font-medium text-gray-700 mb-2'>
                  Revenue Range
                </label>
                <div className='flex space-x-2'>
                  <input
                    type='number'
                    placeholder='Min'
                    className='w-full border border-gray-300 rounded px-2 py-1 text-sm'
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        revenueRange: { ...prev.revenueRange, min: Number(e.target.value) || 0 },
                      }))
                    }
                  />
                  <input
                    type='number'
                    placeholder='Max'
                    className='w-full border border-gray-300 rounded px-2 py-1 text-sm'
                    onChange={(e) =>
                      setFilters((prev) => ({
                        ...prev,
                        revenueRange: {
                          ...prev.revenueRange,
                          max: Number(e.target.value) || 10000,
                        },
                      }))
                    }
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Bulk Actions */}
      {selectedCustomers.size > 0 && (
        <div className='bg-blue-50 border border-blue-200 rounded-lg p-4'>
          <div className='flex items-center justify-between'>
            <span className='text-sm text-blue-700'>
              {selectedCustomers.size} customer{selectedCustomers.size !== 1 ? 's' : ''} selected
            </span>
            <div className='flex gap-2'>
              <button
                onClick={() => handleBulkAction('suspend')}
                className='px-3 py-1 bg-yellow-100 text-yellow-800 rounded text-sm font-medium hover:bg-yellow-200'
              >
                Suspend
              </button>
              <button
                onClick={() => handleBulkAction('activate')}
                className='px-3 py-1 bg-green-100 text-green-800 rounded text-sm font-medium hover:bg-green-200'
              >
                Activate
              </button>
              <button
                onClick={() => handleBulkAction('delete')}
                className='px-3 py-1 bg-red-100 text-red-800 rounded text-sm font-medium hover:bg-red-200'
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Advanced Data Table */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden'>
        <div className='overflow-x-auto'>
          <table className='min-w-full divide-y divide-gray-200'>
            <thead className='bg-gray-50'>
              <tr>
                <th className='px-6 py-3'>
                  <input
                    type='checkbox'
                    checked={
                      selectedCustomers.size === sortedCustomers.length &&
                      sortedCustomers.length > 0
                    }
                    onChange={handleSelectAll}
                    className='h-4 w-4 text-blue-600 rounded border-gray-300'
                  />
                </th>
                <SortableHeader field='name'>Customer</SortableHeader>
                <SortableHeader field='email'>Contact & Location</SortableHeader>
                <SortableHeader field='plan'>Plan & Revenue</SortableHeader>
                <SortableHeader field='status'>Status</SortableHeader>
                <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                  Usage
                </th>
                <SortableHeader field='lastLogin'>Activity</SortableHeader>
                <th className='relative px-6 py-3'>
                  <span className='sr-only'>Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className='bg-white divide-y divide-gray-200'>
              {loading ? (
                <tr>
                  <td colSpan={8} className='px-6 py-12 text-center'>
                    <div className='flex items-center justify-center'>
                      <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600'></div>
                      <span className='ml-2 text-gray-500'>Loading customers...</span>
                    </div>
                  </td>
                </tr>
              ) : sortedCustomers.length === 0 ? (
                <tr>
                  <td colSpan={8} className='px-6 py-12 text-center text-gray-500'>
                    {searchQuery || filters.status.length > 0
                      ? 'No customers match your search criteria.'
                      : 'No customers found.'}
                  </td>
                </tr>
              ) : (
                sortedCustomers.map((customer) => (
                  <tr key={customer.id} className='hover:bg-gray-50'>
                    <td className='px-6 py-4'>
                      <input
                        type='checkbox'
                        checked={selectedCustomers.has(customer.id)}
                        onChange={() => handleSelectCustomer(customer.id)}
                        className='h-4 w-4 text-blue-600 rounded border-gray-300'
                      />
                    </td>
                    <td className='px-6 py-4'>
                      <div className='flex items-center'>
                        <div className='flex-shrink-0 h-10 w-10'>
                          <div className='h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center'>
                            <UserIcon className='h-5 w-5 text-blue-600' />
                          </div>
                        </div>
                        <div className='ml-4'>
                          <div className='text-sm font-medium text-gray-900'>{customer.name}</div>
                          <div className='text-sm text-gray-500'>ID: {customer.id}</div>
                          {customer.tags.length > 0 && (
                            <div className='flex mt-1 gap-1'>
                              {customer.tags.slice(0, 2).map((tag) => (
                                <span
                                  key={tag}
                                  className='inline-flex px-2 py-1 text-xs rounded bg-gray-100 text-gray-600'
                                >
                                  {tag}
                                </span>
                              ))}
                              {customer.tags.length > 2 && (
                                <span className='text-xs text-gray-400'>
                                  +{customer.tags.length - 2}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className='px-6 py-4'>
                      <div className='text-sm text-gray-900'>{customer.email}</div>
                      <div className='text-sm text-gray-500'>{customer.phone}</div>
                      <div className='flex items-center text-sm text-gray-500 mt-1'>
                        <MapPinIcon className='h-3 w-3 mr-1' />
                        {customer.address.city}, {customer.address.state}
                      </div>
                    </td>
                    <td className='px-6 py-4'>
                      <div className='text-sm font-medium text-gray-900'>{customer.plan}</div>
                      <div className='text-xs text-gray-500 capitalize'>{customer.planType}</div>
                      <div className='flex items-center text-sm text-green-600 mt-1'>
                        <CreditCardIcon className='h-3 w-3 mr-1' />${customer.monthlyRevenue}/mo
                      </div>
                    </td>
                    <td className='px-6 py-4'>
                      <StatusBadge status={customer.status} />
                      <div className='mt-1'>
                        <PaymentStatusBadge status={customer.paymentStatus} />
                      </div>
                    </td>
                    <td className='px-6 py-4'>
                      <div className='text-sm text-gray-900'>
                        {customer.dataUsage.current}
                        {customer.dataUsage.unit} / {customer.dataUsage.limit}
                        {customer.dataUsage.unit}
                      </div>
                      <div className='w-full bg-gray-200 rounded-full h-2 mt-1'>
                        <div
                          className='bg-blue-600 h-2 rounded-full'
                          style={{
                            width: `${(customer.dataUsage.current / customer.dataUsage.limit) * 100}%`,
                          }}
                        />
                      </div>
                      <div className='text-xs text-gray-500 mt-1'>
                        {Math.round((customer.dataUsage.current / customer.dataUsage.limit) * 100)}%
                        used
                      </div>
                    </td>
                    <td className='px-6 py-4'>
                      <div className='text-sm text-gray-900'>
                        {customer.lastLogin
                          ? new Date(customer.lastLogin).toLocaleDateString()
                          : 'Never'}
                      </div>
                      <div className='text-xs text-gray-500'>
                        Created {new Date(customer.createdAt).toLocaleDateString()}
                      </div>
                    </td>
                    <td className='px-6 py-4 text-right'>
                      <div className='flex items-center justify-end space-x-2'>
                        <button
                          onClick={() => router.push(`/customers/${customer.id}`)}
                          className='p-2 text-blue-600 hover:text-blue-900 hover:bg-blue-50 rounded'
                          title='View Details'
                        >
                          <EyeIcon className='h-4 w-4' />
                        </button>
                        <button
                          onClick={() => router.push(`/customers/${customer.id}/edit`)}
                          className='p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded'
                          title='Edit Customer'
                        >
                          <EditIcon className='h-4 w-4' />
                        </button>
                        {customer.status === 'active' && (
                          <button
                            onClick={() => handleSuspend(customer.id)}
                            disabled={actionLoading === customer.id}
                            className='p-2 text-yellow-600 hover:text-yellow-900 hover:bg-yellow-50 rounded disabled:opacity-50'
                            title='Suspend Customer'
                          >
                            <PauseIcon className='h-4 w-4' />
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(customer.id)}
                          disabled={actionLoading === customer.id}
                          className='p-2 text-red-600 hover:text-red-900 hover:bg-red-50 rounded disabled:opacity-50'
                          title='Delete Customer'
                        >
                          <TrashIcon className='h-4 w-4' />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Enhanced Pagination */}
        <div className='px-6 py-4 bg-gray-50 border-t border-gray-200'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-2'>
              <span className='text-sm text-gray-700'>
                Showing <span className='font-medium'>{startIndex}</span> to{' '}
                <span className='font-medium'>{endIndex}</span> of{' '}
                <span className='font-medium'>{totalCount}</span> customers
              </span>
              {filteredAndSearchedCustomers.length !== totalCount && (
                <span className='text-sm text-blue-600'>
                  ({filteredAndSearchedCustomers.length} filtered)
                </span>
              )}
            </div>

            <div className='flex items-center space-x-2'>
              <select
                value={pageSize}
                onChange={(e) => updateURL({ pageSize: e.target.value, page: '1' })}
                className='border border-gray-300 rounded px-2 py-1 text-sm'
              >
                <option value='10'>10 per page</option>
                <option value='20'>20 per page</option>
                <option value='50'>50 per page</option>
                <option value='100'>100 per page</option>
              </select>

              <nav className='flex items-center space-x-1'>
                <button
                  onClick={() => updateURL({ page: '1' })}
                  disabled={currentPage === 1}
                  className='px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-500 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed'
                >
                  First
                </button>
                <button
                  onClick={() => updateURL({ page: String(currentPage - 1) })}
                  disabled={currentPage === 1}
                  className='px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-500 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed'
                >
                  Previous
                </button>

                {/* Page Numbers */}
                <div className='flex items-center space-x-1'>
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }

                    return (
                      <button
                        key={pageNum}
                        onClick={() => updateURL({ page: String(pageNum) })}
                        className={`px-3 py-2 border rounded-md text-sm font-medium ${
                          currentPage === pageNum
                            ? 'bg-blue-50 border-blue-500 text-blue-600'
                            : 'border-gray-300 text-gray-500 bg-white hover:bg-gray-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>

                <button
                  onClick={() => updateURL({ page: String(currentPage + 1) })}
                  disabled={currentPage === totalPages}
                  className='px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-500 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed'
                >
                  Next
                </button>
                <button
                  onClick={() => updateURL({ page: String(totalPages) })}
                  disabled={currentPage === totalPages}
                  className='px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-500 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed'
                >
                  Last
                </button>
              </nav>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
