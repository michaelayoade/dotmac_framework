'use client';

import { useState, useCallback } from 'react';
import { AlertTriangle } from 'lucide-react';
import { useManagementAuth } from '@/components/auth/ManagementAuthProvider';
import { useDashboardMetrics } from '@/hooks/useAnalytics';
import { usePartnerStats } from '@/hooks/usePartners';
import { useCommissionStats } from '@/hooks/useCommissions';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { MetricsGrid, formatMetricsData } from '@/components/dashboard/MetricsGrid';
import { StatsSection } from '@/components/dashboard/StatsSection';

export default function DashboardPage() {
  const { user, canViewAnalytics } = useManagementAuth();
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  const dashboardMetrics = useDashboardMetrics();
  const { data: partnerStats, isLoading: partnerStatsLoading, refetch: refetchPartners } = usePartnerStats();
  const { data: commissionStats, isLoading: commissionStatsLoading, refetch: refetchCommissions } = useCommissionStats();

  const isLoading = dashboardMetrics.isLoading || partnerStatsLoading || commissionStatsLoading;

  // Handle export functionality (placeholder for now)
  const handleExport = useCallback(async (format: 'CSV' | 'XLSX' | 'PDF') => {
    console.log('Export requested:', format);
    alert(`${format} export functionality will be available soon`);
  }, []);

  // Handle dashboard refresh
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([
        dashboardMetrics.refetch?.(),
        refetchPartners?.(),
        refetchCommissions?.()
      ]);
    } catch (error) {
      console.error('Refresh failed:', error);
    } finally {
      setIsRefreshing(false);
    }
  }, [dashboardMetrics.refetch, refetchPartners, refetchCommissions]);

  if (!canViewAnalytics) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Access Restricted</h3>
          <p className="text-gray-600">You don't have permission to view analytics</p>
        </div>
      </div>
    );
  }

  const metrics = dashboardMetrics?.channelMetrics || {
    total_partners: 0,
    active_partners: 0,
    pending_approvals: 0,
    total_revenue: 0,
    commission_payout: 0,
    avg_deal_size: 0,
    conversion_rate: 0,
    partner_satisfaction: 0,
    territory_coverage: 0,
    top_performers: [],
    revenue_by_tier: {},
    commission_by_month: [],
    partner_growth: [],
  };

  const keyMetrics = formatMetricsData(metrics);

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <DashboardHeader
        user={user!}
        onExport={handleExport}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {/* Key Metrics Grid */}
      <MetricsGrid 
        metrics={keyMetrics} 
        isLoading={isLoading}
      />

      {/* Additional Stats */}
      <StatsSection
        partnerStats={partnerStats}
        commissionStats={commissionStats}
        isLoading={isLoading}
      />
    </div>
  );
}