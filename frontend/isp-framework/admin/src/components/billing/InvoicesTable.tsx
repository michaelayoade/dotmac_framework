/**
 * Invoices Table Component
 * Displays invoices using the new DataTable component
 */

'use client';

import { useState, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  FileText,
  Eye,
  Mail,
  Download,
  User,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle,
} from 'lucide-react';
import { StatusBadge } from '@dotmac/providers/indicators/StatusIndicators';
import { DataTable, type TableColumn } from '../ui/DataTable';
import { useInvoices } from '../../hooks/useBillingData';
import type { Invoice, BillingFilters, InvoiceStatus } from '../../types/billing';

interface InvoicesTableProps {
  className?: string;
  pageSize?: number;
}

function getStatusIcon(status: InvoiceStatus) {
  switch (status) {
    case 'paid':
      return CheckCircle;
    case 'pending':
      return Clock;
    case 'overdue':
      return XCircle;
    default:
      return AlertTriangle;
  }
}

function getStatusVariant(status: InvoiceStatus): 'paid' | 'pending' | 'overdue' | 'suspended' {
  switch (status) {
    case 'paid':
      return 'paid';
    case 'pending':
      return 'pending';
    case 'overdue':
      return 'overdue';
    default:
      return 'suspended';
  }
}

export function InvoicesTable({ className = '', pageSize = 10 }: InvoicesTableProps) {
  const router = useRouter();
  const [filters, setFilters] = useState<BillingFilters>({});

  // Fetch invoices with current filters
  const { data, isLoading, error, refetch } = useInvoices(filters, 1, 1000); // Get all for client-side processing

  const handleViewInvoice = useCallback(
    (id: string) => {
      router.push(`/billing/invoices/${id}`);
    },
    [router]
  );

  const handleSendReminder = useCallback((id: string) => {
    console.log('Send reminder for invoice:', id);
    // TODO: Implement send reminder functionality
  }, []);

  const handleDownload = useCallback((id: string) => {
    console.log('Download invoice:', id);
    // TODO: Implement download functionality
  }, []);

  const handleRowClick = useCallback(
    (invoice: Invoice) => {
      handleViewInvoice(invoice.id);
    },
    [handleViewInvoice]
  );

  const handleSelectionChange = useCallback((selectedIds: (string | number)[]) => {
    console.log('Selected invoices:', selectedIds);
    // TODO: Handle selection changes
  }, []);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleExport = useCallback(() => {
    console.log('Export invoices');
    // TODO: Implement export functionality
  }, []);

  const columns: TableColumn<Invoice>[] = useMemo(
    () => [
      {
        key: 'id',
        header: 'Invoice',
        sortable: true,
        filterable: true,
        accessor: (invoice) => (
          <div className='flex items-center space-x-3'>
            <div className='flex-shrink-0'>
              <FileText className='w-5 h-5 text-gray-400' />
            </div>
            <div>
              <div className='text-sm font-medium text-gray-900'>{invoice.id}</div>
              <div className='text-sm text-gray-500'>
                {new Date(invoice.createdAt).toLocaleDateString()}
              </div>
            </div>
          </div>
        ),
      },
      {
        key: 'customerName',
        header: 'Customer',
        sortable: true,
        filterable: true,
        accessor: (invoice) => (
          <div className='flex items-center space-x-3'>
            <div className='flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center'>
              <User className='w-4 h-4 text-gray-600' />
            </div>
            <div>
              <div className='text-sm font-medium text-gray-900'>{invoice.customerName}</div>
              <div className='text-sm text-gray-500'>{invoice.customerEmail}</div>
            </div>
          </div>
        ),
      },
      {
        key: 'total',
        header: 'Amount',
        sortable: true,
        align: 'right',
        accessor: (invoice) => (
          <div>
            <div className='text-sm text-gray-900'>${invoice.total.toFixed(2)}</div>
            <div className='text-xs text-gray-500'>
              Amount: ${invoice.amount.toFixed(2)} + Tax: ${invoice.tax.toFixed(2)}
            </div>
          </div>
        ),
      },
      {
        key: 'status',
        header: 'Status',
        sortable: true,
        filterable: true,
        accessor: (invoice) => {
          const StatusIcon = getStatusIcon(invoice.status);
          return (
            <StatusBadge
              variant={getStatusVariant(invoice.status)}
              size='sm'
              showDot={true}
              pulse={invoice.status === 'overdue'}
            >
              <StatusIcon className='w-3 h-3 mr-1' />
              {invoice.status}
            </StatusBadge>
          );
        },
      },
      {
        key: 'dueDate',
        header: 'Due Date',
        sortable: true,
        accessor: (invoice) => {
          const isOverdue = invoice.status === 'overdue';
          const daysPastDue = isOverdue
            ? Math.floor((Date.now() - new Date(invoice.dueDate).getTime()) / (1000 * 60 * 60 * 24))
            : 0;

          return (
            <div>
              <div className='text-sm text-gray-900'>
                {new Date(invoice.dueDate).toLocaleDateString()}
              </div>
              {isOverdue && (
                <div className='text-xs text-red-600 font-medium'>{daysPastDue} days overdue</div>
              )}
            </div>
          );
        },
      },
      {
        key: 'actions',
        header: 'Actions',
        sortable: false,
        width: '120px',
        accessor: (invoice) => (
          <div className='flex items-center space-x-2'>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleViewInvoice(invoice.id);
              }}
              className='p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded'
              title='View Invoice'
            >
              <Eye className='w-4 h-4' />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleSendReminder(invoice.id);
              }}
              className='p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded'
              title='Send Reminder'
            >
              <Mail className='w-4 h-4' />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDownload(invoice.id);
              }}
              className='p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded'
              title='Download PDF'
            >
              <Download className='w-4 h-4' />
            </button>
          </div>
        ),
      },
    ],
    [handleViewInvoice, handleSendReminder, handleDownload]
  );

  return (
    <DataTable<Invoice>
      data={data?.data || []}
      columns={columns}
      loading={isLoading}
      error={error?.message || null}
      title='Invoices'
      description='Manage customer invoices and billing'
      className={className}
      pageSize={pageSize}
      searchable={true}
      filterable={true}
      sortable={true}
      exportable={true}
      refreshable={true}
      selectable={true}
      onRowClick={handleRowClick}
      onSelectionChange={handleSelectionChange}
      onRefresh={handleRefresh}
      onExport={handleExport}
      emptyState={
        <div className='text-center py-12'>
          <FileText className='mx-auto h-12 w-12 text-gray-400 mb-4' />
          <h3 className='mt-2 text-sm font-medium text-gray-900'>No invoices</h3>
          <p className='mt-1 text-sm text-gray-500'>Get started by creating your first invoice.</p>
        </div>
      }
    />
  );
}
