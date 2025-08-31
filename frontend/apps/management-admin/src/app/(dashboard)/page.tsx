/**
 * Enhanced Management Admin Dashboard
 * Unified portal with cross-tenant analytics, dynamic resource allocation, and compliance monitoring
 */

import { Suspense } from 'react';
import { EnhancedManagementDashboard } from '@dotmac/management-portal-enhanced';

export default function DashboardPage() {
  return (
    <Suspense fallback={
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-gray-200 rounded w-1/3"></div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded"></div>
          ))}
        </div>
        <div className="h-96 bg-gray-200 rounded"></div>
      </div>
    }>
      <EnhancedManagementDashboard />
    </Suspense>
  );
}