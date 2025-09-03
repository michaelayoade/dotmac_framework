/**
 * Invoice Management - Focused component for invoice operations
 * Handles invoice listing, actions, and bulk operations
 */

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  FileTextIcon,
  UserIcon,
  EyeIcon,
  MailIcon,
  DownloadIcon,
  SearchIcon,
  FilterIcon,
} from 'lucide-react';
import { StatusBadge } from '@dotmac/providers/indicators/StatusIndicators';
import type { Invoice } from '../../../types/billing';

interface InvoiceManagementProps {
  invoices: Invoice[];
  onInvoiceAction?: (action: string, invoiceId: string) => void;
}

export function InvoiceManagement({ invoices, onInvoiceAction }: InvoiceManagementProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  const handleInvoiceAction = (action: string, invoiceId: string) => {
    if (onInvoiceAction) {
      onInvoiceAction(action, invoiceId);
    }
  };

  const filteredInvoices = invoices.filter((invoice) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      invoice.id.toLowerCase().includes(query) ||
      invoice.customerName.toLowerCase().includes(query) ||
      invoice.customerEmail.toLowerCase().includes(query)
    );
  });

  return (
    <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
      {/* Search and Actions Bar */}
      <div className='p-6 border-b border-gray-200'>
        <div className='flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between'>
          <div className='flex-1 max-w-lg'>
            <div className='relative'>
              <SearchIcon className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5' />
              <input
                type='text'
                placeholder='Search invoices by ID, customer, or email...'
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
              />
            </div>
          </div>
          <div className='flex items-center gap-2'>
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
            {selectedItems.size > 0 && (
              <div className='flex items-center gap-2'>
                <span className='text-sm text-gray-600'>{selectedItems.size} selected</span>
                <button
                  onClick={() =>
                    handleInvoiceAction('bulk-reminder', Array.from(selectedItems).join(','))
                  }
                  className='px-3 py-2 bg-blue-100 text-blue-800 rounded-lg text-sm font-medium hover:bg-blue-200'
                >
                  Send Reminders
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Invoices Table */}
      <div className='overflow-x-auto'>
        <table className='min-w-full divide-y divide-gray-200'>
          <thead className='bg-gray-50'>
            <tr>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                <input
                  type='checkbox'
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedItems(new Set(invoices.map((i) => i.id)));
                    } else {
                      setSelectedItems(new Set());
                    }
                  }}
                  className='h-4 w-4 text-blue-600 rounded border-gray-300'
                />
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Invoice
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Customer
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Amount
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Status
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Due Date
              </th>
              <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                Actions
              </th>
            </tr>
          </thead>
          <tbody className='bg-white divide-y divide-gray-200'>
            {filteredInvoices.map((invoice) => (
              <InvoiceRow
                key={invoice.id}
                invoice={invoice}
                isSelected={selectedItems.has(invoice.id)}
                onToggleSelect={(selected) => {
                  const newSelected = new Set(selectedItems);
                  if (selected) {
                    newSelected.add(invoice.id);
                  } else {
                    newSelected.delete(invoice.id);
                  }
                  setSelectedItems(newSelected);
                }}
                onAction={handleInvoiceAction}
                onView={() => router.push(`/billing/invoices/${invoice.id}`)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface InvoiceRowProps {
  invoice: Invoice;
  isSelected: boolean;
  onToggleSelect: (selected: boolean) => void;
  onAction: (action: string, invoiceId: string) => void;
  onView: () => void;
}

function InvoiceRow({ invoice, isSelected, onToggleSelect, onAction, onView }: InvoiceRowProps) {
  return (
    <tr className='hover:bg-gray-50'>
      <td className='px-6 py-4'>
        <input
          type='checkbox'
          checked={isSelected}
          onChange={(e) => onToggleSelect(e.target.checked)}
          className='h-4 w-4 text-blue-600 rounded border-gray-300'
        />
      </td>
      <td className='px-6 py-4'>
        <div className='flex items-center space-x-3'>
          <div className='flex-shrink-0'>
            <FileTextIcon className='w-5 h-5 text-gray-400' />
          </div>
          <div>
            <div className='text-sm font-medium text-gray-900'>{invoice.id}</div>
            <div className='text-sm text-gray-500'>
              {new Date(invoice.createdAt).toLocaleDateString()}
            </div>
          </div>
        </div>
      </td>
      <td className='px-6 py-4'>
        <div className='flex items-center space-x-3'>
          <div className='flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center'>
            <UserIcon className='w-4 h-4 text-gray-600' />
          </div>
          <div>
            <div className='text-sm font-medium text-gray-900'>{invoice.customerName}</div>
            <div className='text-sm text-gray-500'>{invoice.customerEmail}</div>
          </div>
        </div>
      </td>
      <td className='px-6 py-4'>
        <div className='text-sm text-gray-900'>${invoice.total.toFixed(2)}</div>
        <div className='text-xs text-gray-500'>
          Amount: ${invoice.amount.toFixed(2)} + Tax: ${invoice.tax.toFixed(2)}
        </div>
      </td>
      <td className='px-6 py-4'>
        <StatusBadge
          variant={
            invoice.status === 'paid'
              ? 'paid'
              : invoice.status === 'pending'
                ? 'pending'
                : invoice.status === 'overdue'
                  ? 'overdue'
                  : 'suspended'
          }
          size='sm'
          showDot={true}
          pulse={invoice.status === 'overdue'}
        >
          {invoice.status}
        </StatusBadge>
      </td>
      <td className='px-6 py-4'>
        <div className='text-sm text-gray-900'>
          {new Date(invoice.dueDate).toLocaleDateString()}
        </div>
        {invoice.status === 'overdue' && (
          <div className='text-xs text-red-600'>
            {Math.floor((Date.now() - new Date(invoice.dueDate).getTime()) / (1000 * 60 * 60 * 24))}{' '}
            days overdue
          </div>
        )}
      </td>
      <td className='px-6 py-4'>
        <div className='flex items-center space-x-2'>
          <button
            onClick={onView}
            className='p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded'
            title='View Invoice'
          >
            <EyeIcon className='w-4 h-4' />
          </button>
          <button
            onClick={() => onAction('send-reminder', invoice.id)}
            className='p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded'
            title='Send Reminder'
          >
            <MailIcon className='w-4 h-4' />
          </button>
          <button
            onClick={() => onAction('download', invoice.id)}
            className='p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded'
            title='Download PDF'
          >
            <DownloadIcon className='w-4 h-4' />
          </button>
        </div>
      </td>
    </tr>
  );
}
