import type { DashboardConfig } from '@dotmac/patterns/templates';
import { SpeedTestWidget } from '../components/quality/SpeedTestWidget';
import { SignalStrengthWidget } from '../components/quality/SignalStrengthWidget';

export const qualityConfig: DashboardConfig = {
  title: 'Service Quality',
  subtitle: 'Real-time performance and reliability metrics',
  portal: 'customer',
  apiEndpoint: '/api/customer/quality',
  refreshInterval: 30, // seconds
  timeRanges: [
    { label: '24h', value: '24h' },
    { label: '7d', value: '7d' },
    { label: '30d', value: '30d' }
  ],
  metrics: [
    { key: 'downMbps', title: 'Download', value: 0, format: 'number', precision: 1, color: '#2563eb' },
    { key: 'upMbps', title: 'Upload', value: 0, format: 'number', precision: 1, color: '#22c55e' },
    { key: 'latencyMs', title: 'Latency', value: 0, format: 'number', precision: 0, color: '#f97316' },
    { key: 'uptimePct', title: 'Uptime', value: 0.0, format: 'percentage', precision: 2, color: '#10b981' },
  ],
  sections: [
    { id: 'speed', title: 'Speed Test', type: 'custom', size: 'md', order: 1, component: SpeedTestWidget },
    { id: 'signal', title: 'Signal Strength', type: 'custom', size: 'md', order: 2, component: SignalStrengthWidget },
    { id: 'incidents', title: 'Service Issues', type: 'table', size: 'lg', order: 3, config: {
      columns: [
        { key: 'id', label: 'ID' },
        { key: 'title', label: 'Title' },
        { key: 'status', label: 'Status' },
        { key: 'eta', label: 'ETA' },
      ],
      apiEndpoint: '/api/customer/quality',
      maxItems: 5,
    }},
    { id: 'trends', title: 'Performance History', type: 'chart', size: 'full', order: 4, config: {
      id: 'trends', title: 'Download / Upload', type: 'line', dataKey: 'trends', height: 280, showLegend: true
    }},
  ],
};
