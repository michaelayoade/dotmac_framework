'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { WorkflowRunner, useWorkflow } from '@dotmac/workflows-system';
import type { WorkflowDefinition } from '@dotmac/workflows-system';
import { Button } from '@dotmac/primitives';
import {
  MapPin,
  Wrench,
  CheckCircle,
  Globe,
  User,
  Wifi,
  Zap,
  Calendar,
  DollarSign
} from 'lucide-react';

interface ServiceProvisioningWorkflowProps {
  onComplete?: (result: any) => void;
  onCancel?: () => void;
  requestId?: string;
  customerInfo?: {
    name: string;
    email: string;
    address: string;
  };
  serviceType?: 'residential_fiber' | 'business_fiber' | 'enterprise_dedicated' | 'bulk_service';
  className?: string;
}

const serviceProvisioningDefinition: WorkflowDefinition = {
  id: 'service_provisioning',
  name: 'Service Provisioning',
  description: 'Complete service provisioning workflow for new customer installations',
  version: '1.0.0',
  category: 'provisioning',
  steps: [
    {
      id: 'site_survey',
      name: 'Site Survey',
      description: 'Conduct site survey and assess installation requirements',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            surveyDate: {
              type: 'string',
              title: 'Survey Date',
              format: 'date',
              description: 'When was the site survey conducted?'
            },
            accessType: {
              type: 'string',
              title: 'Access Type',
              enum: ['aerial', 'underground', 'building_entry'],
              enumNames: ['Aerial', 'Underground', 'Building Entry']
            },
            installationPath: {
              type: 'string',
              title: 'Installation Path',
              enum: ['clear', 'minor_obstacles', 'major_obstacles'],
              enumNames: ['Clear Path', 'Minor Obstacles', 'Major Obstacles']
            },
            permitsRequired: {
              type: 'array',
              title: 'Permits Required',
              items: {
                type: 'string',
                enum: ['city_permit', 'hoa_approval', 'utility_locates', 'tree_removal', 'sidewalk_boring']
              },
              uniqueItems: true
            },
            estimatedInstallTime: {
              type: 'number',
              title: 'Estimated Install Time (hours)',
              minimum: 1,
              maximum: 80
            },
            specialRequirements: {
              type: 'string',
              title: 'Special Requirements',
              description: 'Any special equipment or considerations needed',
              format: 'textarea',
              maxLength: 1000
            },
            sitePhotos: {
              type: 'boolean',
              title: 'Site photos captured',
              description: 'Confirm that site photos have been taken and uploaded'
            }
          },
          required: ['surveyDate', 'accessType', 'installationPath', 'estimatedInstallTime', 'sitePhotos']
        },
        layout: 'two-column',
        sections: [
          {
            title: 'Survey Details',
            description: 'Basic survey information',
            fields: ['surveyDate', 'accessType', 'installationPath', 'sitePhotos']
          },
          {
            title: 'Requirements Assessment',
            description: 'Installation requirements and permits',
            fields: ['permitsRequired', 'estimatedInstallTime', 'specialRequirements']
          }
        ]
      },
      canSkip: false,
      timeout: 1800000 // 30 minutes
    },
    {
      id: 'permits_approvals',
      name: 'Permits & Approvals',
      description: 'Obtain necessary permits and approvals',
      type: 'approval',
      input: {
        policy: 'all',
        approvers: ['permit_coordinator', 'field_supervisor'],
        message: 'Please review and approve the permit applications for this service installation.',
        timeout: 172800000, // 48 hours
        allowDelegation: true
      },
      canSkip: false
    },
    {
      id: 'equipment_staging',
      name: 'Equipment Staging',
      description: 'Stage equipment and materials for installation',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            equipmentList: {
              type: 'array',
              title: 'Equipment Required',
              items: {
                type: 'string',
                enum: [
                  'ont_device',
                  'fiber_cable',
                  'splitter',
                  'patch_panel',
                  'router_residential',
                  'router_business',
                  'router_enterprise',
                  'power_supply',
                  'mounting_hardware',
                  'weatherproof_enclosure'
                ]
              },
              uniqueItems: true
            },
            stagingLocation: {
              type: 'string',
              title: 'Staging Location',
              enum: ['warehouse_main', 'truck_inventory', 'field_office', 'customer_site'],
              enumNames: ['Main Warehouse', 'Truck Inventory', 'Field Office', 'Customer Site']
            },
            inventoryVerified: {
              type: 'boolean',
              title: 'Inventory Verified',
              description: 'All equipment has been verified and is in good condition'
            },
            qualityCheck: {
              type: 'boolean',
              title: 'Quality Check Complete',
              description: 'Equipment has passed quality inspection'
            },
            serialNumbers: {
              type: 'string',
              title: 'Serial Numbers',
              description: 'Record serial numbers of key equipment (ONT, Router, etc.)',
              format: 'textarea',
              maxLength: 500
            }
          },
          required: ['equipmentList', 'stagingLocation', 'inventoryVerified', 'qualityCheck']
        },
        layout: 'single-column'
      },
      canSkip: false
    },
    {
      id: 'schedule_installation',
      name: 'Schedule Installation',
      description: 'Schedule installation appointment with customer',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            installationDate: {
              type: 'string',
              title: 'Installation Date',
              format: 'date',
              description: 'Scheduled installation date'
            },
            timeSlot: {
              type: 'string',
              title: 'Time Slot',
              enum: ['morning', 'afternoon', 'all_day'],
              enumNames: ['Morning (8 AM - 12 PM)', 'Afternoon (1 PM - 5 PM)', 'All Day']
            },
            assignedTechnician: {
              type: 'string',
              title: 'Assigned Technician',
              description: 'Primary technician for this installation'
            },
            backupTechnician: {
              type: 'string',
              title: 'Backup Technician',
              description: 'Backup technician if primary is unavailable'
            },
            customerContacted: {
              type: 'boolean',
              title: 'Customer Contacted',
              description: 'Customer has been contacted and confirmed the appointment'
            },
            customerInstructions: {
              type: 'string',
              title: 'Customer Instructions',
              description: 'Special instructions for the customer (access, parking, etc.)',
              format: 'textarea',
              maxLength: 500
            },
            weatherContingency: {
              type: 'string',
              title: 'Weather Contingency Plan',
              enum: ['proceed', 'reschedule', 'partial_indoor'],
              enumNames: ['Proceed Regardless', 'Reschedule if Bad Weather', 'Indoor Work Only if Weather is Bad']
            }
          },
          required: ['installationDate', 'timeSlot', 'assignedTechnician', 'customerContacted']
        },
        layout: 'two-column'
      },
      canSkip: false
    },
    {
      id: 'installation_execution',
      name: 'Installation Execution',
      description: 'Execute the service installation',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            arrivalTime: {
              type: 'string',
              title: 'Arrival Time',
              format: 'time',
              description: 'What time did the technician arrive?'
            },
            installationSteps: {
              type: 'array',
              title: 'Installation Steps Completed',
              items: {
                type: 'string',
                enum: [
                  'fiber_drop_installed',
                  'ont_mounted',
                  'ont_powered',
                  'fiber_terminated',
                  'ont_provisioned',
                  'router_installed',
                  'network_configured',
                  'speed_test_passed',
                  'customer_training',
                  'area_cleaned'
                ]
              },
              uniqueItems: true
            },
            speedTestResults: {
              type: 'object',
              title: 'Speed Test Results',
              properties: {
                downloadSpeed: {
                  type: 'number',
                  title: 'Download Speed (Mbps)',
                  minimum: 0
                },
                uploadSpeed: {
                  type: 'number',
                  title: 'Upload Speed (Mbps)',
                  minimum: 0
                },
                latency: {
                  type: 'number',
                  title: 'Latency (ms)',
                  minimum: 0
                }
              },
              required: ['downloadSpeed', 'uploadSpeed', 'latency']
            },
            customerSignature: {
              type: 'boolean',
              title: 'Customer Signature Obtained',
              description: 'Customer has signed off on the completed installation'
            },
            issuesEncountered: {
              type: 'string',
              title: 'Issues Encountered',
              description: 'Any issues or complications during installation',
              format: 'textarea',
              maxLength: 1000
            },
            completionTime: {
              type: 'string',
              title: 'Completion Time',
              format: 'time',
              description: 'What time was the installation completed?'
            }
          },
          required: ['arrivalTime', 'installationSteps', 'speedTestResults', 'customerSignature', 'completionTime']
        },
        layout: 'single-column'
      },
      canSkip: false
    },
    {
      id: 'service_activation',
      name: 'Service Activation',
      description: 'Activate service in billing and monitoring systems',
      type: 'api_call',
      input: {
        url: '/api/provisioning/activate-service',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        timeout: 30000
      },
      canSkip: false
    },
    {
      id: 'quality_assurance',
      name: 'Quality Assurance',
      description: 'Final quality check and customer follow-up',
      type: 'form',
      input: {
        schema: {
          type: 'object',
          properties: {
            serviceStatus: {
              type: 'string',
              title: 'Service Status',
              enum: ['active', 'active_with_issues', 'failed_activation'],
              enumNames: ['Active - No Issues', 'Active - Minor Issues', 'Failed Activation']
            },
            customerSatisfaction: {
              type: 'string',
              title: 'Customer Satisfaction',
              enum: ['very_satisfied', 'satisfied', 'neutral', 'dissatisfied', 'very_dissatisfied'],
              enumNames: ['Very Satisfied', 'Satisfied', 'Neutral', 'Dissatisfied', 'Very Dissatisfied']
            },
            followUpRequired: {
              type: 'boolean',
              title: 'Follow-up Required',
              description: 'Does this installation require follow-up?'
            },
            followUpNotes: {
              type: 'string',
              title: 'Follow-up Notes',
              description: 'Notes for follow-up activities',
              format: 'textarea',
              maxLength: 500
            },
            warrantyActivated: {
              type: 'boolean',
              title: 'Warranty Activated',
              description: 'Equipment warranty has been activated'
            },
            documentationComplete: {
              type: 'boolean',
              title: 'Documentation Complete',
              description: 'All installation documentation has been completed and filed'
            }
          },
          required: ['serviceStatus', 'customerSatisfaction', 'warrantyActivated', 'documentationComplete']
        },
        layout: 'single-column'
      },
      canSkip: false
    }
  ],
  metadata: {
    estimatedDuration: 14400, // 4 hours
    category: 'service_provisioning',
    priority: 'high',
    tags: ['provisioning', 'installation', 'service_activation']
  }
};

export function ServiceProvisioningWorkflow({
  onComplete,
  onCancel,
  requestId,
  customerInfo,
  serviceType = 'residential_fiber',
  className
}: ServiceProvisioningWorkflowProps) {
  const [isStarted, setIsStarted] = useState(false);

  const {
    start: startWorkflow,
    pause,
    cancel,
    instance,
    isRunning,
    currentStep,
    progress
  } = useWorkflow({
    definition: serviceProvisioningDefinition,
    onComplete: (result) => {
      console.log('Provisioning completed:', result);
      onComplete?.(result);
    },
    onError: (error) => {
      console.error('Provisioning error:', error);
    },
    onStepComplete: (stepId, output) => {
      console.log(`Step ${stepId} completed:`, output);
    },
    context: {
      requestId,
      customerInfo,
      serviceType,
      startedAt: new Date().toISOString()
    }
  });

  const handleStart = () => {
    setIsStarted(true);
    startWorkflow();
  };

  const handleCancel = () => {
    cancel();
    onCancel?.();
  };

  const getServiceTypeInfo = (type: string) => {
    switch (type) {
      case 'residential_fiber':
        return {
          icon: User,
          name: 'Residential Fiber',
          description: 'High-speed fiber internet for homes'
        };
      case 'business_fiber':
        return {
          icon: Globe,
          name: 'Business Fiber',
          description: 'Professional fiber service for businesses'
        };
      case 'enterprise_dedicated':
        return {
          icon: Zap,
          name: 'Enterprise Dedicated',
          description: 'Dedicated enterprise-grade connectivity'
        };
      case 'bulk_service':
        return {
          icon: Wifi,
          name: 'Bulk Service',
          description: 'Multi-unit building service'
        };
      default:
        return {
          icon: Globe,
          name: 'Internet Service',
          description: 'High-speed internet service'
        };
    }
  };

  const serviceInfo = getServiceTypeInfo(serviceType);
  const ServiceIcon = serviceInfo.icon;

  // Welcome screen before starting workflow
  if (!isStarted) {
    return (
      <div className={`provisioning-welcome ${className || ''}`}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="welcome-container max-w-4xl mx-auto p-8"
        >
          <div className="welcome-header text-center mb-8">
            <div className="service-icon mb-6">
              <ServiceIcon className="w-16 h-16 text-blue-600 mx-auto" />
            </div>

            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Service Provisioning Workflow
            </h1>

            <p className="text-lg text-gray-600 mb-4">
              {serviceInfo.name} - {serviceInfo.description}
            </p>

            {customerInfo && (
              <div className="customer-info bg-gray-50 rounded-lg p-4 mb-6">
                <h3 className="font-medium text-gray-900 mb-2">Customer Information</h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p><strong>Name:</strong> {customerInfo.name}</p>
                  <p><strong>Email:</strong> {customerInfo.email}</p>
                  <p><strong>Address:</strong> {customerInfo.address}</p>
                </div>
              </div>
            )}
          </div>

          <div className="workflow-steps mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Provisioning Process</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
                <MapPin className="w-6 h-6 text-blue-600 flex-shrink-0" />
                <div>
                  <div className="font-medium text-sm">Site Survey</div>
                  <div className="text-xs text-gray-600">Assess installation requirements</div>
                </div>
              </div>

              <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
                <CheckCircle className="w-6 h-6 text-blue-600 flex-shrink-0" />
                <div>
                  <div className="font-medium text-sm">Permits & Approvals</div>
                  <div className="text-xs text-gray-600">Obtain necessary approvals</div>
                </div>
              </div>

              <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
                <DollarSign className="w-6 h-6 text-blue-600 flex-shrink-0" />
                <div>
                  <div className="font-medium text-sm">Equipment Staging</div>
                  <div className="text-xs text-gray-600">Prepare installation materials</div>
                </div>
              </div>

              <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
                <Calendar className="w-6 h-6 text-blue-600 flex-shrink-0" />
                <div>
                  <div className="font-medium text-sm">Schedule Installation</div>
                  <div className="text-xs text-gray-600">Coordinate with customer</div>
                </div>
              </div>

              <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
                <Wrench className="w-6 h-6 text-blue-600 flex-shrink-0" />
                <div>
                  <div className="font-medium text-sm">Installation</div>
                  <div className="text-xs text-gray-600">Execute service installation</div>
                </div>
              </div>

              <div className="step-item flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
                <CheckCircle className="w-6 h-6 text-blue-600 flex-shrink-0" />
                <div>
                  <div className="font-medium text-sm">Quality Assurance</div>
                  <div className="text-xs text-gray-600">Final validation and follow-up</div>
                </div>
              </div>
            </div>
          </div>

          <div className="estimated-time text-center mb-8">
            <p className="text-sm text-gray-500">
              Estimated completion time: 2-4 hours (depending on complexity)
            </p>
          </div>

          <div className="action-buttons flex gap-4 justify-center">
            <Button
              onClick={handleStart}
              size="lg"
              className="min-w-40"
            >
              Start Provisioning
            </Button>

            {onCancel && (
              <Button
                onClick={handleCancel}
                variant="outline"
                size="lg"
                className="min-w-32"
              >
                Cancel
              </Button>
            )}
          </div>

          {requestId && (
            <div className="request-id text-center mt-4">
              <p className="text-xs text-gray-400">
                Request ID: {requestId}
              </p>
            </div>
          )}
        </motion.div>
      </div>
    );
  }

  // Show workflow runner when started
  return (
    <div className={`service-provisioning-workflow ${className || ''}`}>
      <WorkflowRunner
        workflowId={instance?.id}
        showProgress={true}
        showStepNavigation={true}
        className="max-w-5xl mx-auto"
        onCancel={handleCancel}
      />
    </div>
  );
}

export default ServiceProvisioningWorkflow;
