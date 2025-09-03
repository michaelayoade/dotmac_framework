'use client';

import React, { useEffect, useState } from 'react';
import {
  BarChart,
  TrendingUp,
  Clock,
  MapPin,
  AlertTriangle,
  CheckCircle,
  Activity,
} from 'lucide-react';
import { Card } from '@dotmac/primitives';
import {
  MLService,
  InsightService,
  recognizePatterns,
  detectAnomalies,
} from '@dotmac/ml-analytics';
import type {
  WorkOrder,
  BusinessInsight,
  AnomalyDetection,
  PatternRecognition,
  TimeSeriesData,
} from '@dotmac/ml-analytics';

interface WorkOrderAnalyticsProps {
  workOrders: WorkOrder[];
  technicianId: string;
  className?: string;
}

interface AnalyticsMetrics {
  completionRate: number;
  avgDuration: number;
  efficiencyTrend: 'up' | 'down' | 'stable';
  anomaliesDetected: number;
  patternsFound: number;
  predictedEfficiency: number;
}

export function WorkOrderAnalytics({
  workOrders,
  technicianId,
  className = '',
}: WorkOrderAnalyticsProps) {
  const [metrics, setMetrics] = useState<AnalyticsMetrics>({
    completionRate: 0,
    avgDuration: 0,
    efficiencyTrend: 'stable',
    anomaliesDetected: 0,
    patternsFound: 0,
    predictedEfficiency: 0,
  });

  const [insights, setInsights] = useState<BusinessInsight[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyDetection | null>(null);
  const [patterns, setPatterns] = useState<PatternRecognition | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyzeWorkOrders();
  }, [workOrders, technicianId]);

  const analyzeWorkOrders = async () => {
    setLoading(true);

    try {
      const mlService = new MLService();
      const insightService = new InsightService();

      // Prepare time series data from work orders
      const timeSeriesData: TimeSeriesData[] = workOrders
        .filter((wo) => wo.completedAt)
        .map((wo) => ({
          timestamp: new Date(wo.completedAt!),
          value: calculateWorkOrderDuration(wo),
        }))
        .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

      // Generate business insights
      const operationInsights = await insightService.generateBusinessInsights({
        operations: workOrders,
        technician: { id: technicianId },
      });

      // Detect anomalies in work patterns
      const anomalyResults = await detectAnomalies(timeSeriesData, {
        method: 'statistical',
        sensitivity: 0.8,
        threshold: 2.0,
      });

      // Recognize patterns
      const patternResults = await recognizePatterns(timeSeriesData, {
        includeTrends: true,
        includeSeasonality: true,
        sensitivity: 0.7,
      });

      // Calculate metrics
      const completedOrders = workOrders.filter((wo) => wo.status === 'completed');
      const completionRate = (completedOrders.length / workOrders.length) * 100;

      const avgDuration =
        timeSeriesData.length > 0
          ? timeSeriesData.reduce((sum, d) => sum + d.value, 0) / timeSeriesData.length
          : 0;

      // Predict efficiency using ML
      const efficiencyPrediction = await mlService.predict('efficiency-model', {
        features: [completionRate, avgDuration, workOrders.length, anomalyResults.anomalies.length],
      });

      // Determine efficiency trend
      const recentDurations = timeSeriesData.slice(-10).map((d) => d.value);
      const olderDurations = timeSeriesData.slice(-20, -10).map((d) => d.value);

      const recentAvg =
        recentDurations.reduce((sum, d) => sum + d, 0) / recentDurations.length || 0;
      const olderAvg = olderDurations.reduce((sum, d) => sum + d, 0) / olderDurations.length || 0;

      const efficiencyTrend =
        recentAvg < olderAvg ? 'up' : recentAvg > olderAvg ? 'down' : 'stable';

      setMetrics({
        completionRate,
        avgDuration,
        efficiencyTrend,
        anomaliesDetected: anomalyResults.anomalies.length,
        patternsFound: patternResults.patterns.length,
        predictedEfficiency: efficiencyPrediction.confidence * 100,
      });

      setInsights(operationInsights);
      setAnomalies(anomalyResults);
      setPatterns(patternResults);
    } catch (error) {
      console.error('Failed to analyze work orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateWorkOrderDuration = (workOrder: WorkOrder): number => {
    if (!workOrder.completedAt || !workOrder.assignedAt) return 0;

    const start = new Date(workOrder.assignedAt).getTime();
    const end = new Date(workOrder.completedAt).getTime();

    return (end - start) / (1000 * 60 * 60); // Hours
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className='w-4 h-4 text-green-500' />;
      case 'down':
        return <TrendingUp className='w-4 h-4 text-red-500 transform rotate-180' />;
      default:
        return <Activity className='w-4 h-4 text-blue-500' />;
    }
  };

  const getInsightIcon = (type: string) => {
    switch (type) {
      case 'operational':
        return <Activity className='w-4 h-4 text-blue-500' />;
      case 'predictive':
        return <TrendingUp className='w-4 h-4 text-purple-500' />;
      default:
        return <BarChart className='w-4 h-4 text-gray-500' />;
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'critical':
        return 'border-red-500 bg-red-50';
      case 'high':
        return 'border-orange-500 bg-orange-50';
      case 'medium':
        return 'border-yellow-500 bg-yellow-50';
      default:
        return 'border-green-500 bg-green-50';
    }
  };

  if (loading) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className='animate-pulse'>
          <div className='h-4 bg-gray-200 rounded w-1/3 mb-4'></div>
          <div className='space-y-3'>
            <div className='h-3 bg-gray-200 rounded'></div>
            <div className='h-3 bg-gray-200 rounded w-2/3'></div>
            <div className='h-3 bg-gray-200 rounded w-1/2'></div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Key Metrics */}
      <Card className='p-6'>
        <h2 className='text-lg font-semibold text-gray-900 mb-4 flex items-center'>
          <BarChart className='w-5 h-5 mr-2' />
          Work Order Analytics
        </h2>

        <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
          <div className='text-center'>
            <div className='flex items-center justify-center mb-2'>
              <CheckCircle className='w-6 h-6 text-green-500' />
            </div>
            <div className='text-2xl font-bold text-gray-900'>
              {metrics.completionRate.toFixed(1)}%
            </div>
            <div className='text-sm text-gray-600'>Completion Rate</div>
          </div>

          <div className='text-center'>
            <div className='flex items-center justify-center mb-2'>
              <Clock className='w-6 h-6 text-blue-500' />
            </div>
            <div className='text-2xl font-bold text-gray-900'>
              {metrics.avgDuration.toFixed(1)}h
            </div>
            <div className='text-sm text-gray-600'>Avg Duration</div>
          </div>

          <div className='text-center'>
            <div className='flex items-center justify-center mb-2'>
              {getTrendIcon(metrics.efficiencyTrend)}
            </div>
            <div className='text-2xl font-bold text-gray-900'>
              {metrics.predictedEfficiency.toFixed(0)}%
            </div>
            <div className='text-sm text-gray-600'>Predicted Efficiency</div>
          </div>

          <div className='text-center'>
            <div className='flex items-center justify-center mb-2'>
              <AlertTriangle className='w-6 h-6 text-orange-500' />
            </div>
            <div className='text-2xl font-bold text-gray-900'>{metrics.anomaliesDetected}</div>
            <div className='text-sm text-gray-600'>Anomalies Detected</div>
          </div>
        </div>
      </Card>

      {/* ML-Powered Insights */}
      {insights.length > 0 && (
        <Card className='p-6'>
          <h3 className='text-lg font-semibold text-gray-900 mb-4'>AI-Powered Insights</h3>

          <div className='space-y-4'>
            {insights.slice(0, 3).map((insight) => (
              <div
                key={insight.id}
                className={`p-4 rounded-lg border ${getImpactColor(insight.impact)}`}
              >
                <div className='flex items-start space-x-3'>
                  {getInsightIcon(insight.type)}
                  <div className='flex-1'>
                    <div className='flex items-center justify-between mb-2'>
                      <h4 className='font-medium text-gray-900'>{insight.title}</h4>
                      <span className='text-xs px-2 py-1 bg-gray-100 rounded-full text-gray-600'>
                        {Math.round(insight.confidence * 100)}% confidence
                      </span>
                    </div>
                    <p className='text-sm text-gray-700 mb-3'>{insight.description}</p>

                    {insight.recommendations && insight.recommendations.length > 0 && (
                      <div>
                        <p className='text-xs font-medium text-gray-800 mb-1'>Recommendations:</p>
                        <ul className='text-xs text-gray-600 space-y-1'>
                          {insight.recommendations.slice(0, 2).map((rec, index) => (
                            <li key={index} className='flex items-start'>
                              <span className='mr-2'>•</span>
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Pattern Recognition Results */}
      {patterns && patterns.patterns.length > 0 && (
        <Card className='p-6'>
          <h3 className='text-lg font-semibold text-gray-900 mb-4'>Discovered Patterns</h3>

          <div className='grid grid-cols-1 md:grid-cols-2 gap-4'>
            {patterns.patterns.slice(0, 4).map((pattern) => (
              <div key={pattern.id} className='p-3 bg-gray-50 rounded-lg'>
                <div className='flex items-center justify-between mb-2'>
                  <span className='text-sm font-medium text-gray-900 capitalize'>
                    {pattern.type} Pattern
                  </span>
                  <span className='text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded-full'>
                    {Math.round(pattern.confidence * 100)}%
                  </span>
                </div>
                <p className='text-sm text-gray-600'>{pattern.description}</p>

                {pattern.metadata?.frequency && (
                  <div className='mt-2 text-xs text-gray-500'>
                    Frequency: {pattern.metadata.frequency.toFixed(2)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Anomalies */}
      {anomalies && anomalies.anomalies.length > 0 && (
        <Card className='p-6'>
          <h3 className='text-lg font-semibold text-gray-900 mb-4'>Performance Anomalies</h3>

          <div className='space-y-3'>
            {anomalies.anomalies.slice(0, 5).map((anomaly, index) => (
              <div
                key={index}
                className='flex items-center justify-between p-3 bg-orange-50 border border-orange-200 rounded-lg'
              >
                <div className='flex items-center space-x-3'>
                  <AlertTriangle className='w-4 h-4 text-orange-500' />
                  <div>
                    <div className='text-sm font-medium text-gray-900'>
                      Unusual duration detected
                    </div>
                    <div className='text-xs text-gray-600'>
                      {new Date(anomaly.timestamp).toLocaleDateString()} - Duration:{' '}
                      {anomaly.value.toFixed(1)}h (Expected: {anomaly.expected?.toFixed(1)}h)
                    </div>
                  </div>
                </div>
                <span className='text-xs px-2 py-1 bg-orange-100 text-orange-800 rounded-full'>
                  {anomaly.severity}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
