import { Suspense } from 'react';
import { getCustomers } from '../../actions/customers';
import { AdminLayout } from '../../../components/layout/AdminLayout';
import { CustomersTable } from '../../../components/customers/CustomersTable';
import { AddCustomerButton } from '../../../components/customers/AddCustomerButton';
import { SkeletonTable } from '@dotmac/primitives';

// Server Component - data fetching happens on the server
export default async function CustomersPage({
  searchParams,
}: {
  searchParams: { page?: string; search?: string };
}) {
  const page = Number(searchParams.page) || 1;
  const search = searchParams.search || '';

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Customer Management</h1>
            <p className="mt-1 text-sm text-gray-500">
              Manage customer accounts, services, and billing
            </p>
          </div>
          <AddCustomerButton />
        </div>

        <Suspense
          fallback={
            <div className="bg-white rounded-lg shadow">
              <SkeletonTable rows={10} columns={6} />
            </div>
          }
        >
          <CustomersDataTable page={page} search={search} />
        </Suspense>
      </div>
    </AdminLayout>
  );
}

// Async component for data fetching
async function CustomersDataTable({ page, search }: { page: number; search: string }) {
  try {
    const data = await getCustomers(page, 20);
    
    return (
      <div className="bg-white rounded-lg shadow">
        <CustomersTable 
          customers={data.customers} 
          totalCount={data.total}
          currentPage={page}
        />
      </div>
    );
  } catch (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center">
          <p className="text-red-600">Failed to load customers</p>
          <p className="text-sm text-gray-500 mt-2">Please try refreshing the page</p>
        </div>
      </div>
    );
  }
}