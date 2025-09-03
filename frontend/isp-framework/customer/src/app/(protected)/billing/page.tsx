import { BillingOverviewUniversal } from '../../../components/billing/BillingOverviewUniversal';
import { CustomerLayout } from '../../../components/layout/CustomerLayout';

export default function BillingPage() {
  return (
    <CustomerLayout>
      <div className='space-y-6'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Billing & Payments</h1>
          <p className='mt-1 text-sm text-gray-500'>Manage your invoices and payment methods</p>
        </div>

        <BillingOverviewUniversal className='mt-6' />
      </div>
    </CustomerLayout>
  );
}
