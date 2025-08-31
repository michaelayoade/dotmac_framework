/**
 * Reseller Territory Dashboard
 * Coverage + KPIs + leads by region using DashboardTemplate
 */

'use client';

import React from 'react';
import { DashboardTemplate, DashboardConfig } from '@dotmac/patterns/templates';
import { TerritoryMap } from '@dotmac/mapping';
import { Card } from '@dotmac/primitives';
import { MapPin, Users, TrendingUp, Target, AlertCircle } from 'lucide-react';

// Custom territory map component for dashboard
function TerritoryMapSection({ data, isLoading }: { data?: any; isLoading: boolean }) {
  if (isLoading) {
    return <div className="h-96 bg-gray-100 rounded-lg animate-pulse" />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Territory Coverage</h3>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500 rounded-full" />
            <span className="text-sm">Active</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-yellow-500 rounded-full" />
            <span className="text-sm">Opportunity</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-500 rounded-full" />
            <span className="text-sm">Unassigned</span>
          </div>
        </div>
      </div>
      <TerritoryMap
        territories={data?.territories || []}
        leads={data?.leads || []}
        customers={data?.customers || []}
        height={400}
        interactive={true}
        showControls={true}
      />
    </div>
  );
}

// Lead priority component
function LeadsPrioritySection({ data, isLoading }: { data?: any; isLoading: boolean }) {
  if (isLoading) {
    return <div className="space-y-3">
      {[1, 2, 3].map(i => (
        <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
      ))}
    </div>;
  }

  const priorityLeads = data?.priorityLeads || [];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium">High Priority Leads</h3>
      <div className="space-y-3">
        {priorityLeads.slice(0, 5).map((lead: any) => (
          <Card key={lead.id} className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{lead.company || lead.name}</div>
                <div className="text-sm text-gray-500">
                  {lead.location} • Score: {lead.score}/100
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className={`px-2 py-1 rounded text-xs ${
                  lead.priority === 'high' ? 'bg-red-100 text-red-700' :
                  lead.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-green-100 text-green-700'
                }`}>
                  {lead.priority.toUpperCase()}
                </div>
                <div className="text-sm text-gray-500">
                  ${lead.estimatedValue?.toLocaleString()}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

const dashboardConfig: DashboardConfig = {
  title: 'Territory Dashboard',
  subtitle: 'Coverage, KPIs, and leads by region',
  portal: 'reseller',
  apiEndpoint: '/api/reseller/territory/dashboard',
  refreshInterval: 300, // 5 minutes
  timeRanges: [
    { label: 'Last 7 days', value: '7d' },
    { label: 'Last 30 days', value: '30d' },
    { label: 'Last 90 days', value: '90d' },
    { label: 'This year', value: '1y' }
  ],
  filters: [
    {
      key: 'region',
      label: 'Region',
      type: 'select',
      options: [
        { label: 'North', value: 'north' },
        { label: 'South', value: 'south' },
        { label: 'East', value: 'east' },
        { label: 'West', value: 'west' }
      ]
    },
    {
      key: 'leadStatus',
      label: 'Lead Status',
      type: 'select',
      options: [
        { label: 'New', value: 'new' },
        { label: 'Contacted', value: 'contacted' },
        { label: 'Qualified', value: 'qualified' },
        { label: 'Proposal', value: 'proposal' }
      ]
    }
  ],
  metrics: [
    {
      id: 'territory-coverage',
      label: 'Territory Coverage',
      value: '87.5%',
      change: '+2.3%',
      trend: 'up' as const,
      icon: MapPin,
      description: 'Geographic coverage of assigned territory'
    },
    {
      id: 'active-leads',
      label: 'Active Leads',
      value: '142',
      change: '+18',
      trend: 'up' as const,
      icon: Users,
      description: 'Qualified leads in pipeline'
    },
    {
      id: 'conversion-rate',
      label: 'Conversion Rate',
      value: '24.8%',
      change: '+1.2%',
      trend: 'up' as const,
      icon: TrendingUp,
      description: 'Lead to customer conversion rate'
    },
    {
      id: 'pipeline-value',
      label: 'Pipeline Value',
      value: '$1.2M',
      change: '+$180K',
      trend: 'up' as const,
      icon: Target,
      description: 'Total value of active opportunities'
    }
  ],
  sections: [
    {
      id: 'territory-map',
      title: 'Territory Coverage',
      type: 'custom',
      size: 'full',
      order: 1,
      component: TerritoryMapSection,
      permission: 'reseller:territory:view'
    },
    {
      id: 'leads-chart',
      title: 'Leads by Region',
      type: 'chart',
      size: 'lg',
      order: 2,
      config: {
        id: 'leads-by-region',
        title: 'Leads by Region',
        type: 'bar' as const,
        dataKey: 'leads',
        height: 300,
        color: '#3B82F6',
        showLegend: true,
        interactive: true
      }
    },
    {
      id: 'priority-leads',
      title: 'High Priority Leads',
      type: 'custom',
      size: 'md',
      order: 3,
      component: LeadsPrioritySection
    },
    {
      id: 'conversion-funnel',
      title: 'Conversion Funnel',
      type: 'chart',
      size: 'lg',
      order: 4,
      config: {
        id: 'conversion-funnel',
        title: 'Lead Conversion Funnel',
        type: 'area' as const,
        dataKey: 'value',
        height: 250,
        color: '#10B981',
        showLegend: false,
        interactive: true
      }
    },
    {
      id: 'recent-activity',
      title: 'Recent Activity',
      type: 'table',
      size: 'lg',
      order: 5,
      config: {
        id: 'recent-activity',
        title: 'Recent Territory Activity',
        columns: [
          { key: 'timestamp', label: 'Time' },
          { key: 'type', label: 'Activity' },
          { key: 'lead', label: 'Lead/Customer' },
          { key: 'location', label: 'Location' },
          { key: 'value', label: 'Value' }
        ],
        apiEndpoint: '/api/reseller/territory/activity',
        maxItems: 10,
        showViewAll: true
      }
    },
    {
      id: 'performance-metrics',
      title: 'Performance vs Target',
      type: 'chart',
      size: 'md',
      order: 6,
      config: {
        id: 'performance-target',
        title: 'Performance vs Target',
        type: 'donut' as const,
        dataKey: 'percentage',
        height: 200,
        color: '#8B5CF6',
        showLegend: true,
        interactive: false
      }
    }
  ],
  permissions: {
    view: 'reseller:territory:view',
    export: 'reseller:territory:export',
    manage: 'reseller:territory:manage'
  }
};

export default function TerritoryPage() {
  return (
    <DashboardTemplate 
      config={dashboardConfig}
      className="max-w-7xl mx-auto"
    />
  );
}
