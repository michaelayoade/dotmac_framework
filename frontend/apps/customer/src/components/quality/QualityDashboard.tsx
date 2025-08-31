'use client';

import React, { useState, useEffect } from 'react';
import { DashboardTemplate } from '@dotmac/primitives/templates/DashboardTemplate';
import { 
  SignalIcon,
  WifiIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  PhoneIcon
} from '@heroicons/react/24/outline';

interface QualityMetric {
  timestamp: string;
  downloadSpeed: number;
  uploadSpeed: number;
  latency: number;
  jitter: number;
  packetLoss: number;
  signalStrength: number;
  status: 'excellent' | 'good' | 'fair' | 'poor';
}

interface ServiceIssue {
  id: string;
  type: 'outage' | 'slowdown' | 'intermittent' | 'maintenance';
  severity: 'critical' | 'major' | 'minor';
  title: string;
  description: string;
  startTime: string;
  estimatedResolution?: string;
  affectedServices: string[];
  status: 'investigating' | 'identified' | 'monitoring' | 'resolved';
}

const mockMetrics: QualityMetric[] = [
  {
    timestamp: '2023-12-01T10:00:00Z',
    downloadSpeed: 145.2,
    uploadSpeed: 23.8,
    latency: 12,
    jitter: 2.1,
    packetLoss: 0,
    signalStrength: -45,
    status: 'excellent'
  },
  {
    timestamp: '2023-12-01T09:45:00Z',
    downloadSpeed: 132.4,
    uploadSpeed: 21.3,
    latency: 15,
    jitter: 3.2,
    packetLoss: 0.1,
    signalStrength: -48,
    status: 'good'
  }
];

const mockIssues: ServiceIssue[] = [
  {
    id: '1',
    type: 'maintenance',
    severity: 'minor',
    title: 'Scheduled Network Maintenance',
    description: 'Routine maintenance on local equipment may cause brief interruptions.',
    startTime: '2023-12-02T02:00:00Z',
    estimatedResolution: '2023-12-02T06:00:00Z',
    affectedServices: ['Internet'],
    status: 'monitoring'
  }
];

export const QualityDashboard: React.FC = () => {
  const [currentMetrics, setCurrentMetrics] = useState<QualityMetric>(mockMetrics[0]);
  const [historicalMetrics, setHistoricalMetrics] = useState<QualityMetric[]>(mockMetrics);
  const [activeIssues, setActiveIssues] = useState<ServiceIssue[]>(mockIssues);
  const [isRunningSpeedTest, setIsRunningSpeedTest] = useState(false);
  const [loading, setLoading] = useState(false);

  const runSpeedTest = async () => {
    setIsRunningSpeedTest(true);
    
    // Simulate speed test
    try {
      await new Promise(resolve => setTimeout(resolve, 10000)); // 10 second test
      
      const newMetric: QualityMetric = {
        timestamp: new Date().toISOString(),
        downloadSpeed: Math.floor(Math.random() * 50) + 100,
        uploadSpeed: Math.floor(Math.random() * 10) + 15,
        latency: Math.floor(Math.random() * 20) + 8,
        jitter: Math.floor(Math.random() * 5) + 1,
        packetLoss: Math.random() * 0.5,
        signalStrength: Math.floor(Math.random() * 20) - 55,
        status: 'good'
      };
      
      setCurrentMetrics(newMetric);
      setHistoricalMetrics(prev => [newMetric, ...prev.slice(0, 23)]);
    } finally {
      setIsRunningSpeedTest(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'excellent': return 'green';
      case 'good': return 'blue';
      case 'fair': return 'yellow';
      case 'poor': return 'red';
      default: return 'gray';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'major': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'minor': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const metrics = [
    {
      id: 'download',
      title: 'Download Speed',
      value: `${currentMetrics.downloadSpeed.toFixed(1)} Mbps`,
      change: {
        value: 12.5,
        type: 'increase' as const,
        period: 'last test'
      },
      icon: SignalIcon,
      color: getStatusColor(currentMetrics.status)
    },
    {
      id: 'upload',
      title: 'Upload Speed',
      value: `${currentMetrics.uploadSpeed.toFixed(1)} Mbps`,
      change: {
        value: 8.3,
        type: 'increase' as const,
        period: 'last test'
      },
      icon: WifiIcon,
      color: getStatusColor(currentMetrics.status)
    },
    {
      id: 'latency',
      title: 'Latency',
      value: `${currentMetrics.latency} ms`,
      change: {
        value: 2.1,
        type: 'decrease' as const,
        period: 'last test'
      },
      icon: ClockIcon,
      color: currentMetrics.latency < 20 ? 'green' : currentMetrics.latency < 50 ? 'yellow' : 'red'
    },
    {
      id: 'signal',
      title: 'Signal Strength',
      value: `${currentMetrics.signalStrength} dBm`,
      change: {
        value: 3.2,
        type: 'increase' as const,
        period: 'last reading'
      },
      icon: ChartBarIcon,
      color: currentMetrics.signalStrength > -50 ? 'green' : currentMetrics.signalStrength > -70 ? 'yellow' : 'red'
    }
  ];

  // Speed Test Chart Component
  const SpeedTestChart: React.FC<{ data?: any }> = () => (
    <div className="h-64 flex items-center justify-center">
      {isRunningSpeedTest ? (
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-lg font-medium text-gray-900">Running Speed Test...</p>
          <p className="text-sm text-gray-600 mt-2">This may take up to 30 seconds</p>
        </div>
      ) : (
        <div className="text-center">
          <ChartBarIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-4">Speed test history chart</p>
          <button
            onClick={runSpeedTest}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Run Speed Test
          </button>
        </div>
      )}
    </div>
  );

  // Signal Quality Chart Component
  const SignalQualityChart: React.FC<{ data?: any }> = () => (
    <div className="h-64 flex items-center justify-center">
      <div className="text-center w-full">
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">{currentMetrics.jitter.toFixed(1)}</div>
            <div className="text-sm text-gray-600">Jitter (ms)</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900">{currentMetrics.packetLoss.toFixed(2)}%</div>
            <div className="text-sm text-gray-600">Packet Loss</div>
          </div>
        </div>
        <div className="mt-6 bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full ${
              currentMetrics.status === 'excellent' ? 'bg-green-500' :
              currentMetrics.status === 'good' ? 'bg-blue-500' :
              currentMetrics.status === 'fair' ? 'bg-yellow-500' :
              'bg-red-500'
            }`}
            style={{ 
              width: `${
                currentMetrics.status === 'excellent' ? 100 :
                currentMetrics.status === 'good' ? 80 :
                currentMetrics.status === 'fair' ? 60 :
                40
              }%` 
            }}
          />
        </div>
        <div className="mt-2 text-sm font-medium capitalize text-gray-900">
          Connection Quality: {currentMetrics.status}
        </div>
      </div>
    </div>
  );

  // Service Status Component
  const ServiceStatusWidget: React.FC<{ data?: any }> = () => (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">Current Service Issues</h4>
      
      {activeIssues.length === 0 ? (
        <div className="text-center py-8">
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <SignalIcon className="w-6 h-6 text-green-600" />
          </div>
          <p className="text-sm text-gray-600">All services operating normally</p>
        </div>
      ) : (
        <div className="space-y-3">
          {activeIssues.map((issue) => (
            <div
              key={issue.id}
              className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <ExclamationTriangleIcon className="w-4 h-4" />
                    <h5 className="font-medium">{issue.title}</h5>
                  </div>
                  <p className="text-sm mt-1">{issue.description}</p>
                  <div className="flex items-center space-x-4 mt-2 text-xs">
                    <span>Started: {new Date(issue.startTime).toLocaleString()}</span>
                    {issue.estimatedResolution && (
                      <span>ETA: {new Date(issue.estimatedResolution).toLocaleString()}</span>
                    )}
                  </div>
                </div>
                <span className={`
                  px-2 py-1 text-xs font-medium rounded capitalize
                  ${issue.status === 'resolved' ? 'bg-green-100 text-green-800' :
                    issue.status === 'monitoring' ? 'bg-blue-100 text-blue-800' :
                    'bg-yellow-100 text-yellow-800'
                  }
                `}>
                  {issue.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const charts = [
    {
      id: 'speed-test',
      title: 'Internet Speed Test',
      component: SpeedTestChart,
      size: 'medium' as const,
    },
    {
      id: 'signal-quality',
      title: 'Signal Quality',
      component: SignalQualityChart,
      size: 'medium' as const,
    },
    {
      id: 'service-status',
      title: 'Service Status',
      component: ServiceStatusWidget,
      size: 'full' as const,
    }
  ];

  const quickActions = [
    {
      id: 'run-test',
      label: 'Run Speed Test',
      onClick: runSpeedTest,
      disabled: isRunningSpeedTest
    },
    {
      id: 'report-issue',
      label: 'Report Issue',
      onClick: () => {
        // Navigate to support
      }
    },
    {
      id: 'contact-support',
      label: 'Contact Support',
      onClick: () => {
        window.open('tel:+1-800-555-0123', '_self');
      },
      icon: PhoneIcon
    }
  ];

  const customContent = (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Service Quality Tips</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">Optimize Wi-Fi</h4>
            <p className="text-sm text-blue-800">
              Place your router in a central location away from interference sources.
            </p>
          </div>
          <div className="p-4 bg-green-50 rounded-lg">
            <h4 className="font-medium text-green-900 mb-2">Check Connections</h4>
            <p className="text-sm text-green-800">
              Ensure all cables are securely connected and not damaged.
            </p>
          </div>
          <div className="p-4 bg-yellow-50 rounded-lg">
            <h4 className="font-medium text-yellow-900 mb-2">Restart Equipment</h4>
            <p className="text-sm text-yellow-800">
              Restart your modem and router if experiencing connectivity issues.
            </p>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Test History</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Download
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Upload
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Latency
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {historicalMetrics.slice(0, 5).map((metric, index) => (
                <tr key={index}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(metric.timestamp).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {metric.downloadSpeed.toFixed(1)} Mbps
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {metric.uploadSpeed.toFixed(1)} Mbps
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {metric.latency} ms
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`
                      inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize
                      ${metric.status === 'excellent' ? 'bg-green-100 text-green-800' :
                        metric.status === 'good' ? 'bg-blue-100 text-blue-800' :
                        metric.status === 'fair' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }
                    `}>
                      {metric.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  return (
    <DashboardTemplate
      title="Service Quality"
      subtitle="Monitor your internet performance and service status"
      metrics={metrics}
      charts={charts}
      quickActions={quickActions}
      customContent={customContent}
      refreshData={() => setLoading(true)}
      loading={loading}
      className="h-full"
    />
  );
};