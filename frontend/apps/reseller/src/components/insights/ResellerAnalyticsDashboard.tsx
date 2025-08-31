'use client';

import { MLInsightsDashboard, SalesForecasting, CustomerBehaviorAnalysis } from '@dotmac/ml-analytics';
import { useUniversalAuth } from '@dotmac/headless';
import { Card } from '@dotmac/primitives';

export function ResellerAnalyticsDashboard() {
  const { user } = useUniversalAuth();

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Sales Analytics & Forecasting</h2>
        <p className="text-gray-600">ML-powered insights for your reseller operations</p>
      </div>

      {/* Sales Forecasting */}
      <Card className="p-6">
        <SalesForecasting
          resellerId={user?.id}
          forecastPeriod={90}
          metrics={['revenue', 'customer_acquisition', 'churn_rate']}
          seasonalityDetection={true}
          confidenceInterval={0.95}
          onForecastUpdate={(forecast) => {
            // Forecast updated - handled by internal state management
          }}
        />
      </Card>

      {/* Customer Behavior Analysis */}
      <CustomerBehaviorAnalysis
        resellerId={user?.id}
        analysisTypes={['churn_prediction', 'upsell_opportunities', 'engagement_patterns']}
        enableRealtime={true}
        onBehaviorInsight={(insight) => {
          console.log('Customer behavior insight:', insight);
        }}
      />

      {/* Full ML Insights Dashboard */}
      <MLInsightsDashboard
        entityId={user?.id}
        entityType="reseller"
        insights={[
          'commission_optimization',
          'territory_analysis',
          'customer_segmentation',
          'competitive_intelligence',
          'market_opportunities'
        ]}
        timeRange="6months"
        enableInteractive={true}
        theme="light"
        onInsightGenerated={(insight) => {
          console.log('New reseller insight:', insight);
        }}
      />
    </div>
  );
}
