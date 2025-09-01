"""
Unified Partner Dashboard
React/TypeScript components for partners to view performance across all their tenants
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import json

# This represents the TypeScript/React component structure as Python models
# for data serialization and API responses

class DashboardWidget(BaseModel):
    widget_id: str
    widget_type: str = Field(..., regex="^(metric_card|chart|table|list|map)$")
    title: str
    size: str = Field(..., regex="^(sm|md|lg|xl|full)$")
    position: Dict[str, int] = {"row": 0, "col": 0}
    data_source: str
    refresh_interval_seconds: Optional[int] = Field(None, ge=30, le=3600)
    config: Dict[str, Any] = {}


class DashboardLayout(BaseModel):
    layout_id: str
    layout_name: str
    partner_id: str
    is_default: bool = False
    widgets: List[DashboardWidget] = []
    created_at: datetime
    updated_at: datetime


# TypeScript/React Component Templates
DASHBOARD_COMPONENT_TEMPLATES = {
    "UnifiedPartnerDashboard": """
// UnifiedPartnerDashboard.tsx
'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { 
  Users, 
  DollarSign, 
  TrendingUp, 
  TrendingDown,
  Building2,
  BarChart3,
  PieChart,
  Filter,
  Download,
  Settings,
  Refresh,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';

interface TenantMetrics {
  tenant_id: string;
  tenant_name: string;
  total_revenue: number;
  total_customers: number;
  customer_satisfaction: number | null;
  revenue_growth_rate: number;
  service_uptime_percentage: number | null;
}

interface CrossTenantDashboardData {
  partner_id: string;
  partner_name: string;
  report_period: {
    start: string;
    end: string;
  };
  total_tenants: number;
  total_customers: number;
  total_revenue: number;
  average_customer_satisfaction: number | null;
  tenant_rankings: Array<{
    tenant_id: string;
    tenant_name: string;
    rank: number;
    score: number;
    strengths: string[];
    improvement_areas: string[];
  }>;
  performance_insights: string[];
  growth_opportunities: string[];
  risk_alerts: string[];
}

interface Props {
  partner_id: string;
  initial_data?: CrossTenantDashboardData;
}

export default function UnifiedPartnerDashboard({ partner_id, initial_data }: Props) {
  const [dashboardData, setDashboardData] = useState<CrossTenantDashboardData | null>(initial_data || null);
  const [selectedPeriod, setSelectedPeriod] = useState('30d');
  const [selectedTenants, setSelectedTenants] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(!initial_data);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // Fetch dashboard data
  const fetchDashboardData = async (period: string = selectedPeriod) => {
    setIsLoading(true);
    try {
      const endDate = new Date();
      const startDate = new Date();
      
      switch (period) {
        case '7d':
          startDate.setDate(endDate.getDate() - 7);
          break;
        case '30d':
          startDate.setDate(endDate.getDate() - 30);
          break;
        case '90d':
          startDate.setDate(endDate.getDate() - 90);
          break;
        case '1y':
          startDate.setFullYear(endDate.getFullYear() - 1);
          break;
      }

      const params = new URLSearchParams({
        period_start: startDate.toISOString(),
        period_end: endDate.toISOString(),
      });

      if (selectedTenants.length > 0) {
        params.append('tenant_filter', selectedTenants.join(','));
      }

      const response = await fetch(`/api/partners/${partner_id}/cross-tenant-dashboard?${params}`);
      const data = await response.json();
      
      setDashboardData(data);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!initial_data) {
      fetchDashboardData();
    }
  }, [partner_id, selectedPeriod, selectedTenants]);

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(() => {
      fetchDashboardData();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, [selectedPeriod, selectedTenants]);

  const handleRefresh = () => {
    fetchDashboardData();
  };

  const handleExport = async (format: 'csv' | 'xlsx' | 'pdf') => {
    try {
      const response = await fetch(`/api/partners/${partner_id}/export-dashboard?format=${format}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          period: selectedPeriod,
          tenant_filter: selectedTenants,
          dashboard_data: dashboardData,
        }),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `partner-dashboard-${partner_id}-${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  if (isLoading && !dashboardData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading partner dashboard...</p>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Data Available</h3>
          <p className="text-gray-600">Unable to load dashboard data</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {dashboardData.partner_name} - Multi-Tenant Dashboard
              </h1>
              <p className="text-gray-600 mt-1">
                Performance across {dashboardData.total_tenants} tenants
              </p>
            </div>
            
            <div className="flex items-center space-x-3">
              {/* Period Selector */}
              <select
                value={selectedPeriod}
                onChange={(e) => setSelectedPeriod(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm"
              >
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="90d">Last 90 days</option>
                <option value="1y">Last year</option>
              </select>

              {/* Export Button */}
              <div className="relative">
                <button
                  onClick={() => handleExport('xlsx')}
                  className="flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm hover:bg-gray-50"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </button>
              </div>

              {/* Refresh Button */}
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                <Refresh className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Revenue"
            value={`$${dashboardData.total_revenue.toLocaleString()}`}
            icon={DollarSign}
            trend="up"
            trendValue="12.3%"
            className="bg-gradient-to-r from-green-500 to-green-600"
          />
          
          <MetricCard
            title="Total Customers"
            value={dashboardData.total_customers.toLocaleString()}
            icon={Users}
            trend="up"
            trendValue="8.7%"
            className="bg-gradient-to-r from-blue-500 to-blue-600"
          />
          
          <MetricCard
            title="Active Tenants"
            value={dashboardData.total_tenants.toString()}
            icon={Building2}
            trend="stable"
            className="bg-gradient-to-r from-purple-500 to-purple-600"
          />
          
          <MetricCard
            title="Avg Satisfaction"
            value={dashboardData.average_customer_satisfaction?.toFixed(1) || 'N/A'}
            icon={CheckCircle}
            trend={dashboardData.average_customer_satisfaction && dashboardData.average_customer_satisfaction > 8 ? 'up' : 'down'}
            trendValue="0.3pt"
            className="bg-gradient-to-r from-orange-500 to-orange-600"
          />
        </div>

        {/* Insights and Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <InsightCard
            title="Performance Insights"
            items={dashboardData.performance_insights}
            icon={TrendingUp}
            type="success"
          />
          
          <InsightCard
            title="Growth Opportunities"
            items={dashboardData.growth_opportunities}
            icon={ArrowUpRight}
            type="info"
          />
          
          <InsightCard
            title="Risk Alerts"
            items={dashboardData.risk_alerts}
            icon={AlertTriangle}
            type="warning"
          />
        </div>

        {/* Tenant Rankings */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-900">Tenant Performance Rankings</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Rank
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tenant
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Strengths
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Improvement Areas
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {dashboardData.tenant_rankings.map((tenant) => (
                  <tr key={tenant.tenant_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className={`flex items-center justify-center w-8 h-8 rounded-full text-white text-sm font-medium ${
                        tenant.rank === 1 ? 'bg-yellow-500' :
                        tenant.rank === 2 ? 'bg-gray-400' :
                        tenant.rank === 3 ? 'bg-orange-500' : 'bg-gray-300'
                      }`}>
                        {tenant.rank}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {tenant.tenant_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {tenant.score.toFixed(1)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {tenant.strengths.slice(0, 2).map((strength, idx) => (
                          <span
                            key={idx}
                            className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800"
                          >
                            {strength}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {tenant.improvement_areas.slice(0, 2).map((area, idx) => (
                          <span
                            key={idx}
                            className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800"
                          >
                            {area}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-gray-500">
          Last updated: {lastRefresh.toLocaleString()}
        </div>
      </div>
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  className?: string;
}

function MetricCard({ title, value, icon: Icon, trend, trendValue, className }: MetricCardProps) {
  return (
    <div className={`rounded-lg p-6 text-white ${className || 'bg-gray-600'}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-white/80 text-sm font-medium">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
          {trend && trendValue && (
            <div className="flex items-center mt-2">
              {trend === 'up' ? (
                <TrendingUp className="h-4 w-4 mr-1" />
              ) : trend === 'down' ? (
                <TrendingDown className="h-4 w-4 mr-1" />
              ) : null}
              <span className="text-sm">{trendValue}</span>
            </div>
          )}
        </div>
        <Icon className="h-8 w-8 text-white/80" />
      </div>
    </div>
  );
}

interface InsightCardProps {
  title: string;
  items: string[];
  icon: React.ComponentType<{ className?: string }>;
  type: 'success' | 'info' | 'warning';
}

function InsightCard({ title, items, icon: Icon, type }: InsightCardProps) {
  const colorClasses = {
    success: 'border-green-200 bg-green-50 text-green-800',
    info: 'border-blue-200 bg-blue-50 text-blue-800',
    warning: 'border-yellow-200 bg-yellow-50 text-yellow-800'
  };

  const iconColorClasses = {
    success: 'text-green-600',
    info: 'text-blue-600', 
    warning: 'text-yellow-600'
  };

  return (
    <div className={`border rounded-lg p-6 ${colorClasses[type]}`}>
      <div className="flex items-center mb-4">
        <Icon className={`h-5 w-5 mr-2 ${iconColorClasses[type]}`} />
        <h3 className="font-medium">{title}</h3>
      </div>
      
      {items.length > 0 ? (
        <ul className="space-y-2 text-sm">
          {items.slice(0, 3).map((item, idx) => (
            <li key={idx} className="flex items-start">
              <span className="flex-shrink-0 w-1.5 h-1.5 bg-current rounded-full mt-2 mr-2" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm">No insights available</p>
      )}
    </div>
  );
}
""",

    "TenantComparisonModal": """
// TenantComparisonModal.tsx
'use client';

import React, { useState, useEffect } from 'react';
import { X, BarChart3, TrendingUp, Users, DollarSign } from 'lucide-react';

interface TenantComparisonData {
  comparison_id: string;
  partner_id: string;
  tenant_ids: string[];
  revenue_comparison: Record<string, number>;
  customer_comparison: Record<string, number>;
  growth_comparison: Record<string, number>;
  satisfaction_comparison: Record<string, number>;
  top_performers: string[];
  underperformers: string[];
  improvement_recommendations: Record<string, string[]>;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  partner_id: string;
  selected_tenant_ids: string[];
}

export default function TenantComparisonModal({ isOpen, onClose, partner_id, selected_tenant_ids }: Props) {
  const [comparisonData, setComparisonData] = useState<TenantComparisonData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen && selected_tenant_ids.length >= 2) {
      fetchComparisonData();
    }
  }, [isOpen, selected_tenant_ids]);

  const fetchComparisonData = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/partners/${partner_id}/tenant-comparison`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tenant_ids: selected_tenant_ids,
          period_start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          period_end: new Date().toISOString(),
        }),
      });
      
      const data = await response.json();
      setComparisonData(data);
    } catch (error) {
      console.error('Failed to fetch comparison data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" onClick={onClose} />
        
        <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-4xl">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div className="flex items-center">
              <BarChart3 className="h-6 w-6 text-blue-600 mr-3" />
              <h3 className="text-lg font-medium text-gray-900">
                Tenant Performance Comparison
              </h3>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                <span className="ml-3 text-gray-600">Loading comparison...</span>
              </div>
            ) : comparisonData ? (
              <div className="space-y-6">
                {/* Comparison Charts */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <ComparisonChart
                    title="Revenue Comparison"
                    data={comparisonData.revenue_comparison}
                    icon={DollarSign}
                    format="currency"
                  />
                  
                  <ComparisonChart
                    title="Customer Count"
                    data={comparisonData.customer_comparison}
                    icon={Users}
                    format="number"
                  />
                  
                  <ComparisonChart
                    title="Growth Rate"
                    data={comparisonData.growth_comparison}
                    icon={TrendingUp}
                    format="percentage"
                  />
                  
                  <ComparisonChart
                    title="Customer Satisfaction"
                    data={comparisonData.satisfaction_comparison}
                    icon={BarChart3}
                    format="rating"
                  />
                </div>

                {/* Performance Categories */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-green-800 mb-2">Top Performers</h4>
                    <ul className="space-y-1">
                      {comparisonData.top_performers.map((tenantId) => (
                        <li key={tenantId} className="text-sm text-green-700">
                          • Tenant {tenantId.slice(-4).toUpperCase()}
                        </li>
                      ))}
                    </ul>
                  </div>
                  
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-red-800 mb-2">Needs Attention</h4>
                    <ul className="space-y-1">
                      {comparisonData.underperformers.map((tenantId) => (
                        <li key={tenantId} className="text-sm text-red-700">
                          • Tenant {tenantId.slice(-4).toUpperCase()}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Improvement Recommendations */}
                {Object.keys(comparisonData.improvement_recommendations).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Improvement Recommendations</h4>
                    <div className="space-y-3">
                      {Object.entries(comparisonData.improvement_recommendations).map(([tenantId, recommendations]) => (
                        <div key={tenantId} className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                          <h5 className="text-sm font-medium text-yellow-800 mb-2">
                            Tenant {tenantId.slice(-4).toUpperCase()}
                          </h5>
                          <ul className="space-y-1">
                            {recommendations.slice(0, 3).map((rec, idx) => (
                              <li key={idx} className="text-xs text-yellow-700">
                                • {rec}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <p className="text-gray-600">No comparison data available</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-3 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ComparisonChartProps {
  title: string;
  data: Record<string, number>;
  icon: React.ComponentType<{ className?: string }>;
  format: 'currency' | 'number' | 'percentage' | 'rating';
}

function ComparisonChart({ title, data, icon: Icon, format }: ComparisonChartProps) {
  const formatValue = (value: number) => {
    switch (format) {
      case 'currency':
        return `$${value.toLocaleString()}`;
      case 'percentage':
        return `${(value * 100).toFixed(1)}%`;
      case 'rating':
        return `${value.toFixed(1)}/10`;
      default:
        return value.toLocaleString();
    }
  };

  const maxValue = Math.max(...Object.values(data));
  
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center mb-3">
        <Icon className="h-4 w-4 text-gray-600 mr-2" />
        <h5 className="text-sm font-medium text-gray-900">{title}</h5>
      </div>
      
      <div className="space-y-3">
        {Object.entries(data).map(([tenantId, value]) => (
          <div key={tenantId}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-600">
                Tenant {tenantId.slice(-4).toUpperCase()}
              </span>
              <span className="font-medium text-gray-900">
                {formatValue(value)}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{
                  width: `${maxValue > 0 ? (value / maxValue) * 100 : 0}%`
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
"""
}


# API Response Templates
class UnifiedDashboardAPIResponse(BaseModel):
    """API response structure for unified dashboard data"""
    partner_id: str
    dashboard_data: Dict[str, Any]
    layout: Optional[DashboardLayout] = None
    real_time_updates: bool = True
    cache_timestamp: datetime
    next_refresh: datetime


class DashboardExportRequest(BaseModel):
    """Request model for dashboard data export"""
    format: str = Field(..., regex="^(csv|xlsx|pdf)$")
    period: str = Field(..., regex="^(7d|30d|90d|1y)$")
    tenant_filter: List[str] = []
    dashboard_data: Dict[str, Any]
    include_charts: bool = True
    include_raw_data: bool = False


def generate_dashboard_component_files():
    """Generate React/TypeScript component files for the unified dashboard"""
    
    component_files = {}
    
    for component_name, component_code in DASHBOARD_COMPONENT_TEMPLATES.items():
        component_files[f"{component_name}.tsx"] = component_code
    
    # Add supporting files
    component_files["dashboard-types.ts"] = """
// dashboard-types.ts
export interface TenantMetrics {
  tenant_id: string;
  tenant_name: string;
  total_revenue: number;
  total_customers: number;
  customer_satisfaction: number | null;
  revenue_growth_rate: number;
  service_uptime_percentage: number | null;
}

export interface CrossTenantDashboardData {
  partner_id: string;
  partner_name: string;
  report_period: {
    start: string;
    end: string;
  };
  total_tenants: number;
  total_customers: number;
  total_revenue: number;
  total_attributed_revenue: number;
  average_customer_satisfaction: number | null;
  tenant_rankings: Array<{
    tenant_id: string;
    tenant_name: string;
    rank: number;
    score: number;
    strengths: string[];
    improvement_areas: string[];
  }>;
  performance_insights: string[];
  growth_opportunities: string[];
  risk_alerts: string[];
}

export interface DashboardConfig {
  refresh_interval: number;
  auto_refresh: boolean;
  default_period: string;
  visible_metrics: string[];
  chart_types: Record<string, string>;
}
"""
    
    component_files["dashboard-hooks.ts"] = """
// dashboard-hooks.ts
import { useState, useEffect, useCallback } from 'react';
import type { CrossTenantDashboardData } from './dashboard-types';

export function useDashboardData(partnerId: string, period: string = '30d') {
  const [data, setData] = useState<CrossTenantDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetch, setLastFetch] = useState(new Date());

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const endDate = new Date();
      const startDate = new Date();
      
      switch (period) {
        case '7d':
          startDate.setDate(endDate.getDate() - 7);
          break;
        case '30d':
          startDate.setDate(endDate.getDate() - 30);
          break;
        case '90d':
          startDate.setDate(endDate.getDate() - 90);
          break;
        case '1y':
          startDate.setFullYear(endDate.getFullYear() - 1);
          break;
      }

      const params = new URLSearchParams({
        period_start: startDate.toISOString(),
        period_end: endDate.toISOString(),
      });

      const response = await fetch(`/api/partners/${partnerId}/cross-tenant-dashboard?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const dashboardData = await response.json();
      setData(dashboardData);
      setLastFetch(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data');
    } finally {
      setIsLoading(false);
    }
  }, [partnerId, period]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    data,
    isLoading,
    error,
    lastFetch,
    refetch: fetchData,
  };
}

export function useRealTimeUpdates(partnerId: string, onUpdate: (data: any) => void) {
  useEffect(() => {
    // WebSocket connection for real-time updates
    const ws = new WebSocket(`ws://localhost:8000/ws/partners/${partnerId}/dashboard`);
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      onUpdate(update);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    return () => {
      ws.close();
    };
  }, [partnerId, onUpdate]);
}
"""
    
    return component_files


__all__ = [
    "DashboardWidget",
    "DashboardLayout", 
    "UnifiedDashboardAPIResponse",
    "DashboardExportRequest",
    "DASHBOARD_COMPONENT_TEMPLATES",
    "generate_dashboard_component_files"
]