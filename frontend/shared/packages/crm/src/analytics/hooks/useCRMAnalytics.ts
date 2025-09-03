import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@dotmac/headless';
import { crmDb } from '../database';
import type {
  CRMDashboardMetrics,
  CustomerMetrics,
  LeadMetrics,
  CommunicationMetrics,
  SupportMetrics,
} from '../../types';

interface UseCRMAnalyticsOptions {
  timeRange?: {
    start: string;
    end: string;
  };
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseCRMAnalyticsReturn {
  metrics: CRMDashboardMetrics | null;
  loading: boolean;
  error: string | null;

  // Metrics by category
  customerMetrics: CustomerMetrics | null;
  leadMetrics: LeadMetrics | null;
  communicationMetrics: CommunicationMetrics | null;
  supportMetrics: SupportMetrics | null;

  // Time-based analytics
  customerTrends: { date: string; new: number; churned: number; active: number }[];
  leadTrends: { date: string; created: number; converted: number; score: number }[];
  communicationTrends: { date: string; count: number; type: string }[];
  supportTrends: { date: string; created: number; resolved: number }[];

  // Conversion analytics
  conversionFunnel: { stage: string; count: number; rate: number }[];
  leadSources: { source: string; count: number; conversion: number }[];
  customerSegments: { segment: string; count: number; revenue: number }[];

  // Performance analytics
  teamPerformance: {
    userId: string;
    userName: string;
    leadsConverted: number;
    customersManaged: number;
    avgResponseTime: number;
    ticketsResolved: number;
  }[];

  // Revenue analytics
  revenueMetrics: {
    totalRevenue: number;
    monthlyRecurring: number;
    averageLifetimeValue: number;
    churnRate: number;
    revenueBySegment: Record<string, number>;
    revenueGrowth: { month: string; revenue: number; growth: number }[];
  };

  // Forecasting
  leadScoreDistribution: { range: string; count: number; conversionRate: number }[];
  churnPrediction: { customerId: string; riskScore: number; factors: string[] }[];
  revenueForecasting: { month: string; predicted: number; confidence: number }[];

  // Actions
  refreshMetrics: () => Promise<void>;
  updateTimeRange: (start: string, end: string) => void;
  exportReport: (format: 'csv' | 'json' | 'pdf') => Promise<string>;

  // Real-time updates
  lastUpdated: Date | null;
  isStale: boolean;
}

export function useCRMAnalytics(options: UseCRMAnalyticsOptions = {}): UseCRMAnalyticsReturn {
  const {
    timeRange: initialTimeRange,
    autoRefresh = true,
    refreshInterval = 300000, // 5 minutes
  } = options;

  const { tenantId } = useAuth();

  const [metrics, setMetrics] = useState<CRMDashboardMetrics | null>(null);
  const [customerMetrics, setCustomerMetrics] = useState<CustomerMetrics | null>(null);
  const [leadMetrics, setLeadMetrics] = useState<LeadMetrics | null>(null);
  const [communicationMetrics, setCommunicationMetrics] = useState<CommunicationMetrics | null>(
    null
  );
  const [supportMetrics, setSupportMetrics] = useState<SupportMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Trends data
  const [customerTrends, setCustomerTrends] = useState<
    { date: string; new: number; churned: number; active: number }[]
  >([]);
  const [leadTrends, setLeadTrends] = useState<
    { date: string; created: number; converted: number; score: number }[]
  >([]);
  const [communicationTrends, setCommunicationTrends] = useState<
    { date: string; count: number; type: string }[]
  >([]);
  const [supportTrends, setSupportTrends] = useState<
    { date: string; created: number; resolved: number }[]
  >([]);

  // Analytics data
  const [conversionFunnel, setConversionFunnel] = useState<
    { stage: string; count: number; rate: number }[]
  >([]);
  const [leadSources, setLeadSources] = useState<
    { source: string; count: number; conversion: number }[]
  >([]);
  const [customerSegments, setCustomerSegments] = useState<
    { segment: string; count: number; revenue: number }[]
  >([]);
  const [teamPerformance, setTeamPerformance] = useState<any[]>([]);
  const [revenueMetrics, setRevenueMetrics] = useState<any>({
    totalRevenue: 0,
    monthlyRecurring: 0,
    averageLifetimeValue: 0,
    churnRate: 0,
    revenueBySegment: {},
    revenueGrowth: [],
  });

  // Forecasting data
  const [leadScoreDistribution, setLeadScoreDistribution] = useState<
    { range: string; count: number; conversionRate: number }[]
  >([]);
  const [churnPrediction, setChurnPrediction] = useState<
    { customerId: string; riskScore: number; factors: string[] }[]
  >([]);
  const [revenueForecasting, setRevenueForecasting] = useState<
    { month: string; predicted: number; confidence: number }[]
  >([]);

  // Time range state
  const [timeRange, setTimeRange] = useState(
    initialTimeRange || {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days ago
      end: new Date().toISOString(),
    }
  );

  // Calculate customer metrics
  const calculateCustomerMetrics = useCallback(async (): Promise<CustomerMetrics> => {
    if (!tenantId)
      return {
        totalCustomers: 0,
        activeCustomers: 0,
        newCustomers: 0,
        churnedCustomers: 0,
        churnRate: 0,
        lifetimeValue: 0,
        averageRevenue: 0,
        customersBySegment: {},
        customersByStatus: {},
      };

    const dbMetrics = await crmDb.getCustomerMetrics(tenantId);

    return {
      totalCustomers: dbMetrics.total,
      activeCustomers: dbMetrics.active,
      newCustomers: dbMetrics.new,
      churnedCustomers: dbMetrics.churned,
      churnRate: dbMetrics.total > 0 ? (dbMetrics.churned / dbMetrics.total) * 100 : 0,
      lifetimeValue: dbMetrics.averageRevenue * 24, // 2 years average
      averageRevenue: dbMetrics.averageRevenue,
      customersBySegment: dbMetrics.bySegment as any,
      customersByStatus: dbMetrics.byStatus as any,
    };
  }, [tenantId]);

  // Calculate lead metrics
  const calculateLeadMetrics = useCallback(async (): Promise<LeadMetrics> => {
    if (!tenantId)
      return {
        totalLeads: 0,
        newLeads: 0,
        qualifiedLeads: 0,
        convertedLeads: 0,
        conversionRate: 0,
        averageScore: 0,
        leadsBySource: {},
        leadsByStatus: {},
      };

    const dbMetrics = await crmDb.getLeadMetrics(tenantId);

    return {
      totalLeads: dbMetrics.total,
      newLeads: dbMetrics.new,
      qualifiedLeads: dbMetrics.qualified,
      convertedLeads: dbMetrics.converted,
      conversionRate: dbMetrics.conversionRate,
      averageScore: dbMetrics.averageScore,
      leadsBySource: dbMetrics.bySource as any,
      leadsByStatus: dbMetrics.byStatus as any,
    };
  }, [tenantId]);

  // Calculate communication metrics
  const calculateCommunicationMetrics = useCallback(async (): Promise<CommunicationMetrics> => {
    if (!tenantId)
      return {
        totalCommunications: 0,
        responseRate: 0,
        averageResponseTime: 0,
        communicationsByType: {} as any,
        sentimentAnalysis: { positive: 0, neutral: 0, negative: 0 },
      };

    const allCommunications = await crmDb.communications
      .where('tenantId')
      .equals(tenantId)
      .toArray();

    const totalCommunications = allCommunications.length;
    const emailCommunications = allCommunications.filter((c) => c.type === 'email');
    const sentEmails = emailCommunications.filter((c) => c.direction === 'outbound');
    const repliedEmails = emailCommunications.filter((c) => c.repliedAt);

    const responseRate =
      sentEmails.length > 0 ? (repliedEmails.length / sentEmails.length) * 100 : 0;

    // Calculate average response time (in hours)
    const responseTimes = repliedEmails
      .map((c) =>
        c.repliedAt && c.timestamp
          ? (new Date(c.repliedAt).getTime() - new Date(c.timestamp).getTime()) / (1000 * 60 * 60)
          : 0
      )
      .filter((time) => time > 0);

    const averageResponseTime =
      responseTimes.length > 0
        ? responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length
        : 0;

    // Communication by type
    const communicationsByType: any = {};
    allCommunications.forEach((comm) => {
      communicationsByType[comm.type] = (communicationsByType[comm.type] || 0) + 1;
    });

    // Sentiment analysis
    const sentimentCounts = { positive: 0, neutral: 0, negative: 0 };
    allCommunications.forEach((comm) => {
      if (comm.sentiment) {
        sentimentCounts[comm.sentiment]++;
      }
    });

    return {
      totalCommunications,
      responseRate,
      averageResponseTime,
      communicationsByType,
      sentimentAnalysis: sentimentCounts,
    };
  }, [tenantId]);

  // Calculate support metrics
  const calculateSupportMetrics = useCallback(async (): Promise<SupportMetrics> => {
    if (!tenantId)
      return {
        totalTickets: 0,
        openTickets: 0,
        resolvedTickets: 0,
        averageResolutionTime: 0,
        firstResponseTime: 0,
        satisfactionRating: 0,
        ticketsByCategory: {} as any,
        ticketsByPriority: {} as any,
        slaCompliance: 0,
      };

    const allTickets = await crmDb.supportTickets.where('tenantId').equals(tenantId).toArray();

    const totalTickets = allTickets.length;
    const openTickets = allTickets.filter((t) => ['open', 'in_progress'].includes(t.status)).length;
    const resolvedTickets = allTickets.filter((t) => t.status === 'resolved').length;

    // Calculate average resolution time
    const resolvedWithTimes = allTickets.filter((t) => t.resolutionTime);
    const averageResolutionTime =
      resolvedWithTimes.length > 0
        ? resolvedWithTimes.reduce((sum, t) => sum + (t.resolutionTime || 0), 0) /
          resolvedWithTimes.length /
          60
        : 0;

    // Other metrics (simplified)
    const firstResponseTime = 4; // Hours
    const satisfactionRating = 4.2;

    // Tickets by category and priority
    const ticketsByCategory: any = {};
    const ticketsByPriority: any = {};

    allTickets.forEach((ticket) => {
      ticketsByCategory[ticket.category] = (ticketsByCategory[ticket.category] || 0) + 1;
      ticketsByPriority[ticket.priority] = (ticketsByPriority[ticket.priority] || 0) + 1;
    });

    // SLA compliance
    const ticketsWithSLA = allTickets.filter((t) => t.slaTarget);
    const slaCompliantTickets = ticketsWithSLA.filter((t) => !t.slaBreached);
    const slaCompliance =
      ticketsWithSLA.length > 0 ? (slaCompliantTickets.length / ticketsWithSLA.length) * 100 : 100;

    return {
      totalTickets,
      openTickets,
      resolvedTickets,
      averageResolutionTime,
      firstResponseTime,
      satisfactionRating,
      ticketsByCategory,
      ticketsByPriority,
      slaCompliance,
    };
  }, [tenantId]);

  // Calculate trends
  const calculateTrends = useCallback(async () => {
    if (!tenantId) return;

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    // Generate daily data points for the last 30 days
    const dates = Array.from({ length: 30 }, (_, i) => {
      const date = new Date(thirtyDaysAgo);
      date.setDate(date.getDate() + i);
      return date.toISOString().split('T')[0];
    });

    // Customer trends
    const customers = await crmDb.customers.where('tenantId').equals(tenantId).toArray();
    const customerTrendsData = dates.map((date) => {
      const newCustomers = customers.filter((c) => c.createdAt.startsWith(date)).length;

      const churnedCustomers = customers.filter(
        (c) => c.status === 'churned' && c.updatedAt.startsWith(date)
      ).length;

      const activeCustomers = customers.filter(
        (c) => c.status === 'active' && c.createdAt <= date + 'T23:59:59'
      ).length;

      return { date, new: newCustomers, churned: churnedCustomers, active: activeCustomers };
    });

    setCustomerTrends(customerTrendsData);

    // Lead trends
    const leads = await crmDb.leads.where('tenantId').equals(tenantId).toArray();
    const leadTrendsData = dates.map((date) => {
      const createdLeads = leads.filter((l) => l.createdAt.startsWith(date)).length;

      const convertedLeads = leads.filter(
        (l) => l.convertedDate && l.convertedDate.startsWith(date)
      ).length;

      const dailyLeads = leads.filter((l) => l.createdAt.startsWith(date));

      const avgScore =
        dailyLeads.length > 0
          ? dailyLeads.reduce((sum, l) => sum + l.score, 0) / dailyLeads.length
          : 0;

      return { date, created: createdLeads, converted: convertedLeads, score: avgScore };
    });

    setLeadTrends(leadTrendsData);

    // Communication trends (simplified)
    const communications = await crmDb.communications.where('tenantId').equals(tenantId).toArray();
    const commTrendsData = dates.flatMap((date) => {
      const dailyComms = communications.filter((c) => c.timestamp.startsWith(date));

      const commsByType: Record<string, number> = {};
      dailyComms.forEach((c) => {
        commsByType[c.type] = (commsByType[c.type] || 0) + 1;
      });

      return Object.entries(commsByType).map(([type, count]) => ({
        date,
        count,
        type,
      }));
    });

    setCommunicationTrends(commTrendsData);

    // Support trends
    const tickets = await crmDb.supportTickets.where('tenantId').equals(tenantId).toArray();
    const supportTrendsData = dates.map((date) => {
      const createdTickets = tickets.filter((t) => t.createdAt.startsWith(date)).length;

      const resolvedTickets = tickets.filter(
        (t) => t.resolvedAt && t.resolvedAt.startsWith(date)
      ).length;

      return { date, created: createdTickets, resolved: resolvedTickets };
    });

    setSupportTrends(supportTrendsData);
  }, [tenantId]);

  // Calculate conversion funnel
  const calculateConversionFunnel = useCallback(async () => {
    if (!tenantId) return;

    const leads = await crmDb.leads.where('tenantId').equals(tenantId).toArray();
    const customers = await crmDb.customers.where('tenantId').equals(tenantId).toArray();

    const funnelData = [
      { stage: 'Total Leads', count: leads.length, rate: 100 },
      { stage: 'Contacted', count: leads.filter((l) => l.status !== 'new').length, rate: 0 },
      { stage: 'Qualified', count: leads.filter((l) => l.status === 'qualified').length, rate: 0 },
      { stage: 'Proposal', count: leads.filter((l) => l.status === 'proposal').length, rate: 0 },
      { stage: 'Customers', count: customers.length, rate: 0 },
    ];

    // Calculate conversion rates
    for (let i = 1; i < funnelData.length; i++) {
      const previousCount = funnelData[i - 1].count;
      funnelData[i].rate = previousCount > 0 ? (funnelData[i].count / previousCount) * 100 : 0;
    }

    setConversionFunnel(funnelData);
  }, [tenantId]);

  // Calculate lead sources
  const calculateLeadSources = useCallback(async () => {
    if (!tenantId) return;

    const leads = await crmDb.leads.where('tenantId').equals(tenantId).toArray();

    const sourceData: Record<string, { count: number; converted: number }> = {};

    leads.forEach((lead) => {
      if (!sourceData[lead.source]) {
        sourceData[lead.source] = { count: 0, converted: 0 };
      }
      sourceData[lead.source].count++;
      if (lead.status === 'closed_won') {
        sourceData[lead.source].converted++;
      }
    });

    const sourcesArray = Object.entries(sourceData).map(([source, data]) => ({
      source,
      count: data.count,
      conversion: data.count > 0 ? (data.converted / data.count) * 100 : 0,
    }));

    setLeadSources(sourcesArray);
  }, [tenantId]);

  // Calculate customer segments
  const calculateCustomerSegments = useCallback(async () => {
    if (!tenantId) return;

    const customers = await crmDb.customers.where('tenantId').equals(tenantId).toArray();

    const segmentData: Record<string, { count: number; revenue: number }> = {};

    customers.forEach((customer) => {
      if (!segmentData[customer.segment]) {
        segmentData[customer.segment] = { count: 0, revenue: 0 };
      }
      segmentData[customer.segment].count++;
      segmentData[customer.segment].revenue += customer.monthlyRevenue;
    });

    const segmentsArray = Object.entries(segmentData).map(([segment, data]) => ({
      segment,
      count: data.count,
      revenue: data.revenue,
    }));

    setCustomerSegments(segmentsArray);
  }, [tenantId]);

  // Calculate revenue metrics
  const calculateRevenueMetrics = useCallback(async () => {
    if (!tenantId) return;

    const customers = await crmDb.customers.where('tenantId').equals(tenantId).toArray();

    const totalRevenue = customers.reduce((sum, c) => sum + c.totalRevenue, 0);
    const monthlyRecurring = customers.reduce((sum, c) => sum + c.monthlyRevenue, 0);
    const averageLifetimeValue =
      customers.length > 0
        ? customers.reduce((sum, c) => sum + c.lifetimeValue, 0) / customers.length
        : 0;

    const activeCustomers = customers.filter((c) => c.status === 'active').length;
    const churnedCustomers = customers.filter((c) => c.status === 'churned').length;
    const churnRate = customers.length > 0 ? (churnedCustomers / customers.length) * 100 : 0;

    const revenueBySegment: Record<string, number> = {};
    customers.forEach((customer) => {
      revenueBySegment[customer.segment] =
        (revenueBySegment[customer.segment] || 0) + customer.monthlyRevenue;
    });

    // Generate mock revenue growth data
    const revenueGrowth = Array.from({ length: 12 }, (_, i) => {
      const month = new Date();
      month.setMonth(month.getMonth() - (11 - i));
      const monthStr = month.toISOString().substring(0, 7);

      const revenue = monthlyRecurring * (0.8 + Math.random() * 0.4);
      const growth =
        i > 0 ? ((revenue - monthlyRecurring * 0.9) / (monthlyRecurring * 0.9)) * 100 : 0;

      return { month: monthStr, revenue, growth };
    });

    setRevenueMetrics({
      totalRevenue,
      monthlyRecurring,
      averageLifetimeValue,
      churnRate,
      revenueBySegment,
      revenueGrowth,
    });
  }, [tenantId]);

  // Calculate lead score distribution
  const calculateLeadScoreDistribution = useCallback(async () => {
    if (!tenantId) return;

    const leads = await crmDb.leads.where('tenantId').equals(tenantId).toArray();

    const ranges = [
      { range: '0-20', min: 0, max: 20 },
      { range: '21-40', min: 21, max: 40 },
      { range: '41-60', min: 41, max: 60 },
      { range: '61-80', min: 61, max: 80 },
      { range: '81-100', min: 81, max: 100 },
    ];

    const distribution = ranges.map(({ range, min, max }) => {
      const leadsInRange = leads.filter((l) => l.score >= min && l.score <= max);
      const convertedInRange = leadsInRange.filter((l) => l.status === 'closed_won');
      const conversionRate =
        leadsInRange.length > 0 ? (convertedInRange.length / leadsInRange.length) * 100 : 0;

      return {
        range,
        count: leadsInRange.length,
        conversionRate,
      };
    });

    setLeadScoreDistribution(distribution);
  }, [tenantId]);

  // Main refresh function
  const refreshMetrics = useCallback(async () => {
    if (!tenantId) return;

    try {
      setLoading(true);
      setError(null);

      // Calculate all metrics in parallel
      const [customerMetricsData, leadMetricsData, communicationMetricsData, supportMetricsData] =
        await Promise.all([
          calculateCustomerMetrics(),
          calculateLeadMetrics(),
          calculateCommunicationMetrics(),
          calculateSupportMetrics(),
        ]);

      setCustomerMetrics(customerMetricsData);
      setLeadMetrics(leadMetricsData);
      setCommunicationMetrics(communicationMetricsData);
      setSupportMetrics(supportMetricsData);

      // Combine into dashboard metrics
      const dashboardMetrics: CRMDashboardMetrics = {
        customer: customerMetricsData,
        lead: leadMetricsData,
        communication: communicationMetricsData,
        support: supportMetricsData,
        timeRange,
        lastUpdated: new Date().toISOString(),
      };

      setMetrics(dashboardMetrics);

      // Calculate trends and analytics
      await Promise.all([
        calculateTrends(),
        calculateConversionFunnel(),
        calculateLeadSources(),
        calculateCustomerSegments(),
        calculateRevenueMetrics(),
        calculateLeadScoreDistribution(),
      ]);

      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh CRM analytics');
      console.error('Failed to refresh CRM analytics:', err);
    } finally {
      setLoading(false);
    }
  }, [
    tenantId,
    timeRange,
    calculateCustomerMetrics,
    calculateLeadMetrics,
    calculateCommunicationMetrics,
    calculateSupportMetrics,
    calculateTrends,
    calculateConversionFunnel,
    calculateLeadSources,
    calculateCustomerSegments,
    calculateRevenueMetrics,
    calculateLeadScoreDistribution,
  ]);

  // Update time range
  const updateTimeRange = useCallback((start: string, end: string) => {
    setTimeRange({ start, end });
  }, []);

  // Export report
  const exportReport = useCallback(
    async (format: 'csv' | 'json' | 'pdf'): Promise<string> => {
      if (!metrics) throw new Error('No metrics available to export');

      if (format === 'json') {
        return JSON.stringify(
          {
            metrics,
            customerTrends,
            leadTrends,
            communicationTrends,
            supportTrends,
            conversionFunnel,
            leadSources,
            customerSegments,
            revenueMetrics,
            leadScoreDistribution,
            exportedAt: new Date().toISOString(),
          },
          null,
          2
        );
      } else if (format === 'csv') {
        // Create CSV summary
        const csvData = [
          ['Metric', 'Value'],
          ['Total Customers', metrics.customer.totalCustomers.toString()],
          ['Active Customers', metrics.customer.activeCustomers.toString()],
          ['Total Leads', metrics.lead.totalLeads.toString()],
          ['Lead Conversion Rate', `${metrics.lead.conversionRate.toFixed(2)}%`],
          ['Total Communications', metrics.communication.totalCommunications.toString()],
          ['Email Response Rate', `${metrics.communication.responseRate.toFixed(2)}%`],
          ['Total Support Tickets', metrics.support.totalTickets.toString()],
          ['SLA Compliance', `${metrics.support.slaCompliance.toFixed(2)}%`],
        ];

        return csvData
          .map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(','))
          .join('\n');
      } else {
        // PDF format would require a PDF generation library
        throw new Error('PDF export not implemented yet');
      }
    },
    [
      metrics,
      customerTrends,
      leadTrends,
      communicationTrends,
      supportTrends,
      conversionFunnel,
      leadSources,
      customerSegments,
      revenueMetrics,
      leadScoreDistribution,
    ]
  );

  // Check if data is stale
  const isStale = lastUpdated
    ? new Date().getTime() - lastUpdated.getTime() > refreshInterval * 2
    : true;

  // Initialize
  useEffect(() => {
    refreshMetrics();
  }, [refreshMetrics]);

  // Auto-refresh interval
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(refreshMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, refreshMetrics]);

  // Refresh when time range changes
  useEffect(() => {
    refreshMetrics();
  }, [timeRange, refreshMetrics]);

  return {
    metrics,
    loading,
    error,

    // Metrics by category
    customerMetrics,
    leadMetrics,
    communicationMetrics,
    supportMetrics,

    // Time-based analytics
    customerTrends,
    leadTrends,
    communicationTrends,
    supportTrends,

    // Conversion analytics
    conversionFunnel,
    leadSources,
    customerSegments,

    // Performance analytics
    teamPerformance,

    // Revenue analytics
    revenueMetrics,

    // Forecasting
    leadScoreDistribution,
    churnPrediction,
    revenueForecasting,

    // Actions
    refreshMetrics,
    updateTimeRange,
    exportReport,

    // Real-time updates
    lastUpdated,
    isStale,
  };
}
