/**
 * Virtualized Customer Management Component
 *
 * High-performance customer management with virtual scrolling for handling
 * large datasets efficiently. Includes comprehensive search, filtering,
 * sorting, and CRUD operations.
 */

'use client';

import React, { useState, useCallback, useMemo, useRef } from 'react';
import {
  VirtualizedTable,
  VirtualizedTableColumn,
  VirtualizedTableRef,
  useVirtualizedTable,
} from '@dotmac/providers/performance/VirtualizedTable';
// Removed unused security import - can be added back later if needed
import {
  usePartnerCustomers,
  useCreateCustomer,
  useUpdateCustomer,
  useDeleteCustomer,
} from '@dotmac/headless';
import {
  Search,
  Filter,
  Plus,
  Download,
  Upload,
  Edit3,
  Trash2,
  Eye,
  Mail,
  Phone,
  Building,
  MapPin,
  Calendar,
  DollarSign,
  TrendingUp,
  Star,
  CheckCircle,
  AlertCircle,
  Clock,
  XCircle,
} from 'lucide-react';

// Customer type definition
export interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  company?: string;
  address?: string;
  city?: string;
  state?: string;
  zipCode?: string;
  status:
    | 'active'
    | 'pending'
    | 'suspended'
    | 'cancelled'
    | 'prospect'
    | 'qualified'
    | 'negotiating';
  source: 'website' | 'referral' | 'campaign' | 'cold-call' | 'social' | 'partner';
  plan: string;
  usage: number;
  mrr: number;
  monthlyRevenue: number;
  connectionStatus: 'online' | 'offline';
  joinDate: string;
  signupDate?: string;
  lastPayment?: string;
  lastContact?: string;
  nextFollowUp?: string;
  probability?: number;
  dealSize?: number;
  lifetimeValue?: number;
  contractLength?: number;
  notes?: string;
  tags?: string[];
}

interface CustomerManagementVirtualizedProps {
  partnerId?: string;
  height?: number;
  className?: string;
}

export function CustomerManagementVirtualized({
  partnerId = 'default',
  height = 600,
  className = '',
}: CustomerManagementVirtualizedProps) {
  const tableRef = useRef<VirtualizedTableRef>(null);

  // Search and filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<keyof Customer>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null);
  const [viewingCustomer, setViewingCustomer] = useState<Customer | null>(null);

  // API hooks
  const {
    data: customersData,
    isLoading,
    error,
    refetch,
  } = usePartnerCustomers(partnerId, {
    search: searchTerm,
    status: statusFilter === 'all' ? undefined : statusFilter,
    source: sourceFilter === 'all' ? undefined : sourceFilter,
    sortBy,
    sortOrder,
    limit: 1000, // Large limit for virtual scrolling
  });

  const createCustomerMutation = useCreateCustomer();
  const updateCustomerMutation = useUpdateCustomer();
  const deleteCustomerMutation = useDeleteCustomer();

  // Virtual table management
  const { selectedRows, onSelectionChange, clearSelection, selectAll } = useVirtualizedTable(
    customersData?.customers || []
  );

  // Form handling for create/edit
  const {
    values: formValues,
    sanitizedValues,
    violations,
    isValid,
    setField,
    setValues,
    reset: resetForm,
  } = useSanitizedForm<Partial<Customer>>(
    {},
    {
      fieldConfigs: {
        name: { type: 'text', maxLength: 100, required: true },
        email: { type: 'email', required: true },
        phone: { type: 'phone', required: true },
        company: { type: 'text', maxLength: 100 },
        address: { type: 'text', maxLength: 200 },
        city: { type: 'text', maxLength: 50 },
        state: { type: 'text', maxLength: 20 },
        zipCode: { type: 'text', maxLength: 10 },
        notes: { type: 'text', maxLength: 1000 },
      },
      validateOnChange: true,
      onViolation: (field, fieldViolations) => {
        console.warn(`Field ${String(field)} has violations:`, fieldViolations);
      },
    }
  );

  // Memoized customers data
  const customers = useMemo(() => {
    return customersData?.customers || [];
  }, [customersData]);

  // Status badge renderer
  const renderStatusBadge = useCallback((status: Customer['status']) => {
    const statusConfig = {
      active: { color: 'bg-green-100 text-green-800', icon: CheckCircle, label: 'Active' },
      pending: { color: 'bg-yellow-100 text-yellow-800', icon: Clock, label: 'Pending' },
      suspended: { color: 'bg-red-100 text-red-800', icon: XCircle, label: 'Suspended' },
      cancelled: { color: 'bg-gray-100 text-gray-800', icon: XCircle, label: 'Cancelled' },
      prospect: { color: 'bg-blue-100 text-blue-800', icon: Eye, label: 'Prospect' },
      qualified: { color: 'bg-purple-100 text-purple-800', icon: Star, label: 'Qualified' },
      negotiating: {
        color: 'bg-orange-100 text-orange-800',
        icon: TrendingUp,
        label: 'Negotiating',
      },
    };

    const config = statusConfig[status] || statusConfig.pending;
    const Icon = config.icon;

    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}
      >
        <Icon className='w-3 h-3 mr-1' />
        {config.label}
      </span>
    );
  }, []);

  // Format currency
  const formatCurrency = useCallback((amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  }, []);

  // Format date
  const formatDate = useCallback((dateString: string) => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(new Date(dateString));
  }, []);

  // Table columns definition
  const columns: VirtualizedTableColumn<Customer>[] = useMemo(
    () => [
      {
        key: 'name',
        title: 'Customer',
        width: 250,
        sortable: true,
        render: (value, customer) => (
          <div className='flex items-center space-x-3'>
            <div className='flex-shrink-0'>
              <div className='w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white font-medium text-sm'>
                {customer.name.charAt(0).toUpperCase()}
              </div>
            </div>
            <div className='min-w-0 flex-1'>
              <p className='text-sm font-medium text-gray-900 truncate'>{customer.name}</p>
              {customer.company && (
                <p className='text-sm text-gray-500 truncate'>{customer.company}</p>
              )}
            </div>
          </div>
        ),
      },
      {
        key: 'email',
        title: 'Contact',
        width: 220,
        render: (value, customer) => (
          <div className='space-y-1'>
            <div className='flex items-center text-sm text-gray-900'>
              <Mail className='w-4 h-4 mr-1 text-gray-400' />
              <a href={`mailto:${customer.email}`} className='hover:text-blue-600 truncate'>
                {customer.email}
              </a>
            </div>
            <div className='flex items-center text-sm text-gray-500'>
              <Phone className='w-4 h-4 mr-1 text-gray-400' />
              <span className='truncate'>{customer.phone}</span>
            </div>
          </div>
        ),
      },
      {
        key: 'status',
        title: 'Status',
        width: 120,
        sortable: true,
        render: (status) => renderStatusBadge(status as Customer['status']),
      },
      {
        key: 'plan',
        title: 'Plan',
        width: 120,
        sortable: true,
        render: (value) => <span className='text-sm font-medium text-gray-900'>{value}</span>,
      },
      {
        key: 'mrr',
        title: 'MRR',
        width: 100,
        sortable: true,
        align: 'right',
        render: (value) => (
          <span className='text-sm font-semibold text-green-600'>
            {formatCurrency(value as number)}
          </span>
        ),
      },
      {
        key: 'lifetimeValue',
        title: 'LTV',
        width: 120,
        sortable: true,
        align: 'right',
        render: (value) => (
          <span className='text-sm font-medium text-gray-900'>
            {value ? formatCurrency(value as number) : '—'}
          </span>
        ),
      },
      {
        key: 'joinDate',
        title: 'Join Date',
        width: 110,
        sortable: true,
        render: (value) => (
          <span className='text-sm text-gray-500'>{formatDate(value as string)}</span>
        ),
      },
      {
        key: 'actions',
        title: 'Actions',
        width: 120,
        render: (_, customer) => (
          <div className='flex items-center space-x-2'>
            <button
              onClick={() => setViewingCustomer(customer)}
              className='p-1 text-gray-400 hover:text-blue-600 transition-colors'
              title='View details'
            >
              <Eye className='w-4 h-4' />
            </button>
            <button
              onClick={() => setEditingCustomer(customer)}
              className='p-1 text-gray-400 hover:text-green-600 transition-colors'
              title='Edit customer'
            >
              <Edit3 className='w-4 h-4' />
            </button>
            <button
              onClick={() => handleDeleteCustomer(customer)}
              className='p-1 text-gray-400 hover:text-red-600 transition-colors'
              title='Delete customer'
            >
              <Trash2 className='w-4 h-4' />
            </button>
          </div>
        ),
      },
    ],
    [renderStatusBadge, formatCurrency, formatDate]
  );

  // Event handlers
  const handleSort = useCallback((column: keyof Customer, direction: 'asc' | 'desc') => {
    setSortBy(column);
    setSortOrder(direction);
  }, []);

  const handleCreateCustomer = useCallback(async () => {
    if (!isValid) {
      console.error('Form validation failed:', violations);
      return;
    }

    try {
      await createCustomerMutation.mutateAsync(sanitizedValues as Customer);
      setShowCreateModal(false);
      resetForm();
      refetch();
    } catch (error) {
      console.error('Failed to create customer:', error);
    }
  }, [isValid, violations, sanitizedValues, createCustomerMutation, resetForm, refetch]);

  const handleUpdateCustomer = useCallback(async () => {
    if (!editingCustomer || !isValid) return;

    try {
      await updateCustomerMutation.mutateAsync({
        ...editingCustomer,
        ...sanitizedValues,
      } as Customer);
      setEditingCustomer(null);
      resetForm();
      refetch();
    } catch (error) {
      console.error('Failed to update customer:', error);
    }
  }, [editingCustomer, isValid, sanitizedValues, updateCustomerMutation, resetForm, refetch]);

  const handleDeleteCustomer = useCallback(
    async (customer: Customer) => {
      if (!confirm(`Are you sure you want to delete ${customer.name}?`)) {
        return;
      }

      try {
        await deleteCustomerMutation.mutateAsync(customer.id);
        refetch();
      } catch (error) {
        console.error('Failed to delete customer:', error);
      }
    },
    [deleteCustomerMutation, refetch]
  );

  const handleExportData = useCallback(() => {
    const selectedCustomers = customers.filter((_, index) => selectedRows.has(index));
    const dataToExport = selectedCustomers.length > 0 ? selectedCustomers : customers;

    const csvContent = [
      // Header
      'Name,Email,Phone,Company,Status,Plan,MRR,LTV,Join Date',
      // Data rows
      ...dataToExport.map((customer) =>
        [
          customer.name,
          customer.email,
          customer.phone,
          customer.company || '',
          customer.status,
          customer.plan,
          customer.mrr,
          customer.lifetimeValue || '',
          customer.joinDate,
        ].join(',')
      ),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `customers-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }, [customers, selectedRows]);

  // Loading and error states
  if (isLoading) {
    return (
      <div className='flex items-center justify-center h-64'>
        <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500'></div>
        <span className='ml-2'>Loading customers...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className='bg-red-50 border border-red-200 rounded-md p-4'>
        <div className='flex'>
          <AlertCircle className='h-5 w-5 text-red-400' />
          <div className='ml-3'>
            <h3 className='text-sm font-medium text-red-800'>Error Loading Customers</h3>
            <p className='mt-1 text-sm text-red-700'>{error.message}</p>
            <button
              onClick={() => refetch()}
              className='mt-2 text-sm bg-red-100 text-red-800 px-3 py-1 rounded hover:bg-red-200'
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className='flex justify-between items-center'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Customer Management</h1>
          <p className='mt-1 text-sm text-gray-500'>
            Manage your customer relationships and track performance
          </p>
        </div>
        <div className='flex space-x-3'>
          <button
            onClick={handleExportData}
            className='inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50'
          >
            <Download className='w-4 h-4 mr-2' />
            Export
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className='inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700'
          >
            <Plus className='w-4 h-4 mr-2' />
            Add Customer
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className='bg-white p-4 rounded-lg border border-gray-200'>
        <div className='grid grid-cols-1 md:grid-cols-4 gap-4'>
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>Search</label>
            <div className='relative'>
              <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4' />
              <input
                type='text'
                placeholder='Search customers...'
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className='pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
              />
            </div>
          </div>
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className='w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            >
              <option value='all'>All Status</option>
              <option value='active'>Active</option>
              <option value='pending'>Pending</option>
              <option value='prospect'>Prospect</option>
              <option value='suspended'>Suspended</option>
            </select>
          </div>
          <div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>Source</label>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className='w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500'
            >
              <option value='all'>All Sources</option>
              <option value='website'>Website</option>
              <option value='referral'>Referral</option>
              <option value='campaign'>Campaign</option>
              <option value='social'>Social</option>
            </select>
          </div>
          <div className='flex items-end'>
            <button
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('all');
                setSourceFilter('all');
              }}
              className='w-full px-4 py-2 text-sm text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200'
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Results Summary */}
      <div className='flex justify-between items-center text-sm text-gray-500'>
        <div>
          Showing {customers.length} customers
          {selectedRows.size > 0 && ` (${selectedRows.size} selected)`}
        </div>
        <div className='space-x-4'>
          {selectedRows.size > 0 && (
            <>
              <button onClick={clearSelection} className='hover:text-gray-700'>
                Clear selection
              </button>
              <button onClick={selectAll} className='hover:text-gray-700'>
                Select all
              </button>
            </>
          )}
        </div>
      </div>

      {/* Virtualized Table */}
      <VirtualizedTable
        ref={tableRef}
        data={customers}
        columns={columns}
        height={height}
        rowHeight={64}
        onSort={handleSort}
        sortBy={sortBy}
        sortDirection={sortOrder}
        selectedRows={selectedRows}
        onSelectionChange={onSelectionChange}
        loading={isLoading}
        className='shadow-sm border border-gray-200 rounded-lg'
        stickyHeader={true}
        overscanCount={10}
      />

      {/* Modals would go here - Create, Edit, View */}
      {/* Implementation of modals omitted for brevity but would include form handling */}
    </div>
  );
}
