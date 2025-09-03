'use client';

import { MLInsightsDashboard, UsagePredictionWidget, AnomalyAlerts } from '@dotmac/ml-analytics';
import { useUniversalAuth } from '@dotmac/headless';
import { Card } from '@dotmac/primitives';

export function CustomerInsightsDashboard() {
  const { user } = useUniversalAuth();

  return (
    <div className='space-y-6'>
      <div>
        <h2 className='text-2xl font-bold text-gray-900'>Usage Insights</h2>
        <p className='text-gray-600'>AI-powered insights about your service usage</p>
      </div>

      {/* Anomaly Alerts */}
      <AnomalyAlerts
        customerId={user?.id}
        alertTypes={['unusual_usage', 'billing_anomaly', 'service_degradation']}
        enableRealtime={true}
        onAnomalyDetected={(anomaly) => {
          console.log('Customer anomaly detected:', anomaly);
        }}
      />

      {/* Usage Prediction */}
      <Card className='p-6'>
        <UsagePredictionWidget
          customerId={user?.id}
          predictionPeriod={30}
          metrics={['bandwidth', 'billing_amount', 'service_calls']}
          enableTrends={true}
          onPredictionUpdate={(prediction) => {
            console.log('Usage prediction updated:', prediction);
          }}
        />
      </Card>

      {/* Full ML Insights Dashboard */}
      <MLInsightsDashboard
        entityId={user?.id}
        entityType='customer'
        insights={[
          'usage_patterns',
          'cost_optimization',
          'service_recommendations',
          'billing_predictions',
        ]}
        timeRange='3months'
        enableInteractive={true}
        theme='light'
        onInsightGenerated={(insight) => {
          console.log('New customer insight:', insight);
        }}
      />
    </div>
  );
}
