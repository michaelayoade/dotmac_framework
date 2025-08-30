/**
 * Example integration for Customer Portal
 * Shows how to use the Universal Audit System in the customer portal (simplified)
 */

'use client';

import React from 'react';
import { UniversalAuditDashboard } from '../UniversalAuditDashboard';
import { useCustomerAudit } from '../../hooks/portal-specific';

interface CustomerAuditExampleProps {
  userId?: string;
  className?: string;
}

export function CustomerAuditExample({ userId, className }: CustomerAuditExampleProps) {
  // Use customer-specific audit hook (simplified tracking)
  const audit = useCustomerAudit({ userId });

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">Account Activity</h2>
        <div className="text-sm text-gray-500">
          Your Recent Activity
        </div>
      </div>

      <UniversalAuditDashboard
        portalType="customer"
        userId={userId}
        enableRealTime={false}
        showCompliancePanel={false}
        showMetricsOverview={false}
        compactMode={true}
        features={{
          eventFiltering: false,
          complianceReports: false,
          eventExport: false,
          realTimeAlerts: false,
          auditTrail: true,
          userTracking: false,
          systemEvents: false
        }}
        onEventClick={(event) => {
          console.log('Customer audit event clicked:', event);
          // Limited event details for customer portal
        }}
      />
    </div>
  );
}

export default CustomerAuditExample;
