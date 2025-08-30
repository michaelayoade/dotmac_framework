'use client';

import { UniversalPaymentManager } from '@dotmac/billing-system';

interface PaymentMethodsProps {
  methods?: any[];
}

export function PaymentMethods({ methods }: PaymentMethodsProps) {
  return (
    <UniversalPaymentManager
      portalType="customer"
      currency="USD"
      locale="en-US"
      theme="light"
      apiEndpoint="/api/billing/payment-methods"
      enableRealtime={true}
      features={{
        addPaymentMethod: true,
        editPaymentMethod: true,
        deletePaymentMethod: true,
        setDefaultMethod: true,
        autoPaySettings: true,
        securityNotice: true,
        billingAddress: true
      }}
      initialMethods={methods}
      onPaymentMethodAdded={(method) => {
        console.log('Payment method added:', method);
      }}
      onPaymentMethodUpdated={(method) => {
        console.log('Payment method updated:', method);
      }}
      onPaymentMethodDeleted={(methodId) => {
        console.log('Payment method deleted:', methodId);
      }}
    />
  );
}
