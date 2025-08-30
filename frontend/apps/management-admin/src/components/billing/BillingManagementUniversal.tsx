'use client';

import { UniversalBillingDashboard } from '@dotmac/billing-system';

interface BillingManagementUniversalProps {
  customerId?: string;
  className?: string;
}

export function BillingManagementUniversal({ customerId, className }: BillingManagementUniversalProps) {
  return (
    <UniversalBillingDashboard
      portalType="management"
      customerId={customerId}
      currency="USD"
      locale="en-US"
      theme="light"
      apiEndpoint="/api/management/billing"
      enableRealtime={true}
      className={className}
      features={{
        invoiceGeneration: true,
        paymentProcessing: true,
        refunds: true,
        reporting: true,
        bulkOperations: true,
        automations: true,
        analytics: true
      }}
    />
  );
}
