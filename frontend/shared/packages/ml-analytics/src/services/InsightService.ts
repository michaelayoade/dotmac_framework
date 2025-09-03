import type {
  BusinessInsight,
  InsightGenerationConfig,
  DataPattern,
  PredictiveInsight,
  CompetitiveInsight,
  OperationalInsight,
  RevenueInsight,
  CustomerInsight,
  TimeSeriesData,
  MLModel,
  ForecastResult,
} from '../types';

export class InsightService {
  private models: Map<string, MLModel> = new Map();

  async generateBusinessInsights(
    data: Record<string, any[]>,
    config: InsightGenerationConfig = {}
  ): Promise<BusinessInsight[]> {
    const insights: BusinessInsight[] = [];

    // Revenue insights
    if (data.revenue) {
      const revenueInsights = await this.generateRevenueInsights(data.revenue, config);
      insights.push(...revenueInsights);
    }

    // Customer insights
    if (data.customers) {
      const customerInsights = await this.generateCustomerInsights(data.customers, config);
      insights.push(...customerInsights);
    }

    // Operational insights
    if (data.operations) {
      const operationalInsights = await this.generateOperationalInsights(data.operations, config);
      insights.push(...operationalInsights);
    }

    return insights;
  }

  async generatePredictiveInsights(
    data: TimeSeriesData[],
    horizon: number = 30,
    config: Partial<InsightGenerationConfig> = {}
  ): Promise<PredictiveInsight[]> {
    const insights: PredictiveInsight[] = [];

    // Trend analysis
    const trendInsight = await this.analyzeTrend(data);
    if (trendInsight) insights.push(trendInsight);

    // Seasonality detection
    const seasonalInsight = await this.analyzeSeasonality(data);
    if (seasonalInsight) insights.push(seasonalInsight);

    // Forecast-based insights
    const forecastInsights = await this.generateForecastInsights(data, horizon);
    insights.push(...forecastInsights);

    return insights;
  }

  private async generateRevenueInsights(
    revenueData: any[],
    config: InsightGenerationConfig
  ): Promise<RevenueInsight[]> {
    const insights: RevenueInsight[] = [];

    // Revenue growth analysis
    const monthlyRevenue = this.aggregateByMonth(revenueData);
    const growthRate = this.calculateGrowthRate(monthlyRevenue);

    if (Math.abs(growthRate) > 0.1) {
      // 10% threshold
      insights.push({
        id: `revenue-growth-${Date.now()}`,
        type: 'revenue',
        category: 'performance',
        title: growthRate > 0 ? 'Strong Revenue Growth Detected' : 'Revenue Decline Alert',
        description: `Revenue ${growthRate > 0 ? 'increased' : 'decreased'} by ${Math.abs(growthRate * 100).toFixed(1)}% compared to previous period`,
        impact: growthRate > 0.2 ? 'high' : growthRate < -0.1 ? 'critical' : 'medium',
        confidence: 0.85,
        dataPoints: monthlyRevenue.length,
        recommendations:
          growthRate > 0
            ? ['Scale successful initiatives', 'Increase marketing spend', 'Expand to new markets']
            : [
                'Investigate decline causes',
                'Review pricing strategy',
                'Focus on customer retention',
              ],
        metrics: {
          currentValue: monthlyRevenue[monthlyRevenue.length - 1]?.value || 0,
          previousValue: monthlyRevenue[monthlyRevenue.length - 2]?.value || 0,
          changePercent: growthRate * 100,
          trend: growthRate > 0 ? 'increasing' : 'decreasing',
        },
        generatedAt: new Date(),
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
        tags: ['revenue', 'growth', 'performance'],
      });
    }

    return insights;
  }

  private async generateCustomerInsights(
    customerData: any[],
    config: InsightGenerationConfig
  ): Promise<CustomerInsight[]> {
    const insights: CustomerInsight[] = [];

    // Customer churn analysis
    const churnRate = this.calculateChurnRate(customerData);
    if (churnRate > 0.05) {
      // 5% threshold
      insights.push({
        id: `customer-churn-${Date.now()}`,
        type: 'customer',
        category: 'retention',
        title: 'High Customer Churn Detected',
        description: `Customer churn rate is ${(churnRate * 100).toFixed(1)}%, indicating potential retention issues`,
        impact: churnRate > 0.15 ? 'critical' : 'high',
        confidence: 0.78,
        dataPoints: customerData.length,
        recommendations: [
          'Implement customer success programs',
          'Improve onboarding process',
          'Conduct exit interviews',
          'Review product-market fit',
        ],
        metrics: {
          churnRate: churnRate * 100,
          customersLost: Math.floor(customerData.length * churnRate),
          retentionRate: (1 - churnRate) * 100,
          avgCustomerLifetime: this.calculateAvgLifetime(customerData),
        },
        generatedAt: new Date(),
        expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
        tags: ['customer', 'churn', 'retention'],
      });
    }

    return insights;
  }

  private async generateOperationalInsights(
    operationData: any[],
    config: InsightGenerationConfig
  ): Promise<OperationalInsight[]> {
    const insights: OperationalInsight[] = [];

    // Efficiency analysis
    const efficiencyMetrics = this.calculateEfficiencyMetrics(operationData);

    if (efficiencyMetrics.utilizationRate < 0.7) {
      insights.push({
        id: `operational-efficiency-${Date.now()}`,
        type: 'operational',
        category: 'efficiency',
        title: 'Low Resource Utilization Detected',
        description: `Resource utilization is at ${(efficiencyMetrics.utilizationRate * 100).toFixed(1)}%, indicating potential optimization opportunities`,
        impact: 'medium',
        confidence: 0.72,
        dataPoints: operationData.length,
        recommendations: [
          'Optimize resource allocation',
          'Implement load balancing',
          'Review capacity planning',
          'Automate routine tasks',
        ],
        metrics: {
          utilizationRate: efficiencyMetrics.utilizationRate * 100,
          wastePercentage: (1 - efficiencyMetrics.utilizationRate) * 100,
          potentialSavings: efficiencyMetrics.potentialSavings,
          currentCost: efficiencyMetrics.currentCost,
        },
        generatedAt: new Date(),
        expiresAt: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000),
        tags: ['operational', 'efficiency', 'optimization'],
      });
    }

    return insights;
  }

  private async analyzeTrend(data: TimeSeriesData[]): Promise<PredictiveInsight | null> {
    if (data.length < 10) return null;

    const values = data.map((d) => d.value);
    const trend = this.calculateTrendDirection(values);
    const strength = this.calculateTrendStrength(values);

    if (strength > 0.6) {
      // Strong trend threshold
      return {
        id: `trend-${Date.now()}`,
        type: 'predictive',
        category: 'trend',
        title: `${trend > 0 ? 'Strong Upward' : 'Strong Downward'} Trend Detected`,
        description: `Data shows a ${trend > 0 ? 'positive' : 'negative'} trend with ${(strength * 100).toFixed(1)}% confidence`,
        impact: strength > 0.8 ? 'high' : 'medium',
        confidence: strength,
        dataPoints: data.length,
        recommendations:
          trend > 0
            ? [
                'Capitalize on positive momentum',
                'Scale successful initiatives',
                'Plan for increased demand',
              ]
            : ['Address underlying issues', 'Implement corrective measures', 'Monitor closely'],
        prediction: {
          horizon: 30,
          expectedChange: trend * strength * 0.3, // Conservative estimate
          confidenceInterval: [0.6, 0.9],
        },
        generatedAt: new Date(),
        expiresAt: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000),
        tags: ['trend', 'prediction', 'analysis'],
      };
    }

    return null;
  }

  private async analyzeSeasonality(data: TimeSeriesData[]): Promise<PredictiveInsight | null> {
    if (data.length < 24) return null;

    const seasonality = this.detectSeasonality(data.map((d) => d.value));

    if (seasonality.detected && seasonality.strength! > 0.4) {
      return {
        id: `seasonality-${Date.now()}`,
        type: 'predictive',
        category: 'seasonality',
        title: 'Seasonal Pattern Identified',
        description: `Data exhibits ${seasonality.period}-period seasonality with ${(seasonality.strength! * 100).toFixed(1)}% strength`,
        impact: 'medium',
        confidence: seasonality.strength!,
        dataPoints: data.length,
        recommendations: [
          'Plan for seasonal variations',
          'Adjust inventory accordingly',
          'Optimize marketing timing',
          'Prepare seasonal staffing',
        ],
        prediction: {
          horizon: seasonality.period!,
          expectedCycle: seasonality.period!,
          peakPeriods: this.identifyPeakPeriods(data, seasonality.period!),
        },
        generatedAt: new Date(),
        expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
        tags: ['seasonality', 'pattern', 'forecast'],
      };
    }

    return null;
  }

  private async generateForecastInsights(
    data: TimeSeriesData[],
    horizon: number
  ): Promise<PredictiveInsight[]> {
    const insights: PredictiveInsight[] = [];

    // Import forecasting functionality
    const { createForecast } = await import('../algorithms/forecasting');

    try {
      const forecast = createForecast(data, horizon);

      // Analyze forecast for insights
      const lastValue = data[data.length - 1].value;
      const avgForecast =
        forecast.predictions.reduce((sum, p) => sum + p.value, 0) / forecast.predictions.length;
      const change = (avgForecast - lastValue) / lastValue;

      if (Math.abs(change) > 0.1) {
        // 10% change threshold
        insights.push({
          id: `forecast-${Date.now()}`,
          type: 'predictive',
          category: 'forecast',
          title: `${change > 0 ? 'Growth' : 'Decline'} Expected in Next ${horizon} Periods`,
          description: `Forecasting models predict a ${Math.abs(change * 100).toFixed(1)}% ${change > 0 ? 'increase' : 'decrease'} over the next ${horizon} periods`,
          impact: Math.abs(change) > 0.25 ? 'high' : 'medium',
          confidence: forecast.metrics.accuracy,
          dataPoints: data.length,
          recommendations:
            change > 0
              ? ['Prepare for increased demand', 'Scale operations', 'Optimize supply chain']
              : ['Implement cost controls', 'Review strategy', 'Focus on efficiency'],
          prediction: {
            horizon,
            expectedValue: avgForecast,
            confidenceInterval: [
              Math.min(...forecast.predictions.map((p) => p.bounds.lower)),
              Math.max(...forecast.predictions.map((p) => p.bounds.upper)),
            ],
            method: 'machine_learning',
          },
          generatedAt: new Date(),
          expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
          tags: ['forecast', 'prediction', 'ml'],
        });
      }
    } catch (error) {
      console.error('Error generating forecast insights:', error);
    }

    return insights;
  }

  // Helper methods
  private aggregateByMonth(data: any[]): TimeSeriesData[] {
    const monthlyData = new Map<string, { sum: number; count: number }>();

    data.forEach((item) => {
      const date = new Date(item.date || item.timestamp || item.created_at);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;

      if (!monthlyData.has(monthKey)) {
        monthlyData.set(monthKey, { sum: 0, count: 0 });
      }

      const entry = monthlyData.get(monthKey)!;
      entry.sum += item.amount || item.value || 0;
      entry.count += 1;
    });

    return Array.from(monthlyData.entries())
      .map(([monthKey, data]) => ({
        timestamp: new Date(monthKey + '-01'),
        value: data.sum / data.count,
      }))
      .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }

  private calculateGrowthRate(data: TimeSeriesData[]): number {
    if (data.length < 2) return 0;

    const recent = data[data.length - 1].value;
    const previous = data[data.length - 2].value;

    return previous > 0 ? (recent - previous) / previous : 0;
  }

  private calculateChurnRate(customerData: any[]): number {
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    const activeCustomers = customerData.filter(
      (c) => new Date(c.lastActivity || c.updated_at || c.created_at) > thirtyDaysAgo
    );

    return customerData.length > 0 ? 1 - activeCustomers.length / customerData.length : 0;
  }

  private calculateAvgLifetime(customerData: any[]): number {
    const lifetimes = customerData.map((customer) => {
      const created = new Date(customer.created_at || customer.joinDate);
      const lastActive = new Date(customer.lastActivity || customer.updated_at || Date.now());
      return (lastActive.getTime() - created.getTime()) / (1000 * 60 * 60 * 24); // Days
    });

    return lifetimes.reduce((sum, lifetime) => sum + lifetime, 0) / lifetimes.length;
  }

  private calculateEfficiencyMetrics(operationData: any[]) {
    const totalCapacity = operationData.reduce((sum, item) => sum + (item.capacity || 100), 0);
    const actualUsage = operationData.reduce(
      (sum, item) => sum + (item.usage || item.utilized || 0),
      0
    );
    const totalCost = operationData.reduce((sum, item) => sum + (item.cost || 0), 0);

    const utilizationRate = totalCapacity > 0 ? actualUsage / totalCapacity : 0;
    const potentialSavings = totalCost * (1 - utilizationRate) * 0.3; // Conservative estimate

    return {
      utilizationRate,
      potentialSavings,
      currentCost: totalCost,
    };
  }

  private calculateTrendDirection(values: number[]): number {
    if (values.length < 2) return 0;

    let positiveChanges = 0;
    let negativeChanges = 0;

    for (let i = 1; i < values.length; i++) {
      const change = values[i] - values[i - 1];
      if (change > 0) positiveChanges++;
      else if (change < 0) negativeChanges++;
    }

    const totalChanges = positiveChanges + negativeChanges;
    return totalChanges > 0 ? (positiveChanges - negativeChanges) / totalChanges : 0;
  }

  private calculateTrendStrength(values: number[]): number {
    if (values.length < 3) return 0;

    // Calculate correlation coefficient between values and their indices
    const n = values.length;
    const indices = Array.from({ length: n }, (_, i) => i);

    const meanX = indices.reduce((sum, x) => sum + x, 0) / n;
    const meanY = values.reduce((sum, y) => sum + y, 0) / n;

    let numerator = 0;
    let sumXSquared = 0;
    let sumYSquared = 0;

    for (let i = 0; i < n; i++) {
      const xDiff = indices[i] - meanX;
      const yDiff = values[i] - meanY;

      numerator += xDiff * yDiff;
      sumXSquared += xDiff * xDiff;
      sumYSquared += yDiff * yDiff;
    }

    const denominator = Math.sqrt(sumXSquared * sumYSquared);
    return denominator > 0 ? Math.abs(numerator / denominator) : 0;
  }

  private detectSeasonality(values: number[]): {
    detected: boolean;
    period?: number;
    strength?: number;
  } {
    // Import seasonality detection
    try {
      const { detectSeasonality } = require('../algorithms/forecasting');
      return detectSeasonality(values);
    } catch {
      // Fallback simple seasonality detection
      return this.simpleSeasonalityDetection(values);
    }
  }

  private simpleSeasonalityDetection(values: number[]): {
    detected: boolean;
    period?: number;
    strength?: number;
  } {
    const testPeriods = [7, 12, 24, 30];
    let bestPeriod = 0;
    let bestStrength = 0;

    for (const period of testPeriods) {
      if (values.length < period * 2) continue;

      const strength = this.calculateSeasonalStrength(values, period);
      if (strength > bestStrength) {
        bestStrength = strength;
        bestPeriod = period;
      }
    }

    return {
      detected: bestStrength > 0.3,
      period: bestPeriod > 0 ? bestPeriod : undefined,
      strength: bestStrength > 0 ? bestStrength : undefined,
    };
  }

  private calculateSeasonalStrength(values: number[], period: number): number {
    if (values.length < period * 2) return 0;

    const seasons = Math.floor(values.length / period);
    const seasonalMeans = Array(period).fill(0);
    const seasonalCounts = Array(period).fill(0);

    for (let i = 0; i < values.length; i++) {
      const seasonIndex = i % period;
      seasonalMeans[seasonIndex] += values[i];
      seasonalCounts[seasonIndex]++;
    }

    for (let i = 0; i < period; i++) {
      if (seasonalCounts[i] > 0) {
        seasonalMeans[i] /= seasonalCounts[i];
      }
    }

    const overallMean = values.reduce((sum, v) => sum + v, 0) / values.length;
    let seasonalVariance = 0;
    let totalVariance = 0;

    for (let i = 0; i < values.length; i++) {
      const seasonIndex = i % period;
      seasonalVariance += Math.pow(seasonalMeans[seasonIndex] - overallMean, 2);
      totalVariance += Math.pow(values[i] - overallMean, 2);
    }

    return totalVariance > 0 ? seasonalVariance / totalVariance : 0;
  }

  private identifyPeakPeriods(data: TimeSeriesData[], period: number): number[] {
    const seasonalAvgs = Array(period).fill(0);
    const seasonalCounts = Array(period).fill(0);

    data.forEach((item, index) => {
      const seasonIndex = index % period;
      seasonalAvgs[seasonIndex] += item.value;
      seasonalCounts[seasonIndex]++;
    });

    for (let i = 0; i < period; i++) {
      if (seasonalCounts[i] > 0) {
        seasonalAvgs[i] /= seasonalCounts[i];
      }
    }

    const avgValue = seasonalAvgs.reduce((sum, v) => sum + v, 0) / seasonalAvgs.length;

    return seasonalAvgs
      .map((avg, index) => ({ index, avg }))
      .filter((item) => item.avg > avgValue * 1.1) // 10% above average
      .map((item) => item.index);
  }
}
