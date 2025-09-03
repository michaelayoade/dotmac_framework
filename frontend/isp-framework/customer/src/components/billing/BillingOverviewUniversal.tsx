'use client';

import { UniversalBillingDashboard } from '@dotmac/billing-system';

interface BillingOverviewUniversalProps {
  customerId?: string;
  className?: string;
}

export function BillingOverviewUniversal({ customerId, className }: BillingOverviewUniversalProps) {
  return (
    <UniversalBillingDashboard
      portalType='customer'
      customerId={customerId}
      currency='USD'
      locale='en-US'
      theme='light'
      apiEndpoint='/api/billing'
      enableRealtime={true}
      className={className}
      features={{
        invoiceGeneration: false,
        paymentProcessing: true,
        refunds: false,
        reporting: false,
        bulkOperations: false,
        automations: false,
        analytics: false,
      }}
    />
  );
}
