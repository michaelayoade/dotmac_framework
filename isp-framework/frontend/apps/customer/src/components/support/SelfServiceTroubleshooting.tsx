'use client';

import { useState } from 'react';
import { Card } from '@dotmac/styled-components/customer';
import {
  Wifi,
  WifiOff,
  Router,
  Smartphone,
  Monitor,
  CheckCircle,
  AlertCircle,
  Clock,
  RefreshCw,
  Phone,
  MessageSquare,
  Calendar,
  Play,
  ChevronRight,
  HelpCircle,
  Zap,
  Network,
  Settings,
  Activity
} from 'lucide-react';

interface TroubleshootingStep {
  id: string;
  title: string;
  description: string;
  action?: string;
  completed?: boolean;
  result?: 'success' | 'failed' | 'pending';
}

interface DiagnosticResult {
  name: string;
  status: 'pass' | 'fail' | 'warning';
  message: string;
  action?: string;
}

interface TroubleshootingFlow {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  steps: TroubleshootingStep[];
  estimatedTime: string;
}

export function SelfServiceTroubleshooting() {
  const [activeFlow, setActiveFlow] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [isRunningDiagnostics, setIsRunningDiagnostics] = useState(false);
  const [diagnosticResults, setDiagnosticResults] = useState<DiagnosticResult[]>([]);

  const troubleshootingFlows: TroubleshootingFlow[] = [
    {
      id: 'internet-slow',
      title: 'Slow Internet Connection',
      description: 'Your internet feels slower than usual',
      icon: Wifi,
      estimatedTime: '5-10 minutes',
      steps: [
        {
          id: 'speed-test',
          title: 'Run Speed Test',
          description: 'Test your current internet speed',
          action: 'Run speed test from this device'
        },
        {
          id: 'restart-modem',
          title: 'Restart Your Modem',
          description: 'Unplug your modem for 30 seconds, then plug it back in',
          action: 'Power cycle modem'
        },
        {
          id: 'restart-router',
          title: 'Restart Your Router',
          description: 'If you have a separate router, restart it too',
          action: 'Power cycle router'
        },
        {
          id: 'check-connections',
          title: 'Check Connections',
          description: 'Ensure all cables are securely connected',
          action: 'Verify physical connections'
        },
        {
          id: 'test-devices',
          title: 'Test Multiple Devices',
          description: 'Check if the issue affects all devices or just one',
          action: 'Test speed on different devices'
        }
      ]
    },
    {
      id: 'no-internet',
      title: 'No Internet Connection',
      description: 'You cannot connect to the internet at all',
      icon: WifiOff,
      estimatedTime: '10-15 minutes',
      steps: [
        {
          id: 'check-lights',
          title: 'Check Modem Status Lights',
          description: 'Look at the lights on your modem - they should be solid green',
          action: 'Inspect modem LED indicators'
        },
        {
          id: 'check-cables',
          title: 'Verify Cable Connections',
          description: 'Ensure all cables are properly connected and undamaged',
          action: 'Check all physical connections'
        },
        {
          id: 'power-cycle',
          title: 'Power Cycle Equipment',
          description: 'Unplug modem and router for 2 minutes, then plug back in',
          action: 'Full equipment restart'
        },
        {
          id: 'direct-connection',
          title: 'Test Direct Connection',
          description: 'Connect directly to modem with ethernet cable',
          action: 'Bypass router connection'
        },
        {
          id: 'check-service-status',
          title: 'Check Service Status',
          description: 'Verify if there are any service outages in your area',
          action: 'Review service status'
        }
      ]
    },
    {
      id: 'wifi-issues',
      title: 'WiFi Connection Problems',
      description: 'Issues connecting to or staying connected to WiFi',
      icon: Router,
      estimatedTime: '8-12 minutes',
      steps: [
        {
          id: 'check-wifi-name',
          title: 'Verify Network Name',
          description: 'Make sure you are connecting to the correct WiFi network',
          action: 'Confirm network SSID'
        },
        {
          id: 'check-password',
          title: 'Verify WiFi Password',
          description: 'Ensure you are entering the correct WiFi password',
          action: 'Confirm network password'
        },
        {
          id: 'forget-reconnect',
          title: 'Forget and Reconnect',
          description: 'Remove the network from your device and reconnect',
          action: 'Reset network connection'
        },
        {
          id: 'router-placement',
          title: 'Check Router Placement',
          description: 'Ensure router is in a central, elevated location',
          action: 'Optimize router position'
        },
        {
          id: 'restart-router-wifi',
          title: 'Restart Router',
          description: 'Power cycle your router to refresh the WiFi connection',
          action: 'Restart wireless router'
        }
      ]
    },
    {
      id: 'phone-issues',
      title: 'Phone Service Problems',
      description: 'Issues with your phone service',
      icon: Phone,
      estimatedTime: '5-8 minutes',
      steps: [
        {
          id: 'check-dial-tone',
          title: 'Check for Dial Tone',
          description: 'Pick up your phone and listen for a dial tone',
          action: 'Test dial tone'
        },
        {
          id: 'check-phone-cables',
          title: 'Check Phone Connections',
          description: 'Ensure phone cables are properly connected to adapter',
          action: 'Verify phone line connections'
        },
        {
          id: 'test-different-phone',
          title: 'Try Different Phone',
          description: 'Test with a different phone to isolate the issue',
          action: 'Test alternate phone device'
        },
        {
          id: 'restart-phone-adapter',
          title: 'Restart Phone Adapter',
          description: 'Unplug and replug your phone adapter',
          action: 'Power cycle phone adapter'
        }
      ]
    }
  ];

  const mockDiagnosticResults: DiagnosticResult[] = [
    {
      name: 'Internet Speed Test',
      status: 'warning',
      message: 'Download: 45 Mbps, Upload: 38 Mbps (Expected: 100/100 Mbps)',
      action: 'Speed is below expected. Continue troubleshooting.'
    },
    {
      name: 'Modem Connection',
      status: 'pass',
      message: 'Modem is online and receiving signal',
    },
    {
      name: 'Router Status',
      status: 'fail',
      message: 'Router may need restart - high error rate detected',
      action: 'Restart your router to resolve connection issues'
    },
    {
      name: 'DNS Resolution',
      status: 'pass',
      message: 'DNS servers responding normally',
    },
    {
      name: 'Network Congestion',
      status: 'warning',
      message: 'Moderate network usage detected in your area',
      action: 'Performance may improve during off-peak hours'
    }
  ];

  const handleStartFlow = (flowId: string) => {
    setActiveFlow(flowId);
    setCurrentStep(0);
    setDiagnosticResults([]);
  };

  const handleCompleteStep = (success: boolean) => {
    const flow = troubleshootingFlows.find(f => f.id === activeFlow);
    if (!flow) return;

    if (success) {
      // If this step resolved the issue, mark as complete
      setActiveFlow(null);
      setCurrentStep(0);
    } else if (currentStep < flow.steps.length - 1) {
      // Move to next step
      setCurrentStep(prev => prev + 1);
    } else {
      // All steps completed without resolution - offer escalation
      setCurrentStep(-1); // Special state for escalation
    }
  };

  const handleRunDiagnostics = () => {
    setIsRunningDiagnostics(true);
    
    // Simulate diagnostic process
    setTimeout(() => {
      setDiagnosticResults(mockDiagnosticResults);
      setIsRunningDiagnostics(false);
    }, 3000);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'fail':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  if (activeFlow) {
    const flow = troubleshootingFlows.find(f => f.id === activeFlow);
    if (!flow) return null;

    const currentStepData = flow.steps[currentStep];

    if (currentStep === -1) {
      // Escalation screen
      return (
        <Card className="p-8 text-center">
          <HelpCircle className="mx-auto h-16 w-16 text-blue-600 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Need Additional Help?
          </h2>
          <p className="text-gray-600 mb-8">
            We've completed all troubleshooting steps. Let's get you connected with our support team.
          </p>
          
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3 mb-8">
            <button className="flex flex-col items-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50">
              <MessageSquare className="h-8 w-8 text-blue-600 mb-2" />
              <span className="font-medium">Live Chat</span>
              <span className="text-gray-500 text-sm">Usually &lt; 2 min</span>
            </button>
            
            <button className="flex flex-col items-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50">
              <Phone className="h-8 w-8 text-green-600 mb-2" />
              <span className="font-medium">Phone Support</span>
              <span className="text-gray-500 text-sm">Call (555) 123-4567</span>
            </button>
            
            <button className="flex flex-col items-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50">
              <Calendar className="h-8 w-8 text-purple-600 mb-2" />
              <span className="font-medium">Schedule Visit</span>
              <span className="text-gray-500 text-sm">Technician visit</span>
            </button>
          </div>
          
          <button
            onClick={() => setActiveFlow(null)}
            className="text-blue-600 hover:text-blue-700"
          >
            ← Back to Troubleshooting
          </button>
        </Card>
      );
    }

    return (
      <div className="space-y-6">
        {/* Progress Header */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => setActiveFlow(null)}
              className="text-blue-600 hover:text-blue-700"
            >
              ← Back to Issues
            </button>
            <span className="text-gray-600 text-sm">
              Step {currentStep + 1} of {flow.steps.length}
            </span>
          </div>
          
          <h2 className="text-xl font-semibold text-gray-900 mb-2">{flow.title}</h2>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / flow.steps.length) * 100}%` }}
            />
          </div>
        </Card>

        {/* Current Step */}
        <Card className="p-6">
          <div className="flex items-start mb-6">
            <div className="flex-shrink-0">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100">
                <span className="font-medium text-blue-600">{currentStep + 1}</span>
              </div>
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {currentStepData.title}
              </h3>
              <p className="text-gray-600 mt-1">{currentStepData.description}</p>
              {currentStepData.action && (
                <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                  <p className="text-blue-800 text-sm font-medium">
                    Action: {currentStepData.action}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="flex space-x-4">
            <button
              onClick={() => handleCompleteStep(true)}
              className="flex-1 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 font-medium"
            >
              This Fixed the Issue!
            </button>
            <button
              onClick={() => handleCompleteStep(false)}
              className="flex-1 border border-gray-300 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-50 font-medium"
            >
              Issue Still Exists
            </button>
          </div>
        </Card>

        {/* Previous Steps */}
        {currentStep > 0 && (
          <Card className="p-6">
            <h4 className="font-medium text-gray-900 mb-4">Completed Steps</h4>
            <div className="space-y-3">
              {flow.steps.slice(0, currentStep).map((step, index) => (
                <div key={step.id} className="flex items-center">
                  <CheckCircle className="h-5 w-5 text-green-600 mr-3" />
                  <span className="text-gray-600">{step.title}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Self-Service Troubleshooting</h1>
        <p className="text-gray-600">Resolve common issues quickly on your own</p>
      </div>

      {/* Quick Diagnostics */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Quick System Diagnostics</h3>
            <p className="text-gray-600 text-sm">
              Run automated tests to identify potential issues
            </p>
          </div>
          <button
            onClick={handleRunDiagnostics}
            disabled={isRunningDiagnostics}
            className="flex items-center bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isRunningDiagnostics ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Running Tests...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Diagnostics
              </>
            )}
          </button>
        </div>

        {isRunningDiagnostics && (
          <div className="space-y-2">
            <div className="flex items-center text-gray-600 text-sm">
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
              Testing internet connection...
            </div>
          </div>
        )}

        {diagnosticResults.length > 0 && (
          <div className="space-y-3 mt-4">
            <h4 className="font-medium text-gray-900">Diagnostic Results</h4>
            {diagnosticResults.map((result, index) => (
              <div key={index} className="flex items-start p-3 border rounded-lg">
                <div className="mr-3 mt-0.5">
                  {getStatusIcon(result.status)}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{result.name}</p>
                  <p className="text-gray-600 text-sm">{result.message}</p>
                  {result.action && (
                    <p className="text-blue-600 text-sm mt-1 font-medium">
                      {result.action}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Common Issues */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Your Issue</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {troubleshootingFlows.map((flow) => {
            const Icon = flow.icon;
            return (
              <Card key={flow.id} className="p-6 hover:shadow-md transition-shadow cursor-pointer">
                <button
                  onClick={() => handleStartFlow(flow.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start">
                      <Icon className="h-8 w-8 text-blue-600 mr-4 mt-1" />
                      <div>
                        <h4 className="font-semibold text-gray-900 mb-2">{flow.title}</h4>
                        <p className="text-gray-600 text-sm mb-3">{flow.description}</p>
                        <div className="flex items-center text-gray-500 text-xs">
                          <Clock className="mr-1 h-3 w-3" />
                          {flow.estimatedTime}
                        </div>
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400 mt-2" />
                  </div>
                </button>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Quick Actions */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <button className="flex flex-col items-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50">
            <Zap className="h-6 w-6 text-yellow-600 mb-2" />
            <span className="text-sm font-medium">Speed Test</span>
          </button>
          
          <button className="flex flex-col items-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50">
            <Network className="h-6 w-6 text-blue-600 mb-2" />
            <span className="text-sm font-medium">Network Status</span>
          </button>
          
          <button className="flex flex-col items-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50">
            <Settings className="h-6 w-6 text-gray-600 mb-2" />
            <span className="text-sm font-medium">Equipment Reset</span>
          </button>
          
          <button className="flex flex-col items-center p-4 border border-gray-300 rounded-lg hover:bg-gray-50">
            <Activity className="h-6 w-6 text-green-600 mb-2" />
            <span className="text-sm font-medium">Service Health</span>
          </button>
        </div>
      </Card>

      {/* Still Need Help */}
      <Card className="p-6 bg-gray-50">
        <div className="text-center">
          <HelpCircle className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Still Need Help?
          </h3>
          <p className="text-gray-600 mb-6">
            Can't find what you're looking for? Our support team is here to help.
          </p>
          
          <div className="flex justify-center space-x-4">
            <button className="flex items-center bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
              <MessageSquare className="mr-2 h-4 w-4" />
              Live Chat
            </button>
            <button className="flex items-center border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-white">
              <Phone className="mr-2 h-4 w-4" />
              Call Support
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
}