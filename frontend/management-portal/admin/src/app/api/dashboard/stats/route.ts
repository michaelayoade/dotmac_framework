import { NextRequest, NextResponse } from 'next/server';
import type { DashboardStats, DashboardStatsResponse } from '@/types/dashboard';

// Mock data generator for development
function generateMockDashboardStats(): DashboardStats {
  const now = new Date();
  const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());

  // Generate realistic tenant data
  const totalTenants = Math.floor(Math.random() * 50) + 100; // 100-150 tenants
  const activeTenants = Math.floor(totalTenants * 0.85); // ~85% active
  const inactiveTenants = Math.floor(totalTenants * 0.08); // ~8% inactive
  const suspendedTenants = Math.floor(totalTenants * 0.05); // ~5% suspended
  const pendingTenants = totalTenants - activeTenants - inactiveTenants - suspendedTenants;

  // Generate trend data
  const tenantGrowth = Math.floor(Math.random() * 15) + 2; // 2-17% growth
  const previousTotalTenants = Math.floor(totalTenants / (1 + tenantGrowth / 100));
  const previousActiveTenants = Math.floor(previousTotalTenants * 0.82);

  // Generate subscription data
  const activeSubscriptions = Math.floor(activeTenants * 1.2); // Some tenants have multiple subs
  const monthlyRevenue = activeSubscriptions * (Math.random() * 50 + 25); // $25-75 per sub
  const annualRevenue = monthlyRevenue * 12;

  // Generate deployment data
  const totalDeployments = activeTenants + Math.floor(Math.random() * 20);
  const healthyDeployments = Math.floor(totalDeployments * 0.92); // 92% healthy
  const unhealthyDeployments = Math.floor(totalDeployments * 0.05); // 5% unhealthy
  const deployingDeployments = totalDeployments - healthyDeployments - unhealthyDeployments;

  // Generate recent activity
  const activities = [
    {
      id: '1',
      type: 'tenant_created' as const,
      message: 'New tenant "Acme Corp" created successfully',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      metadata: { tenant_name: 'Acme Corp', tenant_id: 'acme-corp' },
      severity: 'success' as const,
    },
    {
      id: '2',
      type: 'subscription_created' as const,
      message: 'Enterprise plan subscription activated for TechStart Inc',
      timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(), // 4 hours ago
      metadata: { plan: 'Enterprise', tenant: 'TechStart Inc' },
      severity: 'info' as const,
    },
    {
      id: '3',
      type: 'deployment_completed' as const,
      message: 'Infrastructure deployment completed for Global Solutions',
      timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(), // 6 hours ago
      metadata: { deployment_id: 'dep-123', tenant: 'Global Solutions' },
      severity: 'success' as const,
    },
    {
      id: '4',
      type: 'system_alert' as const,
      message: 'High CPU usage detected on server cluster-01',
      timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(), // 8 hours ago
      metadata: { server: 'cluster-01', cpu_usage: 85 },
      severity: 'warning' as const,
    },
    {
      id: '5',
      type: 'tenant_updated' as const,
      message: 'Configuration updated for Smart Industries tenant',
      timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(), // 12 hours ago
      metadata: { tenant: 'Smart Industries', config_type: 'billing' },
      severity: 'info' as const,
    },
  ];

  return {
    tenants: {
      total: totalTenants,
      active: activeTenants,
      inactive: inactiveTenants,
      suspended: suspendedTenants,
      pending: pendingTenants,
      trends: {
        total: {
          current: totalTenants,
          previous: previousTotalTenants,
          change: totalTenants - previousTotalTenants,
          changePercent: tenantGrowth,
          changeType: 'positive',
        },
        active: {
          current: activeTenants,
          previous: previousActiveTenants,
          change: activeTenants - previousActiveTenants,
          changePercent: Math.round(
            ((activeTenants - previousActiveTenants) / previousActiveTenants) * 100
          ),
          changeType: 'positive',
        },
      },
    },

    subscriptions: {
      active: activeSubscriptions,
      total: activeSubscriptions + Math.floor(Math.random() * 10), // Some inactive subs
      revenue: {
        monthly: Math.round(monthlyRevenue),
        annual: Math.round(annualRevenue),
      },
      trends: {
        subscriptions: {
          current: activeSubscriptions,
          previous: Math.floor(activeSubscriptions * 0.95),
          change: Math.floor(activeSubscriptions * 0.05),
          changePercent: 5,
          changeType: 'positive',
        },
        revenue: {
          current: monthlyRevenue,
          previous: monthlyRevenue * 0.92,
          change: monthlyRevenue * 0.08,
          changePercent: 8,
          changeType: 'positive',
        },
      },
    },

    deployments: {
      total: totalDeployments,
      healthy: healthyDeployments,
      unhealthy: unhealthyDeployments,
      deploying: deployingDeployments,
      trends: {
        deployments: {
          current: totalDeployments,
          previous: Math.floor(totalDeployments * 0.93),
          change: Math.floor(totalDeployments * 0.07),
          changePercent: 7,
          changeType: 'positive',
        },
        success_rate: {
          current: 92,
          previous: 89,
          change: 3,
          changePercent: 3.4,
          changeType: 'positive',
        },
      },
    },

    system: {
      health: Math.random() > 0.1 ? 'healthy' : Math.random() > 0.5 ? 'warning' : 'critical',
      uptime: Math.floor(Math.random() * 30 + 20) * 24 * 60 * 60, // 20-50 days in seconds
      version: '1.2.3',
      last_updated: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString(),
    },

    activity: activities,
  };
}

export async function GET(_request: NextRequest) {
  try {
    // In a real application, this would fetch data from your database
    // For now, return realistic mock data
    const dashboardStats = generateMockDashboardStats();

    const response: DashboardStatsResponse = {
      success: true,
      data: dashboardStats,
      timestamp: new Date().toISOString(),
    };

    return NextResponse.json(response, {
      status: 200,
      headers: {
        'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=300', // Cache for 1 minute
      },
    });
  } catch (error) {
    console.error('Dashboard stats API error:', error);

    return NextResponse.json(
      {
        success: false,
        error: 'Failed to fetch dashboard statistics',
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}
