/**
 * System Monitoring Page
 * Integrates with the existing ISP framework monitoring system
 * Provides comprehensive system health and performance monitoring
 */

import { SystemMonitoringDashboard } from '@/components/monitoring/SystemMonitoringDashboard';

export const metadata = {
  title: 'System Monitoring - Management Admin',
  description: 'Comprehensive system health and performance monitoring',
};

export default function MonitoringPage() {
  return (
    <div className='space-y-6'>
      <SystemMonitoringDashboard />
    </div>
  );
}
