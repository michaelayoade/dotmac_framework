import { Suspense } from 'react';
import { getInvoices, getPaymentMethods } from '../../actions/billing';
import { CustomerLayout } from '../../../components/layout/CustomerLayout';
import { InvoicesList } from '../../../components/billing/InvoicesList';
import { PaymentMethods } from '../../../components/billing/PaymentMethods';
import { BillingOverview } from '../../../components/billing/BillingOverview';
import { SkeletonCard, SkeletonTable } from '@dotmac/primitives';

export default function BillingPage() {
  return (
    <CustomerLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Billing & Payments</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage your invoices and payment methods
          </p>
        </div>

        <Suspense fallback={<BillingSkeleton />}>
          <BillingContent />
        </Suspense>
      </div>
    </CustomerLayout>
  );
}

async function BillingContent() {
  const [invoices, paymentMethods] = await Promise.all([
    getInvoices(),
    getPaymentMethods(),
  ]);

  return (
    <div className="space-y-6">
      <BillingOverview invoices={invoices} />
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <InvoicesList invoices={invoices} />
        </div>
        <div>
          <PaymentMethods methods={paymentMethods} />
        </div>
      </div>
    </div>
  );
}

function BillingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SkeletonTable rows={5} columns={4} />
        </div>
        <div>
          <SkeletonCard />
        </div>
      </div>
    </div>
  );
}
