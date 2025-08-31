"use client";

import { LeadManagementDashboard } from '@/components/leads/LeadManagementDashboard';

export default function LeadsPage() {
  return (
    <div className="container mx-auto px-4 py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Lead Management</h1>
        <p className="text-gray-600 mt-1">
          Track and manage your sales leads with CRM-like functionality
        </p>
      </div>
      
      <LeadManagementDashboard />
    </div>
  );
}