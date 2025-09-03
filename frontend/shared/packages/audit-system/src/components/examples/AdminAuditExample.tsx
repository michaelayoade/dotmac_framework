/**
 * Example integration for Admin Portal
 * Shows how to use the Universal Audit System in the admin portal
 */

'use client';

import React from 'react';
import { UniversalAuditDashboard } from '../UniversalAuditDashboard';
import { useAdminAudit } from '../../hooks/portal-specific';

interface AdminAuditExampleProps {
  userId?: string;
  className?: string;
}

export function AdminAuditExample({ userId, className }: AdminAuditExampleProps) {
  // Use portal-specific audit hook
  const audit = useAdminAudit({ userId });

  return (
    <div className={`space-y-6 ${className}`}>
      <div className='flex items-center justify-between'>
        <h2 className='text-2xl font-bold text-gray-900'>Admin Audit Dashboard</h2>
        <div className='text-sm text-gray-500'>Portal: Admin | User: {userId || 'System'}</div>
      </div>

      <UniversalAuditDashboard
        portalType='admin'
        userId={userId}
        enableRealTime={true}
        showCompliancePanel={true}
        showMetricsOverview={true}
        compactMode={false}
        features={{
          eventFiltering: true,
          complianceReports: true,
          eventExport: true,
          realTimeAlerts: true,
          auditTrail: true,
          userTracking: true,
          systemEvents: true,
        }}
        onEventClick={(event) => {
          console.log('Admin audit event clicked:', event);
          // Handle event click - could show modal, navigate, etc.
        }}
      />
    </div>
  );
}

export default AdminAuditExample;
