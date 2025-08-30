import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@dotmac/auth';
import type {
  JourneyMetrics,
  ConversionFunnel,
  UseConversionAnalyticsReturn,
  CustomerJourney
} from '../types';
import { ConversionAnalytics } from '../analytics/ConversionAnalytics';
import { JourneyOrchestrator } from '../orchestrator/JourneyOrchestrator';

/**
 * Hook for conversion analytics and funnel analysis
 */
export function useConversionAnalytics(): UseConversionAnalyticsReturn {
  const { tenantId } = useAuth();
  const analyticsRef = useRef<ConversionAnalytics | null>(null);
  const orchestratorRef = useRef<JourneyOrchestrator | null>(null);

  // State
  const [metrics, setMetrics] = useState<JourneyMetrics | null>(null);
  const [funnels, setFunnels] = useState<ConversionFunnel[]>([]);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize analytics
  useEffect(() => {
    if (!tenantId) return;

    try {
      analyticsRef.current = new ConversionAnalytics(tenantId);
      orchestratorRef.current = new JourneyOrchestrator(tenantId);

      // Load initial analytics
      refreshMetrics();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initialize analytics');
      setLoading(false);
    }

    return () => {
      orchestratorRef.current?.destroy();
    };
  }, [tenantId]);

  // Refresh metrics
  const refreshMetrics = useCallback(async (): Promise<void> => {
    if (!analyticsRef.current || !orchestratorRef.current) {
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const journeys = orchestratorRef.current.getJourneys();

      // Generate metrics
      const journeyMetrics = await analyticsRef.current.generateJourneyMetrics(journeys);
      setMetrics(journeyMetrics);

      // Generate funnels for different types
      const acquisitionFunnel = await analyticsRef.current.generateConversionFunnel(journeys, 'acquisition');
      const onboardingFunnel = await analyticsRef.current.generateConversionFunnel(journeys, 'onboarding');
      const retentionFunnel = await analyticsRef.current.generateConversionFunnel(journeys, 'retention');

      setFunnels([acquisitionFunnel, onboardingFunnel, retentionFunnel]);

      // Generate trend data
      const trendsData = generateTrendsData(journeys);
      setTrends(trendsData);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh metrics');
    } finally {
      setLoading(false);
    }
  }, []);

  // Get funnel data for specific type
  const getFunnelData = useCallback(async (type: string): Promise<ConversionFunnel> => {
    if (!analyticsRef.current || !orchestratorRef.current) {
      throw new Error('Analytics not initialized');
    }

    try {
      const journeys = orchestratorRef.current.getJourneys();
      return await analyticsRef.current.generateConversionFunnel(
        journeys,
        type as 'acquisition' | 'onboarding' | 'support' | 'retention'
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get funnel data';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Get drop-off analysis
  const getDropoffAnalysis = useCallback(async (stage: any): Promise<any> => {
    if (!analyticsRef.current || !orchestratorRef.current) {
      throw new Error('Analytics not initialized');
    }

    try {
      const journeys = orchestratorRef.current.getJourneys();
      return await analyticsRef.current.analyzeDropOffs(journeys, stage);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get drop-off analysis';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Get attribution data
  const getAttributionData = useCallback(async (): Promise<any> => {
    if (!analyticsRef.current || !orchestratorRef.current) {
      throw new Error('Analytics not initialized');
    }

    try {
      const journeys = orchestratorRef.current.getJourneys();
      return await analyticsRef.current.analyzeAttribution(journeys);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get attribution data';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Export analytics
  const exportAnalytics = useCallback(async (format: 'csv' | 'json'): Promise<string> => {
    if (!analyticsRef.current || !orchestratorRef.current) {
      throw new Error('Analytics not initialized');
    }

    try {
      const journeys = orchestratorRef.current.getJourneys();
      return await analyticsRef.current.exportAnalytics(journeys, format);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to export analytics';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Generate report
  const generateReport = useCallback(async (type: string, params?: Record<string, any>): Promise<any> => {
    if (!analyticsRef.current || !orchestratorRef.current) {
      throw new Error('Analytics not initialized');
    }

    try {
      const journeys = orchestratorRef.current.getJourneys();

      switch (type) {
        case 'conversion_summary':
          return {
            metrics: await analyticsRef.current.generateJourneyMetrics(journeys),
            funnels: await Promise.all([
              analyticsRef.current.generateConversionFunnel(journeys, 'acquisition'),
              analyticsRef.current.generateConversionFunnel(journeys, 'onboarding')
            ]),
            attribution: await analyticsRef.current.analyzeAttribution(journeys)
          };

        case 'cohort_analysis':
          return await analyticsRef.current.generateCohortAnalysis(
            journeys,
            params?.periodType || 'month'
          );

        case 'drop_off_analysis':
          const stages = ['prospect', 'lead', 'qualified', 'customer', 'active_service'];
          const dropOffData = await Promise.all(
            stages.map(stage =>
              analyticsRef.current!.analyzeDropOffs(journeys, stage as any)
            )
          );
          return dropOffData;

        default:
          throw new Error(`Unknown report type: ${type}`);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate report';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Helper function to generate trends data
  const generateTrendsData = (journeys: CustomerJourney[]): any[] => {
    const trendsMap = new Map<string, Map<string, { count: number; value: number }>>();

    journeys.forEach(journey => {
      const date = new Date(journey.startedAt).toISOString().split('T')[0];

      if (!trendsMap.has(date)) {
        trendsMap.set(date, new Map());
      }

      const dayTrends = trendsMap.get(date)!;
      const stage = journey.stage;

      if (!dayTrends.has(stage)) {
        dayTrends.set(stage, { count: 0, value: 0 });
      }

      const stageTrend = dayTrends.get(stage)!;
      stageTrend.count++;

      // Add estimated value if available
      if (journey.context.estimatedValue) {
        stageTrend.value += journey.context.estimatedValue;
      }
    });

    // Convert to array format
    const trends: any[] = [];
    trendsMap.forEach((dayTrends, date) => {
      dayTrends.forEach((data, stage) => {
        trends.push({
          date,
          stage,
          count: data.count,
          value: data.value
        });
      });
    });

    return trends.sort((a, b) => a.date.localeCompare(b.date));
  };

  // Auto-refresh metrics periodically
  useEffect(() => {
    if (!tenantId) return;

    const interval = setInterval(refreshMetrics, 5 * 60 * 1000); // Refresh every 5 minutes
    return () => clearInterval(interval);
  }, [tenantId, refreshMetrics]);

  return {
    // Analytics state
    metrics,
    funnels,
    trends,
    loading,
    error,

    // Analytics methods
    refreshMetrics,
    getFunnelData,
    getDropoffAnalysis,
    getAttributionData,

    // Reporting
    exportAnalytics,
    generateReport
  };
}
