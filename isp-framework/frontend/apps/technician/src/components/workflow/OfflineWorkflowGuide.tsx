'use client';

import { useState, useEffect } from 'react';
import {
  Wifi,
  WifiOff,
  CheckCircle,
  Clock,
  AlertTriangle,
  Download,
  Upload,
  Battery,
  Signal,
  MapPin,
  Camera,
  FileText,
  Phone,
  Settings,
  RefreshCw,
  Smartphone,
  HardDrive,
  CloudOff,
  Cloud,
  Info,
  ChevronRight,
  ChevronDown,
  Play,
  Pause
} from 'lucide-react';

interface WorkflowStep {
  id: string;
  title: string;
  description: string;
  type: 'info' | 'action' | 'verification' | 'documentation';
  offline_capable: boolean;
  required_connectivity?: 'none' | 'low' | 'high';
  estimated_time: number; // minutes
  guidance: string[];
  dependencies?: string[];
  data_collection?: {
    photos?: boolean;
    notes?: boolean;
    measurements?: boolean;
    signatures?: boolean;
  };
}

interface OfflineCapability {
  feature: string;
  available_offline: boolean;
  data_sync_required: boolean;
  storage_used: string;
  description: string;
}

interface ConnectivityStatus {
  online: boolean;
  connection_type: 'wifi' | 'cellular' | 'none';
  signal_strength: 'excellent' | 'good' | 'poor' | 'none';
  battery_level: number;
  storage_available: string;
  sync_pending: number;
}

export function OfflineWorkflowGuide() {
  const [activeWorkflow, setActiveWorkflow] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [connectivityStatus, setConnectivityStatus] = useState<ConnectivityStatus>({
    online: navigator.onLine,
    connection_type: 'wifi',
    signal_strength: 'good',
    battery_level: 85,
    storage_available: '2.3 GB',
    sync_pending: 3
  });

  // Mock workflow data
  const workflowSteps: Record<string, WorkflowStep[]> = {
    'installation': [
      {
        id: 'prep',
        title: 'Pre-Installation Preparation',
        description: 'Verify equipment and customer information',
        type: 'verification',
        offline_capable: true,
        required_connectivity: 'none',
        estimated_time: 10,
        guidance: [
          'Check equipment inventory against work order',
          'Verify customer contact information',
          'Review installation notes and special instructions',
          'Take photos of equipment before installation'
        ],
        data_collection: { photos: true, notes: true }
      },
      {
        id: 'site_survey',
        title: 'Site Survey and Assessment',
        description: 'Assess installation location and requirements',
        type: 'action',
        offline_capable: true,
        required_connectivity: 'none',
        estimated_time: 15,
        guidance: [
          'Identify optimal equipment placement location',
          'Check for power outlets and accessibility',
          'Document any obstacles or special requirements',
          'Measure cable runs if needed',
          'Take photos of installation area'
        ],
        data_collection: { photos: true, notes: true, measurements: true }
      },
      {
        id: 'installation',
        title: 'Equipment Installation',
        description: 'Install and connect equipment',
        type: 'action',
        offline_capable: true,
        required_connectivity: 'low',
        estimated_time: 45,
        guidance: [
          'Install equipment according to technical specifications',
          'Connect all cables and verify connections',
          'Document serial numbers and configuration',
          'Take photos of completed installation',
          'Perform basic connectivity tests'
        ],
        data_collection: { photos: true, notes: true }
      },
      {
        id: 'testing',
        title: 'Service Testing and Activation',
        description: 'Test service functionality and activate',
        type: 'verification',
        offline_capable: false,
        required_connectivity: 'high',
        estimated_time: 20,
        guidance: [
          'Connect to service network and test connectivity',
          'Verify internet speeds meet service requirements',
          'Test all service features with customer',
          'Activate customer account if needed',
          'Document test results'
        ],
        dependencies: ['installation'],
        data_collection: { notes: true }
      },
      {
        id: 'completion',
        title: 'Customer Walkthrough and Completion',
        description: 'Complete installation and get customer sign-off',
        type: 'documentation',
        offline_capable: true,
        required_connectivity: 'low',
        estimated_time: 15,
        guidance: [
          'Walk customer through service features',
          'Provide customer with equipment information',
          'Complete installation checklist',
          'Obtain customer signature',
          'Schedule any follow-up if needed'
        ],
        data_collection: { signatures: true, notes: true }
      }
    ],
    'repair': [
      {
        id: 'diagnosis',
        title: 'Issue Diagnosis',
        description: 'Identify and diagnose the service issue',
        type: 'verification',
        offline_capable: true,
        required_connectivity: 'low',
        estimated_time: 20,
        guidance: [
          'Interview customer about the issue',
          'Check equipment status lights and connections',
          'Run basic diagnostic tests',
          'Document symptoms and observations',
          'Take photos of any visible issues'
        ],
        data_collection: { photos: true, notes: true }
      },
      {
        id: 'troubleshooting',
        title: 'Troubleshooting Steps',
        description: 'Follow systematic troubleshooting process',
        type: 'action',
        offline_capable: true,
        required_connectivity: 'none',
        estimated_time: 30,
        guidance: [
          'Check all physical connections',
          'Test signal levels at different points',
          'Replace suspected faulty components',
          'Document all actions taken',
          'Take before/after photos'
        ],
        data_collection: { photos: true, notes: true, measurements: true }
      },
      {
        id: 'resolution',
        title: 'Issue Resolution and Testing',
        description: 'Resolve issue and verify fix',
        type: 'verification',
        offline_capable: false,
        required_connectivity: 'high',
        estimated_time: 15,
        guidance: [
          'Apply the identified solution',
          'Test service functionality thoroughly',
          'Verify customer satisfaction with resolution',
          'Document final resolution',
          'Update service records'
        ],
        dependencies: ['troubleshooting'],
        data_collection: { notes: true }
      }
    ]
  };

  const offlineCapabilities: OfflineCapability[] = [
    {
      feature: 'Work Order Access',
      available_offline: true,
      data_sync_required: false,
      storage_used: '45 MB',
      description: 'View and manage assigned work orders without internet'
    },
    {
      feature: 'Photo Capture',
      available_offline: true,
      data_sync_required: true,
      storage_used: '120 MB',
      description: 'Take and store photos, sync when connection available'
    },
    {
      feature: 'Notes and Documentation',
      available_offline: true,
      data_sync_required: true,
      storage_used: '12 MB',
      description: 'Add notes and fill forms, sync changes later'
    },
    {
      feature: 'Customer Signatures',
      available_offline: true,
      data_sync_required: true,
      storage_used: '8 MB',
      description: 'Capture digital signatures for completion'
    },
    {
      feature: 'Equipment Database',
      available_offline: true,
      data_sync_required: false,
      storage_used: '78 MB',
      description: 'Access equipment manuals and specifications'
    },
    {
      feature: 'Service Activation',
      available_offline: false,
      data_sync_required: false,
      storage_used: '0 MB',
      description: 'Requires live connection to activate services'
    },
    {
      feature: 'Real-time Support Chat',
      available_offline: false,
      data_sync_required: false,
      storage_used: '0 MB',
      description: 'Live communication with support team'
    }
  ];

  useEffect(() => {
    const handleOnlineStatus = () => {
      setConnectivityStatus(prev => ({
        ...prev,
        online: navigator.onLine
      }));
    };

    window.addEventListener('online', handleOnlineStatus);
    window.addEventListener('offline', handleOnlineStatus);

    // Mock battery API
    const updateBattery = () => {
      if ('getBattery' in navigator) {
        (navigator as any).getBattery().then((battery: any) => {
          setConnectivityStatus(prev => ({
            ...prev,
            battery_level: Math.round(battery.level * 100)
          }));
        });
      }
    };

    updateBattery();
    const batteryInterval = setInterval(updateBattery, 30000);

    return () => {
      window.removeEventListener('online', handleOnlineStatus);
      window.removeEventListener('offline', handleOnlineStatus);
      clearInterval(batteryInterval);
    };
  }, []);

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const getConnectivityIcon = () => {
    if (!connectivityStatus.online) return <WifiOff className="h-4 w-4 text-red-500" />;
    
    switch (connectivityStatus.signal_strength) {
      case 'excellent':
        return <Wifi className="h-4 w-4 text-green-500" />;
      case 'good':
        return <Signal className="h-4 w-4 text-green-500" />;
      case 'poor':
        return <Signal className="h-4 w-4 text-yellow-500" />;
      default:
        return <WifiOff className="h-4 w-4 text-red-500" />;
    }
  };

  const getStepIcon = (step: WorkflowStep) => {
    switch (step.type) {
      case 'info':
        return <Info className="h-4 w-4 text-blue-500" />;
      case 'action':
        return <Settings className="h-4 w-4 text-orange-500" />;
      case 'verification':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'documentation':
        return <FileText className="h-4 w-4 text-purple-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <div className="space-y-6 p-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Offline Workflow Guide</h1>
        <p className="text-gray-600">Work efficiently with or without internet connection</p>
      </div>

      {/* Connectivity Status */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">System Status</h3>
          {connectivityStatus.online ? (
            <div className="flex items-center text-green-600">
              <Cloud className="h-4 w-4 mr-1" />
              <span className="text-sm font-medium">Online</span>
            </div>
          ) : (
            <div className="flex items-center text-red-600">
              <CloudOff className="h-4 w-4 mr-1" />
              <span className="text-sm font-medium">Offline</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center space-x-2">
            {getConnectivityIcon()}
            <div>
              <p className="text-sm font-medium text-gray-900">Connection</p>
              <p className="text-xs text-gray-600">
                {connectivityStatus.online ? connectivityStatus.connection_type : 'Offline'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Battery className="h-4 w-4 text-green-500" />
            <div>
              <p className="text-sm font-medium text-gray-900">Battery</p>
              <p className="text-xs text-gray-600">{connectivityStatus.battery_level}%</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <HardDrive className="h-4 w-4 text-blue-500" />
            <div>
              <p className="text-sm font-medium text-gray-900">Storage</p>
              <p className="text-xs text-gray-600">{connectivityStatus.storage_available} free</p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <RefreshCw className="h-4 w-4 text-orange-500" />
            <div>
              <p className="text-sm font-medium text-gray-900">Pending Sync</p>
              <p className="text-xs text-gray-600">{connectivityStatus.sync_pending} items</p>
            </div>
          </div>
        </div>

        {!connectivityStatus.online && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start">
              <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" />
              <div className="text-sm">
                <p className="font-medium text-yellow-800">Limited Connectivity</p>
                <p className="text-yellow-700 mt-1">
                  Some features require internet connection. Data will sync when connection is restored.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Workflow Selection */}
      <div className="bg-white rounded-lg border p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Workflow Guides</h3>
        
        <div className="space-y-3">
          {Object.entries(workflowSteps).map(([workflowId, steps]) => (
            <div key={workflowId} className="border rounded-lg">
              <button
                onClick={() => setActiveWorkflow(activeWorkflow === workflowId ? null : workflowId)}
                className="w-full p-4 text-left flex items-center justify-between hover:bg-gray-50"
              >
                <div>
                  <h4 className="font-medium text-gray-900 capitalize">
                    {workflowId.replace('_', ' ')} Workflow
                  </h4>
                  <p className="text-sm text-gray-600">
                    {steps.length} steps • {steps.reduce((acc, step) => acc + step.estimated_time, 0)} min estimated
                  </p>
                </div>
                {activeWorkflow === workflowId ? (
                  <ChevronDown className="h-4 w-4 text-gray-400" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-gray-400" />
                )}
              </button>

              {activeWorkflow === workflowId && (
                <div className="border-t">
                  {steps.map((step, index) => (
                    <div key={step.id} className="p-4 border-b last:border-b-0">
                      <div className="flex items-start space-x-3">
                        <div className="flex-shrink-0 mt-1">
                          {getStepIcon(step)}
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h5 className="font-medium text-gray-900">{step.title}</h5>
                              <p className="text-sm text-gray-600 mt-1">{step.description}</p>
                            </div>
                            
                            <div className="flex items-center space-x-2 ml-4">
                              <span className="text-xs text-gray-500">
                                {step.estimated_time}m
                              </span>
                              {step.offline_capable ? (
                                <CheckCircle className="h-3 w-3 text-green-500" title="Works offline" />
                              ) : (
                                <WifiOff className="h-3 w-3 text-red-500" title="Requires internet" />
                              )}
                            </div>
                          </div>

                          {/* Connectivity Requirements */}
                          {step.required_connectivity && step.required_connectivity !== 'none' && (
                            <div className="mt-2">
                              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                step.required_connectivity === 'high' 
                                  ? 'bg-red-50 text-red-700'
                                  : 'bg-yellow-50 text-yellow-700'
                              }`}>
                                {step.required_connectivity === 'high' ? 'High' : 'Low'} connectivity required
                              </span>
                            </div>
                          )}

                          {/* Offline Warning */}
                          {!step.offline_capable && !connectivityStatus.online && (
                            <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded-lg">
                              <div className="flex items-center text-red-700 text-xs">
                                <AlertTriangle className="h-3 w-3 mr-1" />
                                <span>This step requires internet connection</span>
                              </div>
                            </div>
                          )}

                          {/* Guidance */}
                          <button
                            onClick={() => toggleSection(`${step.id}-guidance`)}
                            className="mt-3 flex items-center text-blue-600 text-sm hover:text-blue-700"
                          >
                            <Play className="h-3 w-3 mr-1" />
                            Show Step Guidance
                            {expandedSections.has(`${step.id}-guidance`) ? (
                              <ChevronDown className="h-3 w-3 ml-1" />
                            ) : (
                              <ChevronRight className="h-3 w-3 ml-1" />
                            )}
                          </button>

                          {expandedSections.has(`${step.id}-guidance`) && (
                            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
                              <ul className="space-y-2">
                                {step.guidance.map((guidance, idx) => (
                                  <li key={idx} className="flex items-start text-sm text-blue-900">
                                    <div className="w-4 h-4 rounded-full bg-blue-200 flex items-center justify-center mr-2 mt-0.5 flex-shrink-0">
                                      <span className="text-xs font-bold text-blue-800">{idx + 1}</span>
                                    </div>
                                    {guidance}
                                  </li>
                                ))}
                              </ul>

                              {step.data_collection && (
                                <div className="mt-3 pt-3 border-t border-blue-200">
                                  <p className="text-sm font-medium text-blue-900 mb-2">Data Collection:</p>
                                  <div className="flex flex-wrap gap-2">
                                    {step.data_collection.photos && (
                                      <span className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                                        <Camera className="h-3 w-3 mr-1" />
                                        Photos
                                      </span>
                                    )}
                                    {step.data_collection.notes && (
                                      <span className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                                        <FileText className="h-3 w-3 mr-1" />
                                        Notes
                                      </span>
                                    )}
                                    {step.data_collection.signatures && (
                                      <span className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                                        <Smartphone className="h-3 w-3 mr-1" />
                                        Signature
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Offline Capabilities */}
      <div className="bg-white rounded-lg border p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Offline Capabilities</h3>
        
        <div className="space-y-3">
          {offlineCapabilities.map((capability, index) => (
            <div key={index} className="flex items-start justify-between p-3 border rounded-lg">
              <div className="flex items-start space-x-3">
                <div className="mt-1">
                  {capability.available_offline ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <WifiOff className="h-4 w-4 text-red-500" />
                  )}
                </div>
                <div>
                  <h4 className="font-medium text-gray-900">{capability.feature}</h4>
                  <p className="text-sm text-gray-600">{capability.description}</p>
                  <div className="flex items-center space-x-4 mt-1">
                    <span className="text-xs text-gray-500">
                      Storage: {capability.storage_used}
                    </span>
                    {capability.data_sync_required && (
                      <span className="text-xs text-orange-600">
                        Sync required
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg border p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        
        <div className="grid grid-cols-2 gap-3">
          <button className="flex items-center justify-center p-3 border border-gray-300 rounded-lg hover:bg-gray-50">
            <Download className="h-4 w-4 text-blue-600 mr-2" />
            <span className="text-sm font-medium">Sync Data</span>
          </button>
          
          <button className="flex items-center justify-center p-3 border border-gray-300 rounded-lg hover:bg-gray-50">
            <Camera className="h-4 w-4 text-green-600 mr-2" />
            <span className="text-sm font-medium">Take Photo</span>
          </button>
          
          <button className="flex items-center justify-center p-3 border border-gray-300 rounded-lg hover:bg-gray-50">
            <MapPin className="h-4 w-4 text-purple-600 mr-2" />
            <span className="text-sm font-medium">Get Location</span>
          </button>
          
          <button className="flex items-center justify-center p-3 border border-gray-300 rounded-lg hover:bg-gray-50">
            <Phone className="h-4 w-4 text-red-600 mr-2" />
            <span className="text-sm font-medium">Call Support</span>
          </button>
        </div>
      </div>
    </div>
  );
}