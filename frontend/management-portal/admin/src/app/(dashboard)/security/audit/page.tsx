/**
 * Audit Trail Page
 * Comprehensive audit log exploration and compliance reporting
 */

import { AuditTrailVisualization } from '@/components/audit/AuditTrailVisualization';

export const metadata = {
  title: 'Audit Trail - Management Admin',
  description: 'Comprehensive audit log exploration and compliance reporting',
};

export default function AuditTrailPage() {
  return (
    <div className='space-y-6'>
      <AuditTrailVisualization />
    </div>
  );
}
