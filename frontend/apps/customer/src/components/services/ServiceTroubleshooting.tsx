'use client';

import { Card } from '@dotmac/styled-components/customer';
import {
  Activity,
  AlertCircle,
  BookOpen,
  CheckCircle,
  Clock,
  ExternalLink,
  HelpCircle,
  MessageSquare,
  Monitor,
  Phone,
  Play,
  RefreshCw,
  Router,
  Settings,
  Smartphone,
  Video,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useEffect, useState } from 'react';

interface DiagnosticStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  duration?: number;
  result?: string;
  action?: string;
}

interface TroubleshootingGuide {
  id: string;
  title: string;
  category: 'internet' | 'phone' | 'tv' | 'general';
  description: string;
  estimatedTime: string;
  difficulty: 'easy' | 'medium' | 'advanced';
  steps: string[];
  commonCauses: string[];
  videoUrl?: string;
}

const mockDiagnosticSteps: DiagnosticStep[] = [
  {
    id: 'connectivity',
    title: 'Testing Internet Connectivity',
    description: 'Checking your connection to our network',
    status: 'pending',
    duration: 10,
  },
  {
    id: 'speed',
    title: 'Measuring Connection Speed',
    description: 'Testing download and upload speeds',
    status: 'pending',
    duration: 15,
  },
  {
    id: 'latency',
    title: 'Checking Network Latency',
    description: 'Measuring response time and packet loss',
    status: 'pending',
    duration: 8,
  },
  {
    id: 'dns',
    title: 'Testing DNS Resolution',
    description: 'Verifying domain name resolution',
    status: 'pending',
    duration: 5,
  },
  {
    id: 'equipment',
    title: 'Checking Equipment Status',
    description: 'Verifying modem and router connectivity',
    status: 'pending',
    duration: 12,
  },
];

const troubleshootingGuides: TroubleshootingGuide[] = [
  {
    id: 'slow-internet',
    title: 'Slow Internet Speeds',
    category: 'internet',
    description: 'Step-by-step guide to diagnose and fix slow internet connections',
    estimatedTime: '10-15 minutes',
    difficulty: 'easy',
    steps: [
      'Run a speed test using our diagnostic tool',
      'Check if multiple devices are using bandwidth',
      'Restart your modem and router',
      'Move closer to your WiFi router if using wireless',
      'Check for background downloads or updates',
      'Scan for malware on your devices',
      'Contact support if speeds are still below your plan',
    ],
    commonCauses: [
      'WiFi interference from other devices',
      'Too many devices connected simultaneously',
      'Outdated router firmware',
      'Background software updates',
      'Distance from WiFi router',
    ],
    videoUrl: '/guides/slow-internet.mp4',
  },
  {
    id: 'no-internet',
    title: 'No Internet Connection',
    category: 'internet',
    description: 'Resolve complete internet outages and connection issues',
    estimatedTime: '5-10 minutes',
    difficulty: 'easy',
    steps: [
      'Check all cable connections to modem and router',
      'Look for status lights on your modem - should be solid green/blue',
      'Unplug modem for 30 seconds, then plug back in',
      'Wait 2-3 minutes for modem to fully restart',
      'Unplug router for 30 seconds, then plug back in',
      'Wait for WiFi network to appear in your device settings',
      'Test connection on multiple devices',
    ],
    commonCauses: [
      'Loose cable connections',
      'Power outage affecting equipment',
      'Overheated modem or router',
      'Service outage in your area',
      'ISP configuration changes',
    ],
  },
  {
    id: 'wifi-issues',
    title: 'WiFi Connection Problems',
    category: 'internet',
    description: 'Fix WiFi connectivity and performance issues',
    estimatedTime: '15-20 minutes',
    difficulty: 'medium',
    steps: [
      'Forget and reconnect to your WiFi network',
      'Check if WiFi password has been changed recently',
      'Move closer to the router to test signal strength',
      'Change WiFi channel in router settings (try channels 1, 6, or 11)',
      'Update your device WiFi drivers',
      'Restart network adapter on your device',
      'Consider upgrading to WiFi 6 if you have many devices',
    ],
    commonCauses: [
      'WiFi channel congestion from neighbors',
      'Incorrect WiFi password',
      'Outdated device drivers',
      'Physical obstructions blocking signal',
      'Router placed in poor location',
    ],
    videoUrl: '/guides/wifi-troubleshooting.mp4',
  },
  {
    id: 'phone-no-dial-tone',
    title: 'No Dial Tone on Phone',
    category: 'phone',
    description: "Restore phone service when there's no dial tone",
    estimatedTime: '5-10 minutes',
    difficulty: 'easy',
    steps: [
      'Check that phone is properly plugged into phone jack',
      'Try a different phone to isolate the issue',
      'Check phone adapter power and network connections',
      'Look for solid lights on phone adapter',
      'Unplug phone adapter for 30 seconds, then reconnect',
      'Test with corded phone instead of cordless',
      'Check if cordless phone base station is powered on',
    ],
    commonCauses: [
      'Loose phone connections',
      'Phone adapter power issues',
      'Faulty phone handset',
      'Cordless phone battery issues',
      'Phone line configuration problems',
    ],
  },
  {
    id: 'poor-call-quality',
    title: 'Poor Phone Call Quality',
    category: 'phone',
    description: 'Improve voice quality and reduce call issues',
    estimatedTime: '10-15 minutes',
    difficulty: 'medium',
    steps: [
      'Test call quality with a corded phone',
      'Check internet connection stability (VoIP dependency)',
      'Ensure phone adapter is not overheating',
      'Move cordless phone closer to base station',
      'Replace cordless phone batteries if needed',
      'Check for interference from other electronics',
      'Update Quality of Service (QoS) settings on router',
    ],
    commonCauses: [
      'Poor internet connection affecting VoIP',
      'Interference from wireless devices',
      'Low battery in cordless phones',
      'Network congestion during peak hours',
      'Damaged phone cables',
    ],
  },
];

export function ServiceTroubleshooting() {
  const [activeTab, setActiveTab] = useState<'diagnostic' | 'guides' | 'status'>('diagnostic');
  const [diagnostics, setDiagnostics] = useState<DiagnosticStep[]>(mockDiagnosticSteps);
  const [isRunningDiagnostic, setIsRunningDiagnostic] = useState(false);
  const [selectedGuide, setSelectedGuide] = useState<TroubleshootingGuide | null>(null);
  const [serviceStatus] = useState({
    internet: { status: 'operational', lastChecked: '2 minutes ago' },
    phone: { status: 'operational', lastChecked: '2 minutes ago' },
    tv: { status: 'maintenance', lastChecked: '5 minutes ago' },
    network: { status: 'operational', lastChecked: '1 minute ago' },
  });

  const runDiagnostic = async () => {
    setIsRunningDiagnostic(true);

    for (let i = 0; i < diagnostics.length; i++) {
      // Update step status to running
      setDiagnostics(prev =>
        prev.map((step, index) => (index === i ? { ...step, status: 'running' } : step))
      );

      // Simulate diagnostic duration
      await new Promise(resolve => setTimeout(resolve, diagnostics[i].duration! * 100));

      // Simulate results
      const results = [
        { status: 'completed', result: 'Connection successful - 98.5 Mbps down, 99.2 Mbps up' },
        { status: 'completed', result: 'Speed test completed - Above expected performance' },
        { status: 'completed', result: 'Latency: 12ms, Packet loss: 0%' },
        { status: 'completed', result: 'DNS resolution working correctly' },
        { status: 'completed', result: 'All equipment online and functioning' },
      ];

      setDiagnostics(prev =>
        prev.map((step, index) =>
          index === i
            ? {
                ...step,
                status: results[i].status as any,
                result: results[i].result,
                action:
                  i === 1 && Math.random() > 0.7
                    ? 'Consider upgrading for faster speeds'
                    : undefined,
              }
            : step
        )
      );
    }

    setIsRunningDiagnostic(false);
  };

  const resetDiagnostic = () => {
    setDiagnostics(mockDiagnosticSteps);
    setIsRunningDiagnostic(false);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'operational':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'maintenance':
        return <Clock className="h-5 w-5 text-yellow-600" />;
      case 'outage':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      default:
        return <HelpCircle className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'operational':
        return 'text-green-600';
      case 'maintenance':
        return 'text-yellow-600';
      case 'outage':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getDifficultyBadge = (difficulty: string) => {
    const colors = {
      easy: 'bg-green-100 text-green-800',
      medium: 'bg-yellow-100 text-yellow-800',
      advanced: 'bg-red-100 text-red-800',
    };
    return colors[difficulty as keyof typeof colors] || colors.easy;
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'internet':
        return <Wifi className="h-5 w-5 text-blue-600" />;
      case 'phone':
        return <Phone className="h-5 w-5 text-green-600" />;
      case 'tv':
        return <Monitor className="h-5 w-5 text-purple-600" />;
      default:
        return <Settings className="h-5 w-5 text-gray-600" />;
    }
  };

  if (selectedGuide) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setSelectedGuide(null)}
            className="text-blue-600 hover:text-blue-800 font-medium"
          >
            ← Back to Troubleshooting Guides
          </button>
        </div>

        <Card className="p-6">
          <div className="mb-6">
            <div className="flex items-center mb-2">
              {getCategoryIcon(selectedGuide.category)}
              <h2 className="ml-2 text-2xl font-bold text-gray-900">{selectedGuide.title}</h2>
            </div>
            <p className="text-gray-600 mb-4">{selectedGuide.description}</p>

            <div className="flex items-center space-x-4 text-sm">
              <div className="flex items-center">
                <Clock className="mr-1 h-4 w-4 text-gray-400" />
                <span className="text-gray-600">{selectedGuide.estimatedTime}</span>
              </div>
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getDifficultyBadge(selectedGuide.difficulty)}`}
              >
                {selectedGuide.difficulty}
              </span>
              {selectedGuide.videoUrl && (
                <button className="flex items-center text-blue-600 hover:text-blue-800">
                  <Video className="mr-1 h-4 w-4" />
                  Watch Video Guide
                </button>
              )}
            </div>
          </div>

          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Common Causes</h3>
            <ul className="space-y-2">
              {selectedGuide.commonCauses.map((cause, index) => (
                <li key={index} className="flex items-start text-sm text-gray-600">
                  <AlertCircle className="mr-2 h-4 w-4 text-yellow-500 flex-shrink-0 mt-0.5" />
                  <span>{cause}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Step-by-Step Solution</h3>
            <ol className="space-y-3">
              {selectedGuide.steps.map((step, index) => (
                <li key={index} className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white text-sm font-medium rounded-full flex items-center justify-center mr-3 mt-0.5">
                    {index + 1}
                  </span>
                  <span className="text-gray-700">{step}</span>
                </li>
              ))}
            </ol>
          </div>

          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-start">
              <HelpCircle className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <div className="ml-3">
                <h4 className="font-medium text-blue-900">Still Need Help?</h4>
                <p className="mt-1 text-sm text-blue-700">
                  If these steps don't resolve your issue, our technical support team is available
                  24/7.
                </p>
                <div className="mt-3 flex space-x-4">
                  <button className="text-sm text-blue-600 hover:text-blue-800 font-medium">
                    Chat with Support
                  </button>
                  <button className="text-sm text-blue-600 hover:text-blue-800 font-medium">
                    Schedule a Call
                  </button>
                  <button className="text-sm text-blue-600 hover:text-blue-800 font-medium">
                    Request Technician Visit
                  </button>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Troubleshooting & Diagnostics</h2>
        <p className="mt-1 text-sm text-gray-500">
          Run diagnostic tests and access self-service troubleshooting guides
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'diagnostic', label: 'Run Diagnostics', icon: Activity },
            { id: 'guides', label: 'Troubleshooting Guides', icon: BookOpen },
            { id: 'status', label: 'Service Status', icon: Monitor },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center border-b-2 px-1 py-2 text-sm font-medium ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              <tab.icon className="mr-2 h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'diagnostic' && (
        <Card className="p-6">
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Network Diagnostic Test</h3>
            <p className="text-gray-600">
              Run a comprehensive diagnostic to identify and resolve connectivity issues
              automatically.
            </p>
          </div>

          <div className="mb-6">
            <div className="flex space-x-4">
              <button
                onClick={runDiagnostic}
                disabled={isRunningDiagnostic}
                className={`flex items-center px-6 py-2 rounded-lg font-medium transition-colors ${
                  isRunningDiagnostic
                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {isRunningDiagnostic ? (
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                {isRunningDiagnostic ? 'Running Diagnostic...' : 'Start Diagnostic'}
              </button>
              <button
                onClick={resetDiagnostic}
                disabled={isRunningDiagnostic}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Reset
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {diagnostics.map((step, index) => (
              <div key={step.id} className="flex items-center p-4 border rounded-lg">
                <div className="flex-shrink-0 mr-4">
                  {step.status === 'pending' && (
                    <div className="w-8 h-8 border-2 border-gray-300 rounded-full flex items-center justify-center">
                      <span className="text-sm font-medium text-gray-600">{index + 1}</span>
                    </div>
                  )}
                  {step.status === 'running' && (
                    <div className="w-8 h-8 border-2 border-blue-600 rounded-full flex items-center justify-center">
                      <RefreshCw className="h-4 w-4 text-blue-600 animate-spin" />
                    </div>
                  )}
                  {step.status === 'completed' && (
                    <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                      <CheckCircle className="h-5 w-5 text-white" />
                    </div>
                  )}
                  {step.status === 'failed' && (
                    <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center">
                      <AlertCircle className="h-5 w-5 text-white" />
                    </div>
                  )}
                </div>

                <div className="flex-grow">
                  <h4 className="font-medium text-gray-900">{step.title}</h4>
                  <p className="text-sm text-gray-600">{step.description}</p>
                  {step.result && (
                    <p className="mt-1 text-sm text-green-600 font-medium">{step.result}</p>
                  )}
                  {step.action && (
                    <p className="mt-1 text-sm text-blue-600">Recommendation: {step.action}</p>
                  )}
                </div>

                {step.status === 'running' && (
                  <div className="flex-shrink-0 ml-4">
                    <div className="text-sm text-gray-500">~{step.duration}s</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {activeTab === 'guides' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {troubleshootingGuides.map(guide => (
            <Card
              key={guide.id}
              className="p-6 hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => setSelectedGuide(guide)}
            >
              <div className="mb-4">
                <div className="flex items-center mb-2">
                  {getCategoryIcon(guide.category)}
                  <h3 className="ml-2 text-lg font-semibold text-gray-900">{guide.title}</h3>
                </div>
                <p className="text-gray-600 text-sm mb-3">{guide.description}</p>

                <div className="flex items-center space-x-3 text-sm">
                  <div className="flex items-center text-gray-500">
                    <Clock className="mr-1 h-4 w-4" />
                    {guide.estimatedTime}
                  </div>
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getDifficultyBadge(guide.difficulty)}`}
                  >
                    {guide.difficulty}
                  </span>
                  {guide.videoUrl && (
                    <div className="flex items-center text-blue-600">
                      <Video className="mr-1 h-4 w-4" />
                      Video
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">{guide.steps.length} steps</span>
                <div className="flex items-center text-blue-600">
                  <span className="text-sm font-medium">View Guide</span>
                  <ExternalLink className="ml-1 h-4 w-4" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {activeTab === 'status' && (
        <div className="space-y-6">
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Service Status</h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center">
                    <Wifi className="mr-3 h-5 w-5 text-blue-600" />
                    <div>
                      <p className="font-medium text-gray-900">Internet Service</p>
                      <p className="text-sm text-gray-500">
                        Last checked: {serviceStatus.internet.lastChecked}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center">
                    {getStatusIcon(serviceStatus.internet.status)}
                    <span
                      className={`ml-2 text-sm font-medium capitalize ${getStatusColor(serviceStatus.internet.status)}`}
                    >
                      {serviceStatus.internet.status}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center">
                    <Phone className="mr-3 h-5 w-5 text-green-600" />
                    <div>
                      <p className="font-medium text-gray-900">Phone Service</p>
                      <p className="text-sm text-gray-500">
                        Last checked: {serviceStatus.phone.lastChecked}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center">
                    {getStatusIcon(serviceStatus.phone.status)}
                    <span
                      className={`ml-2 text-sm font-medium capitalize ${getStatusColor(serviceStatus.phone.status)}`}
                    >
                      {serviceStatus.phone.status}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center">
                    <Monitor className="mr-3 h-5 w-5 text-purple-600" />
                    <div>
                      <p className="font-medium text-gray-900">TV Service</p>
                      <p className="text-sm text-gray-500">
                        Last checked: {serviceStatus.tv.lastChecked}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center">
                    {getStatusIcon(serviceStatus.tv.status)}
                    <span
                      className={`ml-2 text-sm font-medium capitalize ${getStatusColor(serviceStatus.tv.status)}`}
                    >
                      {serviceStatus.tv.status}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center">
                    <Router className="mr-3 h-5 w-5 text-orange-600" />
                    <div>
                      <p className="font-medium text-gray-900">Network Infrastructure</p>
                      <p className="text-sm text-gray-500">
                        Last checked: {serviceStatus.network.lastChecked}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center">
                    {getStatusIcon(serviceStatus.network.status)}
                    <span
                      className={`ml-2 text-sm font-medium capitalize ${getStatusColor(serviceStatus.network.status)}`}
                    >
                      {serviceStatus.network.status}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-start">
                <Clock className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div className="ml-3">
                  <h4 className="font-medium text-yellow-900">Scheduled Maintenance</h4>
                  <p className="mt-1 text-sm text-yellow-700">
                    TV service maintenance is currently in progress. Expected completion: Today at
                    2:00 PM PST. Some channels may be temporarily unavailable.
                  </p>
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button className="p-4 border border-gray-300 rounded-lg text-center hover:bg-gray-50 transition-colors">
                <RefreshCw className="h-6 w-6 text-blue-600 mx-auto mb-2" />
                <p className="font-medium text-gray-900">Refresh Status</p>
                <p className="text-sm text-gray-500">Update service status</p>
              </button>

              <button className="p-4 border border-gray-300 rounded-lg text-center hover:bg-gray-50 transition-colors">
                <MessageSquare className="h-6 w-6 text-green-600 mx-auto mb-2" />
                <p className="font-medium text-gray-900">Report Issue</p>
                <p className="text-sm text-gray-500">Create support ticket</p>
              </button>

              <button className="p-4 border border-gray-300 rounded-lg text-center hover:bg-gray-50 transition-colors">
                <Smartphone className="h-6 w-6 text-purple-600 mx-auto mb-2" />
                <p className="font-medium text-gray-900">Service Alerts</p>
                <p className="text-sm text-gray-500">Manage notifications</p>
              </button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
