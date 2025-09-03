import { Suspense } from 'react';
import AdminLayout from '../../../components/layout/AdminLayout';
import { BillingManagementUniversal } from '../../../components/billing/BillingManagementUniversal';

interface SearchParams {
  page?: string;
  search?: string;
  status?: string;
  type?: string;
  dateRange?: string;
  pageSize?: string;
  tab?: string;
}

export default function BillingPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <AdminLayout>
      <div className='space-y-6'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Billing & Finance</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Comprehensive billing management, invoicing, payments, and financial reporting
            </p>
          </div>
          <div className='flex gap-3'>
            <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'>
              Generate Invoice
            </button>
            <button className='px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium'>
              Export Reports
            </button>
          </div>
        </div>

        <BillingManagementUniversal className='mt-6' />
      </div>
    </AdminLayout>
  );
}
