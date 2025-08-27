import { Suspense } from 'react';
import AdminLayout from '../../../components/layout/AdminLayout';
import { RealTimeMonitoringDashboard } from '../../../components/network/RealTimeMonitoringDashboard';

export default function MonitoringPage() {
  return (
    <AdminLayout>
      <div className='space-y-6'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Real-Time Monitoring</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Live network performance monitoring and alerting via WebSocket connections
            </p>
          </div>
          <div className='flex gap-3'>
            <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'>
              Configure Alerts
            </button>
            <button className='px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium'>
              Export Metrics
            </button>
          </div>
        </div>

        <Suspense
          fallback={
            <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
              <div className='animate-pulse'>
                <div className='h-6 bg-gray-200 rounded w-1/4 mb-4'></div>
                <div className='grid grid-cols-1 lg:grid-cols-3 gap-6'>
                  <div className='lg:col-span-2 space-y-4'>
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className='h-32 bg-gray-200 rounded'></div>
                    ))}
                  </div>
                  <div className='space-y-3'>
                    {[...Array(5)].map((_, i) => (
                      <div key={i} className='h-24 bg-gray-200 rounded'></div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          }
        >
          <MonitoringContent />
        </Suspense>
      </div>
    </AdminLayout>
  );
}

async function MonitoringContent() {
  // Simulate loading delay
  await new Promise((resolve) => setTimeout(resolve, 300));

  const handleAlert = (alert: any) => {
    console.log('New alert received:', alert);
    // Here you could trigger notifications, send to external systems, etc.
  };

  const handleMetricsUpdate = (metrics: any[]) => {
    console.log('Metrics updated:', metrics.length, 'nodes');
    // Here you could store metrics, trigger analytics, etc.
  };

  return (
    <div className='space-y-6'>
      {/* Real-Time Monitoring Dashboard */}
      <RealTimeMonitoringDashboard
        autoConnect={true}
        refreshInterval={3000}
        onAlert={handleAlert}
        onMetricsUpdate={handleMetricsUpdate}
      />

      {/* Additional monitoring components could go here */}
      <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <h3 className='text-lg font-semibold text-gray-900 mb-4'>Performance Trends</h3>
          <div className='text-center py-8 text-gray-500'>
            <div className='text-sm'>Historical performance data would be displayed here</div>
            <div className='text-xs mt-1'>Integration with time-series database required</div>
          </div>
        </div>

        <div className='bg-white rounded-lg shadow-sm border border-gray-200 p-6'>
          <h3 className='text-lg font-semibold text-gray-900 mb-4'>Alert Configuration</h3>
          <div className='space-y-3 text-sm'>
            <div className='flex justify-between items-center p-2 bg-gray-50 rounded'>
              <span>CPU Threshold</span>
              <span className='font-medium'>80%</span>
            </div>
            <div className='flex justify-between items-center p-2 bg-gray-50 rounded'>
              <span>Memory Threshold</span>
              <span className='font-medium'>85%</span>
            </div>
            <div className='flex justify-between items-center p-2 bg-gray-50 rounded'>
              <span>Latency Threshold</span>
              <span className='font-medium'>20ms</span>
            </div>
            <div className='flex justify-between items-center p-2 bg-gray-50 rounded'>
              <span>Packet Loss Threshold</span>
              <span className='font-medium'>0.5%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
