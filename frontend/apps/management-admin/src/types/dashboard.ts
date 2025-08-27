/**
 * Dashboard and System Overview Types
 */

export interface DashboardStats {
  tenants: {
    total: number;
    active: number;
    inactive: number;
    suspended: number;
    pending: number;
    trends: {
      total: TrendData;
      active: TrendData;
    };
  };
  
  subscriptions: {
    active: number;
    total: number;
    revenue: {
      monthly: number;
      annual: number;
    };
    trends: {
      subscriptions: TrendData;
      revenue: TrendData;
    };
  };

  deployments: {
    total: number;
    healthy: number;
    unhealthy: number;
    deploying: number;
    trends: {
      deployments: TrendData;
      success_rate: TrendData;
    };
  };

  system: {
    health: 'healthy' | 'warning' | 'critical';
    uptime: number;
    version: string;
    last_updated: string;
  };

  activity: ActivityItem[];
}

export interface TrendData {
  current: number;
  previous: number;
  change: number;
  changePercent: number;
  changeType: 'positive' | 'negative' | 'neutral';
}

export interface ActivityItem {
  id: string;
  type: 'tenant_created' | 'tenant_updated' | 'subscription_created' | 'deployment_completed' | 'system_alert';
  message: string;
  timestamp: string;
  metadata?: Record<string, any>;
  severity?: 'info' | 'warning' | 'error' | 'success';
}

export interface SystemOverview {
  dashboard: DashboardStats;
  alerts: SystemAlert[];
  performance: PerformanceMetrics;
}

export interface SystemAlert {
  id: string;
  type: 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: string;
  resolved: boolean;
  metadata?: Record<string, any>;
}

export interface PerformanceMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  network_io: {
    inbound: number;
    outbound: number;
  };
  database: {
    connections: number;
    query_time_avg: number;
  };
  cache: {
    hit_rate: number;
    memory_usage: number;
  };
}

/**
 * API Response types for dashboard endpoints
 */
export interface DashboardStatsResponse {
  success: boolean;
  data: DashboardStats;
  timestamp: string;
}

export interface SystemOverviewResponse {
  success: boolean;
  data: SystemOverview;
  timestamp: string;
}