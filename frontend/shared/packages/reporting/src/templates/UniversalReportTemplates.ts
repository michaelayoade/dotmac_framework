/**
 * Universal Report Templates
 * Cross-portal report templates leveraging existing system patterns
 */

import type { ReportTemplate, PortalVariant, ReportCategory, ChartType } from '../types';

// Base template factory - DRY approach
const createTemplate = (
  id: string,
  name: string,
  description: string,
  category: ReportCategory,
  portal: PortalVariant,
  config: any
): ReportTemplate => ({
  id,
  name,
  description,
  category,
  portal,
  config,
  popular: false,
  featured: false,
});

// Analytics Templates (Universal across portals)
export const ANALYTICS_TEMPLATES = {
  // Usage Analytics - Adapts to each portal context
  usageAnalytics: (portal: PortalVariant): ReportTemplate =>
    createTemplate(
      `${portal}-usage-analytics`,
      `${portal.charAt(0).toUpperCase() + portal.slice(1)} Usage Analytics`,
      `Comprehensive usage metrics for ${portal} portal`,
      'analytics',
      portal,
      {
        dataSource: {
          type: 'api',
          endpoint: `/api/${portal}/analytics/usage`,
          refreshInterval: 300000, // 5 minutes
        },
        visualization: {
          type: 'mixed',
          charts: [
            {
              id: 'usage-trend',
              title: 'Usage Trends',
              type: 'line' as ChartType,
              size: 'large',
              position: { row: 0, col: 0, span: 2 },
            },
            {
              id: 'usage-breakdown',
              title: 'Usage Breakdown',
              type: 'pie' as ChartType,
              size: 'medium',
              position: { row: 1, col: 0 },
            },
            {
              id: 'peak-hours',
              title: 'Peak Usage Hours',
              type: 'bar' as ChartType,
              size: 'medium',
              position: { row: 1, col: 1 },
            },
          ],
          table: {
            columns: [
              { key: 'date', title: 'Date', sortable: true },
              { key: 'users', title: 'Active Users', sortable: true },
              { key: 'sessions', title: 'Sessions', sortable: true },
              { key: 'duration', title: 'Avg Duration', sortable: true },
              { key: 'features', title: 'Features Used', sortable: true },
            ],
            pagination: true,
            sorting: true,
            filtering: true,
          },
        },
        filters: [
          {
            id: 'date-range',
            field: 'date',
            label: 'Date Range',
            type: 'date',
            operator: 'between',
            required: true,
            defaultValue: [new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), new Date()],
          },
        ],
        export: {
          includeHeaders: true,
          formats: ['csv', 'xlsx', 'pdf'],
        },
      }
    ),

  // Performance Dashboard
  performanceDashboard: (portal: PortalVariant): ReportTemplate =>
    createTemplate(
      `${portal}-performance`,
      `${portal.charAt(0).toUpperCase() + portal.slice(1)} Performance Dashboard`,
      `Real-time performance metrics for ${portal} operations`,
      'performance',
      portal,
      {
        dataSource: {
          type: 'realtime',
          endpoint: `/api/${portal}/metrics/performance`,
          refreshInterval: 30000, // 30 seconds
        },
        visualization: {
          type: 'chart',
          charts: [
            {
              id: 'response-time',
              title: 'Response Time',
              type: 'line' as ChartType,
              size: 'medium',
            },
            {
              id: 'throughput',
              title: 'Throughput',
              type: 'area' as ChartType,
              size: 'medium',
            },
            {
              id: 'error-rate',
              title: 'Error Rate',
              type: 'line' as ChartType,
              size: 'medium',
            },
            {
              id: 'resource-usage',
              title: 'Resource Usage',
              type: 'bar' as ChartType,
              size: 'medium',
            },
          ],
        },
        export: {
          includeHeaders: true,
          formats: ['png', 'pdf'],
        },
      }
    ),
};

// Financial Templates (Admin, Management, Reseller)
export const FINANCIAL_TEMPLATES = {
  revenueReport: (portal: 'admin' | 'management' | 'reseller'): ReportTemplate =>
    createTemplate(
      `${portal}-revenue-report`,
      'Revenue Analytics',
      'Comprehensive revenue tracking and forecasting',
      'financial',
      portal,
      {
        dataSource: {
          type: 'api',
          endpoint: `/api/${portal}/financial/revenue`,
          caching: true,
        },
        visualization: {
          type: 'mixed',
          charts: [
            {
              id: 'revenue-trend',
              title: 'Revenue Trend',
              type: 'line' as ChartType,
              size: 'full',
            },
            {
              id: 'revenue-by-service',
              title: 'Revenue by Service',
              type: 'pie' as ChartType,
              size: 'medium',
            },
            {
              id: 'monthly-comparison',
              title: 'Monthly Comparison',
              type: 'bar' as ChartType,
              size: 'medium',
            },
          ],
          table: {
            columns: [
              { key: 'period', title: 'Period', sortable: true },
              {
                key: 'revenue',
                title: 'Revenue',
                sortable: true,
                formatter: (val: any) => `$${val.toLocaleString()}`,
              },
              { key: 'growth', title: 'Growth %', sortable: true },
              { key: 'customers', title: 'Customers', sortable: true },
              {
                key: 'arpu',
                title: 'ARPU',
                sortable: true,
                formatter: (val: any) => `$${val.toFixed(2)}`,
              },
            ],
            pagination: true,
            sorting: true,
            totals: true,
          },
        },
        aggregation: [
          { field: 'revenue', operation: 'sum', label: 'Total Revenue' },
          { field: 'customers', operation: 'count', label: 'Total Customers' },
          { field: 'arpu', operation: 'avg', label: 'Average ARPU' },
        ],
      }
    ),

  billingReport: (portal: 'admin' | 'management'): ReportTemplate =>
    createTemplate(
      `${portal}-billing-report`,
      'Billing & Collections Report',
      'Outstanding invoices and payment tracking',
      'financial',
      portal,
      {
        dataSource: {
          type: 'api',
          endpoint: `/api/${portal}/billing/summary`,
        },
        visualization: {
          type: 'mixed',
          charts: [
            {
              id: 'aging-analysis',
              title: 'Aging Analysis',
              type: 'bar' as ChartType,
              size: 'large',
            },
            {
              id: 'collection-rate',
              title: 'Collection Rate',
              type: 'line' as ChartType,
              size: 'medium',
            },
          ],
          table: {
            columns: [
              { key: 'customer', title: 'Customer', sortable: true },
              { key: 'invoice_date', title: 'Invoice Date', sortable: true },
              { key: 'due_date', title: 'Due Date', sortable: true },
              { key: 'amount', title: 'Amount', sortable: true },
              { key: 'status', title: 'Status', filterable: true },
              { key: 'days_overdue', title: 'Days Overdue', sortable: true },
            ],
            pagination: true,
            sorting: true,
            filtering: true,
          },
        },
      }
    ),
};

// Operational Templates
export const OPERATIONAL_TEMPLATES = {
  customerReport: (portal: 'admin' | 'reseller'): ReportTemplate =>
    createTemplate(
      `${portal}-customer-report`,
      'Customer Analytics',
      'Customer acquisition, retention, and lifetime value metrics',
      'customer',
      portal,
      {
        dataSource: {
          type: 'api',
          endpoint: `/api/${portal}/customers/analytics`,
        },
        visualization: {
          type: 'mixed',
          charts: [
            {
              id: 'acquisition-trend',
              title: 'Customer Acquisition',
              type: 'line' as ChartType,
              size: 'large',
            },
            {
              id: 'churn-rate',
              title: 'Churn Rate',
              type: 'line' as ChartType,
              size: 'medium',
            },
            {
              id: 'customer-segments',
              title: 'Customer Segments',
              type: 'donut' as ChartType,
              size: 'medium',
            },
          ],
          table: {
            columns: [
              { key: 'segment', title: 'Segment', sortable: true },
              { key: 'count', title: 'Customers', sortable: true },
              { key: 'revenue', title: 'Revenue', sortable: true },
              { key: 'avg_tenure', title: 'Avg Tenure', sortable: true },
              { key: 'churn_risk', title: 'Churn Risk', filterable: true },
            ],
            pagination: true,
            sorting: true,
          },
        },
      }
    ),

  networkReport: (portal: 'admin' | 'technician' | 'management'): ReportTemplate =>
    createTemplate(
      `${portal}-network-report`,
      'Network Performance Report',
      'Network uptime, performance metrics, and incident tracking',
      'network',
      portal,
      {
        dataSource: {
          type: 'realtime',
          endpoint: `/api/${portal}/network/performance`,
          refreshInterval: 60000, // 1 minute
        },
        visualization: {
          type: 'mixed',
          charts: [
            {
              id: 'uptime-trend',
              title: 'Network Uptime',
              type: 'area' as ChartType,
              size: 'large',
            },
            {
              id: 'latency-distribution',
              title: 'Latency Distribution',
              type: 'bar' as ChartType,
              size: 'medium',
            },
            {
              id: 'bandwidth-utilization',
              title: 'Bandwidth Utilization',
              type: 'line' as ChartType,
              size: 'medium',
            },
          ],
          table: {
            columns: [
              { key: 'location', title: 'Location', sortable: true },
              { key: 'uptime', title: 'Uptime %', sortable: true },
              { key: 'avg_latency', title: 'Avg Latency', sortable: true },
              { key: 'bandwidth_used', title: 'Bandwidth Used', sortable: true },
              { key: 'incidents', title: 'Incidents', sortable: true },
            ],
            pagination: true,
            sorting: true,
          },
        },
      }
    ),
};

// Compliance Templates
export const COMPLIANCE_TEMPLATES = {
  auditReport: (portal: 'admin' | 'management'): ReportTemplate =>
    createTemplate(
      `${portal}-audit-report`,
      'System Audit Report',
      'Security events, access logs, and compliance tracking',
      'compliance',
      portal,
      {
        dataSource: {
          type: 'api',
          endpoint: `/api/${portal}/audit/events`,
        },
        visualization: {
          type: 'table',
          table: {
            columns: [
              { key: 'timestamp', title: 'Timestamp', sortable: true },
              { key: 'user', title: 'User', sortable: true, filterable: true },
              { key: 'action', title: 'Action', filterable: true },
              { key: 'resource', title: 'Resource', filterable: true },
              { key: 'ip_address', title: 'IP Address', sortable: true },
              { key: 'status', title: 'Status', filterable: true },
              { key: 'details', title: 'Details' },
            ],
            pagination: true,
            sorting: true,
            filtering: true,
          },
        },
        filters: [
          {
            id: 'severity',
            field: 'severity',
            label: 'Severity Level',
            type: 'select',
            operator: 'in',
            values: ['low', 'medium', 'high', 'critical'],
          },
          {
            id: 'date-range',
            field: 'timestamp',
            label: 'Date Range',
            type: 'date',
            operator: 'between',
            required: true,
          },
        ],
      }
    ),
};

// Portal-specific template collections
export const PORTAL_TEMPLATES = {
  admin: [
    ANALYTICS_TEMPLATES.usageAnalytics('admin'),
    ANALYTICS_TEMPLATES.performanceDashboard('admin'),
    FINANCIAL_TEMPLATES.revenueReport('admin'),
    FINANCIAL_TEMPLATES.billingReport('admin'),
    OPERATIONAL_TEMPLATES.customerReport('admin'),
    OPERATIONAL_TEMPLATES.networkReport('admin'),
    COMPLIANCE_TEMPLATES.auditReport('admin'),
  ],

  customer: [
    ANALYTICS_TEMPLATES.usageAnalytics('customer'),
    ANALYTICS_TEMPLATES.performanceDashboard('customer'),
  ],

  reseller: [
    ANALYTICS_TEMPLATES.usageAnalytics('reseller'),
    FINANCIAL_TEMPLATES.revenueReport('reseller'),
    OPERATIONAL_TEMPLATES.customerReport('reseller'),
  ],

  technician: [
    ANALYTICS_TEMPLATES.performanceDashboard('technician'),
    OPERATIONAL_TEMPLATES.networkReport('technician'),
  ],

  management: [
    ANALYTICS_TEMPLATES.usageAnalytics('management'),
    ANALYTICS_TEMPLATES.performanceDashboard('management'),
    FINANCIAL_TEMPLATES.revenueReport('management'),
    FINANCIAL_TEMPLATES.billingReport('management'),
    OPERATIONAL_TEMPLATES.networkReport('management'),
    COMPLIANCE_TEMPLATES.auditReport('management'),
  ],
};

// Template search and filtering utilities
export const getTemplatesByPortal = (portal: PortalVariant): ReportTemplate[] => {
  return PORTAL_TEMPLATES[portal as keyof typeof PORTAL_TEMPLATES] || [];
};

export const getTemplatesByCategory = (
  portal: PortalVariant,
  category: ReportCategory
): ReportTemplate[] => {
  return getTemplatesByPortal(portal).filter((template) => template.category === category);
};

export const getFeaturedTemplates = (portal: PortalVariant): ReportTemplate[] => {
  return getTemplatesByPortal(portal)
    .filter((template) => template.featured)
    .slice(0, 6);
};

export const getPopularTemplates = (portal: PortalVariant): ReportTemplate[] => {
  return getTemplatesByPortal(portal)
    .filter((template) => template.popular)
    .slice(0, 8);
};

export const searchTemplates = (portal: PortalVariant, query: string): ReportTemplate[] => {
  const templates = getTemplatesByPortal(portal);
  const searchTerm = query.toLowerCase();

  return templates.filter(
    (template) =>
      template.name.toLowerCase().includes(searchTerm) ||
      template.description.toLowerCase().includes(searchTerm) ||
      template.category.toLowerCase().includes(searchTerm)
  );
};

// Mark featured templates
if (PORTAL_TEMPLATES.admin[0]) PORTAL_TEMPLATES.admin[0].featured = true; // Usage Analytics
if (PORTAL_TEMPLATES.admin[2]) PORTAL_TEMPLATES.admin[2].featured = true; // Revenue Report
if (PORTAL_TEMPLATES.management[0]) PORTAL_TEMPLATES.management[0].featured = true; // Usage Analytics
if (PORTAL_TEMPLATES.management[2]) PORTAL_TEMPLATES.management[2].featured = true; // Revenue Report

// Mark popular templates
const adminUsageTemplate = ANALYTICS_TEMPLATES.usageAnalytics('admin');
adminUsageTemplate.popular = true;

const adminPerfTemplate = ANALYTICS_TEMPLATES.performanceDashboard('admin');
adminPerfTemplate.popular = true;

const adminRevenueTemplate = FINANCIAL_TEMPLATES.revenueReport('admin');
adminRevenueTemplate.popular = true;

const adminCustomerTemplate = OPERATIONAL_TEMPLATES.customerReport('admin');
adminCustomerTemplate.popular = true;
